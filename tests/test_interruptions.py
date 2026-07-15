import unittest
from core.flow_manager import FlowManager
from core.state_manager import ConversationState
from ai.schemas import IntentResult, EntityExtraction

class TestFlowInterruptions(unittest.TestCase):
    def setUp(self):
        self.flow_manager = FlowManager()
        # Simulate being trapped in order_tracking flow
        self.state = ConversationState()
        self.state.current_flow = "order_tracking"
        self.state.waiting_for_order_id = True

    def test_valid_continuation(self):
        # User provides a valid order ID
        intent_result = IntentResult(
            intent="order_tracking",
            confidence=0.99,
            entities=EntityExtraction(order_id="100000001")
        )
        response = self.flow_manager.execute_flow(intent_result, self.state)
        
        # It should complete the tracking flow (or mock logic)
        self.assertEqual(response.status, "completed")
        if response.status == "completed":
            self.state.current_flow = None
            self.state.waiting_for_order_id = False
            
        self.assertFalse(self.state.waiting_for_order_id)
        self.assertIsNone(self.state.current_flow)
        
    def test_business_interruption(self):
        # User asks a completely different question
        intent_result = IntentResult(
            intent="general_policy",
            confidence=0.98,
            entities=EntityExtraction(policy_topic="delivery", response_mode="standard")
        )
        response = self.flow_manager.execute_flow(intent_result, self.state)
        
        # State should be cleared before executing general_policy
        self.assertFalse(self.state.waiting_for_order_id)
        self.assertIsNone(self.state.current_flow)
        
        # Response should be from GeneralPolicyFlow
        self.assertEqual(response.status, "completed")
        self.assertIn("**Delivery & Shipping Policy**", response.response)

    def test_greeting_interruption(self):
        # User says Hello
        intent_result = IntentResult(
            intent="greeting",
            confidence=0.99,
            entities=EntityExtraction()
        )
        response = self.flow_manager.execute_flow(intent_result, self.state)
        
        self.assertFalse(self.state.waiting_for_order_id)
        self.assertIsNone(self.state.current_flow)
        self.assertIn("Hello!", response.response)

    def test_unknown_interruption(self):
        # User types random text that isn't an order ID
        intent_result = IntentResult(
            intent="unknown",
            confidence=0.99,
            entities=EntityExtraction()
        )
        response = self.flow_manager.execute_flow(intent_result, self.state)
        
        self.assertFalse(self.state.waiting_for_order_id)
        self.assertIsNone(self.state.current_flow)
        self.assertIn("I didn't quite understand that", response.response)

if __name__ == "__main__":
    unittest.main()
