import logging
import sys
from database.connection import DatabaseManager

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

def check_schema():
    query1 = "SHOW CREATE TABLE conversation_messages"
    try:
        with DatabaseManager() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query1)
            row = cursor.fetchone()
            print("--- conversation_messages SCHEMA ---")
            print(row['Create Table'])
            cursor.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_schema()
