import time
from database.repository import OrderRepository

def run_db_test():
    repo = OrderRepository()
    
    print("--- Database Latency Testing ---")
    total_time = 0
    iterations = 5
    for _ in range(iterations):
        start_time = time.time()
        try:
            repo.get_order_by_increment_id("2000096085-1")
        except Exception:
            pass
        elapsed = time.time() - start_time
        total_time += elapsed
        print(f"Query {_+1}: {elapsed:.4f}s")
        
    print(f"Avg DB Latency: {total_time/iterations:.4f}s")
    
if __name__ == "__main__":
    run_db_test()
