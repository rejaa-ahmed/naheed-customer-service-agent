import sys
import os
import unittest
from unittest.mock import patch, MagicMock
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.state_manager import StateManager
from core.conversation_manager import ConversationManager

class TestStateManager(unittest.TestCase):
    def setUp(self):
        self.sm = StateManager(timeout_seconds=2)
        
    def test_state_initialization(self):
        state = self.sm.get_state("user1")
        self.assertIsNotNone(state)
        self.assertEqual(state.current_flow, None)
        self.assertEqual(state.waiting_for_order_id, False)
        
    def test_state_updates(self):
        self.sm.update_state("user1", {"current_flow": "order_tracking", "waiting_for_order_id": True})
        state = self.sm.get_state("user1")
        self.assertEqual(state.current_flow, "order_tracking")
        self.assertTrue(state.waiting_for_order_id)
        
    def test_entities_update(self):
        self.sm.update_entities("user1", {"order_id": "123", "unknown": None})
        state = self.sm.get_state("user1")
        self.assertEqual(state.entities.get("order_id"), "123")
        self.assertNotIn("unknown", state.entities)
        
    def test_context_expiration(self):
        self.sm.update_state("user1", {"current_flow": "refund"})
        state = self.sm.get_state("user1")
        self.assertEqual(state.current_flow, "refund")
        
        # Manually alter timestamp to simulate timeout
        state.timestamp = time.time() - 5
        
        # Should return a fresh state
        new_state = self.sm.get_state("user1")
        self.assertIsNone(new_state.current_flow)
        
    def test_cancellation(self):
        self.assertTrue(self.sm.check_cancellation("cancel"))
        self.assertTrue(self.sm.check_cancellation("start over"))
        self.assertTrue(self.sm.check_cancellation("never mind"))
        self.assertFalse(self.sm.check_cancellation("track order"))
        self.assertFalse(self.sm.check_cancellation("I want a refund"))

class TestStatefulConversationManager(unittest.TestCase):
    def setUp(self):
        self.mock_parser = MagicMock()
        self.mock_router = MagicMock()
        self.mock_order_service = MagicMock()
        self.mock_order_service.track_order.return_value = {"message": "Order is processing."}
        
        self.cm = ConversationManager(
            parser=self.mock_parser,
            router=self.mock_router,
            order_service=self.mock_order_service
        )
        self.cm.confidence_threshold = 0.85
        self.session_id = "test_user"

    def test_order_tracking_flow(self):
        # 1. User says "Track order"
        intent_1 = MagicMock()
        intent_1.intent = "order_tracking"
        intent_1.confidence = 0.95
        intent_1.entities.model_dump.return_value = {}
        self.mock_parser.parse_intent.return_value = intent_1
        
        res1 = self.cm.process_message("Track order", self.session_id)
        self.assertIn("Please provide your Order ID", res1)
        
        state = self.cm.state_manager.get_state(self.session_id)
        self.assertEqual(state.current_flow, "order_tracking")
        self.assertTrue(state.waiting_for_order_id)
        
        # 2. User provides order ID
        intent_2 = MagicMock()
        intent_2.intent = "order_tracking"
        intent_2.confidence = 0.95
        intent_2.entities.model_dump.return_value = {"order_id": "12345"}
        self.mock_parser.parse_intent.return_value = intent_2
        
        res2 = self.cm.process_message("12345", self.session_id)
        self.assertEqual(res2, "Order is processing.")
        
        # State should be cleared after completed flow
        state = self.cm.state_manager.get_state(self.session_id)
        self.assertIsNone(state.current_flow)
        self.assertEqual(len(state.entities), 0)
        
    def test_complaint_flow(self):
        intent_1 = MagicMock()
        intent_1.intent = "complaint"
        intent_1.confidence = 0.95
        intent_1.entities.model_dump.return_value = {}
        self.mock_parser.parse_intent.return_value = intent_1
        
        res1 = self.cm.process_message("I have a complaint", self.session_id)
        self.assertIn("What is your Order ID?", res1)
        
        state = self.cm.state_manager.get_state(self.session_id)
        self.assertEqual(state.current_flow, "complaint")
        
    def test_refund_flow(self):
        intent_1 = MagicMock()
        intent_1.intent = "refund"
        intent_1.confidence = 0.95
        intent_1.entities.model_dump.return_value = {}
        self.mock_parser.parse_intent.return_value = intent_1
        
        res1 = self.cm.process_message("I need a refund", self.session_id)
        self.assertIn("Please provide the Order ID", res1)
        
        state = self.cm.state_manager.get_state(self.session_id)
        self.assertEqual(state.current_flow, "refund")
        
    def test_cancellation_flow(self):
        # User in flow
        self.cm.state_manager.update_state(self.session_id, {"current_flow": "refund"})
        
        # User says cancel
        res = self.cm.process_message("Never mind", self.session_id)
        self.assertEqual(res, "Conversation reset. How can I help you?")
        
        state = self.cm.state_manager.get_state(self.session_id)
        self.assertIsNone(state.current_flow)

if __name__ == '__main__':
    unittest.main()
