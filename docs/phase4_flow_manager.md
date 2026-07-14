# Phase 4: Conversation Flow Orchestration

## Architecture Overview
The core architecture has been heavily decentralized to decouple business flow logic from routing mechanics. The `ConversationManager` is now exclusively a "Thin Coordinator". It handles session state boundaries and exception management, but completely offloads conversational workflow logic to the `FlowManager`.

## Core Components

### 1. The Thin Coordinator (`core/conversation_manager.py`)
- Retrieves the user's conversational state.
- Executes the `IntentParser` to classify the input.
- Passes the classification and state to the `FlowManager`.
- Synchronizes the new state with the `StateManager`.
- Temporary: Mocks service dispatch (to be replaced by `Tool Dispatcher` in Phase 5).

### 2. The Orchestrator (`core/flow_manager.py`)
- Maintains a registry of active conversational sequences (e.g. `OrderTrackingFlow`, `ComplaintFlow`).
- Instantiates and routes the `IntentResult` to the appropriate workflow class.
- Acts as a unified router enforcing the `BaseFlow` interface.

### 3. Workflow Classes (`flows/*.py`)
Each distinct intent now possesses its own dedicated, isolated class encapsulating the steps required to resolve the user's issue. 
- **`OrderTrackingFlow`**: Determines if the user provided an `order_id`. If not, it requests one and locks the state to `waiting_for_input`. Once provided, it emits a `track_order` tool execution request.
- **`ComplaintFlow`**: Requests an `order_id` and prepares the state for logging a formal complaint.
- **`RefundFlow`**: Requests an `order_id` and explains refund policy constraints.
- **`GeneralQueryFlow`**, **`GreetingFlow`**, **`GoodbyeFlow`**, **`UnknownFlow`**: Simple static flows managing boundary dialogue.

## Extensibility & Scaling
This architecture drastically simplifies long-term maintenance. 
**Adding a new conversational capability (e.g., "Cancel Order") only requires:**
1. Creating `flows/cancel_order.py` inheriting from `BaseFlow`.
2. Registering `"cancel_order": CancelOrderFlow()` within `FlowManager`.
No other files require structural modification.

## Flow Interface Protocol
Every Flow class guarantees the execution of `handle(intent_result, state)`, which universally returns a `FlowResponse` Pydantic model:
```python
class FlowResponse(BaseModel):
    status: str  # 'completed', 'waiting_for_input'
    response: str
    updated_state: Dict[str, Any]
    tool_request: Optional[str]
    tool_args: Optional[Dict[str, Any]]
```

By explicitly returning `tool_request` bindings, we have established the final structural prerequisite for Phase 5 (The Tool Dispatcher).
