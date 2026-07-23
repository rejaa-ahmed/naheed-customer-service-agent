from services.order_service import OrderService
from database.connection import DatabaseManager
from database.repository import OrderRepository

def investigate():
    repo = OrderRepository()
    service = OrderService(repository=repo)
    
    with DatabaseManager() as conn:
        cursor = conn.cursor(dictionary=True)
        # Find a pending or approved order that hasn't been canceled yet
        cursor.execute("SELECT increment_id, entity_id FROM sales_order WHERE state != 'canceled' AND status != 'canceled' LIMIT 1")
        order = cursor.fetchone()
        
        print("=== DATABASE CONNECTION INFO ===")
        cursor.execute("SELECT DATABASE() as db")
        print("Database:", cursor.fetchone()['db'])
        cursor.execute("SHOW VARIABLES LIKE 'hostname'")
        host_row = cursor.fetchone()
        print("Hostname:", host_row['Value'] if host_row else 'Unknown')
        cursor.execute("SHOW VARIABLES LIKE 'port'")
        print("Port:", cursor.fetchone()['Value'])
        
        if not order:
            print("No valid order found to test cancellation.")
            return
            
        increment_id = order['increment_id']
        entity_id = order['entity_id']
        print(f"\\n=== TESTING CANCELLATION FOR ORDER {increment_id} (entity_id: {entity_id}) ===")
        
    # Execute cancellation
    result = service.execute_cancellation(increment_id, "test_investigation_reason")
    print("Cancellation Result:", result)
    
    # Query history after cancellation
    with DatabaseManager() as conn:
        cursor = conn.cursor(dictionary=True)
        print(f"\\n=== QUERYING HISTORY FOR parent_id = {entity_id} ===")
        cursor.execute("SELECT * FROM sales_order_status_history WHERE parent_id = %s ORDER BY entity_id DESC", (entity_id,))
        rows = cursor.fetchall()
        
        if rows:
            print(f"Found {len(rows)} history rows for parent_id {entity_id}.")
            for row in rows:
                print(row)
        else:
            print("NO ROWS FOUND IN sales_order_status_history!")
            
        # Also find an existing Magento Admin canceled row to compare
        cursor.execute("SELECT * FROM sales_order_status_history WHERE status = 'canceled' AND comment IS NULL LIMIT 1")
        magento_admin_row = cursor.fetchone()
        
        # If comment is null, it might be standard Magento update. Let's find one with 'canceled'
        cursor.execute("SELECT * FROM sales_order_status_history WHERE status = 'canceled' AND comment LIKE '%canceled by%' LIMIT 1")
        magento_admin_row2 = cursor.fetchone()
        
        print("\\n=== MAGENTO ADMIN CANCELED ROW FOR COMPARISON ===")
        print("Row 1:", magento_admin_row)
        print("Row 2:", magento_admin_row2)
        
        cursor.close()

if __name__ == "__main__":
    investigate()
