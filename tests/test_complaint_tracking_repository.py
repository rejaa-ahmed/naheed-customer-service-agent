import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.repositories.complaint_tracking_repository import ComplaintTrackingRepository

class TestComplaintTrackingRepository(unittest.TestCase):
    def setUp(self):
        self.repo = ComplaintTrackingRepository()

    @patch('data.repositories.complaint_tracking_repository.DatabaseManager')
    def test_get_order_family_child_lookup(self, mock_db_manager):
        # Scenario: User enters child order '2000096614-1'
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_manager.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # First query: SELECT relation_parent_real_id FROM sales_order WHERE increment_id = %s
        # Returns parent ID
        mock_cursor.fetchone.return_value = {'relation_parent_real_id': '2000096614'}

        # Second query: SELECT increment_id FROM sales_order WHERE increment_id = %s OR relation_parent_real_id = %s
        # Returns parent and child
        mock_cursor.fetchall.return_value = [
            {'increment_id': '2000096614'},
            {'increment_id': '2000096614-1'}
        ]

        family = self.repo.get_order_family('2000096614-1')
        self.assertEqual(family, ['2000096614', '2000096614-1'])

    @patch('data.repositories.complaint_tracking_repository.DatabaseManager')
    def test_get_order_family_parent_lookup(self, mock_db_manager):
        # Scenario: User enters parent order '2000096614'
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_manager.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # First query: SELECT relation_parent_real_id FROM sales_order WHERE increment_id = %s
        # Returns None because it is the parent
        mock_cursor.fetchone.return_value = {'relation_parent_real_id': None}

        # Second query returns parent and child
        mock_cursor.fetchall.return_value = [
            {'increment_id': '2000096614'},
            {'increment_id': '2000096614-1'}
        ]

        family = self.repo.get_order_family('2000096614')
        self.assertEqual(family, ['2000096614', '2000096614-1'])
        
    @patch('data.repositories.complaint_tracking_repository.DatabaseManager')
    def test_get_order_family_multiple_children(self, mock_db_manager):
        # Scenario: User enters parent order '2000096614' which has multiple children
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_manager.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.return_value = {'relation_parent_real_id': None}
        mock_cursor.fetchall.return_value = [
            {'increment_id': '2000096614'},
            {'increment_id': '2000096614-1'},
            {'increment_id': '2000096614-2'}
        ]

        family = self.repo.get_order_family('2000096614')
        self.assertEqual(family, ['2000096614', '2000096614-1', '2000096614-2'])

    @patch('data.repositories.complaint_tracking_repository.DatabaseManager')
    def test_get_order_family_invalid_order(self, mock_db_manager):
        # Scenario: Order doesn't exist in DB
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_manager.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.return_value = None

        family = self.repo.get_order_family('INVALID_999')
        # If it doesn't exist, it should fallback to returning just the entered string
        self.assertEqual(family, ['INVALID_999'])

    @patch.object(ComplaintTrackingRepository, 'get_order_family')
    @patch('data.repositories.complaint_tracking_repository.DatabaseManager')
    def test_find_by_order_queries_family(self, mock_db_manager, mock_get_family):
        # Setup mock family return
        mock_get_family.return_value = ['2000096614', '2000096614-1']
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_manager.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Setup mock DB return
        mock_cursor.fetchall.return_value = [
            {"ticket_no": 123, "order_number": "2000096614-1", "status": "Open"}
        ]
        
        results = self.repo.find_by_order('2000096614')
        
        # Verify get_order_family was called
        mock_get_family.assert_called_with('2000096614')
        
        # Verify the executed SQL query contains IN placeholders and ORDER BY
        call_args = mock_cursor.execute.call_args
        sql_query = call_args[0][0]
        params = call_args[0][1]
        
        self.assertIn("IN (%s, %s)", sql_query)
        self.assertIn("ORDER BY created_at DESC, order_number ASC", sql_query)
        
        # Params should be the two IDs followed by limit and offset
        self.assertEqual(params, ('2000096614', '2000096614-1', 50, 0))
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["ticket_no"], 123)

if __name__ == '__main__':
    unittest.main()
