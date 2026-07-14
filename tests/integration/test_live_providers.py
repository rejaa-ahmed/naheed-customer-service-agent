import os
import unittest
from dotenv import load_dotenv
from ai.llm_factory import LLMFactory
from ai.base_client import LLMAPIError

# Load real environment variables
load_dotenv()

class TestLiveProviders(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gemini_key = os.getenv("GEMINI_API_KEY")
        cls.groq_key = os.getenv("GROQ_API_KEY")
        
        # Override the chain for specific tests, but keep the real keys
        cls.factory = LLMFactory()

    @unittest.skipIf(not os.getenv("GEMINI_API_KEY"), "GEMINI_API_KEY not set")
    def test_gemini_connection(self):
        """Test real Gemini API connection"""
        provider = self.factory.instances.get("gemini")
        self.assertIsNotNone(provider)
        
        # Test health check
        self.assertTrue(provider.health_check())
        
        # Test generation
        response = provider.generate_content("Say exactly 'hello'")
        self.assertIn("hello", response.lower())

    @unittest.skipIf(not os.getenv("GROQ_API_KEY"), "GROQ_API_KEY not set")
    def test_groq_connection(self):
        """Test real Groq API connection"""
        provider = self.factory.instances.get("groq")
        self.assertIsNotNone(provider)
        
        self.assertTrue(provider.health_check())
        
        response = provider.generate_content("Say exactly 'hello'")
        self.assertIn("hello", response.lower())

    def test_factory_chain_parsing(self):
        """Test the factory correctly parsed the ordered chain"""
        chain = os.getenv("LLM_PROVIDER_CHAIN", "gemini,groq")
        expected_chain = [p.strip().lower() for p in chain.split(",") if p.strip()]
        
        self.assertEqual(self.factory.provider_chain, expected_chain)

    @unittest.skipIf(not os.getenv("GEMINI_API_KEY") or not os.getenv("GROQ_API_KEY"), "Both keys required for failover test")
    def test_factory_live_failover(self):
        """Test that the factory can successfully execute using the chain"""
        response = self.factory.generate_content_with_failover("Say exactly 'hello failover'")
        self.assertTrue(len(response) > 0)
        self.assertIn("hello", response.lower())

if __name__ == '__main__':
    unittest.main()
