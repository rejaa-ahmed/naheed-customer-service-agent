import logging
import sys
from flows.cancel_order import CancelOrderFlow
from flows.complaint import ComplaintFlow
from core.state_manager import ConversationState, StateManager
from ai.schemas import IntentResult, EntityExtraction
from services.order_service import OrderService

logging.basicConfig(level=logging.WARNING, stream=sys.stdout)

def test_regressions():
    # 1. Order tracking
    print("\\n=== TEST: Order Tracking ===")
    service = OrderService()
    try:
        res = service.track_order("2000096577") # We know this is a real order in the DB
        print("Track Order Success:", res.get("success"))
    except Exception as e:
        print("Track Order Exception:", e)

    # 2. Cancellation flows & Complaint flow
    state_manager = StateManager()
    state = state_manager.get_state("test_session")
    
    print("\\n=== TEST: Cancellation Flow (Already Cancelled) ===")
    # 2000096577 is actually a real order in DB. Let's see what happens.
    flow = CancelOrderFlow(order_service=service)
    res = flow.handle(IntentResult(intent="cancel_order", confidence=0.9, entities=EntityExtraction(order_id="2000096577")), state)
    print("Cancellation Response:", res.response)
    
    print("\\n=== TEST: Complaint Flow ===")
    comp_flow = ComplaintFlow()
    state.current_flow = None
    state.current_stage = None
    res = comp_flow.handle(IntentResult(intent="complaint", confidence=0.9, entities=EntityExtraction()), state)
    print("Complaint Response:", res.response)

    # 3. Conversation Persistence (Mock)
    print("\\n=== TEST: Conversation Persistence ===")
    state_manager.add_message("test_session", "user", "Hello")
    state_manager.update_state("test_session", {"priority": "high"})
    s = state_manager.get_state("test_session")
    print("Persistence:", s.priority == "high" and len(s.conversation_history) == 1)

if __name__ == "__main__":
    test_regressions()
