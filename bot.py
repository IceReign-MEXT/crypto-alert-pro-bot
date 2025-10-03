
import sqlite3, time

DB_NAME = "subscriptions.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS subscriptions (
        user_id INTEGER PRIMARY KEY,
        expiry INTEGER
    )""")
    conn.commit()
    conn.close()

def add_subscription(user_id, days=30):
    expiry = int(time.time()) + days * 86400
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("REPLACE INTO subscriptions (user_id, expiry) VALUES (?, ?)", (user_id, expiry))
    conn.commit()
    conn.close()

def check_subscription(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT expiry FROM subscriptions WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return False
    expiry = row[0]
    return expiry > int(time.time())

def subscription_expiry(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT expiry FROM subscriptions WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None
