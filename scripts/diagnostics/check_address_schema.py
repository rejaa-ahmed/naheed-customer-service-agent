from database.connection import DatabaseManager

def check_schema():
    query1 = "SHOW CREATE TABLE sales_order_address"
    try:
        with DatabaseManager() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query1)
            row = cursor.fetchone()
            print("--- sales_order_address SCHEMA ---")
            print(row['Create Table'])
            
            cursor.execute("SELECT * FROM sales_order_address LIMIT 1")
            addr = cursor.fetchone()
            print("\\n--- SAMPLE ADDRESS ---")
            print(addr)
            
            cursor.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_schema()
