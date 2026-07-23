import logging
import sys
from flows.cancel_order import CancelOrderFlow
from core.state_manager import ConversationState
from ai.schemas import IntentResult, EntityExtraction
from services.order_service import OrderService

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

class MockOrderService(OrderService):
    def get_order_status(self, increment_id):
        if increment_id == "VALID_ORDER":
            return {"success": True, "status": "pending"}
        elif increment_id == "FULFILLED_ORDER":
            return {"success": True, "status": "shipped"}
        return {"success": False, "message": "Order not found."}

    def verify_customer(self, increment_id, phone):
        if increment_id == "VALID_ORDER" and phone == "03001234567":
            return True
        return False
        
    def execute_cancellation(self, increment_id, reason="Unknown reason"):
        return {"success": True, "message": "Successfully cancelled."}

def run_test():
    service = MockOrderService()
    flow = CancelOrderFlow(order_service=service)

    print("=== TEST 1: SUCCESSFUL VERIFICATION AND CANCELLATION ===")
    state = ConversationState()
    
    # 1. Ask to cancel
    res = flow.handle(IntentResult(intent="cancel_order", confidence=0.9, entities=EntityExtraction()), state)
    print(f"Stage 1 Response: {res.response} (Stage: {state.current_stage})")
    
    # 2. Provide order ID
    res = flow.handle(IntentResult(intent="cancel_order", confidence=0.9, entities=EntityExtraction(order_id="VALID_ORDER")), state)
    print(f"Stage 2 Response: {res.response} (Stage: {state.current_stage})")
    
    # 3. Provide correct phone
    state.conversation_history.append({"role": "user", "content": "03001234567"})
    res = flow.handle(IntentResult(intent="cancel_order", confidence=0.9, entities=EntityExtraction(order_id="VALID_ORDER")), state)
    print(f"Stage 3 Response: {res.response} (Stage: {state.current_stage})")
    
    # 4. Provide reason
    res = flow.handle(IntentResult(intent="cancel_order", confidence=0.9, entities=EntityExtraction(cancel_reason="ordered_by_mistake")), state)
    print(f"Stage 4 Response: {res.response} (Stage: {state.current_stage})")


    print("\\n=== TEST 2: FAILED VERIFICATION (3 ATTEMPTS) ===")
    state = ConversationState()
    flow.handle(IntentResult(intent="cancel_order", confidence=0.9, entities=EntityExtraction()), state)
    flow.handle(IntentResult(intent="cancel_order", confidence=0.9, entities=EntityExtraction(order_id="VALID_ORDER")), state)
    
    # Attempt 1
    state.conversation_history.append({"role": "user", "content": "00000"})
    res = flow.handle(IntentResult(intent="cancel_order", confidence=0.9, entities=EntityExtraction(order_id="VALID_ORDER")), state)
    print(f"Attempt 1 Response: {res.response} (Attempts: {state.verification_attempts})")
    
    # Attempt 2
    state.conversation_history.append({"role": "user", "content": "11111"})
    res = flow.handle(IntentResult(intent="cancel_order", confidence=0.9, entities=EntityExtraction(order_id="VALID_ORDER")), state)
    print(f"Attempt 2 Response: {res.response} (Attempts: {state.verification_attempts})")
    
    # Attempt 3
    state.conversation_history.append({"role": "user", "content": "22222"})
    res = flow.handle(IntentResult(intent="cancel_order", confidence=0.9, entities=EntityExtraction(order_id="VALID_ORDER")), state)
    print(f"Attempt 3 Response: {res.response} (Attempts: {state.verification_attempts}, Tool: {res.tool_request})")
    
    print("\\n=== TEST 3: EXISTING CANCELLATION SCENARIO (NOT ELIGIBLE) ===")
    state = ConversationState()
    flow.handle(IntentResult(intent="cancel_order", confidence=0.9, entities=EntityExtraction()), state)
    res = flow.handle(IntentResult(intent="cancel_order", confidence=0.9, entities=EntityExtraction(order_id="FULFILLED_ORDER")), state)
    print(f"Not Eligible Response: {res.response} (Tool: {res.tool_request})")

    print("\\n=== TEST 4: CSR ESCALATION (DURING REASON) ===")
    state = ConversationState()
    flow.handle(IntentResult(intent="cancel_order", confidence=0.9, entities=EntityExtraction()), state)
    flow.handle(IntentResult(intent="cancel_order", confidence=0.9, entities=EntityExtraction(order_id="VALID_ORDER")), state)
    state.conversation_history.append({"role": "user", "content": "03001234567"})
    flow.handle(IntentResult(intent="cancel_order", confidence=0.9, entities=EntityExtraction(order_id="VALID_ORDER")), state)
    
    # Provide escalation reason
    res = flow.handle(IntentResult(intent="agent_handoff", confidence=0.9, escalation_recommended=True, entities=EntityExtraction(order_id="VALID_ORDER")), state)
    print(f"Escalation Response: {res.response} (Tool: {res.tool_request})")


if __name__ == "__main__":
    run_test()
