from database.connection import DatabaseManager

with DatabaseManager() as conn:
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT DISTINCT state, status FROM sales_order WHERE state LIKE '%cancel%' OR status LIKE '%cancel%'")
    for row in cursor.fetchall():
        print(f"State: '{row['state']}', Status: '{row['status']}'")
