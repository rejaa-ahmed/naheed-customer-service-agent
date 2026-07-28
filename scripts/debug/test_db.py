import mysql.connector
from config.settings import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
conn = mysql.connector.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASSWORD)
cursor = conn.cursor(dictionary=True)

cursor.execute("SHOW COLUMNS FROM nhd_sales_order_additionals LIKE 'delivery_due_date'")
col_info = cursor.fetchone()
print('Column Type:', col_info['Type'])

cursor.execute("SELECT delivery_due_date FROM nhd_sales_order_additionals WHERE delivery_due_date IS NOT NULL LIMIT 1")
example = cursor.fetchone()
print('Example Value:', example['delivery_due_date'], type(example['delivery_due_date']).__name__)
