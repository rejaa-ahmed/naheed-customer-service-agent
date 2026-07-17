import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.llm_factory import LLMFactory, ProviderHealth
from ai.base_client import LLMAPIError

class TestLLMFactory(unittest.TestCase):
    def setUp(self):
        # Prevent actual environment variables from dictating test behavior
        os.environ["LLM_PROVIDER_CHAIN"] = "gemini,groq"
        os.environ["LLM_FAILURE_THRESHOLD"] = "3"
        os.environ["LLM_COOLDOWN_SECONDS"] = "60"
        os.environ["GEMINI_API_KEY"] = "test"
        os.environ["GROQ_API_KEY"] = "test"
        os.environ["GROQ_API_URL"] = "https://test.com"
        os.environ["GROQ_MODEL"] = "groq-test"
        
        # Patch the client classes so they don't do real initialization
        self.MockGemini = MagicMock()
        self.MockGroq = MagicMock()
        
        self.mock_gemini_instance = MagicMock()
        self.mock_groq_instance = MagicMock()
        self.MockGemini.return_value = self.mock_gemini_instance
        self.MockGroq.return_value = self.mock_groq_instance
        
        self.mock_gemini_instance.provider_name = "gemini"
        self.mock_groq_instance.provider_name = "groq"
        self.mock_gemini_instance.health_check.return_value = True
        self.mock_groq_instance.health_check.return_value = True

        # Patch the client classes in ai.gemini_client and ai.groq_client
        self.patcher_gemini = patch('ai.gemini_client.GeminiClient', self.MockGemini)
        self.patcher_groq = patch('ai.groq_client.GroqClient', self.MockGroq)
        self.patcher_gemini.start()
        self.patcher_groq.start()
        self.addCleanup(self.patcher_gemini.stop)
        self.addCleanup(self.patcher_groq.stop)
        
        self.factory = LLMFactory()

    def test_factory_selection_logic(self):
        self.assertEqual(self.factory.provider_chain, ["gemini", "groq"])
        self.assertIn("gemini", self.factory.instances)
        self.assertIn("groq", self.factory.instances)

    def test_gemini_success(self):
        self.mock_gemini_instance.generate_content.return_value = "Gemini Response"
        
        result = self.factory.generate_content_with_failover("test prompt")
        
        self.assertEqual(result, "Gemini Response")
        self.mock_gemini_instance.generate_content.assert_called_once()
        self.mock_groq_instance.generate_content.assert_not_called()

    def test_gemini_recoverable_failover_to_groq(self):
        self.mock_gemini_instance.generate_content.side_effect = LLMAPIError("429 Quota Exceeded", "gemini", 429, True)
        self.mock_groq_instance.generate_content.return_value = "Groq Response"
        
        result = self.factory.generate_content_with_failover("test prompt")
        
        self.assertEqual(result, "Groq Response")
        self.mock_gemini_instance.generate_content.assert_called_once()
        self.mock_groq_instance.generate_content.assert_called_once()

    def test_gemini_timeout_failover_to_groq(self):
        self.mock_gemini_instance.generate_content.side_effect = LLMAPIError("504 Timeout", "gemini", 504, True)
        self.mock_groq_instance.generate_content.return_value = "Groq Response"
        
        result = self.factory.generate_content_with_failover("test prompt")
        
        self.assertEqual(result, "Groq Response")
        self.mock_gemini_instance.generate_content.assert_called_once()
        self.mock_groq_instance.generate_content.assert_called_once()

    def test_both_providers_unavailable(self):
        self.mock_gemini_instance.generate_content.side_effect = LLMAPIError("429", "gemini", 429, True)
        self.mock_groq_instance.generate_content.side_effect = LLMAPIError("500", "groq", 500, True)
        
        with self.assertRaises(LLMAPIError):
            self.factory.generate_content_with_failover("test prompt")

    def test_health_management_cooldown(self):
        # Configure max failures to 1 for quick testing
        self.factory.health_stats["gemini"].max_failures = 1
        
        # Trigger failure
        self.mock_gemini_instance.generate_content.side_effect = LLMAPIError("429", "gemini", 429, True)
        self.mock_groq_instance.generate_content.return_value = "Groq Response"
        
        self.factory.generate_content_with_failover("test prompt")
        
        # Assert gemini is now unhealthy (state: DEGRADED)
        self.assertFalse(self.factory.health_stats["gemini"].is_healthy())
        
        # In the stateless traversal design, gemini will still be tried on the next request.
        # So it should be called again, and failover to groq.
        self.mock_groq_instance.generate_content.reset_mock()
        self.mock_gemini_instance.generate_content.reset_mock()
        
        result = self.factory.generate_content_with_failover("test prompt 2")
        
        self.assertEqual(result, "Groq Response")
        self.mock_gemini_instance.generate_content.assert_called_once()
        self.mock_groq_instance.generate_content.assert_called_once()

    def test_unrecoverable_error_bypasses_failover(self):
        # 401/403 should not hit groq
        self.mock_gemini_instance.generate_content.side_effect = LLMAPIError("Invalid API Key", "gemini", 401, False)
        
        with self.assertRaises(LLMAPIError):
            self.factory.generate_content_with_failover("test prompt")
            
        self.mock_groq_instance.generate_content.assert_not_called()

if __name__ == '__main__':
    unittest.main()
