import sys
import os
import uuid
import logging
from unittest.mock import patch, MagicMock

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.conversation_manager import ConversationManager
from services.conversation_service import ConversationService
from data.repositories.conversation_repository import ConversationRepository
from database.connection import DatabaseManager

logging.basicConfig(level=logging.INFO)

# We want to trace:
# 1. ConversationManager.process_message_with_debug
# 2. ConversationService.save_user_message
# 3. ConversationRepository.get_or_create_session
# 4. ConversationRepository.save_message
# 5. SQL INSERT executed?
# 6. connection.commit() executed?
# 7. Exceptions swallowed?

def trace_execution():
    session_id = str(uuid.uuid4())
    message = "Hello, I want to track my order."
    
    # Let's wrap methods with print statements to see the flow.
    orig_process_message_with_debug = ConversationManager.process_message_with_debug
    orig_save_user_message = ConversationService.save_user_message
    orig_get_or_create = ConversationRepository.get_or_create_session
    orig_save_message = ConversationRepository.save_message
    orig_commit = None # Will wrap at runtime
    orig_execute = None
    
    def wrapped_process(*args, **kwargs):
        print("TRACE: ConversationManager.process_message_with_debug() executed")
        return orig_process_message_with_debug(*args, **kwargs)
        
    def wrapped_save_user_message(*args, **kwargs):
        print("TRACE: ConversationService.save_user_message() executed")
        try:
            return orig_save_user_message(*args, **kwargs)
        except Exception as e:
            print(f"TRACE EXCEPTION in save_user_message: {e}")
            raise
            
    def wrapped_get_or_create(*args, **kwargs):
        print("TRACE: ConversationRepository.get_or_create_session() executed")
        try:
            return orig_get_or_create(*args, **kwargs)
        except Exception as e:
            print(f"TRACE EXCEPTION in get_or_create_session: {e}")
            raise
            
    def wrapped_save_message(*args, **kwargs):
        print("TRACE: ConversationRepository.save_message() executed")
        try:
            return orig_save_message(*args, **kwargs)
        except Exception as e:
            print(f"TRACE EXCEPTION in save_message: {e}")
            raise

    ConversationManager.process_message_with_debug = wrapped_process
    ConversationService.save_user_message = wrapped_save_user_message
    ConversationRepository.get_or_create_session = wrapped_get_or_create
    ConversationRepository.save_message = wrapped_save_message

    print("--- STARTING TRACE ---")
    cm = ConversationManager()
    
    # We also want to intercept cursor.execute and conn.commit
    # We can patch DatabaseManager.__enter__ to return a mock or wrapper
    orig_enter = DatabaseManager.__enter__
    
    class WrappedConnection:
        def __init__(self, real_conn):
            self.real_conn = real_conn
            
        def cursor(self, *args, **kwargs):
            real_cursor = self.real_conn.cursor(*args, **kwargs)
            class WrappedCursor:
                def __init__(self, rc):
                    self.rc = rc
                def execute(self, query, params=None):
                    if "INSERT" in query.upper():
                        print(f"TRACE: SQL INSERT executed -> {query.strip()[:50]}...")
                    try:
                        return self.rc.execute(query, params)
                    except Exception as e:
                        print(f"TRACE EXCEPTION in execute: {e}")
                        raise
                def __getattr__(self, item):
                    return getattr(self.rc, item)
            return WrappedCursor(real_cursor)
            
        def commit(self):
            print("TRACE: connection.commit() executed")
            self.real_conn.commit()
            
        def __getattr__(self, item):
            return getattr(self.real_conn, item)
            
    def wrapped_enter(self):
        real_conn = orig_enter(self)
        return WrappedConnection(real_conn)

    DatabaseManager.__enter__ = wrapped_enter
    
    try:
        response, debug_data = cm.process_message_with_debug(message, session_id)
        print("--- TRACE COMPLETE ---")
    except Exception as e:
        print(f"--- TRACE HALTED BY EXCEPTION: {e} ---")

if __name__ == "__main__":
    trace_execution()
