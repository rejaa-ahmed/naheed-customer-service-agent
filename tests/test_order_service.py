import sys
import os
import unittest
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.order_service import OrderService
from database.repository import OrderNotFoundError
from database.schema import Order

class TestOrderService(unittest.TestCase):
    def setUp(self):
        # Inject mock repository to isolate business logic tests
        self.mock_repo = MagicMock()
        self.service = OrderService(repository=self.mock_repo)

    def test_track_order_success(self):
        mock_order = Order(entity_id=1, increment_id="12345", status="processing")
        self.mock_repo.get_order_by_increment_id.return_value = mock_order
        
        response = self.service.track_order("12345")
        
        self.assertTrue(response["success"])
        self.assertEqual(response["status"], "processing")
        self.assertIn("• Order ID: 12345", response["message"])
        self.assertIn("• Current Status: processing", response["message"])
        self.assertEqual(response["order"]["increment_id"], "12345")
        
    def test_track_order_unmapped_status(self):
        mock_order = Order(entity_id=2, increment_id="54321", status="custom_status")
        self.mock_repo.get_order_by_increment_id.return_value = mock_order
        
        response = self.service.track_order("54321")
        
        self.assertTrue(response["success"])
        self.assertEqual(response["status"], "custom_status")
        self.assertIn("custom_status", response["message"])
        
    def test_track_order_not_found(self):
        self.mock_repo.get_order_by_increment_id.side_effect = OrderNotFoundError()
        
        response = self.service.track_order("99999")
        
        self.assertFalse(response["success"])
        self.assertIn("couldn't find", response["message"])
        self.assertIsNone(response["status"])
        self.assertIsNone(response["order"])

    def test_track_order_invalid_id(self):
        for invalid_id in ["123!@#", "2000098941@", "abc#123", "20000$"]:
            response = self.service.track_order(invalid_id)
            self.assertFalse(response["success"])
            self.assertIn("invalid characters", response["message"])
        self.mock_repo.get_order_by_increment_id.assert_not_called()

    def test_track_order_valid_id_format(self):
        mock_order = Order(entity_id=3, increment_id="2000098941_2", status="processing")
        self.mock_repo.get_order_by_increment_id.return_value = mock_order
        
        for valid_id in ["2000098941", "2000098941_2", "ORD-123-ABC"]:
            response = self.service.track_order(valid_id)
            self.assertTrue(response["success"])
            self.assertEqual(response["status"], "processing")

    def test_track_order_empty_id(self):
        response = self.service.track_order("   ")
        
        self.assertFalse(response["success"])
        self.assertIn("Please enter a valid Order ID.", response["message"])
        self.mock_repo.get_order_by_increment_id.assert_not_called()

    def test_track_order_db_error(self):
        self.mock_repo.get_order_by_increment_id.side_effect = Exception("Database Timeout")
        
        response = self.service.track_order("12345")
        
        self.assertFalse(response["success"])
        self.assertIn("technical difficulties", response["message"])
        self.assertIsNone(response["status"])

if __name__ == '__main__':
    unittest.main()
