import logging
import sys
from flows.cancel_order import CancelOrderFlow
from core.state_manager import ConversationState
from ai.schemas import IntentResult, EntityExtraction
from services.order_service import OrderService

logging.basicConfig(level=logging.WARNING, stream=sys.stdout)

class MockOrderService(OrderService):
    def get_order_status(self, increment_id):
        if increment_id == "CANCELLED_ORDER":
            return {"success": True, "status": "canceled", "state": "canceled"}
        elif increment_id == "PENDING_ORDER":
            return {"success": True, "status": "pending", "state": "new"}
        elif increment_id == "APPROVED_ORDER":
            return {"success": True, "status": "approved", "state": "processing"}
        elif increment_id == "PICKING_ORDER":
            return {"success": True, "status": "picking", "state": "processing"}
        elif increment_id == "PROCESSING_ORDER":
            return {"success": True, "status": "processing", "state": "processing"}
        return {"success": False, "message": "We couldn't find an order with that ID."}

    def verify_customer(self, increment_id, phone):
        return True
        
    def execute_cancellation(self, increment_id, reason="Unknown reason"):
        return {"success": True, "message": "Your order has been successfully cancelled."}

def run_test():
    service = MockOrderService()
    flow = CancelOrderFlow(order_service=service)

    def test_order(order_id, desc):
        print(f"\\n=== TEST: {desc} ({order_id}) ===")
        state = ConversationState()
        # 1. Ask to cancel -> Should ask for order id
        flow.handle(IntentResult(intent="cancel_order", confidence=0.9, entities=EntityExtraction()), state)
        
        # 2. Provide order id
        res = flow.handle(IntentResult(intent="cancel_order", confidence=0.9, entities=EntityExtraction(order_id=order_id)), state)
        print(f"Response: {res.response}")
        if res.tool_request:
            print(f"Tool Request: {res.tool_request}")

    test_order("CANCELLED_ORDER", "Already cancelled order")
    test_order("PENDING_ORDER", "Pending order")
    test_order("APPROVED_ORDER", "Approved order")
    test_order("PICKING_ORDER", "Picking order")
    test_order("PROCESSING_ORDER", "Processing order")
    test_order("INVALID_ORDER", "Non-existent order")

if __name__ == "__main__":
    run_test()
