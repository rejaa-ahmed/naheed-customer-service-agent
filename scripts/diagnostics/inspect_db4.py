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

print("--- Check Parent Order ---")
parent = query("SELECT entity_id, increment_id FROM sales_order WHERE increment_id = '2000096085'")
print("Parent:", parent)

if parent:
    pid = parent[0]['entity_id']
    print("\n--- Parent Items ---")
    for i in query(f"SELECT sku, name, qty_ordered, qty_canceled, qty_refunded, qty_shipped FROM sales_order_item WHERE order_id = {pid}"):
        print(i)
        
    print("\n--- Parent Payment ---")
    for p in query(f"SELECT method FROM sales_order_payment WHERE parent_id = {pid}"):
        print(p)
        
    print("\n--- Parent Credit Memos ---")
    for m in query(f"SELECT state, adjustment, grand_total FROM sales_creditmemo WHERE order_id = {pid}"):
        print(m)

conn.close()
