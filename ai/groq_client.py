import os
import time
from groq import Groq
import groq
from ai.base_client import BaseLLMClient, LLMAPIError
from utils.logger import get_logger
from dotenv import load_dotenv

load_dotenv()
logger = get_logger(__name__)

class GroqClient(BaseLLMClient):
    @property
    def provider_name(self) -> str:
        return "groq"

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.default_model = os.getenv("GROQ_MODEL", "llama3-8b-8192")
        
        if not self.api_key:
            logger.critical("GROQ_API_KEY is missing from environment variables.")
            raise LLMAPIError("GROQ_API_KEY must be set in .env", "groq", 401, False)
            
        # Initialize official Groq client
        self.client = Groq(api_key=self.api_key)
        
    def health_check(self) -> bool:
        try:
            self.generate_content("Ping.", model=self.default_model)
            return True
        except Exception as e:
            logger.error(f"Groq API Health check failed: {e}")
            return False

    def generate_content(self, prompt: str, model: str = None, message_id: str = "unknown") -> str:
        model_name = model or self.default_model
        start_time = time.time()
        
        try:
            logger.debug(f"Sending request to Groq API (Model: {model_name})")
            logger.info(f"GroqClient -> Groq API (message_id={message_id})")
            
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model=model_name,
                temperature=0.0
            )
            
            latency = time.time() - start_time
            logger.info(f"Groq API request successful. Latency: {latency:.4f}s")
            
            return chat_completion.choices[0].message.content
            
        except groq.RateLimitError as e:
            latency = time.time() - start_time
            error_msg = str(e).upper()
            logger.error(f"Groq rate limit exceeded after {latency:.4f}s. Error: {error_msg}")
            raise LLMAPIError(f"Rate limit exceeded: {error_msg}", "groq", 429, True, e) from e
            
        except (groq.APITimeoutError, groq.APIConnectionError) as e:
            latency = time.time() - start_time
            error_msg = str(e).upper()
            logger.error(f"Groq network error after {latency:.4f}s. Error: {error_msg}")
            raise LLMAPIError(f"Network error: {error_msg}", "groq", 504, True, e) from e
            
        except groq.InternalServerError as e:
            latency = time.time() - start_time
            error_msg = str(e).upper()
            logger.error(f"Groq server error after {latency:.4f}s. Error: {error_msg}")
            raise LLMAPIError(f"Server error: {error_msg}", "groq", 500, True, e) from e
            
        except groq.AuthenticationError as e:
            latency = time.time() - start_time
            error_msg = str(e).upper()
            logger.error(f"Groq authentication error after {latency:.4f}s. Error: {error_msg}")
            raise LLMAPIError(f"Authentication error: {error_msg}", "groq", 401, False, e) from e
            
        except groq.BadRequestError as e:
            latency = time.time() - start_time
            error_msg = str(e).upper()
            logger.error(f"Groq bad request error after {latency:.4f}s. Error: {error_msg}")
            raise LLMAPIError(f"Bad request error: {error_msg}", "groq", 400, False, e) from e
            
        except Exception as e:
            latency = time.time() - start_time
            error_msg = str(e).upper()
            logger.error(f"Unexpected Groq API request failed after {latency:.4f}s. Error: {error_msg}")
            raise LLMAPIError(f"Unexpected API request failed: {error_msg}", "groq", None, False, e) from e
