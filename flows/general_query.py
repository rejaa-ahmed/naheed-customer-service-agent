from flows.base import BaseFlow, FlowResponse
from ai.schemas import IntentResult
from core.state_manager import ConversationState

class GeneralQueryFlow(BaseFlow):
    def handle(self, intent_result: IntentResult, state: ConversationState) -> FlowResponse:
        return FlowResponse(
            status="completed",
            response="I am a customer service bot. I can help you track orders and register complaints. What would you like to do?",
            updated_state={"current_flow": None}
        )
