import unittest
from unittest.mock import MagicMock
from core.conversation_manager import ConversationManager
from core.state_manager import StateManager
from ai.schemas import IntentResult, EntityExtraction

class TestEscalation(unittest.TestCase):
    def setUp(self):
        self.state_manager = StateManager()
        self.mock_parser = MagicMock()
        self.mock_router = MagicMock()
        
        # Make the router default to returning None (so AI parser takes precedence)
        self.mock_router.route.return_value = None
        
        self.manager = ConversationManager(
            parser=self.mock_parser,
            router=self.mock_router,
            state_manager=self.state_manager
        )

    def test_explicit_agent_request(self):
        self.mock_parser.parse_intent.return_value = IntentResult(
            intent="agent_handoff",
            confidence=0.99,
            escalation_recommended=True,
            escalation_reason="explicit_request"
        )
        
        response = self.manager.process_message("I want to talk to a human", "session1")
        self.assertIn("connecting you to a customer support representative", response.lower())
        
        state = self.state_manager.get_state("session1")
        self.assertTrue(state.handoff_pending)

    def test_recommendation_with_user_acceptance(self):
        # 1. User shows frustration, LLM recommends escalation but keeps intent order_tracking
        self.mock_parser.parse_intent.return_value = IntentResult(
            intent="order_tracking",
            confidence=0.99,
            entities=EntityExtraction(order_id="123"),
            escalation_recommended=True,
            escalation_reason="customer_frustration"
        )
        # Mock order service to return something basic
        self.manager.order_service.track_order = MagicMock(return_value={"message": "Your order is pending."})
        
        response1 = self.manager.process_message("Where is my order? This is frustrating!", "session2")
        self.assertIn("Your order is pending", response1)
        self.assertIn("I understand this has been frustrating. Would you like me to connect you", response1)
        
        state = self.state_manager.get_state("session2")
        self.assertEqual(state.pending_confirmation, "agent_handoff")
        
        # 2. User accepts the escalation (multilingual)
        response2 = self.manager.process_message("haan please", "session2")
        self.assertIn("connecting you to a customer support representative", response2.lower())
        
        state = self.state_manager.get_state("session2")
        self.assertIsNone(state.pending_confirmation)
        self.assertTrue(state.handoff_pending)

    def test_recommendation_with_user_rejection(self):
        # 1. User shows frustration, LLM recommends escalation
        self.mock_parser.parse_intent.return_value = IntentResult(
            intent="order_tracking",
            confidence=0.99,
            escalation_recommended=True,
            escalation_reason="customer_frustration"
        )
        self.manager.order_service.track_order = MagicMock(return_value={"message": "Order is pending."})
        
        response1 = self.manager.process_message("Where is my order? This is frustrating!", "session3")
        self.assertIn("connect you with one of our customer support representatives", response1)
        
        # 2. User rejects (e.g. "no I just want my order") -> AI parses it as order_tracking again
        self.mock_parser.parse_intent.return_value = IntentResult(
            intent="order_tracking",
            entities=EntityExtraction(order_id="123"),
            confidence=0.99,
            escalation_recommended=False
        )
        response2 = self.manager.process_message("no just tell me where it is", "session3")
        self.assertNotIn("Connecting you to an agent", response2)
        
        state = self.state_manager.get_state("session3")
        self.assertIsNone(state.pending_confirmation)
        self.assertFalse(state.handoff_pending)

    def test_repeated_unknown_intents(self):
        self.mock_parser.parse_intent.return_value = IntentResult(intent="unknown", confidence=0.99)
        
        self.manager.process_message("blablabla", "session4") # attempt 1
        self.manager.process_message("asdfasdf", "session4")  # attempt 2
        response3 = self.manager.process_message("qwerqwer", "session4")  # attempt 3
        
        # On the 3rd attempt, it should offer escalation
        self.assertIn("connect you with one of our customer support representatives", response3)
        state = self.state_manager.get_state("session4")
        self.assertEqual(state.pending_confirmation, "agent_handoff")

    def test_repeated_backend_failures(self):
        self.mock_parser.parse_intent.return_value = IntentResult(intent="complaint_tracking", confidence=0.99, entities=EntityExtraction(order_no="123"))
        
        # Mock service to return a message containing "issue"
        self.manager.complaint_service.track_complaint = MagicMock(return_value={"message": "We encountered an issue checking your order."})
        
        self.manager.process_message("Track my complaint", "session5") # tool failure 1
        response2 = self.manager.process_message("Track it again", "session5") # tool failure 2
        
        # On the 2nd tool failure, it should offer escalation
        self.assertIn("connect you with one of our customer support representatives", response2)
        state = self.state_manager.get_state("session5")
        self.assertEqual(state.pending_confirmation, "agent_handoff")

    def test_continuation_of_active_business_flow(self):
        # Even if escalation is offered, the business flow response should still be there.
        self.mock_parser.parse_intent.return_value = IntentResult(
            intent="general_policy",
            confidence=0.99,
            entities=EntityExtraction(policy_topic="delivery"),
            escalation_recommended=True,
            escalation_reason="policy_limitation"
        )
        
        response = self.manager.process_message("What is your return policy? I can't find it anywhere!", "session6")
        
        # Should contain BOTH the policy response and the escalation offer
        self.assertIn("Delivery & Shipping Policy", response) # The response from GeneralPolicyFlow for 'delivery'
        self.assertIn("I understand this has been frustrating", response)

    def test_multilingual_confirmations(self):
        for word in ["yes", "haan", "ji", "okay", "sure"]:
            with self.subTest(word=word):
                session_id = f"session_multi_{word}"
                state = self.state_manager.get_state(session_id)
                state.pending_confirmation = "agent_handoff"
                
                # Should not reach the parser because of affirmative match
                self.mock_parser.parse_intent.side_effect = Exception("Should not reach here")
                
                response = self.manager.process_message(word, session_id)
                self.assertIn("connecting you to a customer support representative", response.lower())
                self.assertTrue(self.state_manager.get_state(session_id).handoff_pending)

if __name__ == '__main__':
    unittest.main()
