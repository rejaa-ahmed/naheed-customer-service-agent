import os
import time
from dotenv import load_dotenv
from core.conversation_manager import ConversationManager

def main():
    print("Loading environment...")
    load_dotenv()
    
    print("Initializing ConversationManager...")
    manager = ConversationManager()
    
    session_id = "test-headless-session"
    message = "hi"
    
    print(f"\nSending message: '{message}'")
    start_time = time.time()
    
    try:
        response, state = manager.process_message_with_debug(message, session_id=session_id)
        end_time = time.time()
        
        print("\n--- RESPONSE ---")
        print(response)
        print(f"----------------")
        print(f"Total time taken: {end_time - start_time:.2f} seconds")
    except Exception as e:
        print(f"\nCRASH: {str(e)}")

if __name__ == "__main__":
    main()
