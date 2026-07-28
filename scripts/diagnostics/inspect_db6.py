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

print("--- Find valid parent and child pairs ---")
sql = """
SELECT p.entity_id as parent_id, p.increment_id as parent_inc,
       c.entity_id as child_id, c.increment_id as child_inc
FROM sales_order c
JOIN sales_order p ON c.relation_parent_id = p.entity_id
LIMIT 5
"""
pairs = query(sql)
for pair in pairs:
    print(pair)

if pairs:
    pid = pairs[0]['parent_id']
    cid = pairs[0]['child_id']
    print(f"\n--- Parent Items (order_id={pid}) ---")
    for i in query(f"SELECT sku, name, qty_ordered, qty_canceled, qty_refunded, qty_shipped FROM sales_order_item WHERE order_id = {pid}"):
        print(i)
    print(f"\n--- Child Items (order_id={cid}) ---")
    for i in query(f"SELECT sku, name, qty_ordered, qty_canceled, qty_refunded, qty_shipped FROM sales_order_item WHERE order_id = {cid}"):
        print(i)
        
    print("\n--- Parent Payment ---")
    for p in query(f"SELECT method FROM sales_order_payment WHERE parent_id = {pid}"):
        print(p)
        
    print("\n--- Parent Credit Memos ---")
    for m in query(f"SELECT state, adjustment, grand_total FROM sales_creditmemo WHERE order_id = {pid}"):
        print(m)

conn.close()
