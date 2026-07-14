# Multi-LLM Provider Architecture

## Overview
To eliminate production outages caused by primary API limits (e.g., 429 RESOURCE_EXHAUSTED from Google Gemini's free tier), the AI layer has been redesigned utilizing a **Factory and Provider Registry Pattern**. This enables instant, automatic failover to secondary LLMs (like Grok) without modifying any downstream chatbot orchestration or business logic.

## Architecture

### 1. The Abstraction (`BaseLLMClient`)
All providers must implement `ai.base_client.BaseLLMClient`, exposing:
- `generate_content(prompt: str, model: str = None, message_id: str) -> str`
- `health_check() -> bool`

**Exception Contract:**
Providers must intercept HTTP errors and raise specific standard exceptions:
- `RecoverableLLMError`: For temporary infrastructure failures (429, timeouts, network loss, 5xx server errors). This explicitly triggers the failover mechanism.
- `UnrecoverableLLMError`: For permanent config errors (400, 401, 403, missing API keys). This immediately bubbles up and bypasses failover to prevent wasting secondary quotas.

### 2. The LLM Factory
The `ai.llm_factory.LLMFactory` maintains a dynamic registry of providers (`{"gemini": GeminiClient, "grok": GrokClient}`).
It instantiates the clients **once** at startup and holds them persistently in memory to optimize cold-starts.

**Failover Sequence:**
1. The `LLMFactory` identifies the primary and fallback providers from the `.env`.
2. It attempts to route the prompt to the primary provider.
3. If the primary provider raises a `RecoverableLLMError`, the factory records the failure metrics, automatically passes the exact same prompt to the fallback provider, and returns the secondary response back to the `IntentParser`.
4. The `ConversationManager` and `IntentParser` remain completely unaware that a failover occurred.

### 3. Provider Health Management
If a provider fails consecutively (e.g., max 3 times), the factory flags the provider as **UNHEALTHY** and begins a configurable cooldown period (e.g., 60 seconds). During this cooldown, the factory bypasses the unhealthy provider entirely to immediately hit the secondary provider, saving request latency. Once the timer expires, it is marked healthy again for retry.

### 4. Observability & Runtime Metrics
The factory logs strict operational metrics on every execution:
```text
INFO  Using Gemini provider.
WARNING Gemini quota exceeded or timeout: API request failed: 429
INFO  Switching to Grok.
INFO  Grok request successful.
INFO  Metrics for [gemini]: Requests=3, Success=2, Failures=1, Failovers=1, AvgLatency=1.2s
INFO  Metrics for [grok]: Requests=1, Success=1, Failures=0, Failovers=0, AvgLatency=0.8s
```

## Configuration
Control the architecture purely through the `.env` file:
```env
LLM_PROVIDER=gemini
FALLBACK_PROVIDER=grok

GEMINI_API_KEY=your_gemini_key
GROK_API_KEY=your_grok_key
```

## Adding Future Providers
To add a new provider (e.g., OpenAI, Claude):
1. Create `ai/openai_client.py` implementing `BaseLLMClient`.
2. Add `"openai": OpenAIClient` to the `_registry` dictionary inside `LLMFactory`.
3. Update `.env` to set `LLM_PROVIDER=openai`.
*(No business logic or core routing code will require modification).*
