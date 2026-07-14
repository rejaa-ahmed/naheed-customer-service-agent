from typing import Dict, Any, Optional
from pydantic import BaseModel
from ai.schemas import IntentResult
from core.state_manager import ConversationState

class FlowResponse(BaseModel):
    status: str  # 'completed', 'waiting_for_input'
    response: str
    updated_state: Dict[str, Any] = {}
    tool_request: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None

class BaseFlow:
    """Interface for all conversational flows."""
    def handle(self, intent_result: IntentResult, state: ConversationState) -> FlowResponse:
        raise NotImplementedError("Each flow must implement handle()")
