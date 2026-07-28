import time
import threading
from database.repository import OrderRepository

def stress_test():
    print("--- Concurrent Stress Test ---")
    repo = OrderRepository()
    
    results = []
    
    def worker(worker_id):
        start = time.perf_counter()
        try:
            repo.get_order_by_increment_id("2000096085-1")
            elapsed = time.perf_counter() - start
            results.append(elapsed)
            print(f"Worker {worker_id}: Success in {elapsed:.4f}s")
        except Exception as e:
            elapsed = time.perf_counter() - start
            print(f"Worker {worker_id}: Failed after {elapsed:.4f}s - {e}")
            
    threads = []
    for i in range(10): # 10 simultaneous requests
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    if results:
        avg = sum(results) / len(results)
        print(f"Concurrent Avg: {avg:.4f}s over {len(results)} successful requests")
        
if __name__ == "__main__":
    stress_test()
