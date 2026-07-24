import os
import time
import threading
import unittest
from unittest.mock import patch, MagicMock
from services.rate_limiter_service import RateLimiterService
from core.conversation_manager import ConversationManager

class TestRateLimiterService(unittest.TestCase):
    def setUp(self):
        # Default config for tests
        os.environ["RATE_LIMIT_ENABLED"] = "true"
        os.environ["RATE_LIMIT_CAPACITY"] = "3"
        os.environ["RATE_LIMIT_REFILL_RATE"] = "2" # 2 tokens per second (fast for testing)
        
    def tearDown(self):
        if "RATE_LIMIT_ENABLED" in os.environ:
            del os.environ["RATE_LIMIT_ENABLED"]
        if "RATE_LIMIT_CAPACITY" in os.environ:
            del os.environ["RATE_LIMIT_CAPACITY"]
        if "RATE_LIMIT_REFILL_RATE" in os.environ:
            del os.environ["RATE_LIMIT_REFILL_RATE"]

    def test_normal_requests_and_exhaustion(self):
        limiter = RateLimiterService()
        session_id = "session1"
        
        # Capacity is 3, so first 3 should be allowed.
        self.assertTrue(limiter.is_allowed(session_id)[0])
        self.assertTrue(limiter.is_allowed(session_id)[0])
        self.assertTrue(limiter.is_allowed(session_id)[0])
        
        # 4th should fail instantly
        self.assertFalse(limiter.is_allowed(session_id)[0])

    def test_token_refill(self):
        limiter = RateLimiterService()
        session_id = "session2"
        
        # Exhaust
        self.assertTrue(limiter.is_allowed(session_id)[0])
        self.assertTrue(limiter.is_allowed(session_id)[0])
        self.assertTrue(limiter.is_allowed(session_id)[0])
        self.assertFalse(limiter.is_allowed(session_id)[0])
        
        # Wait 1 second. Refill rate is 2 tokens/sec. We should get 2 tokens.
        time.sleep(1.0)
        
        # Should now be allowed twice
        self.assertTrue(limiter.is_allowed(session_id)[0])
        self.assertTrue(limiter.is_allowed(session_id)[0])
        # Third one should fail again
        self.assertFalse(limiter.is_allowed(session_id)[0])

    def test_separate_session_isolation(self):
        limiter = RateLimiterService()
        session_a = "sessionA"
        session_b = "sessionB"
        
        # Exhaust A
        self.assertTrue(limiter.is_allowed(session_a)[0])
        self.assertTrue(limiter.is_allowed(session_a)[0])
        self.assertTrue(limiter.is_allowed(session_a)[0])
        self.assertFalse(limiter.is_allowed(session_a)[0])
        
        # B should still have full capacity
        self.assertTrue(limiter.is_allowed(session_b)[0])
        self.assertTrue(limiter.is_allowed(session_b)[0])
        self.assertTrue(limiter.is_allowed(session_b)[0])
        self.assertFalse(limiter.is_allowed(session_b)[0])

    def test_disabled_via_environment_variable(self):
        os.environ["RATE_LIMIT_ENABLED"] = "false"
        limiter = RateLimiterService()
        session_id = "session_disabled"
        
        # Should allow way more than capacity (3)
        for _ in range(10):
            self.assertTrue(limiter.is_allowed(session_id)[0])

    def test_concurrent_requests(self):
        limiter = RateLimiterService()
        session_id = "session_concurrent"
        results = []
        
        def make_request():
            results.append(limiter.is_allowed(session_id)[0])
            
        threads = []
        for _ in range(10):
            t = threading.Thread(target=make_request)
            threads.append(t)
            t.start()
            
        for t in threads:
            t.join()
            
        # Capacity is 3, so exactly 3 should be True, 7 should be False
        trues = sum(1 for r in results if r)
        falses = sum(1 for r in results if not r)
        self.assertEqual(trues, 3)
        self.assertEqual(falses, 7)

    @patch('services.rate_limiter_service.RateLimiterService.is_allowed', side_effect=Exception("Redis dead"))
    def test_service_failure_fallback_in_conversation_manager(self, mock_is_allowed):
        # We want to ensure that if RateLimiterService throws an exception,
        # ConversationManager catches it and allows the conversation.
        manager = ConversationManager()
        
        # Mock IntentParser to prevent actual Gemini call and return a basic result
        manager.parser.parse_intent = MagicMock(return_value=MagicMock(confidence=0.9, intent="greeting"))
        manager.flow_manager.handle_intent = MagicMock(return_value=("Hi there", {}))
        
        # process_message_with_debug should NOT return the rejection message
        response, _ = manager.process_message_with_debug("hello", "fail_session")
        
        self.assertNotEqual(response, manager.rate_limiter_service.rejection_message)

if __name__ == '__main__':
    unittest.main()
