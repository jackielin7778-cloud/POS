"""
POS 收銀系統 v1.5.3 - 加強版
新增：匯入匯出功能
"""
import streamlit as st
import pandas as pd
import os
from database import init_db, get_products, add_product, update_product, delete_product
from database import get_members, add_member, create_sale, get_sales, get_daily_sales
from database import get_member_by_phone
import io

init_db()
st.set_page_config(page_title="POS 收銀系統", page_icon="🏪", layout="wide")

if 'cart' not in st.session_state:
    st.session_state.cart = []


def calculate_price_inc_tax(price_ex_tax):
    if not price_ex_tax:
        return 0.0
    try:
        return round(float(price_ex_tax) * 1.05, 1)
    except:
        return 0.0


def calculate_price_ex_tax(price_inc_tax):
    if not price_inc_tax:
        return 0.0
    try:
        price = float(price_inc_tax)
        tax_amount = round(round(price / 21, 1))
        return round(price - tax_amount, 1)
    except:
        return 0.0


with st.sidebar:
    st.title("🏪 POS 系統")
    page = st.radio("選單", ["收銀前台", "商品管理", "會員管理", "銷售報表", "資料管理"])
    stats = get_daily_sales()
    st.metric("今日營收", f"${stats['revenue']:,.0f}")
    st.metric("訂單數", stats['orders'])


if page == "收銀前台":
    st.title("🛒 收銀前台")
    col1, col2 = st.columns([3, 1])

    with col1:
        search = st.text_input("🔍 搜尋商品", placeholder="輸入商品名稱或條碼...")
        products = get_products(search)
        if products:
            cols = st.columns(4)
            for i, p in enumerate(products):
                p = list(p)
                if p[5] is None:
                    p[5] = 0
                with cols[i % 4]:
                    st.write(f"**{p[1]}**")
                    st.caption(f"含稅: ${p[3]} | 未稅: ${p[2]} | 庫存: {p[5]}")
                    if (p[5] or 0) > 0 and st.button(f"加入購物車", key=f"add_{p[0]}"):
                        st.session_state.cart.append({
                            'product_id': p[0], 
                            'name': p[1], 
                            'price': p[3], 
                            'quantity': 1, 
                            'subtotal': p[3]
                        })
                        st.rerun()

    with col2:
        st.markdown("### 🛒 購物車")
        
        # 會員輸入區塊
        st.markdown("#### 👤 會員")
        if 'selected_member' not in st.session_state:
            st.session_state.selected_member = None
        
        member_search = st.text_input("輸入會員電話", placeholder="09xxxxxxxx", key="member_search")
        if member_search:
            member = get_member_by_phone(member_search)
            if member:
                st.session_state.selected_member = member
                st.success(f"✅ 已登入: {member[1]}")
            else:
                st.warning("找不到會員")
                if st.button("清除"):
                    st.session_state.selected_member = None
                    st.rerun()
        
        if st.session_state.selected_member:
            m = st.session_state.selected_member
            st.info(f"會員: {m[1]} | 電話: {m[2]} | 積分: {m[4]}")
            if st.button("解除登入"):
                st.session_state.selected_member = None
                st.rerun()
        
        st.markdown("---")
        
        for i, item in enumerate(st.session_state.cart):
            c1, c2, c3 = st.columns([2, 1, 1])
            c1.markdown(f"**{item['name']}**")
            c2.write(f"x{item['quantity']}")
            c3.write(f"${item['subtotal']}")
            if st.button("❌", key=f"del_{i}"):
                st.session_state.cart.pop(i)
                st.rerun()

        if st.session_state.cart:
            subtotal = sum(item['subtotal'] for item in st.session_state.cart)
            discount = st.number_input("折扣", 0, int(subtotal), 0)
            total = subtotal - discount
            st.markdown(f"**小計:** ${subtotal}<br>**折扣:** -{discount}<br>### 總計: ${total}", unsafe_allow_html=True)
            
            with st.form("f"):
                cash = st.number_input("收款", min_value=0, value=int(total))
                if st.form_submit_button("💰 結帳"):
                    if cash >= total:
                        change = cash - total
                        member_id = st.session_state.selected_member[0] if st.session_state.selected_member else None
                        create_sale(member_id, subtotal, discount, total, cash, change, st.session_state.cart)
                        st.session_state.cart = []
                        st.session_state.selected_member = None
                        st.success(f"✅ 找零 ${change}")
                        st.rerun()


