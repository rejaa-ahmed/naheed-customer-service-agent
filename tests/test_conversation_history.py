import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.repositories.conversation_repository import ConversationRepository
from services.conversation_service import ConversationService

class TestConversationRepository(unittest.TestCase):
    def setUp(self):
        self.repo = ConversationRepository()

    @patch('data.repositories.conversation_repository.DatabaseManager')
    def test_get_or_create_session_existing(self, mock_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        mock_cursor.fetchone.return_value = {'id': 10}
        
        session_id = self.repo.get_or_create_session("sess_123")
        self.assertEqual(session_id, 10)
        mock_cursor.execute.assert_called_once_with("SELECT id FROM conversation_sessions WHERE session_id = %s", ("sess_123",))

    @patch('data.repositories.conversation_repository.DatabaseManager')
    def test_get_or_create_session_new(self, mock_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        mock_cursor.fetchone.return_value = None
        mock_cursor.lastrowid = 15
        
        session_id = self.repo.get_or_create_session("sess_new")
        self.assertEqual(session_id, 15)
        self.assertEqual(mock_cursor.execute.call_count, 2) # SELECT then INSERT

    @patch('data.repositories.conversation_repository.DatabaseManager')
    def test_save_message_swallows_exception(self, mock_db):
        mock_db.side_effect = Exception("DB Connection Error")
        
        try:
            self.repo.save_message(10, 'user', 'hello')
        except Exception as e:
            self.fail(f"Exception was not swallowed: {e}")

class TestConversationService(unittest.TestCase):
    def setUp(self):
        self.mock_repo = MagicMock(spec=ConversationRepository)
        self.service = ConversationService(repository=self.mock_repo)

    def test_save_user_message(self):
        self.mock_repo.get_or_create_session.return_value = 5
        self.service.save_user_message("sess_1", "hi there", intent="greeting", flow_name="general")
        
        self.mock_repo.save_message.assert_called_with(
            conversation_id=5,
            sender='user',
            message='hi there',
            message_type='text',
            intent='greeting',
            flow_name='general',
            confidence=None,
            metadata=None
        )
        self.mock_repo.update_last_activity.assert_called_with("sess_1")

    def test_save_bot_message(self):
        self.mock_repo.get_or_create_session.return_value = 5
        self.service.save_bot_message("sess_1", "hello back")
        
        self.mock_repo.save_message.assert_called_with(
            conversation_id=5,
            sender='assistant',
            message='hello back',
            metadata=None
        )
        self.mock_repo.update_last_activity.assert_called_with("sess_1")

if __name__ == '__main__':
    unittest.main()
