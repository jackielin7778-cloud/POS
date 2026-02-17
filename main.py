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


# 銷售完成訊息（模擬彈跳視窗）
if 'sale_completed' in st.session_state and st.session_state.sale_completed:
    cash = st.session_state.last_sale['cash']
    change = st.session_state.last_sale['change']
    html = """
    <div style="background-color: #d4edda; padding: 20px; border-radius: 10px; border: 2px solid #28a745; text-align: center; margin: 20px 0;">
        <h2 style="color: #28a745; margin: 0;">✅ 交易完成</h2>
        <h3 style="color: #155724; margin: 10px 0;">收款 $""" + str(cash) + """ 元，找零 $""" + str(change) + """ 元</h3>
        <p style="color: #666;">3秒後自動進入下一筆交易...</p>
    </div>
    <script>
        setTimeout(function(){
            window.location.reload();
        }, 3000);
    </script>
    """
    st.markdown(html, unsafe_allow_html=True)
    
    # 清除狀態
    st.session_state.sale_completed = False
    st.session_state.last_sale = {}
    st.session_state.cart = []
    st.session_state.selected_member = None


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
            total = int(subtotal - discount - promo_discount + 0.5)
            
            st.markdown(f"**小計:** ${subtotal}<br>**折扣:** -{discount}<br>**促銷:** -{promo_discount:.1f}<br>### 總計: ${total}", unsafe_allow_html=True)
            
            cash_input = st.text_input("收款金額（留空或0表示剛剛好）", value="", placeholder="輸入金額")
            
            if cash_input == "" or cash_input == "0":
                cash = total
                change = 0
            else:
                try:
                    cash = float(cash_input)
                    change = int(cash - total + 0.5) if cash >= total else 0
                except:
                    cash = total
                    change = 0
            
            if cash >= total:
                if st.button("💰 結帳", type="primary"):
                    member_id = st.session_state.selected_member[0] if st.session_state.selected_member else None
                    total_discount = discount + promo_discount
                    create_sale(member_id, subtotal, total_discount, total, cash, change, st.session_state.cart)
                    
                    st.session_state.sale_completed = True
                    st.session_state.last_sale = {'cash': cash, 'change': change}
                    st.rerun()


elif page == "商品管理":
    st.title("📦 商品管理")
    # ... (省略)


elif page == "會員管理":
    st.title("👥 會員管理")
    # ... (省略)


elif page == "銷售報表":
    st.title("📊 銷售報表")
    # ... (省略)


elif page == "資料管理":
    st.title("💾 資料管理")
    # ... (省略)