elif page == "商品管理":
    st.title("📦 商品管理")

    # 匯入匯出區塊
    with st.expander("📥 匯入 / 📤 匯出"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📤 匯出商品")
            if st.button("匯出商品 CSV"):
                products = get_products()
                df = pd.DataFrame(products, columns=["ID", "名稱", "售價未稅", "售價含稅", "成本", "庫存", "條碼", "類別", "建立時間"])
                csv = df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="下載 CSV",
                    data=csv,
                    file_name="products.csv",
                    mime="text/csv"
                )
        
        with col2:
            st.subheader("📥 匯入商品")
            uploaded_file = st.file_uploader("選擇 CSV 檔案", type=['csv'])
            if uploaded_file is not None:
                try:
                    df = pd.read_csv(uploaded_file)
                    st.write("預覽：")
                    st.dataframe(df.head())
                    
                    if st.button("確認匯入"):
                        import_count = 0
                        for _, row in df.iterrows():
                            try:
                                add_product(
                                    name=str(row['名稱']),
                                    price_ex_tax=float(row['售價未稅']) if pd.notna(row['售價未稅']) else 0,
                                    price_inc_tax=float(row['售價含稅']) if pd.notna(row['售價含稅']) else 0,
                                    cost=float(row['成本']) if pd.notna(row['成本']) else 0,
                                    stock=int(row['庫存']) if pd.notna(row['庫存']) else 0,
                                    barcode=str(row['條碼']) if pd.notna(row['條碼']) else "",
                                    category=str(row['類別']) if pd.notna(row['類別']) else ""
                                )
                                import_count += 1
                            except Exception as e:
                                continue
                        st.success(f"✅ 成功匯入 {import_count} 筆商品")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ 匯入失敗: {str(e)}")

    with st.expander("➕ 新增商品"):
        with st.form("add"):
            name = st.text_input("商品名稱")
            price_ex_tax = st.number_input("售價未稅", min_value=0.0, step=0.1)
            if price_ex_tax > 0:
                st.info(f"應稅: ${calculate_price_inc_tax(price_ex_tax)}")
            cost = st.number_input("成本", min_value=0.0, step=0.1)
            stock = st.number_input("庫存", min_value=0, step=1)
            barcode = st.text_input("條碼")
            category = st.text_input("類別")
            
            if st.form_submit_button("儲存") and name and price_ex_tax:
                add_product(name, price_ex_tax, calculate_price_inc_tax(price_ex_tax), cost, stock, barcode, category)
                st.success("已新增!")
                st.rerun()

    products = get_products()
    for p in products:
        p = list(p)
        with st.expander(f"{p[1]} - 未稅:${p[2]} 應稅:${p[3]}"):
            c1, c2 = st.columns(2)
            with c1:
                new_name = st.text_input("名稱", p[1], key=f"n{p[0]}")
                new_price_ex = st.number_input("售價未稅", value=float(p[2] or 0), key=f"ex{p[0]}")
                if new_price_ex != (p[2] or 0):
                    st.info(f"應稅: ${calculate_price_inc_tax(new_price_ex)}")
                    new_price_inc = calculate_price_inc_tax(new_price_ex)
                else:
                    new_price_inc = st.number_input("售價應稅", value=float(p[3] or 0), key=f"in{p[0]}")
                if new_price_inc != (p[3] or 0):
                    st.info(f"未稅: ${calculate_price_ex_tax(new_price_inc)}")
                    new_price_ex = calculate_price_ex_tax(new_price_inc)
            with c2:
                new_cost = st.number_input("成本", value=float(p[4] or 0), key=f"c{p[0]}")
                new_stock = st.number_input("庫存", value=int(p[5] or 0), key=f"s{p[0]}")

            col1, col2 = st.columns(2)
            if col1.button("💾 更新", key=f"u{p[0]}"):
                update_product(p[0], new_name, new_price_ex, new_price_inc, new_cost, new_stock, p[6] or "", p[7] or "")
                st.rerun()
            if col2.button("🗑️ 刪除", key=f"d{p[0]}"):
                delete_product(p[0])
                st.rerun()


