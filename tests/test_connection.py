import sys
import os

# Add parent dir to path to import successfully when run as a script
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import Database

def run_health_check():
    print("Testing Database Connection...")
    db = Database()
    result = db.health_check()
    
    if result["status"] == "Connected":
        print("✓ Connection Successful")
        print(f"Database Version: {result['version']}")
        print(f"Current Database: {result['database']}")
    else:
        print("✗ Connection Failed")
        print(f"Error: {result.get('error')}")

if __name__ == "__main__":
    run_health_check()
