# Phase 2: AI Intent Parser

## Architecture
The `IntentParser` wraps the `GeminiClient` to classify raw natural language inputs into structured intents based on the `IntentResult` Pydantic schema. It acts as the primary brain of the `ConversationManager`, replacing the legacy rule-based `IntentRouter` while keeping the legacy router exclusively as a fallback layer.

## Intent Flow
1. **User Message:** Received by `ConversationManager`.
2. **Intent Parser:** The text is passed into `IntentParser.parse_intent`.
3. **LLM Invocation:** Uses `gemini-2.5-flash` with the `INTENT_EXTRACTION_PROMPT` containing few-shot examples and strict JSON structural requirements.
4. **Pydantic Validation:** The LLM's text output is cleanly parsed (stripping any Markdown fences like ````json````), injected into `IntentResult`, and validated.

## Confidence Threshold & Fallback Mechanism
The `ConversationManager` pulls `AI_CONFIDENCE_THRESHOLD` from the `.env` lifecycle (defaulting to 0.85). 
If the AI-classified intent's `confidence` is `< 0.85`, or if the `IntentParser` throws an `IntentParserError` (due to API timeout, invalid JSON, or Pydantic validation failure), the `ConversationManager` suppresses the error and instantly falls back to the legacy `router.route()` function. This creates a zero-downtime, fully resilient intent framework.

## Entity Extraction
The prompt asks the LLM to aggressively identify relevant objects inside the message string (e.g. `order_id` in "Where is my parcel 100000123?") and dump them into the schema's `entities` dictionary for downstream mapping.

## Error Handling
The parser implements a robust error barrier:
- `json.JSONDecodeError` → Re-raised as `IntentParserError("Malformed JSON response from LLM")`
- `ValidationError` → Re-raised as `IntentParserError("Schema validation failed")`
- `GeminiAPIError` → Re-raised as `IntentParserError("API Error")`

## Test Coverage
Comprehensive coverage located in `tests/test_intent_parser.py`:
- Markdown parsing immunity
- Intent recognition across domains (greeting, tracking, complaint, refund, query, unknown)
- Entity extraction validation
- Complete failure isolation (malformed JSON, API outages, low-confidence scores) forcing fallback triggers in `ConversationManager`.
