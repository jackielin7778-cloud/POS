"""POS 收銀系統 v1.5.2"""
import streamlit as st
import pandas as pd
import os
from database import init_db, get_products, add_product, update_product, delete_product
from database import get_members, add_member, create_sale, get_sales, get_daily_sales

# ⚠️ 強制重建資料庫（執行一次後請刪除這3行！）
if os.path.exists("pos.db"):
    os.remove("pos.db")

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
    page = st.radio("選單", ["收銀前台", "商品管理", "會員管理", "銷售報表"])
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
            from database import get_member_by_phone
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
    sales = get_sales()
    if sales:
        df = pd.DataFrame(sales, columns=["ID", "會員", "小計", "折扣", "總額", "收款", "找零", "方式", "時間", "會員名"])
        st.dataframe(df)
        st.metric("總營收", f"${df['總額'].sum():,.0f}")
