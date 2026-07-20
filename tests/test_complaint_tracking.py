import sys
import os
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.complaint_tracking_service import ComplaintTrackingService
from data.repositories.complaint_tracking_repository import ComplaintTrackingRepository
from flows.complaint_tracking import ComplaintTrackingFlow
from core.state_manager import ConversationState
from ai.schemas import IntentResult

class TestComplaintTracking(unittest.TestCase):
    def setUp(self):
        self.mock_repo = MagicMock(spec=ComplaintTrackingRepository)
        self.service = ComplaintTrackingService(tracking_repository=self.mock_repo)

    def test_one_complaint(self):
        self.mock_repo.find_by_order.return_value = [{
            "ticket_no": 10000503,
            "order_number": "000016319",
            "status": "Complete",
            "subject": "Missing Item",
            "type": "General",
            "created_at": datetime(2019, 9, 6),
            "complain": "Item was missing",
            "action_taken": "Replacement approved."
        }]
        
        response = self.service.track_complaint("000016319")
        self.assertTrue(response["success"])
        self.assertIn("Found 1 complaint", response["message"])
        self.assertIn("Ticket No: 10000503", response["message"])
        self.assertIn("Category:\nMissing Item (General)", response["message"])
        self.assertIn("Created:\n06 Sep 2019", response["message"])
        self.assertIn("Replacement approved.", response["message"])

    def test_multiple_complaints(self):
        self.mock_repo.find_by_order.return_value = [
            {
                "ticket_no": 1001,
                "order_number": "123",
                "status": "New",
                "subject": "Missing Item",
                "type": "General",
                "created_at": datetime(2023, 1, 1),
                "complain": "Item was missing",
                "action_taken": None
            },
            {
                "ticket_no": 1002,
                "order_number": "123",
                "status": "In Progress",
                "subject": "Wrong Item",
                "type": "Return",
                "created_at": datetime(2023, 1, 2),
                "complain": "Wrong item sent",
                "action_taken": "Checking stock"
            }
        ]
        
        response = self.service.track_complaint("123")
        self.assertTrue(response["success"])
        self.assertIn("Found 2 complaints", response["message"])
        self.assertIn("Ticket No: 1001", response["message"])
        self.assertIn("Ticket No: 1002", response["message"])
        self.assertIn("No update yet", response["message"])

    def test_no_complaints_valid_order(self):
        self.mock_repo.find_by_order.return_value = []
        self.mock_repo.check_order_exists.return_value = True
        
        response = self.service.track_complaint("999")
        self.assertTrue(response["success"])
        self.assertIn("We couldn't find any complaints for Order 999", response["message"])

    def test_invalid_order(self):
        self.mock_repo.find_by_order.return_value = []
        self.mock_repo.check_order_exists.return_value = False
        
        response = self.service.track_complaint("invalid_order_id")
        self.assertFalse(response["success"])
        self.assertIn("Order #invalid_order_id does not exist", response["message"])

    def test_database_failure(self):
        self.mock_repo.find_by_order.side_effect = Exception("DB Connection Lost")
        
        response = self.service.track_complaint("123")
        self.assertFalse(response["success"])
        self.assertIn("issue retrieving your complaint information", response["message"])

    def test_unicode_complaint_text(self):
        self.mock_repo.find_by_order.return_value = [{
            "ticket_no": 1005,
            "order_number": "123",
            "status": "Open",
            "subject": "شکایت",
            "type": "مسئلہ",
            "created_at": datetime(2023, 1, 1),
            "complain": "میرا سامان نہیں ملا",
            "action_taken": "چیک کر رہے ہیں"
        }]
        
        response = self.service.track_complaint("123")
        self.assertTrue(response["success"])
        self.assertIn("شکایت", response["message"])
        self.assertIn("مسئلہ", response["message"])
        self.assertIn("چیک کر رہے ہیں", response["message"])

    def test_sql_injection_attempt_handling(self):
        self.mock_repo.find_by_order.return_value = []
        self.mock_repo.check_order_exists.return_value = False
        
        injection_str = "123'; DROP TABLE users;--"
        response = self.service.track_complaint(injection_str)
        self.assertFalse(response["success"])
        self.mock_repo.find_by_order.assert_called_with(order_number=injection_str)

class TestComplaintTrackingFlow(unittest.TestCase):
    def setUp(self):
        self.flow = ComplaintTrackingFlow()

    def test_flow_asks_for_order_number(self):
        intent = IntentResult(intent="complaint_tracking", confidence=0.99, entities={})
        state = ConversationState(session_id="test")
        response = self.flow.handle(intent, state)
        self.assertEqual(response.status, "in_progress")
        self.assertIn("Please provide your Order Number", response.response)
        self.assertTrue(response.updated_state["waiting_for_order_id"])
        
    def test_flow_extracts_order_and_dispatches_tool(self):
        intent = IntentResult(intent="complaint_tracking", confidence=0.99, entities={"order_id": "123"})
        state = ConversationState(session_id="test")
        response = self.flow.handle(intent, state)
        self.assertEqual(response.status, "completed")
        self.assertEqual(response.tool_request, "track_complaint")
        self.assertEqual(response.tool_args["order_no"], "123")
        self.assertFalse(response.updated_state["waiting_for_order_id"])

if __name__ == '__main__':
    unittest.main()
