import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.conversation_manager import ConversationManager
from ai.intent_parser import IntentParser, IntentParserError
from ai.gemini_client import GeminiClient, GeminiAPIError
from ai.schemas import IntentResult

class TestRetryLogic(unittest.TestCase):
    def setUp(self):
        self.mock_factory = MagicMock()
        self.parser = IntentParser(factory=self.mock_factory)
        self.mock_router = MagicMock()
        self.cm = ConversationManager(parser=self.parser, router=self.mock_router)
        self.cm.confidence_threshold = 0.85
        
    def test_one_message_one_call(self):
        self.mock_factory.generate_content_with_failover.return_value = '{"intent": "greeting", "confidence": 0.95, "entities": {}, "tool": null}'
        
        self.cm.process_message("hello")
        
        # Verify exactly one call to the LLM per user request
        self.assertEqual(self.mock_factory.generate_content_with_failover.call_count, 1)
        self.mock_router.route.assert_not_called()
        
    def test_router_fallback_on_429(self):
        self.mock_factory.generate_content_with_failover.side_effect = GeminiAPIError("API request failed: 429 RESOURCE_EXHAUSTED")
        self.mock_router.route.return_value = IntentResult(intent="unknown", confidence=1.0, entities={}, tool=None)
        
        self.cm.process_message("track order")
        
        # Verify it does NOT loop, strictly 1 call then immediate fallback
        self.assertEqual(self.mock_factory.generate_content_with_failover.call_count, 1)
        self.mock_router.route.assert_called_once()
        
    def test_router_fallback_on_timeout(self):
        self.mock_factory.generate_content_with_failover.side_effect = GeminiAPIError("API request failed: 504 Deadline Exceeded")
        self.mock_router.route.return_value = IntentResult(intent="unknown", confidence=1.0, entities={}, tool=None)
        
        self.cm.process_message("track order")
        
        self.assertEqual(self.mock_factory.generate_content_with_failover.call_count, 1)
        self.mock_router.route.assert_called_once()
        
    def test_router_fallback_on_malformed_json(self):
        self.mock_factory.generate_content_with_failover.return_value = "This is not JSON at all."
        self.mock_router.route.return_value = IntentResult(intent="unknown", confidence=1.0, entities={}, tool=None)
        
        self.cm.process_message("track order")
        
        self.assertEqual(self.mock_factory.generate_content_with_failover.call_count, 1)
        self.mock_router.route.assert_called_once()

if __name__ == '__main__':
    unittest.main()
