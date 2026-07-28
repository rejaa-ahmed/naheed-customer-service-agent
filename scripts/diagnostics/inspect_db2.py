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

print("--- Payment Tables ---")
cursor.execute("SHOW TABLES LIKE '%payment%'")
for row in cursor.fetchall():
    print(list(row.values())[0])

print("\n--- Describing sales_order_payment ---")
try:
    cursor.execute("DESCRIBE sales_order_payment")
    for row in cursor.fetchall():
        print(f"{row['Field']} ({row['Type']})")
except Exception as e:
    print(e)

print("\n--- Example Parent/Child Order ---")
# Find a child order (one with relation_parent_id set)
child = query("SELECT entity_id, increment_id, relation_parent_id, relation_parent_real_id FROM sales_order WHERE relation_parent_id IS NOT NULL LIMIT 1")
if child:
    print("Child Order:", child[0])
    parent = query(f"SELECT entity_id, increment_id FROM sales_order WHERE increment_id = '{child[0]['relation_parent_real_id']}' OR entity_id = '{child[0]['relation_parent_id']}' LIMIT 1")
    if parent:
        print("Parent Order:", parent[0])
else:
    print("No child orders found!")

conn.close()
