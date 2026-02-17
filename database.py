"""POS 資料庫模組 v1.6.0"""
import sqlite3

DB_PATH = "pos.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
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
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS promotions (
        id INTEGER PRIMARY KEY, name TEXT, type TEXT, value REAL, product_id INTEGER,
        min_quantity INTEGER DEFAULT 1, min_amount REAL DEFAULT 0,
        start_date TEXT, end_date TEXT, is_active INTEGER DEFAULT 1, created_at TIMESTAMP)''')

    conn.commit()
    conn.close()


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
    cursor.execute("""UPDATE products SET name=?, price_ex_tax=?, price_inc_tax=?, cost=?, stock=?, barcode=?, category=? WHERE id=?""", 
        (name, price_ex_tax, price_inc_tax, cost, stock, barcode, category, product_id))
    conn.commit()
    conn.close()


def delete_product(product_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id=?", (product_id,))
    conn.commit()
    conn.close()


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


# ---------- 促銷 ----------
def get_promotions(product_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    if product_id:
        cursor.execute("SELECT * FROM promotions WHERE product_id = ? AND is_active = 1", (product_id,))
    else:
        cursor.execute("SELECT * FROM promotions WHERE is_active = 1")
    promotions = cursor.fetchall()
    conn.close()
    return promotions


def add_promotion(name, promo_type, value, product_id=None, min_quantity=1, min_amount=0, start_date=None, end_date=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""INSERT INTO promotions (name, type, value, product_id, min_quantity, min_amount, start_date, end_date, is_active, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)""", 
        (name, promo_type, value, product_id, min_quantity, min_amount, start_date, end_date))
    conn.commit()
    conn.close()


def delete_promotion(promo_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM promotions WHERE id = ?", (promo_id,))
    conn.commit()
    conn.close()


def calculate_promotion(item, promotions):
    if not promotions:
        return 0
    
    discount = 0
    qty = item['quantity']
    price = item['price']
    
    for p in promotions:
        p = dict(p)
        
        if p['type'] == 'percent':
            discount += price * qty * (p['value'] / 100)
        elif p['type'] == 'fixed':
            discount += p['value']
        elif p['type'] == 'bogo':
            free_items = qty // 2
            discount += free_items * price
        elif p['type'] == 'second_discount':
            if qty >= 2:
                discount += price * (p['value'] / 100)
        elif p['type'] == 'amount':
            if item['subtotal'] >= p['min_amount']:
                discount += p['value']
    
    return round(discount, 2)
