from database.connection import DatabaseManager

try:
    with DatabaseManager() as conn:
        cursor = conn.cursor()
        cursor.execute('ALTER TABLE conversation_sessions ADD COLUMN ended_at DATETIME NULL')
        conn.commit()
        print("Success")
except Exception as e:
    print(f"Error (might already exist): {e}")
