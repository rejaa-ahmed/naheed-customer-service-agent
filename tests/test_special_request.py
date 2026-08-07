import unittest
from core.router import IntentRouter
from core.state_manager import StateManager
from core.flow_manager import FlowManager
from ai.schemas import IntentResult, EntityExtraction
from core.audit_events import AuditEvent
from unittest.mock import patch, MagicMock

class TestSpecialRequestFeature(unittest.TestCase):
    def setUp(self):
        self.router = IntentRouter()
        self.state_manager = StateManager()
        self.flow_manager = FlowManager()

    def test_router_positive_special_requests(self):
        # The router uses regex as a fallback. Here we test the regex fallback.
        positive_phrases = [
            "mera order jaldi deliver karwa do",
            "dispatch jaldi bhej dein",
            "urgent delivery chahiye",
            "priority delivery karwa dein",
            "express delivery kar dein",
            "same day delivery bhej dein",
            "expedite my order",
            "rush my order",
            "speed up delivery please",
            "special request hai"
        ]
        
        for phrase in positive_phrases:
            result = self.router.route(phrase)
            self.assertEqual(result.intent, "special_request", f"Failed to match: {phrase}")

    def test_router_negative_special_requests(self):
        # These should NOT trigger the special_request fallback regex
        negative_phrases = [
            ("track my order", "order_tracking"),
            ("cancel my order", "cancel_order"),
            ("file a complaint", "complaint"),
            ("refund chahiye", "unknown"), # refund isn't in fallback regex, usually LLM handles it
            ("hello there", "greeting"),
            ("goodbye see you", "unknown"),
            ("What is express delivery?", "unknown"),
            ("Do you offer express delivery?", "unknown"),
            ("What are delivery charges?", "unknown")
        ]
        
        for phrase, expected_fallback_not in negative_phrases:
            result = self.router.route(phrase)
            self.assertNotEqual(result.intent, "special_request", f"Falsely matched: {phrase}")

    def test_router_delayed_order_complaints(self):
        # These should trigger the complaint fallback regex
        complaint_phrases = [
            "order bohat late ho gaya hai",
            "delivery delay ho rahi hai",
            "mera order abhi tak nahi aya",
            "why is my order delayed?",
            "mera parcel receive nahi hua"
        ]
        
        for phrase in complaint_phrases:
            result = self.router.route(phrase)
            self.assertEqual(result.intent, "complaint", f"Failed to match complaint: {phrase}")

    def test_router_mixed_sentences(self):
        # These should trigger special_request
        phrase = "order bohat late ho gaya hai, please jaldi deliver karwa dein"
        result = self.router.route(phrase)
        self.assertEqual(result.intent, "special_request", f"Failed to match mixed sentence: {phrase}")

    @patch('flows.special_request.AuditService')
    def test_special_request_flow_behavior(self, mock_audit_service_class):
        mock_audit_service = mock_audit_service_class.return_value
        state = self.state_manager.get_state("test_session")
        state.current_flow = "some_flow"
        state.current_stage = "some_stage"
        state.conversation_history.append({"role": "user", "content": "expedite my order"})

        # Get the flow instance
        flow = self.flow_manager._flows["special_request"]
        
        # We manually inject the mock so we can verify the call
        flow.audit_service = mock_audit_service
        
        intent_result = IntentResult(intent="special_request", confidence=0.9, entities=EntityExtraction())
        
        response = flow.handle(intent_result, state)
        
        # Verify Audit Log was generated
        mock_audit_service.log_event.assert_called_once()
        call_args = mock_audit_service.log_event.call_args[1]
        self.assertEqual(call_args["event_type"], AuditEvent.SPECIAL_REQUEST)
        self.assertEqual(call_args["metadata"]["original_message"], "expedite my order")
        
        # Verify state is cleared
        self.assertIsNone(state.current_flow)
        self.assertIsNone(state.current_stage)
        
        # Verify response matches handoff
        self.assertEqual(response.status, "completed")
        self.assertEqual(response.tool_request, "agent_handoff")
        self.assertIn("connecting you to a customer support representative", response.response)

if __name__ == '__main__':
    unittest.main()
