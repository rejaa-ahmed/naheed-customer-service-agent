from database.connection import DatabaseManager

def check_schema():
    queries = [
        "DESCRIBE sales_order_grid",
        "DESCRIBE sales_order_status_history"
    ]
    try:
        with DatabaseManager() as conn:
            cursor = conn.cursor(dictionary=True)
            for q in queries:
                print(f"--- {q} ---")
                cursor.execute(q)
                for row in cursor.fetchall():
                    print(row)
            cursor.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_schema()
