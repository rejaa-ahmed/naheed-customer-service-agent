from flows.base import BaseFlow, FlowResponse
from ai.schemas import IntentResult
from core.state_manager import ConversationState

class GoodbyeFlow(BaseFlow):
    def handle(self, intent_result: IntentResult, state: ConversationState) -> FlowResponse:
        return FlowResponse(
            status="completed",
            response="Thank you for contacting Naheed. Have a great day!",
            updated_state={"current_flow": None}
        )
