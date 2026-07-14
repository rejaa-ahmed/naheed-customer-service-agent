import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.conversation_manager import ConversationManager
from ai.intent_parser import IntentParser, IntentParserError
from ai.base_client import RecoverableLLMError, UnrecoverableLLMError
from ai.llm_factory import LLMFactory
from ai.schemas import IntentResult
from core.state_manager import StateManager
from core.flow_manager import FlowManager

class TestProductionReliabilityLayer(unittest.TestCase):
    def setUp(self):
        self.mock_factory = MagicMock(spec=LLMFactory)
        self.parser = IntentParser(factory=self.mock_factory)
        self.mock_router = MagicMock()
        self.state_manager = StateManager()
        self.flow_manager = FlowManager()
        
        # Patch flows so they don't do actual business logic that might fail
        self.cm = ConversationManager(
            parser=self.parser, 
            router=self.mock_router,
            state_manager=self.state_manager,
            flow_manager=self.flow_manager
        )
        self.cm.confidence_threshold = 0.85
        
    def test_fallback_on_429(self):
        self.mock_factory.generate_content_with_failover.side_effect = RecoverableLLMError("API request failed: 429")
        self.mock_router.route.return_value = IntentResult(intent="order_tracking", confidence=1.0, entities={}, tool=None)
        
        response = self.cm.process_message("track order")
        
        self.mock_router.route.assert_called_once()
        self.assertIn("Please provide your Order ID", response)
        
    def test_fallback_on_timeout(self):
        self.mock_factory.generate_content_with_failover.side_effect = RecoverableLLMError("API request failed: 504")
        self.mock_router.route.return_value = IntentResult(intent="order_tracking", confidence=1.0, entities={}, tool=None)
        
        response = self.cm.process_message("track order")
        
        self.mock_router.route.assert_called_once()
        self.assertIn("Please provide your Order ID", response)
        
    def test_fallback_on_network_failure(self):
        self.mock_factory.generate_content_with_failover.side_effect = RecoverableLLMError("API request failed: Connection Reset")
        self.mock_router.route.return_value = IntentResult(intent="greeting", confidence=1.0, entities={}, tool=None)
        
        response = self.cm.process_message("hello")
        
        self.mock_router.route.assert_called_once()
        self.assertIn("Welcome to Naheed Customer Support", response)
        
    def test_fallback_on_malformed_json(self):
        self.mock_factory.generate_content_with_failover.return_value = "This is not JSON at all."
        self.mock_router.route.return_value = IntentResult(intent="goodbye", confidence=1.0, entities={}, tool=None)
        
        response = self.cm.process_message("bye")
        
        self.mock_router.route.assert_called_once()
        self.assertIn("Thank you for contacting Naheed", response)
        
    def test_fallback_failure_both_fail(self):
        # Gemini fails
        self.mock_factory.generate_content_with_failover.side_effect = RecoverableLLMError("API request failed")
        
        # Legacy Router also fails (returns None)
        self.mock_router.route.return_value = None
        
        response = self.cm.process_message("some gibberish")
        
        self.mock_router.route.assert_called_once()
        self.assertEqual(response, "I'm having trouble understanding your request. Please try again.")

if __name__ == '__main__':
    unittest.main()
