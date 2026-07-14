from flows.base import BaseFlow, FlowResponse
from ai.schemas import IntentResult
from core.state_manager import ConversationState

class GreetingFlow(BaseFlow):
    def handle(self, intent_result: IntentResult, state: ConversationState) -> FlowResponse:
        return FlowResponse(
            status="completed",
            response="Hello! Welcome to Naheed Customer Support. How can I assist you today?",
            updated_state={"current_flow": None}
        )
