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
        self.assertIn("Order ID:\n12345", response["message"])
        self.assertIn("Shipment Status:\nprocessing", response["message"])
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

    def test_track_parent_order_with_child_and_unavailable_items_cod(self):
        child_order = Order(entity_id=2, increment_id="12345-1", status="shipped", tracking_number="TRACK123", carrier_code="lcsshipping", shipping_city="Lahore")
        parent_order = Order(entity_id=1, increment_id="12345", status="processing")
        parent_order.child_orders = [child_order]
        parent_order.unavailable_items = [{"name": "Item A", "qty": 1.0}, {"name": "Item B", "qty": 2.5}]
        parent_order.payment_method = "cashondelivery"
        self.mock_repo.get_order_by_increment_id.return_value = parent_order
        
        response = self.service.track_order("12345")
        
        self.assertTrue(response["success"])
        self.assertEqual(response["status"], "shipped")
        self.assertIn("Order ID:\n12345-1", response["message"])
        self.assertIn("TRACK123", response["message"])
        self.assertIn("Item A (1)", response["message"])
        self.assertIn("Item B (2.5)", response["message"])
        self.assertIn("This order was placed using Cash on Delivery", response["message"])
        self.assertNotIn("refund", response["message"].lower().replace("no refund is required", ""))
        
    def test_track_parent_order_with_multiple_children(self):
        child1 = Order(entity_id=2, increment_id="12345-1", status="shipped")
        child2 = Order(entity_id=3, increment_id="12345-2", status="processing")
        parent_order = Order(entity_id=1, increment_id="12345", status="processing")
        parent_order.child_orders = [child1, child2]
        self.mock_repo.get_order_by_increment_id.return_value = parent_order
        
        response = self.service.track_order("12345")
        
        self.assertTrue(response["success"])
        self.assertEqual(response["status"], "shipped")
        self.assertIn("Order ID:\n12345-1", response["message"])
        
    def test_track_child_order_directly(self):
        child_order = Order(entity_id=2, increment_id="12345-1", status="shipped")
        self.mock_repo.get_order_by_increment_id.return_value = child_order
        
        response = self.service.track_order("12345-1")
        
        self.assertTrue(response["success"])
        self.assertEqual(response["status"], "shipped")
        # Since it's queried directly and has no child_orders of its own, it formats as normal order
        self.assertIn("Order ID:\n12345-1", response["message"])

    def test_child_order_without_tracking_number(self):
        child_order = Order(entity_id=2, increment_id="12345-1", status="shipped", shipping_city="Lahore")
        parent_order = Order(entity_id=1, increment_id="12345", status="processing")
        parent_order.child_orders = [child_order]
        self.mock_repo.get_order_by_increment_id.return_value = parent_order
        
        response = self.service.track_order("12345")
        self.assertIn("handed over for external delivery", response["message"])
        
    def test_child_order_with_eta(self):
        from datetime import datetime, timedelta
        future_eta = datetime.now() + timedelta(days=2)
        child_order = Order(entity_id=2, increment_id="12345-1", status="shipped", estimated_delivery_datetime=future_eta)
        parent_order = Order(entity_id=1, increment_id="12345", status="processing")
        parent_order.child_orders = [child_order]
        self.mock_repo.get_order_by_increment_id.return_value = parent_order
        
        response = self.service.track_order("12345")
        self.assertIn("Estimated Delivery:", response["message"])

    def test_parent_order_refund_completed(self):
        child_order = Order(entity_id=2, increment_id="12345-1", status="shipped")
        parent_order = Order(entity_id=1, increment_id="12345", status="processing")
        parent_order.child_orders = [child_order]
        parent_order.unavailable_items = [{"name": "Item A", "qty": 1.0}]
        parent_order.payment_method = "ccavenuepay"
        parent_order.refund_state = 2
        self.mock_repo.get_order_by_increment_id.return_value = parent_order
        
        response = self.service.track_order("12345")
        self.assertIn("Refund Status:\n• Completed", response["message"])
        
    def test_parent_order_refund_pending(self):
        child_order = Order(entity_id=2, increment_id="12345-1", status="shipped")
        parent_order = Order(entity_id=1, increment_id="12345", status="processing")
        parent_order.child_orders = [child_order]
        parent_order.unavailable_items = [{"name": "Item A", "qty": 1.0}]
        parent_order.payment_method = "ccavenuepay"
        parent_order.refund_state = 1
        self.mock_repo.get_order_by_increment_id.return_value = parent_order
        
        response = self.service.track_order("12345")
        self.assertIn("Refund Status:\n• Processing", response["message"])

    def test_parent_order_no_refund(self):
        child_order = Order(entity_id=2, increment_id="12345-1", status="shipped")
        parent_order = Order(entity_id=1, increment_id="12345", status="processing")
        parent_order.child_orders = [child_order]
        parent_order.unavailable_items = [{"name": "Item A", "qty": 1.0}]
        parent_order.payment_method = "ccavenuepay"
        self.mock_repo.get_order_by_increment_id.return_value = parent_order
        
        response = self.service.track_order("12345")
        self.assertIn("Refund Status:\n• No refund has been initiated yet.", response["message"])

    def test_parent_order_no_unavailable_items(self):
        child_order = Order(entity_id=2, increment_id="12345-1", status="shipped")
        parent_order = Order(entity_id=1, increment_id="12345", status="processing")
        parent_order.child_orders = [child_order]
        self.mock_repo.get_order_by_increment_id.return_value = parent_order
        
        response = self.service.track_order("12345")
        self.assertNotIn("Unavailable Items:", response["message"])

if __name__ == '__main__':
    unittest.main()
