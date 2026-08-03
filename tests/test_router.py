import sys
import os
import unittest
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.router import IntentRouter, IntentResult
from core.conversation_manager import ConversationManager

class TestIntentRouter(unittest.TestCase):
    def setUp(self):
        self.router = IntentRouter()

    def test_greeting_intent(self):
        result = self.router.route("Hello there!")
        self.assertEqual(result.intent, "greeting")
        self.assertTrue(result.confidence > 0)

    def test_order_tracking_with_id(self):
        result = self.router.route("Where is my order 123456?")
        self.assertEqual(result.intent, "order_tracking")
        self.assertEqual(result.entities.get("order_id"), "123456")

    def test_order_tracking_without_id(self):
        result = self.router.route("track my order")
        self.assertEqual(result.intent, "order_tracking")
        self.assertIsNone(result.entities.get("order_id"))

    def test_complaint_intent(self):
        result = self.router.route("I received a damaged item")
        self.assertEqual(result.intent, "complaint")

    def test_general_query(self):
        result = self.router.route("What time do you close?")
        self.assertEqual(result.intent, "general_query")
        
    def test_id_only_assumes_tracking(self):
        # A raw order ID should automatically route to order tracking
        result = self.router.route("9876543")
        self.assertEqual(result.intent, "order_tracking")
        self.assertEqual(result.entities.get("order_id"), "9876543")

class TestConversationManager(unittest.TestCase):
    def setUp(self):
        self.mock_router = MagicMock()
        self.mock_order_service = MagicMock()
        self.manager = ConversationManager(router=self.mock_router, order_service=self.mock_order_service)

    def test_greeting_response(self):
        self.mock_router.route.return_value = IntentResult(intent="greeting", confidence=0.9)
        response = self.manager.process_message("Hi")
        self.assertIn("Welcome to Naheed", response)
        self.mock_order_service.track_order.assert_not_called()

    def test_order_tracking_missing_id(self):
        self.mock_router.route.return_value = IntentResult(intent="order_tracking", confidence=0.8, entities={})
        response = self.manager.process_message("track order")
        self.assertIn("Please provide your Order ID", response)
        self.mock_order_service.track_order.assert_not_called()

    def test_order_tracking_with_id(self):
        # Setup Router Mock
        self.mock_router.route.return_value = IntentResult(
            intent="order_tracking", 
            confidence=0.9, 
            entities={"order_id": "12345"}
        )
        
        # Setup Service Mock
        self.mock_order_service.track_order.return_value = {
            "success": True, 
            "message": "Your order is prepared."
        }
        self.manager.state_manager.get_state("default").customer_verified = True
        
        response = self.manager.process_message("track order 12345")
        
        self.assertIn("Your order is prepared", response)
        self.mock_order_service.track_order.assert_called_once_with("12345")

    def test_complaint_response(self):
        self.mock_router.route.return_value = IntentResult(intent="complaint", confidence=0.9)
        response = self.manager.process_message("I want to complain")
        self.assertIn("I can register your complaint", response)

if __name__ == '__main__':
    unittest.main()
