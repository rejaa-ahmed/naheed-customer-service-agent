import os
import uuid
from core.conversation_manager import ConversationManager
from database.connection import DatabaseManager
from data.repositories.conversation_repository import ConversationRepository
from services.conversation_service import ConversationService

def run_tests():
    session_id = str(uuid.uuid4())
    print(f"--- Starting Tests for Session: {session_id} ---")
    
    manager = ConversationManager()
    
    # 1. Normal message starts a new session
    print("\n[Test 1] User says 'hello'")
    resp1 = manager.process_message("hello", session_id)
    print(f"Bot: {resp1}")
    
    # Check DB
    with DatabaseManager() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM conversation_sessions WHERE session_id = %s ORDER BY id DESC", (session_id,))
        sessions = cursor.fetchall()
        print(f"Sessions after 'hello': {len(sessions)}")
        if sessions:
            first_session_id = sessions[0]['id']
            print(f"Active Session ID: {first_session_id}, Status: {sessions[0]['status']}")
            
        cursor.execute("SELECT * FROM chatbot_messages WHERE conversation_id = %s", (first_session_id,))
        msgs = cursor.fetchall()
        print(f"Messages in session {first_session_id}: {len(msgs)}")
    
    # 2. Goodbye closes the conversation
    print("\n[Test 2] User says 'goodbye'")
    resp2 = manager.process_message("goodbye", session_id)
    print("Bot: (goodbye response truncated for brevity)")
    
    # Check DB
    with DatabaseManager() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM conversation_sessions WHERE session_id = %s ORDER BY id DESC", (session_id,))
        sessions = cursor.fetchall()
        print(f"Sessions after 'goodbye': {len(sessions)}")
        if sessions:
            print(f"Session {sessions[0]['id']} Status: {sessions[0]['status']}")
            
        # Verify bot message was saved before closing?
        # The bot message in ConversationManager happens AT THE END, after `flow_response.end_conversation` check!
        cursor.execute("SELECT * FROM chatbot_messages WHERE conversation_id = %s", (first_session_id,))
        msgs = cursor.fetchall()
        print(f"Messages in session {first_session_id}: {len(msgs)}")
        if msgs:
            print(f"Last message saved: '{msgs[-1]['message'][:30]}...' by {msgs[-1]['sender']}")
    
    # 3. Next message starts brand new session
    print("\n[Test 3] User says 'hello' again")
    resp3 = manager.process_message("hello", session_id)
    
    # Check DB
    with DatabaseManager() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM conversation_sessions WHERE session_id = %s ORDER BY id DESC", (session_id,))
        sessions = cursor.fetchall()
        print(f"Sessions after second 'hello': {len(sessions)}")
        if len(sessions) > 1:
            second_session_id = sessions[0]['id']
            print(f"New Active Session ID: {second_session_id}, Status: {sessions[0]['status']}")
            
        # Check messages for new session
        cursor.execute("SELECT * FROM chatbot_messages WHERE conversation_id = %s", (second_session_id,))
        msgs2 = cursor.fetchall()
        print(f"Messages in NEW session {second_session_id}: {len(msgs2)}")
        
    print("\n--- Tests Complete ---")

if __name__ == "__main__":
    run_tests()
