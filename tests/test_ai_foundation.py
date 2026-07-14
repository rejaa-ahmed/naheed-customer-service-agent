import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.schemas import IntentResult, ToolRequest
from ai.cache import AICache
import ai.prompts as prompts
import ai.tools as tools

class TestAIFoundation(unittest.TestCase):
    
    @patch('os.getenv')
    def test_gemini_client_missing_key(self, mock_getenv):
        mock_getenv.return_value = None
        from ai.gemini_client import GeminiClient
        with self.assertLogs('ai.gemini_client', level='CRITICAL') as log:
            with self.assertRaises(ValueError) as context:
                GeminiClient()
            self.assertIn("GEMINI_API_KEY", str(context.exception))
        self.assertIn("GEMINI_API_KEY is missing", log.output[0])
        
    @patch('os.getenv')
    @patch('ai.gemini_client.genai.Client')
    def test_gemini_client_health_check_success(self, mock_client, mock_getenv):
        mock_getenv.return_value = "fake_key"
        from ai.gemini_client import GeminiClient
        
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        mock_instance.models.generate_content.return_value = MagicMock(text="Pong.")
        
        client = GeminiClient()
        is_healthy = client.health_check()
        self.assertTrue(is_healthy)
        
    def test_schema_validation(self):
        # Valid intent result
        result = IntentResult(intent="order_tracking", confidence=0.9, entities={"order_id": "123"})
        self.assertEqual(result.intent, "order_tracking")
        
        # Valid ToolRequest
        req = ToolRequest(tool_name="track_order", parameters={"order_id": "123"})
        self.assertEqual(req.tool_name, "track_order")
        
    def test_cache_functionality(self):
        cache = AICache(ttl_seconds=1)
        cache.set("test_key", "test_value")
        self.assertEqual(cache.get("test_key"), "test_value")
        cache.clear()
        self.assertIsNone(cache.get("test_key"))
        
    def test_prompt_and_tool_loading(self):
        self.assertIsNotNone(prompts.INTENT_EXTRACTION_PROMPT)
        self.assertTrue(len(tools.TOOLS_DEFINITIONS) > 0)
        
if __name__ == '__main__':
    unittest.main()
