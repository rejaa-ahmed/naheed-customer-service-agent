import unittest
from flows.general_policy import GeneralPolicyFlow
from ai.schemas import IntentResult, EntityExtraction
from core.state_manager import ConversationState

class TestGeneralPolicyFlow(unittest.TestCase):
    def setUp(self):
        self.flow = GeneralPolicyFlow()
        self.state = ConversationState()

    def test_delivery_policy(self):
        intent = IntentResult(
            intent="general_policy",
            confidence=0.98,
            entities=EntityExtraction(policy_topic="delivery", response_mode="standard")
        )
        response = self.flow.handle(intent, self.state)
        
        self.assertEqual(response.status, "completed")
        self.assertIn("**Delivery & Shipping Policy**", response.response)
        self.assertIn("Standard Shipping: 48-72 Hours", response.response)
        self.assertIn("*Lahore & Islamabad*", response.response)

    def test_payment_policy(self):
        intent = IntentResult(
            intent="general_policy",
            confidence=0.98,
            entities=EntityExtraction(policy_topic="payment", response_mode="standard")
        )
        response = self.flow.handle(intent, self.state)
        
        self.assertEqual(response.status, "completed")
        self.assertIn("**Payment Methods**", response.response)
        self.assertIn("Cash on Delivery", response.response)
        self.assertIn("Online Visa", response.response)

    def test_fallback_policy(self):
        # Testing unknown topic
        intent = IntentResult(
            intent="general_policy",
            confidence=0.98,
            entities=EntityExtraction(policy_topic="unknown_policy", response_mode="standard")
        )
        response = self.flow.handle(intent, self.state)
        
        self.assertEqual(response.status, "completed")
        self.assertIn("I'm sorry", response.response)
        self.assertIn("(021) 111-624-333", response.response)

    def test_missing_topic(self):
        # Testing None topic
        intent = IntentResult(
            intent="general_policy",
            confidence=0.98,
            entities=EntityExtraction()
        )
        response = self.flow.handle(intent, self.state)
        
        self.assertEqual(response.status, "completed")
        self.assertIn("I'm sorry", response.response)

if __name__ == "__main__":
    unittest.main()
