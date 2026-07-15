import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flows.complaint import ComplaintFlow
from core.state_manager import ConversationState
from ai.schemas import IntentResult
from services.complaint_service import ComplaintService

class TestComplaintFeature(unittest.TestCase):
    
    def setUp(self):
        self.mock_order_repo = MagicMock()
        self.mock_order_repo.resolve_to_latest_order_id.side_effect = lambda x: x
        self.mock_order_repo.get_order_by_increment_id.return_value = MagicMock()
        self.mock_order_repo.get_unavailable_items.return_value = []
        self.flow = ComplaintFlow(order_repository=self.mock_order_repo)
        self.state = ConversationState()

    def test_flow_trigger_without_order_id(self):
        intent = IntentResult(intent="complaint", confidence=0.9)
        self.state.conversation_history.append({"role": "user", "content": "I want to file a complaint"})
        
        response = self.flow.handle(intent, self.state)
        
        self.assertEqual(response.status, "waiting_for_input")
        self.assertIn("What is your Order ID?", response.response)
        self.assertTrue(response.updated_state["waiting_for_order_id"])
        self.assertEqual(response.updated_state["current_stage"], "waiting_for_order_id")

    def test_flow_trigger_with_order_id(self):
        intent = IntentResult(intent="complaint", confidence=0.9, entities={"order_id": "100000001"})
        self.state.conversation_history.append({"role": "user", "content": "I want to complain about order 100000001"})
        
        response = self.flow.handle(intent, self.state)
        
        self.assertEqual(response.status, "waiting_for_input")
        self.assertIn("Please select the category", response.response)
        self.assertEqual(response.updated_state["current_stage"], "waiting_for_category")
        self.assertEqual(response.updated_state["entities"]["order_id"], "100000001")

    def test_flow_waiting_for_order_id_fallback(self):
        self.state.current_stage = "waiting_for_order_id"
        self.state.conversation_history.append({"role": "user", "content": "It is order 12345"})
        intent = IntentResult(intent="unknown", confidence=0.5)
        
        response = self.flow.handle(intent, self.state)
        
        self.assertEqual(response.status, "waiting_for_input")
        self.assertIn("Please select the category", response.response)
        self.assertEqual(response.updated_state["current_stage"], "waiting_for_category")
        self.assertEqual(response.updated_state["entities"]["order_id"], "12345")

    def test_flow_waiting_for_category_refund(self):
        self.state.current_stage = "waiting_for_category"
        self.state.entities["order_id"] = "12345"
        self.state.conversation_history.append({"role": "user", "content": "Refund"})
        intent = IntentResult(intent="unknown", confidence=0.5)
        
        response = self.flow.handle(intent, self.state)
        
        self.assertEqual(response.status, "waiting_for_input")
        self.assertIn("Please select the refund sub-category", response.response)
        self.assertEqual(response.updated_state["current_stage"], "waiting_for_refund_sub_category")

    def test_flow_waiting_for_category_general(self):
        self.state.current_stage = "waiting_for_category"
        self.state.entities["order_id"] = "12345"
        self.state.conversation_history.append({"role": "user", "content": "General"})
        intent = IntentResult(intent="unknown", confidence=0.5)
        
        response = self.flow.handle(intent, self.state)
        
        self.assertEqual(response.status, "waiting_for_input")
        self.assertIn("Please describe the issue", response.response)
        self.assertEqual(response.updated_state["current_stage"], "waiting_for_general_details")

    def test_flow_refund_sub_category_missing(self):
        self.state.current_stage = "waiting_for_refund_sub_category"
        self.state.entities["order_id"] = "12345"
        self.state.conversation_history.append({"role": "user", "content": "Missing Item"})
        intent = IntentResult(intent="unknown", confidence=0.5)
        
        response = self.flow.handle(intent, self.state)
        
        self.assertEqual(response.status, "waiting_for_input")
        self.assertIn("describe which items you did", response.response)
        self.assertEqual(response.updated_state["current_stage"], "waiting_for_missing_details")

    def test_flow_refund_sub_category_wrong(self):
        self.state.current_stage = "waiting_for_refund_sub_category"
        self.state.entities["order_id"] = "12345"
        self.state.conversation_history.append({"role": "user", "content": "Wrong Item"})
        intent = IntentResult(intent="unknown", confidence=0.5)
        
        response = self.flow.handle(intent, self.state)
        
        self.assertEqual(response.status, "waiting_for_input")
        self.assertIn("Please upload an image", response.response)
        self.assertEqual(response.updated_state["current_stage"], "waiting_for_image")
        self.assertTrue(response.updated_state["show_upload"])

    def test_flow_wrong_item_image_received(self):
        self.state.current_stage = "waiting_for_image"
        self.state.entities["order_id"] = "12345"
        self.state.conversation_history.append({"role": "user", "content": "[Image Uploaded: /static/uploads/item.jpg]"})
        intent = IntentResult(intent="unknown", confidence=0.5)
        
        response = self.flow.handle(intent, self.state)
        
        self.assertEqual(response.status, "waiting_for_input")
        self.assertIn("Image received", response.response)
        self.assertEqual(response.updated_state["current_stage"], "waiting_for_resolution")
        self.assertEqual(response.updated_state["entities"]["image_url"], "/static/uploads/item.jpg")

    def test_flow_resolution_selection_refund(self):
        self.state.current_stage = "waiting_for_resolution"
        self.state.entities["order_id"] = "12345"
        self.state.entities["refund_sub_category"] = "Wrong Item"
        self.state.entities["image_url"] = "/static/uploads/item.jpg"
        self.state.conversation_history.append({"role": "user", "content": "Refund Money"})
        intent = IntentResult(intent="unknown", confidence=0.5)
        
        response = self.flow.handle(intent, self.state)
        
        self.assertEqual(response.status, "completed")
        self.assertEqual(response.tool_request, "create_complaint")
        self.assertEqual(response.tool_args["order_id"], "12345")
        self.assertEqual(response.tool_args["complaint_type"], "Refund")
        self.assertIn("Refund Money", response.tool_args["details"])

    def test_flow_general_details_received(self):
        self.state.current_stage = "waiting_for_general_details"
        self.state.entities["order_id"] = "12345"
        self.state.conversation_history.append({"role": "user", "content": "Rider behaved rudely"})
        intent = IntentResult(intent="unknown", confidence=0.5)
        
        response = self.flow.handle(intent, self.state)
        
        self.assertEqual(response.status, "completed")
        self.assertEqual(response.tool_request, "create_complaint")
        self.assertEqual(response.tool_args["complaint_type"], "General")
        self.assertEqual(response.tool_args["details"], "Rider behaved rudely")

    @patch('database.repository.ComplaintRepository')
    @patch('database.repository.OrderRepository')
    def test_service_create_complaint(self, MockOrderRepo, MockComplaintRepo):
        mock_order = MagicMock()
        mock_order.entity_id = 999
        mock_order.recipient_name = "Jane Smith"
        mock_order.recipient_phone = "987654321"
        MockOrderRepo.return_value.get_order_by_increment_id.return_value = mock_order
        
        MockComplaintRepo.return_value.create_complaint_ticket.return_value = 5005
        MockComplaintRepo.return_value.has_existing_complaint_type.return_value = False
        
        service = ComplaintService(
            complaint_repository=MockComplaintRepo.return_value,
            order_repository=MockOrderRepo.return_value
        )
        
        result = service.create_complaint(
            order_id="12345",
            complaint_type="Refund",
            details="Refund Sub-category: Missing Item",
            image_url="/static/uploads/item.jpg"
        )
        
        self.assertTrue(result["success"])
        self.assertEqual(result["ticket_no"], 5005)
        self.assertIn("#5005", result["message"])
        MockComplaintRepo.return_value.add_ticket_attachment.assert_called_once_with(5005, "/static/uploads/item.jpg")

    @patch('database.repository.ComplaintRepository.has_existing_complaint_type')
    def test_flow_duplicate_complaint_refund(self, mock_check):
        mock_check.return_value = True
        
        self.state.current_stage = "waiting_for_category"
        self.state.entities["order_id"] = "12345"
        self.state.conversation_history.append({"role": "user", "content": "Refund"})
        intent = IntentResult(intent="unknown", confidence=0.5)
        
        response = self.flow.handle(intent, self.state)
        
        self.assertEqual(response.status, "completed")
        self.assertIn("already filed a Refund complaint", response.response)

    @patch('database.repository.ComplaintRepository')
    @patch('database.repository.OrderRepository')
    def test_service_duplicate_complaint(self, MockOrderRepo, MockComplaintRepo):
        MockComplaintRepo.return_value.has_existing_complaint_type.return_value = True
        
        service = ComplaintService(
            complaint_repository=MockComplaintRepo.return_value,
            order_repository=MockOrderRepo.return_value
        )
        
        result = service.create_complaint(
            order_id="12345",
            complaint_type="Refund",
            details="Refund Sub-category: Missing Item"
        )
        
        self.assertFalse(result["success"])
        self.assertIn("already filed a Refund complaint", result["message"])

    @patch('database.repository.ComplaintRepository')
    def test_flow_parent_order_resolution(self, MockComplaintRepo):
        MockComplaintRepo.return_value.has_existing_complaint_type.return_value = False
        # Setup mock to resolve parent '2000096085' to child '2000096085-1'
        self.mock_order_repo.resolve_to_latest_order_id.side_effect = None
        self.mock_order_repo.resolve_to_latest_order_id.return_value = "2000096085-1"
        self.mock_order_repo.get_unavailable_items.return_value = ["Item X (Qty: 1)"]
        self.mock_order_repo.get_payment_method.return_value = "Cash"
        self.mock_order_repo.get_refund_status.return_value = "not initiated"
        
        intent = IntentResult(intent="complaint", confidence=0.9, entities={"order_id": "2000096085"})
        self.state.conversation_history.append({"role": "user", "content": "complain for 2000096085"})
        
        # 1. Trigger flow (stage: None)
        response = self.flow.handle(intent, self.state)
        self.assertEqual(response.status, "waiting_for_input")
        self.assertIn("Please select the category", response.response)
        self.assertEqual(response.updated_state["entities"]["order_id"], "2000096085-1")
        self.assertEqual(response.updated_state["entities"]["parent_order_id"], "2000096085")
        self.assertEqual(response.updated_state["current_stage"], "waiting_for_category")
        
        # 2. Select Refund (stage: waiting_for_category)
        self.state.current_stage = "waiting_for_category"
        self.state.entities = response.updated_state["entities"]
        self.state.conversation_history.append({"role": "user", "content": "Refund"})
        response = self.flow.handle(intent, self.state)
        self.assertEqual(response.status, "waiting_for_input")
        self.assertEqual(response.updated_state["current_stage"], "waiting_for_refund_sub_category")
        
        # 3. Select Missing Item (stage: waiting_for_refund_sub_category)
        self.state.current_stage = "waiting_for_refund_sub_category"
        self.state.entities = response.updated_state["entities"]
        self.state.conversation_history.append({"role": "user", "content": "Missing Item"})
        response = self.flow.handle(intent, self.state)
        self.assertEqual(response.status, "waiting_for_input")
        self.assertIn("missing at dispatch", response.response)
        self.assertIn("Item X (Qty: 1)", response.response)
        self.assertEqual(response.updated_state["current_stage"], "waiting_for_missing_details")
        
        # Now test going to a different issue from waiting_for_resolution stage
        self.state.current_stage = "waiting_for_resolution"
        self.state.entities = response.updated_state["entities"]
        self.state.conversation_history.append({"role": "user", "content": "different issue"})
        
        response2 = self.flow.handle(intent, self.state)
        self.assertEqual(response2.status, "waiting_for_input")
        self.assertEqual(response2.updated_state["current_stage"], "waiting_for_category")
        self.assertIsNone(response2.updated_state["entities"]["refund_sub_category"])

    @patch('database.repository.ComplaintRepository')
    def test_flow_missing_item_voucher_resolution(self, MockComplaintRepo):
        MockComplaintRepo.return_value.has_existing_complaint_type.return_value = False
        
        self.state.current_stage = "waiting_for_resolution"
        self.state.entities["order_id"] = "12345"
        self.state.entities["refund_sub_category"] = "Missing Item"
        self.state.conversation_history.append({"role": "user", "content": "Notify when restocked and voucher"})
        intent = IntentResult(intent="unknown", confidence=0.5)
        
        response = self.flow.handle(intent, self.state)
        
        self.assertEqual(response.status, "completed")
        self.assertEqual(response.tool_request, "create_complaint")
        self.assertIn("Notify when restocked and voucher generated against the amount", response.tool_args["details"])

if __name__ == '__main__':
    unittest.main()
