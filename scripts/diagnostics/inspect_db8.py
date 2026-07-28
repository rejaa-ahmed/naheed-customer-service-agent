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

print("--- Check Order 2000098287 ---")
order = query("SELECT entity_id, increment_id, relation_parent_id, relation_parent_real_id FROM sales_order WHERE increment_id = '2000098287'")
print(order)

if order:
    eid = order[0]['entity_id']
    print("\n--- Parent Items ---")
    parent_items = query(f"SELECT item_id, sku, name, qty_ordered, parent_item_id FROM sales_order_item WHERE order_id = {eid}")
    for i in parent_items:
        print(i)
        
    print("\n--- Any other orders related? ---")
    related = query(f"SELECT entity_id, increment_id, relation_parent_id, relation_parent_real_id FROM sales_order WHERE relation_parent_id = {eid} OR relation_parent_real_id = '2000098287'")
    for r in related:
        print(r)
        
    for r in related:
        cid = r['entity_id']
        print(f"\n--- Child Items for {r['increment_id']} ---")
        child_items = query(f"SELECT item_id, sku, name, qty_ordered, parent_item_id FROM sales_order_item WHERE order_id = {cid}")
        for i in child_items:
            print(i)

conn.close()
