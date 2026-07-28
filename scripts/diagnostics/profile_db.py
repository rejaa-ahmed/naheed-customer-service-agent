import time
import mysql.connector
from config.settings import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

def profile():
    print("DB Performance Report")
    print("-" * 21)
    
    t0 = time.perf_counter()
    
    # 1. Connection acquisition
    t_conn_start = time.perf_counter()
    conn = mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    t_conn_end = time.perf_counter()
    print(f"Connection acquisition: {t_conn_end - t_conn_start:.2f} s")
    
    # 2. Cursor creation
    t_cursor_start = time.perf_counter()
    cursor = conn.cursor(dictionary=True)
    t_cursor_end = time.perf_counter()
    print(f"Cursor creation: {t_cursor_end - t_cursor_start:.2f} s")
    
    # 3. SQL execution
    query = """
        SELECT 
            o.entity_id, 
            o.increment_id, 
            o.status,
            a.delivery_due_date,
            a.courier,
            a.cn_number,
            addr.city,
            addr.firstname,
            addr.lastname,
            addr.telephone,
            addr.street
        FROM sales_order o
        LEFT JOIN nhd_sales_order_additionals a ON o.entity_id = a.order_id
        LEFT JOIN sales_order_address addr ON o.entity_id = addr.parent_id AND addr.address_type = 'shipping'
        WHERE o.increment_id = %s
    """
    t_sql_start = time.perf_counter()
    cursor.execute(query, ("2000096085-1",))
    t_sql_end = time.perf_counter()
    print(f"SQL execution: {t_sql_end - t_sql_start:.2f} s")
    
    # 4. Row fetch
    t_fetch_start = time.perf_counter()
    result = cursor.fetchone()
    cursor.close()
    t_fetch_end = time.perf_counter()
    print(f"Row fetch: {t_fetch_end - t_fetch_start:.2f} s")
    
    # 5. Object mapping
    t_map_start = time.perf_counter()
    if result:
        # Simulate object mapping
        mapped = {
            "entity_id": result["entity_id"],
            "status": result["status"]
        }
    t_map_end = time.perf_counter()
    print(f"Object mapping: {t_map_end - t_map_start:.2f} s")
    
    # 6. Connection close
    t_close_start = time.perf_counter()
    conn.close()
    t_close_end = time.perf_counter()
    print(f"Connection close: {t_close_end - t_close_start:.2f} s")
    
    t_total = time.perf_counter() - t0
    print(f"Total DB time: {t_total:.2f} s")

if __name__ == "__main__":
    profile()
