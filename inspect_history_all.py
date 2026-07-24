from database.connection import DatabaseManager

def inspect():
    query = "SELECT * FROM sales_order_status_history WHERE comment IS NOT NULL LIMIT 5"
    try:
        with DatabaseManager() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query)
            rows = cursor.fetchall()
            print("--- EXISTING HISTORY ROWS (ALL COLUMNS) ---")
            for r in rows:
                print(r)
            cursor.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect()
