from flows.base import BaseFlow, FlowResponse
from ai.schemas import IntentResult
from core.state_manager import ConversationState

class RefundFlow(BaseFlow):
    def handle(self, intent_result: IntentResult, state: ConversationState) -> FlowResponse:
        entities = intent_result.entities if isinstance(intent_result.entities, dict) else intent_result.entities.model_dump()
        order_id = entities.get("order_id") or state.entities.get("order_id")
        
        if not order_id:
            return FlowResponse(
                status="waiting_for_input",
                response="I understand you want a refund. Please provide the Order ID.",
                updated_state={"current_flow": "refund", "waiting_for_order_id": True}
            )
            
        return FlowResponse(
            status="completed",
            response="I understand you want a refund. Our refund policy requires the order to be returned within 14 days.",
            updated_state={"current_flow": None, "waiting_for_order_id": False},
            tool_request="process_refund",
            tool_args={"order_id": order_id}
        )
