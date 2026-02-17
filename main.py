"""
POS 收銀系統 v1.6.0 - 促銷版
"""
import streamlit as st
import pandas as pd
import os
from database import init_db, get_products, add_product, update_product, delete_product
from database import get_members, add_member, create_sale, get_sales, get_daily_sales
from database import get_member_by_phone, get_promotions, add_promotion, delete_promotion, calculate_promotion

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
                
                promos = get_promotions(p[0])
                promo_text = ""
                if promos:
                    promo = dict(promos[0])
                    if promo['type'] == 'percent':
                        promo_text = f" 🔥 {int(promo['value'])}%OFF"
                    elif promo['type'] == 'bogo':
                        promo_text = " 🔥 買一送一"
                    elif promo['type'] == 'second_discount':
                        promo_text = f" 🔥 第2件{int(promo['value'])}%OFF"
                
                with cols[i % 4]:
                    st.write(f"**{p[1]}**{promo_text}")
                    st.caption(f"含稅: ${p[3]} | 未稅: ${p[2]} | 庫存: {p[5]}")
                    if (p[5] or 0) > 0 and st.button(f"加入購物車", key=f"add_{p[0]}"):
                        found = False
                        for item in st.session_state.cart:
                            if item['product_id'] == p[0]:
                                item['quantity'] += 1
                                item['subtotal'] = item['quantity'] * item['price']
                                found = True
                                break
                        if not found:
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
        
        promo_discount = 0
        
        for i, item in enumerate(st.session_state.cart):
            promos = get_promotions(item['product_id'])
            item_discount = 0
            
            if promos:
                item_discount = calculate_promotion(item, promos)
                promo_discount += item_discount
            
            c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 1])
            c1.markdown(f"**{item['name']}**")
            c2.write(f"x{item['quantity']}")
            
            if c3.button("➕", key=f"plus_{i}"):
                st.session_state.cart[i]['quantity'] += 1
                st.session_state.cart[i]['subtotal'] = st.session_state.cart[i]['quantity'] * st.session_state.cart[i]['price']
                st.rerun()
            if c4.button("➖", key=f"minus_{i}"):
                if st.session_state.cart[i]['quantity'] > 1:
                    st.session_state.cart[i]['quantity'] -= 1
                    st.session_state.cart[i]['subtotal'] = st.session_state.cart[i]['quantity'] * st.session_state.cart[i]['price']
                else:
                    st.session_state.cart.pop(i)
                st.rerun()
            
            if item_discount > 0:
                c5.markdown(f"~~${item['subtotal']}~~ 💰${item['subtotal'] - item_discount}")
            else:
                c5.write(f"${item['subtotal']}")

        if len(st.session_state.cart) > 0:
            if st.button("🗑️ 清空購物車"):
                st.session_state.cart = []
                st.rerun()

        if st.session_state.cart:
            subtotal = sum(item['subtotal'] for item in st.session_state.cart)
            
            if promo_discount > 0:
                st.success(f"🎉 促銷折扣: -${promo_discount:.1f}")
            
            discount = st.number_input("折扣", 0, int(subtotal), 0)
            # 四捨五入到整數
            total = round(subtotal - discount - promo_discount)
            
            st.markdown(f"**小計:** ${subtotal}<br>**折扣:** -{discount}<br>**促銷:** -{promo_discount:.1f}<br>### 總計: ${total}", unsafe_allow_html=True)
            
            with st.form("f"):
                cash = st.number_input("收款", min_value=0, value=int(total))
                if st.form_submit_button("💰 結帳"):
                    if cash >= total:
                        change = round(cash - total)
                        member_id = st.session_state.selected_member[0] if st.session_state.selected_member else None
                        total_discount = discount + promo_discount
                        create_sale(member_id, subtotal, total_discount, total, cash, change, st.session_state.cart)
                        st.session_state.cart = []
                        st.session_state.selected_member = None
                        st.success(f"✅ 找零 ${change}")
                        st.rerun()


