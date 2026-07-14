import sys
import os

# Add project root to path so we can import properly when run as script
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.repository import OrderRepository, OrderNotFoundError

def run_integration_test():
    print("--- Order Repository Integration Test ---")
    
    try:
        # Prompt the user
        increment_id = input("Enter Order Increment ID: ").strip()
        
        if not increment_id:
            print("No Increment ID provided. Exiting.")
            return

        repo = OrderRepository()

        # Call get_order_by_increment_id()
        print("\nFetching full order data...")
        order = repo.get_order_by_increment_id(increment_id)
        
        print("\n--- Order Details ---")
        print(f"Entity ID    : {order.entity_id}")
        print(f"Increment ID : {order.increment_id}")
        print(f"Status       : {order.status}")
        
        # Call get_order_status()
        print("\nFetching standalone status...")
        status = repo.get_order_status(increment_id)
        
        print(f"\nOrder Status: {status}")
        print("---------------------\n")
        
    except OrderNotFoundError:
        print("\nOrder Not Found\n")
    except Exception as e:
        print(f"\nAn error occurred during testing: {e}\n")

if __name__ == "__main__":
    run_integration_test()
