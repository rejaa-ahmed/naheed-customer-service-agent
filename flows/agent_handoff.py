from typing import Dict, Any
from flows.base import BaseFlow, FlowResponse
from ai.schemas import IntentResult
from core.state_manager import ConversationState

class AgentHandoffFlow(BaseFlow):
    def handle(self, intent_result: IntentResult, state: ConversationState) -> FlowResponse:
        # In a real system, this is where we'd invoke the live chat API to create a ticket
        # or alert a representative. 
        
        # Mark handoff as pending, do not clear other context
        state.handoff_pending = True
        state.pending_confirmation = None # Clear this since handoff is triggered
        
        return FlowResponse(
            status="completed",
            response="Connecting you to an agent... A customer support representative will join this chat shortly.",
            tool_request="agent_handoff",
            tool_args={"reason": getattr(intent_result, "escalation_reason", "explicit_request")}
        )

    def is_continuation(self, intent_result: IntentResult, state: ConversationState) -> bool:
        # If we are already handing off, everything is a continuation
        if state.handoff_pending:
            return True
        return intent_result.intent == "agent_handoff"
