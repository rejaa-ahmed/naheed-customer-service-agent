from flows.base import BaseFlow, FlowResponse
from ai.schemas import IntentResult
from core.state_manager import ConversationState

class OrderTrackingFlow(BaseFlow):
    def handle(self, intent_result: IntentResult, state: ConversationState) -> FlowResponse:
        entities = intent_result.entities if isinstance(intent_result.entities, dict) else intent_result.entities.model_dump()
        order_id = entities.get("order_id") or state.entities.get("order_id")
        
        if not order_id:
            return FlowResponse(
                status="waiting_for_input",
                response="I can help you track your order. Please provide your Order ID.",
                updated_state={"current_flow": "order_tracking", "waiting_for_order_id": True}
            )
            
        return FlowResponse(
            status="completed",
            response="Looking up your order status...", # Mocking service response delegation
            updated_state={"current_flow": None, "waiting_for_order_id": False},
            tool_request="track_order",
            tool_args={"order_id": order_id}
        )
    def is_continuation(self, intent_result: IntentResult, state: ConversationState) -> bool:
        if intent_result.intent == "order_tracking":
            return True
        entities = intent_result.entities if isinstance(intent_result.entities, dict) else intent_result.entities.model_dump()
        if entities.get("order_id"):
            return True
        # If we asked for an order ID and the user types random numbers, the intent parser 
        # (due to the STATE_CONTEXT_INJECTION prompt rule) will map it to 'order_tracking'.
        # However, if it's completely unparseable, it might still map to "unknown".
        # If it's "unknown", let's see if we should continue.
        # The prompt says: "If the message is neither a valid continuation nor another business intent (e.g. 'Hello', 'Thanks', random text), do not keep the user trapped".
        # So "unknown" with random text should return False, triggering a fallback.
        return False
