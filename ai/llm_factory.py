import os
import time
from typing import Dict, Type, List
from ai.base_client import BaseLLMClient, LLMAPIError
from ai.gemini_client import GeminiClient
from ai.groq_client import GroqClient
from utils.logger import get_logger

logger = get_logger(__name__)

class ProviderHealth:
    def __init__(self, name: str, max_failures: int, cooldown_sec: int):
        self.name = name
        self.consecutive_failures = 0
        self.max_failures = max_failures
        self.cooldown_sec = cooldown_sec
        self.last_failure_time = 0.0
        self.unhealthy_until = 0.0
        
        # Metrics
        self.request_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.failover_count = 0
        self.total_latency = 0.0

    def is_healthy(self) -> bool:
        if self.consecutive_failures >= self.max_failures:
            if time.time() > self.unhealthy_until:
                # Cooldown expired, allow retry
                self.reset_health()
                return True
            return False
        return True

    def reset_health(self):
        self.consecutive_failures = 0
        self.unhealthy_until = 0.0
        logger.info(f"Provider {self.name} cooldown expired. Marked HEALTHY for retry.")

    def record_success(self, latency: float):
        self.consecutive_failures = 0
        self.request_count += 1
        self.success_count += 1
        self.total_latency += latency
        
    def record_failure(self, latency: float, trigger_failover: bool = False):
        self.consecutive_failures += 1
        self.request_count += 1
        self.failure_count += 1
        self.total_latency += latency
        self.last_failure_time = time.time()
        
        if trigger_failover:
            self.failover_count += 1
            
        if self.consecutive_failures >= self.max_failures:
            self.unhealthy_until = time.time() + self.cooldown_sec
            logger.warning(f"Provider {self.name} marked UNHEALTHY. Cooldown: {self.cooldown_sec}s")

    def print_metrics(self):
        avg_latency = self.total_latency / self.request_count if self.request_count > 0 else 0
        logger.info(f"Metrics for [{self.name}]: Requests={self.request_count}, Success={self.success_count}, Failures={self.failure_count}, Failovers={self.failover_count}, AvgLatency={avg_latency:.4f}s")


class LLMFactory:
    _registry: Dict[str, Type[BaseLLMClient]] = {
        "gemini": GeminiClient,
        "groq": GroqClient
    }
    
    def __init__(self):
        chain_env = os.getenv("LLM_PROVIDER_CHAIN", "gemini,groq")
        self.provider_chain: List[str] = [p.strip().lower() for p in chain_env.split(",") if p.strip()]
        
        # Read health configs
        max_failures = int(os.getenv("LLM_FAILURE_THRESHOLD", "3"))
        cooldown_sec = int(os.getenv("LLM_COOLDOWN_SECONDS", "60"))
        
        self.instances: Dict[str, BaseLLMClient] = {}
        self.health_stats: Dict[str, ProviderHealth] = {}
        
        # Initialize instances in chain
        for name in self.provider_chain:
            if name in self._registry:
                try:
                    self.instances[name] = self._registry[name]()
                    self.health_stats[name] = ProviderHealth(name, max_failures, cooldown_sec)
                    logger.info(f"Successfully initialized LLM provider: {name}")
                except Exception as e:
                    logger.error(f"Failed to initialize provider {name}: {e}")
            else:
                logger.warning(f"Provider {name} in LLM_PROVIDER_CHAIN is not registered.")
                    
    def _execute_with_provider(self, name: str, prompt: str, message_id: str) -> str:
        provider = self.instances.get(name)
        stats = self.health_stats.get(name)
        
        if not provider or not stats:
            raise LLMAPIError(f"Provider {name} is not initialized.", name, None, False)
            
        if not stats.is_healthy():
            raise LLMAPIError(f"Provider {name} is currently unhealthy.", name, None, True)
            
        start_time = time.time()
        try:
            logger.info(f"Using {name.capitalize()} provider.")
            response = provider.generate_content(prompt, message_id=message_id)
            latency = time.time() - start_time
            stats.record_success(latency)
            stats.print_metrics()
            logger.info(f"{name.capitalize()} request successful.")
            return response
            
        except LLMAPIError as e:
            latency = time.time() - start_time
            stats.record_failure(latency, trigger_failover=e.recoverable)
            stats.print_metrics()
            raise
            
    def generate_content_with_failover(self, prompt: str, message_id: str = "unknown") -> str:
        last_error = None
        
        for i, provider_name in enumerate(self.provider_chain):
            try:
                return self._execute_with_provider(provider_name, prompt, message_id)
            except LLMAPIError as e:
                last_error = e
                if not e.recoverable:
                    logger.error(f"Unrecoverable error from {provider_name}. Bypassing failover.")
                    raise
                
                # If there is another provider in the chain, log failover intent
                if i < len(self.provider_chain) - 1:
                    next_provider = self.provider_chain[i + 1]
                    logger.warning(f"{provider_name.capitalize()} failed (recoverable). Switching to {next_provider.capitalize()}.")
        
        # If we exhausted the chain
        logger.error("All providers in the chain failed.")
        if last_error:
            raise last_error
        else:
            raise LLMAPIError("No valid providers configured in chain.", "factory", None, False)
