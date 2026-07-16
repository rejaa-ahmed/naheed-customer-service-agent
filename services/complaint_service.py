import logging
from typing import Dict, Any
from database.repository import OrderRepository, ComplaintRepository

logger = logging.getLogger(__name__)

class ComplaintService:
    def __init__(self, complaint_repository=None, order_repository=None):
        self.complaint_repository = complaint_repository or ComplaintRepository()
        self.order_repository = order_repository or OrderRepository()

    def create_complaint(self, order_id: str, complaint_type: str, details: str, image_url: str = None, priority: str = "low", mood: str = "happy") -> Dict[str, Any]:
        try:
            # Check for duplicate complaint type
            if self.complaint_repository.has_existing_complaint_type(order_id, complaint_type):
                return {
                    "success": False,
                    "message": f"You have already filed a {complaint_type} complaint for Order #{order_id}. Duplicate complaints of the same type are not allowed."
                }
            # 1. Fetch order to get entity_id and customer info
            try:
                order = self.order_repository.get_order_by_increment_id(order_id)
                entity_id = order.entity_id
                name = order.recipient_name or "Valued Customer"
                phone = order.recipient_phone or ""
                email = "" # We don't have email in Order schema, but we can set it empty or query order address
            except Exception as e:
                logger.warning(f"Could not retrieve order details for complaint #{order_id}: {e}")
                entity_id = 0
                name = "Valued Customer"
                phone = ""
                email = ""

            subject = f"Complaint for Order #{order_id} ({complaint_type})"
            ticket_no = self.complaint_repository.create_complaint_ticket(
                order_number=order_id,
                entity_id=entity_id,
                name=name,
                email=email,
                phone=phone,
                subject=subject,
                complain=details,
                complain_type=complaint_type,
                priority=priority or "low",
                mood=mood or "happy"
            )

            if image_url:
                self.complaint_repository.add_ticket_attachment(ticket_no, image_url)

            return {
                "success": True,
                "ticket_no": ticket_no,
                "message": f"Your complaint has been successfully registered. Ticket Number: #{ticket_no}"
            }
        except Exception as e:
            logger.error(f"Error creating complaint in service: {e}")
            return {
                "success": False,
                "message": f"Failed to register complaint: {e}"
            }
