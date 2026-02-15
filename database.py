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