elif page == "商品管理":
    st.title("📦 商品管理")

    with st.expander("📥 匯入 / 📤 匯出"):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📤 匯出商品")
            if st.button("匯出商品 CSV"):
                products = get_products()
                df = pd.DataFrame(products, columns=["ID", "名稱", "售價未稅", "售價含稅", "成本", "庫存", "條碼", "類別", "建立時間"])
                csv = df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(label="下載 CSV", data=csv, file_name="products.csv", mime="text/csv")
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
                            except:
                                continue
                        st.success(f"✅ 成功匯入 {import_count} 筆")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ 錯誤: {str(e)}")

    products = get_products()
    product_options = {f"{p[1]} (${p[3]})": p[0] for p in products}
    
    if product_options:
        selected_product = st.selectbox("選擇商品", list(product_options.keys()))
        product_id = product_options[selected_product]
        product = [p for p in products if p[0] == product_id][0]
        product = list(product)
        
        with st.expander("📝 商品基本資料", expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                new_name = st.text_input("名稱", product[1])
                new_price_ex = st.number_input("售價未稅", value=float(product[2] or 0))
                if new_price_ex != (product[2] or 0):
                    st.info(f"應稅: ${calculate_price_inc_tax(new_price_ex)}")
                    new_price_inc = calculate_price_inc_tax(new_price_ex)
                else:
                    new_price_inc = st.number_input("售價應稅", value=float(product[3] or 0))
            with c2:
                new_cost = st.number_input("成本", value=float(product[4] or 0))
                new_stock = st.number_input("庫存", value=int(product[5] or 0))
                new_barcode = st.text_input("條碼", product[6] or "")
                new_category = st.text_input("類別", product[7] or "")
            
            col1, col2 = st.columns(2)
            if col1.button("💾 更新商品"):
                update_product(product_id, new_name, new_price_ex, new_price_inc, new_cost, new_stock, new_barcode, new_category)
                st.success("✅ 已更新")
                st.rerun()
            if col2.button("🗑️ 刪除商品", type="primary"):
                delete_product(product_id)
                st.success("✅ 已刪除")
                st.rerun()
        
        with st.expander("🏷️ 促銷設定", expanded=True):
            st.write("### 🎫 目前促銷")
            promos = get_promotions(product_id)
            
            if promos:
                for p in promos:
                    p = dict(p)
                    type_names = {'percent': '百分比折扣', 'fixed': '固定金額', 'bogo': '買一送一', 'second_discount': '第二件折扣', 'amount': '滿額折扣'}
                    with st.container():
                        col1, col2, col3 = st.columns([3, 2, 1])
                        col1.write(f"**{p['name']}**")
                        col2.write(f"{type_names.get(p['type'], p['type'])}: {p['value']}")
                        if col3.button("🗑️", key=f"del_promo_{p['id']}"):
                            delete_promotion(p['id'])
                            st.rerun()
            else:
                st.info("尚無促銷")
            
            st.write("---")
            st.write("### ➕ 新增促銷")
            
            with st.form("add_promo"):
                promo_name = st.text_input("促銷名稱")
                promo_type = st.selectbox("促銷類型", 
                    ['percent', 'fixed', 'bogo', 'second_discount', 'amount'],
                    format_func=lambda x: {
                        'percent': '百分比折扣 (%)', '固定金額 ($)': 'fixed', 
                        'bogo': '買一送一', 'second_discount': '第二件折扣 (%)', 'amount': '滿額折扣 ($)'
                    }[x])
                
                promo_value = 0
                min_amount = 0
                
                if promo_type == 'percent':
                    promo_value = st.slider("折扣%", 1, 100, 10)
                elif promo_type == 'fixed':
                    promo_value = st.number_input("金額", min_value=0.0, value=10.0)
                elif promo_type == 'bogo':
                    st.caption("買一送一")
                elif promo_type == 'second_discount':
                    promo_value = st.slider("第二件折扣%", 0, 100, 50)
                elif promo_type == 'amount':
                    promo_value = st.number_input("折扣金額", min_value=0.0, value=50.0)
                    min_amount = st.number_input("最低消費", min_value=0.0, value=200.0)
                
                if st.form_submit_button("➕ 新增"):
                    add_promotion(promo_name, promo_type, promo_value, product_id, min_amount=min_amount)
                    st.success("✅ 已新增")
                    st.rerun()


elif page == "會員管理":
    st.title("👥 會員管理")

    with st.expander("📥 匯入 / 📤 匯出"):
        col1, col2 = st.columns(2)
        with col1:
            if st.button("匯出會員 CSV"):
                members = get_members()
                df = pd.DataFrame(members, columns=["ID", "姓名", "電話", "Email", "積分", "總消費", "建立時間"])
                csv = df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(label="下載", data=csv, file_name="members.csv", mime="text/csv")

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

    with st.expander("📤 匯出"):
        if st.button("匯出銷售 CSV"):
            sales = get_sales()
            if sales:
                df = pd.DataFrame(sales, columns=["ID", "會員ID", "小計", "折扣", "總額", "收款", "找零", "方式", "時間", "會員名"])
                csv = df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(label="下載", data=csv, file_name="sales.csv", mime="text/csv")
    
    sales = get_sales()
    if sales:
        df = pd.DataFrame(sales, columns=["ID", "會員", "小計", "折扣", "總額", "收款", "找零", "方式", "時間", "會員名"])
        st.dataframe(df)
        col1, col2, col3 = st.columns(3)
        col1.metric("總營收", f"${df['總額'].sum():,.0f}")
        col2.metric("總訂單", len(df))
        col3.metric("平均", f"${df['總額'].mean():,.0f}")
        
        st.subheader("📈 趨勢")
        df['日期'] = pd.to_datetime(df['時間']).dt.date
        st.line_chart(df.groupby('日期')['總額'].sum())


elif page == "資料管理":
    st.title("💾 資料管理")
    st.warning("⚠️ 請先備份！")
    
    with st.expander("💾 備份資料庫"):
        if os.path.exists("pos.db"):
            with open("pos.db", "rb") as f:
                st.download_button(label="下載資料庫", data=f, file_name="pos_backup.db", mime="application/octet-stream")
        else:
            st.info("資料庫尚未建立")
