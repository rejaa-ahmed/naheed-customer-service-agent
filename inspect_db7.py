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

print("--- 1. Parent Order ---")
parent = query("SELECT entity_id, increment_id FROM sales_order WHERE increment_id = '2000098287'")
print(parent)

if parent:
    pid = parent[0]['entity_id']
    
    print("\n--- 2. Child Orders ---")
    children = query(f"SELECT entity_id, increment_id FROM sales_order WHERE relation_parent_id = {pid} OR relation_parent_real_id = '2000098287'")
    print(children)
    
    print("\n--- 3. Parent Order Items ---")
    parent_items = query(f"SELECT item_id, sku, name, qty_ordered, parent_item_id FROM sales_order_item WHERE order_id = {pid}")
    for i in parent_items:
        print(i)
        
    print("\n--- 4. Child Order Items ---")
    child_ids = [str(c['entity_id']) for c in children]
    if child_ids:
        cids_str = ",".join(child_ids)
        child_items = query(f"SELECT order_id, item_id, sku, name, qty_ordered, parent_item_id FROM sales_order_item WHERE order_id IN ({cids_str})")
        for i in child_items:
            print(i)

conn.close()
