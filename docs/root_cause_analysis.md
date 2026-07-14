# Root Cause Analysis: Gemini API 429 RESOURCE_EXHAUSTED Loop

## 1. The Execution Path
For a single user message, the request follows this path:
```text
User 
  ↓
Streamlit (or User API)
  ↓
ConversationManager.process_message(message="track order")
  ↓ (message_id is generated)
IntentParser.parse_intent(message="track order", message_id=...)
  ↓
GeminiClient.generate_content(prompt="...", message_id=...)
  ↓
Gemini API
```

## 2. The Root Cause of Duplicate API Requests
Upon analyzing the `ai/gemini_client.py` file, we discovered a highly destructive interaction between the API client configuration and the strict free-tier rate limits.

The `GeminiClient.generate_content()` method was decorated with the `tenacity` library's `@retry` wrapper:
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True
)
```
**Why this caused cascading failures:**
1. When the Free-Tier Google Gemini API returned a `429 RESOURCE_EXHAUSTED` error, the underlying `google-genai` package threw an Exception.
2. The `tenacity` decorator immediately caught the Exception, swallowed it, and initiated a retry loop inside `GeminiClient`.
3. Because the quota had already been hit, the next 2 retries also immediately failed with 429 errors.
4. From the outside (`ConversationManager` and `IntentParser`), it looked like a single long-running request. However, on the network level, **a single user message triggered 3 simultaneous 429 API requests**. This compounded the quota exhaustion limit and artificially delayed the Router Fallback mechanism.

## 3. The Resolution
### Refactoring
1. **Removed Nested Retries:** The `@retry` block was entirely deleted from `GeminiClient.generate_content()`. The client now strictly guarantees one execution per call.
2. **Immediate Fallback Validation:** Now, when a 429 Error, 504 Timeout, or Malformed JSON error occurs, the `GeminiAPIError` bubbles up to `IntentParser`, which wraps it in an `IntentParserError`. The `ConversationManager` catches this and immediately triggers the `legacy_router` without any repeated network hits.

### Observability Added
We have injected strict `message_id` UUID tracking across the stack. The logs now clearly demarcate:
```text
[REQUEST START]
message_id=532a8f8...
user_message=track order
ConversationManager -> IntentParser (message_id=532a8f8...)
IntentParser -> GeminiClient (message_id=532a8f8...)
GeminiClient -> Gemini API (message_id=532a8f8...)
[REQUEST END] message_id=532a8f8...
```
This guarantees that any future duplication is instantly visible on a per-request level in the terminal.

### Validation
A dedicated test suite (`tests/test_retry_logic.py`) was introduced to lock down this behaviour. It utilizes `MagicMock` against the GeminiClient to explicitly assert `call_count == 1`, proving that no loops exist in the ConversationManager or IntentParser logic.
