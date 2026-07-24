import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "34.249.120.145")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_NAME = os.getenv("DB_NAME", "pg_1")
DB_USER = os.getenv("DB_USER", "stageusr")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Naheed321@@$$")

def investigate():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        cursor = conn.cursor(dictionary=True)
        
        print("=== SCHEMA OF nhd_complain_tickets ===")
        cursor.execute("DESCRIBE nhd_complain_tickets;")
        columns = cursor.fetchall()
        for col in columns:
            print(f"Field: {col['Field']}, Type: {col['Type']}, Null: {col['Null']}, Key: {col['Key']}, Default: {col['Default']}, Extra: {col['Extra']}")

        print("\n=== INDEXES ===")
        cursor.execute("SHOW INDEX FROM nhd_complain_tickets;")
        indexes = cursor.fetchall()
        for idx in indexes:
            print(f"Table: {idx['Table']}, Key_name: {idx['Key_name']}, Column_name: {idx['Column_name']}, Index_type: {idx['Index_type']}")
            
        print("\n=== SAMPLE DATA (LIMIT 5) ===")
        cursor.execute("SELECT * FROM nhd_complain_tickets LIMIT 5;")
        samples = cursor.fetchall()
        for sample in samples:
            print(sample)
            
        # Check counts per order
        print("\n=== MULTIPLE COMPLAINTS PER ORDER TEST ===")
        cursor.execute("SHOW COLUMNS FROM nhd_complain_tickets LIKE '%order%';")
        order_cols = cursor.fetchall()
        if order_cols:
            order_col_name = order_cols[0]['Field']
            query = f"SELECT {order_col_name}, COUNT(*) as count FROM nhd_complain_tickets GROUP BY {order_col_name} HAVING count > 1 LIMIT 5;"
            cursor.execute(query)
            multiples = cursor.fetchall()
            for m in multiples:
                print(f"Order {m[order_col_name]} has {m['count']} complaints.")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    investigate()
