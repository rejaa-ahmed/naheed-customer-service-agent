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

def find_tables(keyword):
    cursor.execute("SHOW TABLES LIKE %s", (f"%{keyword}%",))
    tables = cursor.fetchall()
    print(f"\n--- Tables containing '{keyword}' ---")
    for t in tables:
        print(list(t.values())[0])

def describe_table(table_name):
    try:
        cursor.execute(f"DESCRIBE {table_name}")
        cols = cursor.fetchall()
        print(f"\n--- Structure of {table_name} ---")
        for c in cols:
            print(f"{c['Field']} ({c['Type']})")
    except Exception as e:
        print(f"Error describing {table_name}: {e}")

find_tables("sales_order")
find_tables("sales_shipment")
find_tables("sales_creditmemo")
find_tables("sales_payment")

describe_table("sales_order")
describe_table("sales_order_item")
describe_table("sales_shipment")
describe_table("sales_shipment_item")
describe_table("sales_payment")
describe_table("sales_creditmemo")

conn.close()