elif page == "會員管理":
    st.title("👥 會員管理")

    # 匯入匯出區塊
    with st.expander("📥 匯入 / 📤 匯出"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📤 匯出會員")
            if st.button("匯出會員 CSV"):
                members = get_members()
                df = pd.DataFrame(members, columns=["ID", "姓名", "電話", "Email", "積分", "總消費", "建立時間"])
                csv = df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="下載 CSV",
                    data=csv,
                    file_name="members.csv",
                    mime="text/csv"
                )
        
        with col2:
            st.subheader("📥 匯入會員")
            uploaded_file = st.file_uploader("選擇 CSV 檔案", type=['csv'], key="member_upload")
            if uploaded_file is not None:
                try:
                    df = pd.read_csv(uploaded_file)
                    st.write("預覽：")
                    st.dataframe(df.head())
                    
                    if st.button("確認匯入會員"):
                        import_count = 0
                        for _, row in df.iterrows():
                            try:
                                add_member(
                                    name=str(row['姓名']),
                                    phone=str(row['電話']),
                                    email=str(row['Email']) if pd.notna(row['Email']) else ""
                                )
                                import_count += 1
                            except Exception as e:
                                continue
                        st.success(f"✅ 成功匯入 {import_count} 筆會員")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ 匯入失敗: {str(e)}")

    with st.expander("➕ 新增會員"):
        with st.form("am"):
            name = st.text_input("姓名")
            phone = st.text_input("電話")
            email = st.text_input("Email")
            if st.form_submit_button("儲存") and name and phone:
                add_member(name, phone, email)
                st.rerun()

    members = get_members()
    if members:
        st.dataframe(pd.DataFrame(members, columns=["ID", "姓名", "電話", "Email", "積分", "總消費", "建立時間"]))


elif page == "銷售報表":
    st.title("📊 銷售報表")

    # 匯出區塊
    with st.expander("📤 匯出銷售資料"):
        if st.button("匯出銷售 CSV"):
            sales = get_sales()
            if sales:
                df = pd.DataFrame(sales, columns=["ID", "會員ID", "小計", "折扣", "總額", "收款", "找零", "方式", "時間", "會員名"])
                csv = df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="下載 CSV",
                    data=csv,
                    file_name="sales.csv",
                    mime="text/csv"
                )
    
    sales = get_sales()
    if sales:
        df = pd.DataFrame(sales, columns=["ID", "會員", "小計", "折扣", "總額", "收款", "找零", "方式", "時間", "會員名"])
        st.dataframe(df)
        
        # 統計
        col1, col2, col3 = st.columns(3)
        col1.metric("總營收", f"${df['總額'].sum():,.0f}")
        col2.metric("總訂單數", len(df))
        col3.metric("平均訂單", f"${df['總額'].mean():,.0f}")
        
        # 圖表
        st.subheader("📈 營收趨勢")
        df['日期'] = pd.to_datetime(df['時間']).dt.date
        daily = df.groupby('日期')['總額'].sum()
        st.line_chart(daily)


elif page == "資料管理":
    st.title("💾 資料管理")
    
    st.warning("⚠️ 以下操作會影響資料庫，請先備份！")
    
    with st.expander("🗑️ 清除所有資料"):
        st.write("此操作會清除所有銷售紀錄，但保留商品和會員資料。")
        if st.button("確認清除銷售資料", type="primary"):
            st.info("功能開發中...")
    
    with st.expander("💾 備份資料庫"):
        st.write("下載完整的 SQLite 資料庫檔案")
        if os.path.exists("pos.db"):
            with open("pos.db", "rb") as f:
                st.download_button(
                    label="下載資料庫",
                    data=f,
                    file_name="pos_backup.db",
                    mime="application/octet-stream"
                )
        else:
            st.info("資料庫尚未建立")
