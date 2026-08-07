import os
from dotenv import load_dotenv
import mysql.connector
import time

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = os.getenv("DB_PORT", 3306)

print(f"Attempting to connect to database at {DB_HOST}:{DB_PORT} as {DB_USER}...")

start = time.time()
try:
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT,
        connect_timeout=10  # 10 seconds timeout
    )
    if conn.is_connected():
        print(f"SUCCESS: Connected to database in {time.time() - start:.2f} seconds.")
        conn.close()
    else:
        print("FAILED: Connection returned false.")
except Exception as e:
    print(f"FAILED: Exception occurred after {time.time() - start:.2f} seconds.")
    print(f"Error Details: {str(e)}")
