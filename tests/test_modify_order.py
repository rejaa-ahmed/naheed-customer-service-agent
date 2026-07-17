import sys
import os
import unittest
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flows.modify_order import ModifyOrderFlow
from core.state_manager import ConversationState
from ai.schemas import IntentResult
from services.order_service import OrderService
from database.repository import OrderNotFoundError
from database.schema import Order

class TestModifyOrderFlow(unittest.TestCase):
    def setUp(self):
        self.flow = ModifyOrderFlow()
        self.state = ConversationState()

    def test_flow_trigger_without_order_id(self):
        intent = IntentResult(intent="modify_order", confidence=0.95)
        self.state.conversation_history.append({"role": "user", "content": "I want to change my order"})

        response = self.flow.handle(intent, self.state)

        self.assertEqual(response.status, "waiting_for_input")
        self.assertIn("Please provide your Order ID", response.response)
        self.assertTrue(response.updated_state["waiting_for_order_id"])
        self.assertEqual(response.updated_state["current_flow"], "modify_order")

    def test_flow_trigger_with_order_id(self):
        intent = IntentResult(intent="modify_order", confidence=0.95, entities={"order_id": "100002"})
        self.state.conversation_history.append({"role": "user", "content": "change order 100002"})

        response = self.flow.handle(intent, self.state)

        self.assertEqual(response.status, "completed")
        self.assertEqual(response.tool_request, "modify_order")
        self.assertEqual(response.tool_args["order_id"], "100002")
        self.assertFalse(response.updated_state["waiting_for_order_id"])
        self.assertIsNone(response.updated_state["current_flow"])

    def test_flow_continuation_with_order_id(self):
        self.state.current_flow = "modify_order"
        self.state.waiting_for_order_id = True
        
        # User provides order ID
        intent = IntentResult(intent="modify_order", confidence=0.95, entities={"order_id": "100002"})
        self.state.conversation_history.append({"role": "user", "content": "100002"})
        
        response = self.flow.handle(intent, self.state)
        
        self.assertEqual(response.status, "completed")
        self.assertEqual(response.tool_request, "modify_order")
        self.assertEqual(response.tool_args["order_id"], "100002")


class TestOrderServiceModificationCheck(unittest.TestCase):
    def setUp(self):
        self.mock_repo = MagicMock()
        self.service = OrderService(repository=self.mock_repo)

    def test_check_invalid_order_id(self):
        res1 = self.service.check_order_modifiable(None)
        self.assertFalse(res1["success"])
        self.assertFalse(res1["modifiable"])
        
        res2 = self.service.check_order_modifiable("   ")
        self.assertFalse(res2["success"])
        
        res3 = self.service.check_order_modifiable("123#abc")
        self.assertFalse(res3["success"])

    def test_check_order_not_found(self):
        self.mock_repo.get_order_by_increment_id.side_effect = OrderNotFoundError()
        res = self.service.check_order_modifiable("100028")
        self.assertFalse(res["success"])
        self.assertFalse(res["modifiable"])
        self.assertIn("couldn't find an order", res["message"])

    def test_check_order_packed(self):
        mock_order = Order(entity_id=1, increment_id="100028", status="packed")
        self.mock_repo.get_order_by_increment_id.return_value = mock_order
        
        res = self.service.check_order_modifiable("100028")
        self.assertTrue(res["success"])
        self.assertFalse(res["modifiable"])
        self.assertIn("already been packed or shipped", res["message"])

    def test_check_order_shipped(self):
        mock_order = Order(entity_id=1, increment_id="100028", status="shipped")
        self.mock_repo.get_order_by_increment_id.return_value = mock_order
        
        res = self.service.check_order_modifiable("100028")
        self.assertTrue(res["success"])
        self.assertFalse(res["modifiable"])
        self.assertIn("already been packed or shipped", res["message"])

    def test_check_order_processing_eligible(self):
        mock_order = Order(entity_id=1, increment_id="100028", status="processing")
        self.mock_repo.get_order_by_increment_id.return_value = mock_order
        
        res = self.service.check_order_modifiable("100028")
        self.assertTrue(res["success"])
        self.assertTrue(res["modifiable"])
        self.assertIn("Connecting you to a live agent", res["message"])

if __name__ == '__main__':
    unittest.main()
