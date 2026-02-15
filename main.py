好的主人！這是 **main.py**：

```python
"""
POS 收銀系統 - Streamlit Web Application
"""

import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd

# 資料庫路徑
DB_PATH = "pos.db"

# ============ 資料庫初始化 ============
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            cost REAL DEFAULT 0,
            stock INTEGER DEFAULT 0,
            barcode TEXT UNIQUE,
            category TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT UNIQUE,
            email TEXT,
            points INTEGER DEFAULT 0,
            total_spent REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER,
            subtotal REAL NOT NULL,
            discount REAL DEFAULT 0,
            total REAL NOT NULL,
            cash REAL,
            change_amount REAL,
            payment_method TEXT DEFAULT 'cash',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (member_id) REFERENCES members(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            subtotal REAL NOT NULL,
            FOREIGN KEY (sale_id) REFERENCES sales(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    ''')
    
    conn.commit()
    conn.close()

# ============ 商品操作 ============
def get_products(search=""):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if search:
        cursor.execute("SELECT * FROM products WHERE name LIKE ? OR barcode LIKE ? ORDER BY name", (f"%{search}%", f"%{search}%"))
    else:
        cursor.execute("SELECT * FROM products ORDER BY name")
    products = cursor.fetchall()
    conn.close()
    return products

def add_product(name, price, cost=0, stock=0, barcode="", category=""):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO products (name, price, cost, stock, barcode, category) VALUES (?, ?, ?, ?, ?, ?)",
        (name, price, cost, stock, barcode, category)
    )
    conn.commit()
    conn.close()

def update_product(product_id, name, price, cost, stock, barcode, category):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE products SET name=?, price=?, cost=?, stock=?, barcode=?, category=? WHERE id=?",
        (name, price, cost, stock, barcode, category, product_id)
    )
    conn.commit()
    conn.close()

def delete_product(product_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id=?", (product_id,))
    conn.commit()
    conn.close()

# ============ 會員操作 ============
def get_members(search=""):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if search:
        cursor.execute("SELECT * FROM members WHERE name LIKE ? OR phone LIKE ?", (f"%{search}%", f"%{search}%"))
    else:
        cursor.execute("SELECT * FROM members")
    members = cursor.fetchall()
    conn.close()
    return members

def add_member(name, phone, email=""):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO members (name, phone, email) VALUES (?, ?, ?)",
        (name, phone, email)
    )
    conn.commit()
    conn.close()

def get_member_by_id(member_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members WHERE id=?", (member_id,))
    member = cursor.fetchone()
    conn.close()
    return member

# ============ 銷售操作 ============
def create_sale(member_id, subtotal, discount, total, cash, change_amount, payment_method="cash", items=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO sales (member_id, subtotal, discount, total, cash, change_amount, payment_method) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (member_id, subtotal, discount, total, cash, change_amount, payment_method)
    )
    sale_id = cursor.lastrowid
    
    if items:
        for item in items:
            cursor.execute(
                "INSERT INTO sale_items (sale_id, product_id, product_name, quantity, unit_price, subtotal) VALUES (?, ?, ?, ?, ?, ?)",
                (sale_id, item['product_id'], item['name'], item['quantity'], item['price'], item['subtotal'])
            )
            cursor.execute("UPDATE products SET stock = stock - ? WHERE id=?", (item['quantity'], item['product_id']))
    
    if member_id:
        points = int(total)
        cursor.execute("UPDATE members SET points = points + ?, total_spent = total_spent + ? WHERE id=?", (points, total, member_id))
    
    conn.commit()
    conn.close()
    return sale_id

def get_sales(start_date="", end_date=""):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    query = "SELECT s.*, m.name as member_name FROM sales s LEFT JOIN members m ON s.member_id = m.id WHERE 1=1"
    params = []
    if start_date:
        query += " AND date(s.created_at) >= date(?)"
        params.append(start_date)
    if end_date:
        query += " AND date(s.created_at) <= date(?)"
        params.append(end_date)
    query += " ORDER BY s.created_at DESC"
    cursor.execute(query, params)
    sales = cursor.fetchall()
    conn.close()
    return sales

def get_sale_details(sale_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sale_items WHERE sale_id=?", (sale_id,))
    items = cursor.fetchall()
    conn.close()
    return items

def get_daily_sales():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) as total_orders, SUM(total) as total_revenue, SUM(discount) as total_discount
        FROM sales WHERE date(created_at) = date('now')
    """)
    result = cursor.fetchone()
    conn.close()
    return {'orders': result[0] or 0, 'revenue': result[1] or 0, 'discount': result[2] or 0}

def get_top_products(limit=10):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT product_name, SUM(quantity) as total_qty, SUM(subtotal) as total_sales
        FROM sale_items GROUP BY product_id ORDER BY total_qty DESC LIMIT ?
    """, (limit,))
    products = cursor.fetchall()
    conn.close()
    return products

# 初始化
init_db()

# ============ Streamlit 頁面配置 ============
st.set_page_config(page_title="POS 收銀系統", page_icon="🏪", layout="wide")

# _session_state_ for cart
if 'cart' not in st.session_state:
    st.session_state.cart = []
if 'current_member' not in st.session_state:
    st.session_state.current_member = None

# CSS 樣式
st.markdown("""
<style>
    .product-card {
        background-color: white;
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        transition: transform 0.2s;
    }
    .product-card:hover {
        transform: scale(1.02);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .price { font-size: 20px; font-weight: bold; color: #27ae60; }
    .stock { font-size: 12px; color: #7f8c8d; }
    .stock-low { color: #e74c3c; }
</style>
""", unsafe_allow_html=True)

# 側邊欄 - 頁面導航
with st.sidebar:
    st.title("🏪 POS 系統")
    page = st.radio("選單", ["收銀前台", "商品管理", "會員管理", "銷售報表"])
    
    st.divider()
    
    # 今日營收
    stats = get_daily_sales()
    st.metric("今日營收", f"${stats['revenue']:,.0f}")
    st.metric("訂單數", stats['orders'])

# ============ 頁面：收銀前台 ============
if page == "收銀前台":
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # 搜尋
        search = st.text_input("🔍 搜尋商品", placeholder="輸入商品名稱或條碼...")
        
        # 商品網格
        products = get_products(search)
        
        if products:
            cols = st.columns(4)
            for i, p in enumerate(products):
                with cols[i % 4]:
                    with st.container():
                        st.markdown(f"""
                        <div class="product-card">
                            <b>{p[1]}</b><br>
                            <span class="price">${p[2]:.0f}</span><br>
                            <span class="stock {'stock-low' if p[4] <= 5 else ''}">庫存: {p[4]}</span>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if p[4] > 0:
                            if st.button(f"加入購物車", key=f"add_{p[0]}"):
                                # 檢查購物車是否已有
                                found = False
                                for item in st.session_state.cart:
                                    if item['product_id'] == p[0]:
                                        if item['quantity'] < p[4]:
                                            item['quantity'] += 1
                                            item['subtotal'] = item['quantity'] * item['price']
                                            found = True
                                        break
                                if not found:
                                    st.session_state.cart.append({
                                        'product_id': p[0],
                                        'name': p[1],
                                        'price': p[2],
                                        'quantity': 1,
                                        'subtotal': p[2]
                                    })
                                st.rerun()
                        else:
                            st.button("缺貨", disabled=True, key=f"out_{p[0]}")
                        st.markdown("<br>", unsafe_allow_html=True)
        else:
            st.info("尚無商品，請先到商品管理新增")
    
    with col2:
        st.markdown("### 🛒 購物車")
        
        # 會員選擇
        if st.session_state.current_member:
            st.success(f"👤 {st.session_state.current_member['name']} (積分: {st.session_state.current_member[4]})")
            if st.button("清除會員"):
                st.session_state.current_member = None
                st.rerun()
        else:
            members = get_members()
            if members:
                member_options = ["請選擇會員"] + [f"{m[1]} - {m[2]}" for m in members]
                selected = st.selectbox("👥 選擇會員", member_options)
                if selected != "請選擇會員":
                    idx = member_options.index(selected) - 1
                    st.session_state.current_member = members[idx]
                    st.rerun()
        
        st.divider()
        
        # 購物車內容
        for i, item in enumerate(st.session_state.cart):
            with st.container():
                c1, c2, c3 = st.columns([2, 1, 1])
                c1.markdown(f"**{item['name']}**")
                c2.write(f"x{item['quantity']}")
                c3.write(f"${item['subtotal']:.0f}")
                
                bc1, bc2 = st.columns(2)
                if bc1.button("➕", key=f"inc_{i}"):
                    products = get_products()
                    product = next((p for p in products if p[0] == item['product_id']), None)
                    if product and item['quantity'] < product[4]:
                        item['quantity'] += 1
                        item['subtotal'] = item['quantity'] * item['price']
                        st.rerun()
                if bc2.button("➖", key=f"dec_{i}"):
                    if item['quantity'] > 1:
                        item['quantity'] -= 1
                        item['subtotal'] = item['quantity'] * item['price']
                    else:
                        st.session_state.cart.pop(i)
                    st.rerun()
                st.divider()
        
        # 金額計算
        if st.session_state.cart:
            subtotal = sum(item['subtotal'] for item in st.session_state.cart)
            discount = st.number_input("折扣", min_value=0, max_value=int(subtotal), value=0)
            total = subtotal - discount
            
            st.markdown(f"**小計:** ${subtotal:.0f}")
            st.markdown(f"**折扣:** -${discount:.0f}")
            st.markdown(f"### 總計: ${total:.0f}")
            
            # 結帳
            with st.form("checkout_form"):
                cash = st.number_input("收款金額", min_value=0, value=int(total))
                submitted = st.form_submit_button("💰 結帳")
                
                if submitted:
                    if cash >= total:
                        change = cash - total
                        
                        # 建立銷售
                        member_id = st.session_state.current_member[0] if st.session_state.current_member else None
                        sale_id = create_sale(
                            member_id=member_id,
                            subtotal=subtotal,
                            discount=discount,
                            total=total,
                            cash=cash,
                            change_amount=change
                        )
                        
                        # 清空購物車
                        st.session_state.cart = []
                        st.session_state.current_member = None
                        
                        st.success(f"✅ 結帳成功！找零 ${change:.0f}")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("金額不足！")
            
            if st.button("🗑️ 清空購物車", type="primary"):
                st.session_state.cart = []
                st.rerun()
        else:
            st.info("購物車是空的")

# ============ 頁面：商品管理 ============
elif page == "商品管理":
    st.title("📦 商品管理")
    
    # 新增商品
    with st.expander("➕ 新增商品", expanded=False):
        with st.form("add_product"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("商品名稱 *")
                price = st.number_input("售價 *", min_value=0, value=0)
                cost = st.number_input("成本", min_value=0, value=0)
            with col2 st.number_input("庫存", min:
                stock =_value=0, value=0)
                barcode = st.text_input("條碼")
                category = st.text_input("類別")
            submitted = st.form_submit_button("儲存")
            if submitted:
                if name and price > 0:
                    add_product(name, price, cost, stock, barcode, category)
                    st.success("商品已新增！")
                    st.rerun()
                else:
                    st.error("請輸入商品名稱和售價")
    
    # 商品列表
    products = get_products()
    if products:
        df = pd.DataFrame(products, columns=["ID", "名稱", "售價", "成本", "庫存", "條碼", "類別", "建立時間"])
        
        # 編輯/刪除
        for i, row in df.iterrows():
            with st.expander(f"{row['名稱']} - ${row['售價']:.0f} (庫存: {row['庫存']})"):
                c1, c2 = st.columns(2)
                with c1:
                    new_name = st.text_input("名稱", value=row["名稱"], key=f"name_{row['ID']}")
                    new_price = st.number_input("售價", value=row["售價"], key=f"price_{row['ID']}")
                    new_cost = st.number_input("成本", value=row["成本"], key=f"cost_{row['ID']}")
                with c2:
                    new_stock = st.number_input("庫存", value=row["庫存"], key=f"stock_{row['ID']}")
                    new_barcode = st.text_input("條碼", value=row["條碼"] or "", key=f"barcode_{row['ID']}")
                    new_category = st.text_input("類別", value=row["類別"] or "", key=f"cat_{row['ID']}")
                
                c3, c4 = st.columns(2)
                if c3.button("💾 更新", key=f"update_{row['ID']}"):
                    update_product(row['ID'], new_name, new_price, new_cost, new_stock, new_barcode, new_category)
                    st.success("已更新！")
                    st.rerun()
                if c4.button("🗑️ 刪除", key=f"delete_{row['ID']}"):
                    delete_product(row['ID'])
                    st.success("已刪除！")
                    st.rerun()
    else:
        st.info("尚無商品")

# ============ 頁面：會員管理 ============
elif page == "會員管理":
    st.title("👥 會員管理")
    
    # 新增會員
    with st.expander("➕ 新增會員", expanded=False):
        with st.form("add_member"):
            col1, col2 = st.columns(2)
            name = col1.text_input("姓名 *")
            phone = col2.text_input("電話 *")
            email = st.text_input("Email")
            submitted = st.form_submit_button("儲存")
            if submitted:
                if name and phone:
                    add_member(name, phone, email)
                    st.success("會員已新增！")
                    st.rerun()
                else:
                    st.error("請輸入姓名和電話")
    
    # 會員列表
    members = get_members()
    if members:
        df = pd.DataFrame(members, columns=["ID", "姓名", "電話", "Email", "積分", "總消費", "建立時間"])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("尚無會員")

# ============ 頁面：銷售報表 ============
elif page == "銷售報表":
    st.title("📊 銷售報表")
    
    # 篩選
    col1, col2 = st.columns(2)
    start_date = col1.date_input("開始日期")
    end_date = col2.date_input("結束日期")
    
    # 銷售記錄
    sales = get_sales(str(start_date), str(end_date))
    if sales:
        df = pd.DataFrame(sales, columns=["ID", "會員ID", "小計", "折扣", "總額", "收款", "找零", "付款方式", "時間", "會員名"])
        df = df.drop(columns=["會員ID"])
        df["時間"] = pd.to_datetime(df["時間"]).dt.strftime("%Y-%m-%d %H:%M")
        st.dataframe(df, use_container_width=True)
        
        # 統計
        total_revenue = df["總額"].sum()
        total_orders = len(df)
        total_discount = df["折扣"].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("總營收", f"${total_revenue:,.0f}")
        c2.metric("訂單數", total_orders)
        c3.metric("總折扣", f"${total_discount:,.0f}")
        
        # 熱銷商品
        st.subheader("🔥 熱銷商品排行")
        top_products = get_top_products()
        if top_products:
            top_df = pd.DataFrame(top_products, columns=["商品名", "銷售數量", "銷售金額"])
            st.dataframe(top_df, use_container_width=True)
    else:
        st.info("查無銷售記錄")
```

---

接下來要貼 **database.py** 還是 **requirements.txt**？

Tokens: 22 in / 312 out  
Context: 0/200k (0%)