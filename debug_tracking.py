import os
import sys

# Configure logging to print to console
import logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.conversation_manager import ConversationManager

def test_flow():
    cm = ConversationManager()
    session_id = "test_session_123"
    
    print("\n--- User: What is the status of my complaint? ---")
    response1 = cm.process_message("What is the status of my complaint?", session_id)
    print(f"Bot: {response1}")
    
    print("\n--- User: 000016180 ---")
    response2 = cm.process_message("000016180", session_id)
    print(f"Bot: {response2}")

if __name__ == "__main__":
    test_flow()
