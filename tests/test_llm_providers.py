import unittest
from unittest.mock import MagicMock, patch
from ai.llm_factory import LLMFactory, ProviderState
from ai.base_client import BaseLLMClient, RecoverableLLMError, UnrecoverableLLMError

class MockProvider(BaseLLMClient):
    def __init__(self, name: str, health: bool = True):
        self._name = name
        self._health = health
        self.generate_mock = MagicMock()
        
    @property
    def provider_name(self) -> str:
        return self._name
        
    def health_check(self) -> bool:
        return self._health
        
    def generate_content(self, prompt: str, model: str = None, message_id: str = "unknown") -> str:
        return self.generate_mock(prompt, model, message_id)


class TestLLMProviders(unittest.TestCase):
    @patch.dict('os.environ', {
        'LLM_PROVIDER_CHAIN': 'mock1,mock2,mock3',
        'LLM_FAILURE_THRESHOLD': '3'
    })
    def setUp(self):
        self.factory = LLMFactory()
        # Register test providers manually, bypassing _load_default_providers defaults
        self.mock1 = MockProvider("mock1")
        self.mock2 = MockProvider("mock2")
        self.mock3 = MockProvider("mock3", health=False) # mock3 is disabled by offline check
        
        self.factory.register_provider("mock1", self.mock1)
        self.factory.register_provider("mock2", self.mock2)
        self.factory.register_provider("mock3", self.mock3)
        
        # Re-initialize chain to apply registered providers
        self.factory._initialize_chain()

    def test_startup_health_check(self):
        self.assertEqual(self.factory.health_stats["mock1"].state, ProviderState.CONFIGURED)
        self.assertEqual(self.factory.health_stats["mock2"].state, ProviderState.CONFIGURED)
        self.assertEqual(self.factory.health_stats["mock3"].state, ProviderState.DISABLED)

    def test_healthy_transition_on_success(self):
        self.mock1.generate_mock.return_value = "Success"
        
        response = self.factory.generate_content_with_failover("Test")
        self.assertEqual(response, "Success")
        self.mock1.generate_mock.assert_called_once()
        self.mock2.generate_mock.assert_not_called()
        
        # Should transition from CONFIGURED -> HEALTHY
        self.assertEqual(self.factory.health_stats["mock1"].state, ProviderState.HEALTHY)

    def test_failover_on_recoverable_error(self):
        self.mock1.generate_mock.side_effect = RecoverableLLMError("Timeout", "mock1", 504)
        self.mock2.generate_mock.return_value = "Fallback Success"
        
        response = self.factory.generate_content_with_failover("Test")
        self.assertEqual(response, "Fallback Success")
        self.mock1.generate_mock.assert_called_once()
        self.mock2.generate_mock.assert_called_once()
        
        # mock1 failed but not 3 times yet, so state should still be CONFIGURED (or HEALTHY if it was already)
        self.assertEqual(self.factory.health_stats["mock1"].state, ProviderState.CONFIGURED)
        self.assertEqual(self.factory.health_stats["mock1"].consecutive_failures, 1)

    def test_stateless_traversal_guarantee(self):
        # Request 1: mock1 fails, mock2 succeeds
        self.mock1.generate_mock.side_effect = RecoverableLLMError("Timeout", "mock1", 504)
        self.mock2.generate_mock.return_value = "Fallback Success"
        self.factory.generate_content_with_failover("Test1")
        
        # Request 2: mock1 recovers
        self.mock1.generate_mock.side_effect = None
        self.mock1.generate_mock.return_value = "Mock1 Success"
        self.mock2.generate_mock.reset_mock()
        
        response = self.factory.generate_content_with_failover("Test2")
        self.assertEqual(response, "Mock1 Success")
        # mock2 should NOT be called on request 2 because traversal is stateless
        self.mock2.generate_mock.assert_not_called()

    def test_progressive_degradation(self):
        self.mock1.generate_mock.side_effect = RecoverableLLMError("Timeout", "mock1", 504)
        self.mock2.generate_mock.return_value = "Success"
        
        # First let's make it HEALTHY
        self.mock1.generate_mock.side_effect = None
        self.mock1.generate_mock.return_value = "Success"
        self.factory.generate_content_with_failover("Test")
        self.assertEqual(self.factory.health_stats["mock1"].state, ProviderState.HEALTHY)
        
        self.mock1.generate_mock.side_effect = RecoverableLLMError("Timeout", "mock1", 504)
        
        # 3 consecutive failures to cross the threshold
        self.factory.generate_content_with_failover("Test")
        self.assertEqual(self.factory.health_stats["mock1"].state, ProviderState.HEALTHY)
        self.factory.generate_content_with_failover("Test")
        self.assertEqual(self.factory.health_stats["mock1"].state, ProviderState.HEALTHY)
        self.factory.generate_content_with_failover("Test")
        self.assertEqual(self.factory.health_stats["mock1"].state, ProviderState.DEGRADED)

    def test_self_healing(self):
        # Force into DEGRADED
        self.mock1.generate_mock.return_value = "Success"
        self.factory.generate_content_with_failover("Test")
        
        self.mock1.generate_mock.side_effect = RecoverableLLMError("Timeout", "mock1", 504)
        self.mock2.generate_mock.return_value = "Success"
        for _ in range(3):
            self.factory.generate_content_with_failover("Test")
            
        self.assertEqual(self.factory.health_stats["mock1"].state, ProviderState.DEGRADED)
        
        # Self-heal on next request
        self.mock1.generate_mock.side_effect = None
        self.mock1.generate_mock.return_value = "Healed"
        
        response = self.factory.generate_content_with_failover("Test")
        self.assertEqual(response, "Healed")
        self.assertEqual(self.factory.health_stats["mock1"].state, ProviderState.HEALTHY)

    def test_failover_on_401_invalid_key(self):
        # mock1 401 fails -> mock2 succeeds
        self.mock1.generate_mock.side_effect = RecoverableLLMError("Authentication failed", "mock1", 401)
        self.mock2.generate_mock.return_value = "Success"
        
        response = self.factory.generate_content_with_failover("Test")
        self.assertEqual(response, "Success")
        self.assertEqual(self.factory.health_stats["mock1"].state, ProviderState.AUTH_FAILED)
        self.assertEqual(self.factory.health_stats["mock1"].consecutive_failures, 0)
        
    def test_cascading_failover_401_to_timeout(self):
        # mock1 401 fails -> mock2 Timeout -> mock3 succeeds (wait, mock3 is DISABLED, let's enable it for this test)
        self.factory.health_stats["mock3"].state = ProviderState.CONFIGURED
        self.mock1.generate_mock.side_effect = RecoverableLLMError("Authentication failed", "mock1", 401)
        self.mock2.generate_mock.side_effect = RecoverableLLMError("Network timeout", "mock2", 504)
        self.mock3.generate_mock.return_value = "Groq Success"
        
        response = self.factory.generate_content_with_failover("Test")
        self.assertEqual(response, "Groq Success")
        self.assertEqual(self.factory.health_stats["mock1"].state, ProviderState.AUTH_FAILED)
        self.assertEqual(self.factory.health_stats["mock2"].consecutive_failures, 1)

    def test_cascading_failover_401_to_invalid_model(self):
        self.factory.health_stats["mock3"].state = ProviderState.CONFIGURED
        self.mock1.generate_mock.side_effect = RecoverableLLMError("Authentication failed", "mock1", 401)
        self.mock2.generate_mock.side_effect = RecoverableLLMError("Model unavailable", "mock2", 404)
        self.mock3.generate_mock.return_value = "Groq Success 2"
        
        response = self.factory.generate_content_with_failover("Test")
        self.assertEqual(response, "Groq Success 2")
        self.assertEqual(self.factory.health_stats["mock1"].state, ProviderState.AUTH_FAILED)
        self.assertEqual(self.factory.health_stats["mock2"].consecutive_failures, 1)

    def test_all_providers_fail_aggregated(self):
        self.factory.health_stats["mock3"].state = ProviderState.CONFIGURED
        self.mock1.generate_mock.side_effect = RecoverableLLMError("Authentication failed", "mock1", 401)
        self.mock2.generate_mock.side_effect = RecoverableLLMError("Network timeout", "mock2", 504)
        self.mock3.generate_mock.side_effect = RecoverableLLMError("Authentication failed", "mock3", 401)
        
        with self.assertRaises(RecoverableLLMError) as cm:
            self.factory.generate_content_with_failover("Test")
            
        self.assertEqual(cm.exception.message, "Authentication failed")
        self.assertEqual(cm.exception.provider, "mock3")
        
    def test_system_wide_error_halts_chain(self):
        self.mock1.generate_mock.side_effect = UnrecoverableLLMError("Malformed payload", "mock1", 400)
        
        with self.assertRaises(UnrecoverableLLMError) as cm:
            self.factory.generate_content_with_failover("Test")
            
        self.assertEqual(cm.exception.message, "Malformed payload")
        self.mock2.generate_mock.assert_not_called()

if __name__ == "__main__":
    unittest.main()