```

---

## 📁 database.py（資料庫模組）

```python
"""POS 資料庫模組 v1.5.1"""
import sqlite3

DB_PATH = "pos.db"


def get_connection():
    """建立資料庫連線"""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化資料庫"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY, name TEXT, price_ex_tax REAL, price_inc_tax REAL, 
        cost REAL, stock INTEGER, barcode TEXT, category TEXT, created_at TIMESTAMP)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY, name TEXT, phone TEXT UNIQUE, email TEXT, 
        points INTEGER, total_spent REAL, created_at TIMESTAMP)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY, member_id INTEGER, subtotal REAL, discount REAL, 
        total REAL, cash REAL, change_amount REAL, payment_method TEXT, created_at TIMESTAMP)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS sale_items (
        id INTEGER PRIMARY KEY, sale_id INTEGER, product_id INTEGER, product_name TEXT, 
        quantity INTEGER, unit_price REAL, subtotal REAL)''')

    conn.commit()
    conn.close()


# ---------- 商品 ----------

def get_products(search=""):
    conn = get_connection()
    cursor = conn.cursor()
    if search:
        cursor.execute("SELECT * FROM products WHERE name LIKE ? OR barcode LIKE ?", (f"%{search}%", f"%{search}%"))
    else:
        cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    conn.close()
    return products


def add_product(name, price_ex_tax, price_inc_tax, cost=0, stock=0, barcode="", category=""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO products VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)", 
        (name, price_ex_tax, price_inc_tax, cost, stock, barcode, category))
    conn.commit()
    conn.close()


def update_product(product_id, name, price_ex_tax, price_inc_tax, cost, stock, barcode, category):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE products 
        SET name=?, price_ex_tax=?, price_inc_tax=?, cost=?, stock=?, barcode=?, category=? 
        WHERE id=?
    """, (name, price_ex_tax, price_inc_tax, cost, stock, barcode, category, product_id))
    conn.commit()
    conn.close()


def delete_product(product_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id=?", (product_id,))
    conn.commit()
    conn.close()


# ---------- 會員 ----------

def get_members():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members")
    members = cursor.fetchall()
    conn.close()
    return members


def add_member(name, phone, email=""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO members VALUES (NULL, ?, ?, ?, 0, 0, CURRENT_TIMESTAMP)", (name, phone, email))
    conn.commit()
    conn.close()


def get_member_by_phone(phone):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members WHERE phone = ?", (phone,))
    member = cursor.fetchone()
    conn.close()
    return member


# ---------- 銷售 ----------

def create_sale(member_id, subtotal, discount, total, cash, change_amount, items=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO sales VALUES (NULL, ?, ?, ?, ?, ?, ?, 'cash', CURRENT_TIMESTAMP)", 
        (member_id, subtotal, discount, total, cash, change_amount))
    sale_id = cursor.lastrowid
    if items:
        for item in items:
            cursor.execute("INSERT INTO sale_items VALUES (NULL, ?, ?, ?, ?, ?, ?)", 
                (sale_id, item['product_id'], item['name'], item['quantity'], item['price'], item['subtotal']))
            cursor.execute("UPDATE products SET stock = stock - ? WHERE id=?", (item['quantity'], item['product_id']))
    conn.commit()
    conn.close()
    return sale_id


def get_sales():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT s.*, m.name FROM sales s LEFT JOIN members m ON s.member_id = m.id ORDER BY s.created_at DESC")
    sales = cursor.fetchall()
    conn.close()
    return sales


def get_daily_sales():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*), SUM(total), SUM(discount) FROM sales WHERE date(created_at) = date('now')")
    result = cursor.fetchone()
    conn.close()
    return {'orders': result[0] or 0, 'revenue': result[1] or 0}
```

---

## 📁 requirements.txt

```
streamlit>=1.28.0
pandas>=2.0.0
openpyxl>=3.1.0
