from database.connection import DatabaseManager
with DatabaseManager() as conn:
    cursor = conn.cursor(dictionary=True)
    cursor.execute('DESCRIBE sales_order')
    for row in cursor.fetchall():
        if row['Field'] in ('status', 'state', 'canceled'):
            print(row)
