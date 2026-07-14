import mysql.connector
from dotenv import load_dotenv
import os

load_dotenv()

conn = mysql.connector.connect(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", 3306)),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", ""),
    database=os.getenv("DB_NAME", "magento")
)

cursor = conn.cursor(dictionary=True)

def query(sql):
    cursor.execute(sql)
    return cursor.fetchall()

print("--- Parent Items ---")
parent_items = query("SELECT sku, name, qty_ordered, qty_canceled, qty_refunded, qty_shipped FROM sales_order_item WHERE order_id = 109788")
for i in parent_items:
    print(i)

print("\n--- Child Items ---")
child_items = query("SELECT sku, name, qty_ordered, qty_canceled, qty_refunded, qty_shipped FROM sales_order_item WHERE order_id = 110345")
for i in child_items:
    print(i)

print("\n--- Parent Payment ---")
payments = query("SELECT method FROM sales_order_payment WHERE parent_id = 109788")
for p in payments:
    print(p)

print("\n--- Parent Credit Memos ---")
memos = query("SELECT state, adjustment, grand_total FROM sales_creditmemo WHERE order_id = 109788")
for m in memos:
    print(m)

conn.close()
