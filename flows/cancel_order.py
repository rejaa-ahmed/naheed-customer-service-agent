from typing import Optional
from flows.base import BaseFlow, FlowResponse
from ai.schemas import IntentResult
from core.state_manager import ConversationState
from services.order_service import OrderService
from utils.logger import get_logger

logger = get_logger(__name__)

class CancelOrderFlow(BaseFlow):
    """
    Handles the intelligent order cancellation workflow.
    Ensures the order is eligible, asks for the reason, and decides whether
    to auto-cancel or redirect to agent handoff.
    """
    def __init__(self, order_service: Optional[OrderService] = None):
        self.order_service = order_service or OrderService()

    def is_continuation(self, intent_result: IntentResult, state: ConversationState) -> bool:
        if state.current_flow == "cancel_order":
            # If the user explicitly asks to cancel again, or provides a reason, it's a continuation.
            return intent_result.intent in ("cancel_order", "unknown", "general_query", "agent_handoff")
        return False

    def handle(self, intent_result: IntentResult, state: ConversationState) -> FlowResponse:
        # Initialize state if this is the first turn
        if state.current_flow != "cancel_order":
            state.current_flow = "cancel_order"
            state.current_stage = "ask_order_id"
            state.waiting_for_order_id = True

        order_id = getattr(intent_result.entities, "order_id", None) or state.entities.get("order_id")

        if state.current_stage == "ask_order_id":
            if not order_id:
                state.waiting_for_order_id = True
                return FlowResponse(
                    status="waiting_for_input",
                    response="Could you please provide the Order ID you would like to cancel?"
                )
            else:
                # We have the order ID. Save it to state and transition to checking eligibility.
                state.entities["order_id"] = order_id
                state.current_stage = "check_eligibility"
                state.waiting_for_order_id = False
                # Fall through to process eligibility in the same turn if we just got the ID.
                # However, for simplicity and natural conversation flow, we process it now.

        if state.current_stage == "check_eligibility":
            status_check = self.order_service.get_order_status(order_id)
            if not status_check.get("success"):
                # Order not found or error
                state.current_flow = None
                state.current_stage = None
                state.customer_verified = False
                state.verification_attempts = 0
                return FlowResponse(
                    status="completed",
                    response=status_check.get("message", "We couldn't find an order with that ID.")
                )

            order_status = (status_check.get("status") or "").lower()
            order_state = (status_check.get("state") or "").lower()
            
            if order_state == "canceled" or order_status == "canceled":
                state.current_flow = None
                state.current_stage = None
                state.customer_verified = False
                state.verification_attempts = 0
                return FlowResponse(
                    status="completed",
                    response="This order has already been cancelled. No further action is required."
                )

            if order_status not in ["pending", "approved"]:
                # Cannot cancel
                state.current_flow = None
                state.current_stage = None
                state.customer_verified = False
                state.verification_attempts = 0
                return FlowResponse(
                    status="completed",
                    response="Your order has already entered fulfillment and cannot be cancelled automatically. Connecting you to a customer support representative for assistance.",
                    tool_request="agent_handoff"
                )
            
            # Eligible. Ask for verification if not already verified.
            if getattr(state, "customer_verified", False):
                state.current_stage = "ask_reason"
                return FlowResponse(
                    status="waiting_for_input",
                    response="Your order is eligible for cancellation. Could you please tell us the reason for cancelling?"
                )
            else:
                state.current_stage = "ask_verification"
                return FlowResponse(
                    status="waiting_for_input",
                    response="For security purposes, please provide the phone number associated with this order."
                )

        if state.current_stage == "ask_verification":
            user_message = state.conversation_history[-1]["content"] if state.conversation_history else ""
            if self.order_service.verify_customer(order_id, user_message):
                state.customer_verified = True
                state.verification_attempts = 0
                state.current_stage = "ask_reason"
                return FlowResponse(
                    status="waiting_for_input",
                    response="Verification successful. Your order is eligible for cancellation. Could you please tell us the reason for cancelling?"
                )
            else:
                state.verification_attempts += 1
                if state.verification_attempts >= 3:
                    state.current_flow = None
                    state.current_stage = None
                    state.verification_attempts = 0
                    return FlowResponse(
                        status="completed",
                        response="We were unable to verify the provided phone number. I'm connecting you with a customer support representative for further assistance.",
                        tool_request="agent_handoff"
                    )
                else:
                    return FlowResponse(
                        status="waiting_for_input",
                        response="The phone number provided does not match our records. Please try again."
                    )

        if state.current_stage == "ask_reason":
            reason = getattr(intent_result.entities, "cancel_reason", None)
            
            if intent_result.intent == "agent_handoff" or intent_result.escalation_recommended:
                state.current_flow = None
                state.current_stage = None
                state.customer_verified = False
                state.verification_attempts = 0
                return FlowResponse(
                    status="completed",
                    response="I understand. I am connecting you to a customer support representative who can assist you with this request.",
                    tool_request="agent_handoff"
                )

            if not reason:
                # If LLM didn't extract a reason, we will try again once.
                # Just fallback to generic unknown logic inside flow.
                return FlowResponse(
                    status="waiting_for_input",
                    response="I didn't quite catch that. Could you please clarify why you'd like to cancel your order? (For example: ordered by mistake, found a better price, shipping is too high)"
                )
                
            if reason in ["price_negotiation", "shipping_negotiation"]:
                state.current_flow = None
                state.current_stage = None
                state.customer_verified = False
                state.verification_attempts = 0
                return FlowResponse(
                    status="completed",
                    response="I understand you have concerns regarding the pricing. I am connecting you to a customer support representative to discuss this further.",
                    tool_request="agent_handoff"
                )
            elif reason in ["duplicate_order", "ordered_by_mistake", "no_longer_needed", "change_of_mind"]:
                # Proceed to cancel
                user_msg = state.conversation_history[-1]["content"] if getattr(state, "conversation_history", None) else "No message provided"
                formatted_reason = f"{user_msg} ({reason})"
                cancel_result = self.order_service.execute_cancellation(order_id, formatted_reason)
                state.current_flow = None
                state.current_stage = None
                state.customer_verified = False
                state.verification_attempts = 0
                return FlowResponse(
                    status="completed",
                    response=cancel_result.get("message", "Your order has been successfully cancelled.")
                )
            else:
                # Default case for unexpected reasons
                state.current_flow = None
                state.current_stage = None
                state.customer_verified = False
                state.verification_attempts = 0
                return FlowResponse(
                    status="completed",
                    response="Thank you for providing the reason. I am connecting you to a customer support representative to finalize your request.",
                    tool_request="agent_handoff"
                )

        # Fallback
        state.current_flow = None
        state.current_stage = None
        state.customer_verified = False
        state.verification_attempts = 0
        return FlowResponse(
            status="completed",
            response="I am connecting you to a representative."
        )
