# Phase 3: State Management & Conversational Memory

## Architecture Overview
The chatbot has been upgraded from a stateless intent router to a context-aware conversational agent. This was accomplished by introducing a `StateManager` which persists conversation lifecycles and heavily modifies the data sent to the AI. 

The `IntentParser` no longer evaluates messages in a vacuum. It is now dynamically injected with the active workflow state.

## Core Components
1. **StateManager** (`core/state_manager.py`): Tracks active flows, timeout expiration, conversation history, and user intent variables (e.g. `order_id`).
2. **Contextual IntentParser** (`ai/intent_parser.py`): Receives the `ConversationState` and appends a structured `STATE_CONTEXT_INJECTION` template to the prompt.
3. **ConversationManager** (`core/conversation_manager.py`): Acts as the orchestrator. Before asking the LLM what a message means, it checks if there is an active session, passes that context down, and updates the session upon receiving the LLM's entity extraction.

## State Transitions & Lifecycle
A session follows this lifecycle:
1. **Initialization:** A user sends a message. The `StateManager` spawns a new `ConversationState` linked to their `session_id`.
2. **Flow Activation:** If the LLM detects `order_tracking` but no `order_id` is found, the Manager transitions state: `current_flow = "order_tracking"`, `waiting_for_order_id = True`.
3. **Context Injection:** The user replies `12345`. The Manager injects the state block into the LLM prompt. The LLM perfectly extracts `12345` as an `order_id` entity.
4. **Flow Completion:** The service fetches the order data. The state is wiped clean (`clear_state()`) to prevent context bleeding.

## Context Expiration
To prevent stale context (e.g., a user returning 2 hours later and saying "12345" randomly):
- The `StateManager` validates a `timestamp` upon every access.
- The default timeout is **300 seconds** (5 minutes). 
- If the threshold is breached, the session resets automatically.

## Examples Handled Successfully
**Cross-Turn Entity Extraction:**
- *User:* Track my order
- *Bot:* Please provide your order number. (State updated)
- *User:* 100000123 (Injected context allows LLM to map this numeric string to `order_id` instead of defaulting to `unknown`).

**Cancellation:**
- *User:* I want a refund
- *Bot:* Please provide your order number.
- *User:* Never mind (Triggers cancellation keyword hook, wiping the state and aborting the flow).

## Known Limitations
1. **Multi-Flow Stacking:** The state model currently tracks a single `current_flow`. If a user asks "Track order 123 and also I want to complain about it", the bot cannot branch the flow. It must handle them sequentially.
2. **Hardcoded Cancellation:** The `check_cancellation()` method uses a static list of trigger words rather than LLM semantic clustering for maximum performance, but this risks missing highly nuanced cancellations (e.g. "I think I'll just wait").
