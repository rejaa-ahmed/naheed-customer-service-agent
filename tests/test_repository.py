import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add project root to path so we can import properly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.repository import OrderRepository, OrderNotFoundError
from database.schema import Order

class TestOrderRepository(unittest.TestCase):
    def setUp(self):
        self.repo = OrderRepository()

    @patch('database.repository.DatabaseManager')
    def test_get_order_success(self, MockDBManager):
        # Mock connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        
        # Setup context manager return
        MockDBManager.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Setup query result
        mock_cursor.fetchone.return_value = {
            "entity_id": 1001,
            "increment_id": "100000001",
            "status": "processing",
            "delivery_due_date": "2026-07-14 12:00:00",
            "city": "Karachi",
            "firstname": "John",
            "lastname": "Doe",
            "telephone": "12345678",
            "street": "Main Street",
            "courier": "leopards",
            "cn_number": "CN12345"
        }
        
        order = self.repo.get_order_by_increment_id("100000001")
        
        self.assertIsInstance(order, Order)
        self.assertEqual(order.entity_id, 1001)
        self.assertEqual(order.increment_id, "100000001")
        self.assertEqual(order.status, "processing")
        
        # Ensure query was executed
        mock_cursor.execute.assert_called_once()
        
    @patch('database.repository.DatabaseManager')
    def test_get_order_not_found(self, MockDBManager):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        
        MockDBManager.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None
        
        with self.assertRaises(OrderNotFoundError):
            self.repo.get_order_by_increment_id("999999999")

    @patch('database.repository.DatabaseManager')
    def test_get_order_db_error(self, MockDBManager):
        # Simulate connection timeout/error
        MockDBManager.return_value.__enter__.side_effect = Exception("Connection Timeout")
        
        with self.assertRaises(RuntimeError):
            self.repo.get_order_by_increment_id("100000001")
            
    @patch('database.repository.DatabaseManager')
    def test_get_order_status_success(self, MockDBManager):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        
        MockDBManager.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Only status should be returned for this method
        mock_cursor.fetchone.return_value = {"status": "complete"}
        
        status = self.repo.get_order_status("100000002")
        self.assertEqual(status, "complete")
        mock_cursor.execute.assert_called_once()

if __name__ == '__main__':
    unittest.main()
