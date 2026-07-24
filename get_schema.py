from database.connection import DatabaseManager

def get_schema():
    query = "SHOW CREATE TABLE sales_order_status_history"
    try:
        with DatabaseManager() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query)
            row = cursor.fetchone()
            print("--- SCHEMA ---")
            print(row['Create Table'])
            cursor.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_schema()
