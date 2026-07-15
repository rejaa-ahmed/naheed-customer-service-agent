from typing import Dict, Type
from flows.base import BaseFlow, FlowResponse
from ai.schemas import IntentResult
from core.state_manager import ConversationState

# Import all flows
from flows.order_tracking import OrderTrackingFlow
from flows.complaint import ComplaintFlow
from flows.refund import RefundFlow
from flows.general_policy import GeneralPolicyFlow
from flows.general_query import GeneralQueryFlow
from flows.greeting import GreetingFlow
from flows.goodbye import GoodbyeFlow
from flows.unknown import UnknownFlow

class FlowManager:
    """
    Acts as the orchestration layer mapping intents to their respective conversational flows.
    """
    def __init__(self):
        # Register flows
        self._flows: Dict[str, BaseFlow] = {
            "order_tracking": OrderTrackingFlow(),
            "complaint": ComplaintFlow(),
            "refund": RefundFlow(),
            "general_policy": GeneralPolicyFlow(),
            "general_query": GeneralQueryFlow(),
            "greeting": GreetingFlow(),
            "goodbye": GoodbyeFlow(),
            "unknown": UnknownFlow()
        }
        
    def execute_flow(self, intent_result: IntentResult, state: ConversationState) -> FlowResponse:
        # Determine active flow from state, or default to the newly detected intent
        flow_name = state.current_flow or intent_result.intent
        
        flow_instance = self._flows.get(flow_name)
        if not flow_instance:
            # Fallback for unregistered intents
            flow_instance = self._flows["unknown"]
            
        return flow_instance.handle(intent_result, state)
