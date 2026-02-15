好的主人！這是 **database.py**：

```python
"""
POS 收銀系統 - Database Module
"""

import sqlite3
from datetime import datetime

DB_PATH = "pos.db"

def init_db():
    """初始化資料庫"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 商品資料表
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
    
    # 會員資料表
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
    
    # 銷售資料表
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
    
    # 銷售明細資料表
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

def add_product(name, price, cost=0, stock=0, barcode="", category=""):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO products (name, price, cost, stock, barcode, category) VALUES (?, ?, ?, ?, ?, ?)",
        (name, price, cost, stock, barcode, category)
    )
    conn.commit()
    conn.close()

def get_products(search=""):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if search:
        cursor.execute("SELECT * FROM products WHERE name LIKE ? OR barcode LIKE ?", (f"%{search}%", f"%{search}%"))
    else:
        cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    conn.close()
    return products

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

def update_stock(product_id, quantity_change):
    """更新庫存（quantity_change 可為正負數）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE products SET stock = stock + ? WHERE id=?", (quantity_change, product_id))
    conn.commit()
    conn.close()

# ============ 會員操作 ============

def add_member(name, phone, email=""):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO members (name, phone, email) VALUES (?, ?, ?)",
        (name, phone, email)
    )
    conn.commit()
    conn.close()

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

def get_member_by_id(member_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members WHERE id=?", (member_id,))
    member = cursor.fetchone()
    conn.close()
    return member

def update_member_points(member_id, points_change, spent=0):
    """更新會員積分與消費金額"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE members SET points = points + ?, total_spent = total_spent + ? WHERE id=?",
        (points_change, spent, member_id)
    )
    conn.commit()
    conn.close()

# ============ 銷售操作 ============

def create_sale(member_id, subtotal, discount, total, cash, change_amount, payment_method="cash", items=None):
    """建立銷售記錄"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 建立銷售主記錄
    cursor.execute(
        "INSERT INTO sales (member_id, subtotal, discount, total, cash, change_amount, payment_method) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (member_id, subtotal, discount, total, cash, change_amount, payment_method)
    )
    sale_id = cursor.lastrowid
    
    # 建立銷售明細
    if items:
        for item in items:
            cursor.execute(
                "INSERT INTO sale_items (sale_id, product_id, product_name, quantity, unit_price, subtotal) VALUES (?, ?, ?, ?, ?, ?)",
                (sale_id, item['product_id'], item['name'], item['quantity'], item['price'], item['subtotal'])
            )
            # 更新庫存
            cursor.execute("UPDATE products SET stock = stock - ? WHERE id=?", (item['quantity'], item['product_id']))
    
    # 更新會員積分（消費 100 元累積 1 點）
    if member_id:
        points = int(total)
        cursor.execute("UPDATE members SET points = points + ?, total_spent = total_spent + ? WHERE id=?", (points, total, member_id))
    
    conn.commit()
    conn.close()
    return sale_id

def get_sales(start_date="", end_date="", member_id=""):
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
    if member_id:
        query += " AND s.member_id = ?"
        params.append(member_id)
    
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
    """取得今日銷售統計"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            COUNT(*) as total_orders,
            SUM(total) as total_revenue,
            SUM(discount) as total_discount
        FROM sales 
        WHERE date(created_at) = date('now')
    """)
    result = cursor.fetchone()
    conn.close()
    return {
        'orders': result[0] or 0,
        'revenue': result[1] or 0,
        'discount': result[2] or 0
    }

def get_top_products(limit=10):
    """取得熱銷商品排行"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT product_name, SUM(quantity) as total_qty, SUM(subtotal) as total_sales
        FROM sale_items
        GROUP BY product_id
        ORDER BY total_qty DESC
        LIMIT ?
    """, (limit,))
    products = cursor.fetchall()
    conn.close()
    return products

# 初始化資料庫
init_db()
```

---

最後 **requirements.txt** 要貼嗎？

Tokens: 15 in / 305 out  
Context: 0/200k (0%)