import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.intent_parser import IntentParser, IntentParserError
from core.conversation_manager import ConversationManager

class TestIntentParser(unittest.TestCase):
    
    def setUp(self):
        self.mock_factory = MagicMock()
        self.parser = IntentParser(factory=self.mock_factory)
    
    def test_markdown_json_parsing(self):
        self.mock_factory.generate_content_with_failover.return_value = '```json\n{"intent": "greeting", "confidence": 0.99, "entities": {}}\n```'
        result = self.parser.parse_intent("Hello")
        self.assertEqual(result.intent, "greeting")
        
    def test_greeting_intent(self):
        self.mock_factory.generate_content_with_failover.return_value = '{"intent": "greeting", "confidence": 0.99, "entities": {}}'
        result = self.parser.parse_intent("Hi")
        self.assertEqual(result.intent, "greeting")
        
    def test_order_tracking_with_entity(self):
        self.mock_factory.generate_content_with_failover.return_value = '{"intent": "order_tracking", "confidence": 0.95, "entities": {"order_id": "12345"}, "tool": "track_order"}'
        result = self.parser.parse_intent("Track order 12345")
        self.assertEqual(result.intent, "order_tracking")
        self.assertEqual(result.entities.order_id, "12345")
        self.assertEqual(result.tool, "track_order")
        
    def test_complaint_intent(self):
        self.mock_factory.generate_content_with_failover.return_value = '{"intent": "complaint", "confidence": 0.99, "entities": {}}'
        result = self.parser.parse_intent("I want to complain")
        self.assertEqual(result.intent, "complaint")
        
    def test_refund_intent(self):
        self.mock_factory.generate_content_with_failover.return_value = '{"intent": "refund", "confidence": 0.95, "entities": {}}'
        result = self.parser.parse_intent("I want a refund")
        self.assertEqual(result.intent, "refund")
        
    def test_general_query_intent(self):
        self.mock_factory.generate_content_with_failover.return_value = '{"intent": "general_query", "confidence": 0.90, "entities": {}}'
        result = self.parser.parse_intent("Do you sell shoes?")
        self.assertEqual(result.intent, "general_query")
        
    def test_unknown_intent(self):
        self.mock_factory.generate_content_with_failover.return_value = '{"intent": "unknown", "confidence": 0.50, "entities": {}}'
        result = self.parser.parse_intent("asdfasdf")
        self.assertEqual(result.intent, "unknown")
        
    def test_general_policy_intent(self):
        self.mock_factory.generate_content_with_failover.return_value = '{"intent": "general_policy", "confidence": 0.98, "entities": {"policy_topic": "delivery", "response_mode": "standard"}}'
        result = self.parser.parse_intent("What are delivery charges?")
        self.assertEqual(result.intent, "general_policy")
        self.assertEqual(result.entities.policy_topic, "delivery")

    def test_general_policy_negative_regression(self):
        # Even if a user asks something that looks like policy, but is actually tracking, it should map to tracking.
        self.mock_factory.generate_content_with_failover.return_value = '{"intent": "order_tracking", "confidence": 0.99, "entities": {}}'
        result = self.parser.parse_intent("Mera order kidhar hai")
        self.assertEqual(result.intent, "order_tracking")
        
    def test_invalid_json(self):
        self.mock_factory.generate_content_with_failover.return_value = '{intent: greeting, confidence: 0.9}' # missing quotes
        with self.assertRaises(IntentParserError) as e:
            self.parser.parse_intent("Hello")
        self.assertIn("Malformed JSON", str(e.exception))
        
    def test_missing_intent_field(self):
        self.mock_factory.generate_content_with_failover.return_value = '{"confidence": 0.9, "entities": {}}'
        with self.assertRaises(IntentParserError) as e:
            self.parser.parse_intent("Hello")
        self.assertIn("Schema validation failed", str(e.exception))
        
    def test_gemini_api_failure(self):
        from ai.gemini_client import GeminiAPIError
        self.mock_factory.generate_content_with_failover.side_effect = GeminiAPIError("API Timeout")
        with self.assertRaises(IntentParserError) as e:
            self.parser.parse_intent("Hello")
        self.assertIn("API Error", str(e.exception))

class TestConversationManagerPhase2(unittest.TestCase):
    
    def setUp(self):
        self.mock_parser = MagicMock()
        self.mock_router = MagicMock()
        self.mock_order_service = MagicMock()
        
        self.cm = ConversationManager(
            parser=self.mock_parser,
            router=self.mock_router,
            order_service=self.mock_order_service
        )
        self.cm.confidence_threshold = 0.85
        
    def test_high_confidence_ai_routing(self):
        # AI returns confident response
        ai_result = MagicMock()
        ai_result.intent = "greeting"
        ai_result.confidence = 0.95
        ai_result.entities.model_dump.return_value = {}
        self.mock_parser.parse_intent.return_value = ai_result
        
        response = self.cm.process_message("Hi")
        self.mock_router.route.assert_not_called()
        self.assertEqual(response, "Hello! Welcome to Naheed Customer Support. How can I assist you today?")
        
    def test_low_confidence_fallback(self):
        # AI returns low confidence
        ai_result = MagicMock()
        ai_result.intent = "unknown"
        ai_result.confidence = 0.50
        self.mock_parser.parse_intent.return_value = ai_result
        
        # Router fallback
        router_result = MagicMock()
        router_result.intent = "greeting"
        router_result.confidence = 1.0
        router_result.entities = {}
        self.mock_router.route.return_value = router_result
        
        response = self.cm.process_message("Hi there")
        self.mock_router.route.assert_called_once_with("Hi there")
        self.assertEqual(response, "Hello! Welcome to Naheed Customer Support. How can I assist you today?")
        
    def test_ai_parsing_error_fallback(self):
        self.mock_parser.parse_intent.side_effect = IntentParserError("Bad JSON")
        
        router_result = MagicMock()
        router_result.intent = "greeting"
        router_result.confidence = 1.0
        router_result.entities = {}
        self.mock_router.route.return_value = router_result
        
        response = self.cm.process_message("Hi")
        self.mock_router.route.assert_called_once_with("Hi")

if __name__ == '__main__':
    unittest.main()
