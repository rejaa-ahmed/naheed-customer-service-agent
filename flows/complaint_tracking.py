from typing import Dict, Any, Optional
from pydantic import BaseModel
import logging
import re
from core.state_manager import ConversationState
from ai.schemas import IntentResult
from flows.base import BaseFlow, FlowResponse

logger = logging.getLogger(__name__)

class ComplaintTrackingFlow(BaseFlow):
    def __init__(self):
        super().__init__()

    def is_continuation(self, intent_result: IntentResult, state: ConversationState) -> bool:
        return state.current_flow == "complaint_tracking" and state.waiting_for_order_id

    def handle(self, intent_result: IntentResult, state: ConversationState) -> FlowResponse:
        logger.info("ComplaintTrackingFlow.handle() executed")
        order_id = None
        
        # Check entities
        if getattr(intent_result, 'entities', None):
            if isinstance(intent_result.entities, dict):
                order_id = intent_result.entities.get("order_id")
            elif hasattr(intent_result.entities, 'order_id'):
                order_id = intent_result.entities.order_id

        # Check state if not in entities
        if not order_id and state.entities:
            order_id = state.entities.get("order_id")
            
        # Fallback: regex extraction from last user message if order_id still missing
        if not order_id and state.conversation_history:
            last_message = state.conversation_history[-1].get("content", "")
            match = re.search(r'\b\d{5,15}\b', last_message)
            if match:
                order_id = match.group(0)
                logger.info(f"ComplaintTrackingFlow: extracted order_id '{order_id}' via regex fallback.")

        logger.info(f"ComplaintTrackingFlow: received order_id={order_id}")

        if not order_id:
            logger.info("ComplaintTrackingFlow: Order Number is missing. Prompting user.")
            return FlowResponse(
                response="Please provide your Order Number.",
                status="in_progress",
                updated_state={
                    "current_flow": "complaint_tracking",
                    "waiting_for_order_id": True
                }
            )

        logger.info(f"ComplaintTrackingFlow: continuing with order_id={order_id}")
        return FlowResponse(
            response="",  # ConversationManager will handle appending the service response
            status="completed",
            tool_request="track_complaint",
            tool_args={"order_no": order_id},
            updated_state={
                "current_flow": None,
                "waiting_for_order_id": False
            }
        )
