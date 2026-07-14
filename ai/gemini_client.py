import os
import time
from google import genai
from dotenv import load_dotenv
from utils.logger import get_logger
from ai.base_client import BaseLLMClient, LLMAPIError

load_dotenv()
logger = get_logger(__name__)

class GeminiClient(BaseLLMClient):
    @property
    def provider_name(self) -> str:
        return "gemini"

    def __init__(self):
        # Validate the key exists before startup
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.critical("GEMINI_API_KEY is missing from environment variables.")
            raise LLMAPIError("GEMINI_API_KEY must be set in .env", "gemini", 401, False)
        
        # Initialize official client
        self.client = genai.Client(api_key=api_key)
        self.default_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        
    def health_check(self) -> bool:
        """
        Simple health check to verify API connectivity and authentication.
        """
        try:
            start_time = time.time()
            response = self.client.models.generate_content(
                model=self.default_model,
                contents="Ping."
            )
            latency = time.time() - start_time
            logger.info(f"Gemini API Health check passed. Latency: {latency:.4f}s")
            return True
        except Exception as e:
            logger.error(f"Gemini API Health check failed: {e}")
            return False

    def generate_content(self, prompt: str, model: str = None, message_id: str = "unknown") -> str:
        model_name = model or self.default_model
        start_time = time.time()
        
        try:
            logger.debug(f"Sending request to Gemini API (Model: {model_name})")
            logger.info(f"GeminiClient -> Gemini API (message_id={message_id})")
            response = self.client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            latency = time.time() - start_time
            logger.info(f"Gemini API request successful. Latency: {latency:.4f}s")
            
            if not response or not response.text:
                raise LLMAPIError("Received empty or invalid response from Gemini API.", "gemini", 500, True)
                
            return response.text
            
        except Exception as e:
            latency = time.time() - start_time
            error_msg = str(e).upper()
            logger.error(f"Gemini API request failed after {latency:.4f}s. Error: {error_msg}")
            
            # Use heuristics to classify error
            recoverable_markers = ["429", "RESOURCE_EXHAUSTED", "500", "502", "503", "504", "TIMEOUT", "DEADLINE EXCEEDED", "CONNECTION RESET"]
            status_code = None
            
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg: status_code = 429
            elif "500" in error_msg: status_code = 500
            elif "502" in error_msg: status_code = 502
            elif "503" in error_msg: status_code = 503
            elif "504" in error_msg or "TIMEOUT" in error_msg or "DEADLINE" in error_msg: status_code = 504
            elif "400" in error_msg: status_code = 400
            elif "401" in error_msg: status_code = 401
            elif "403" in error_msg: status_code = 403
            
            is_recoverable = any(marker in error_msg for marker in recoverable_markers)
            
            raise LLMAPIError(
                message=f"API request failed: {error_msg}",
                provider="gemini",
                status_code=status_code,
                recoverable=is_recoverable,
                original_exception=e
            ) from e
