import logging
from typing import Dict, Any

from database.repository import OrderRepository, OrderNotFoundError
from utils.logger import get_logger

logger = get_logger(__name__)

from datetime import datetime

class OrderService:
    def __init__(self, repository: OrderRepository = None):
        # Allow injecting a mock repository for testing
        self.repository = repository or OrderRepository()

    def _get_courier_url(self, carrier_code: str, tracking_number: str) -> str:
        if not carrier_code or not tracking_number:
            return None
        mapping = {
            "mnpshipping": f"https://www.mulphilog.com/tracking?consignment_number={tracking_number}",
            "lcsshipping": "https://pk.leopardscourier.com/"
        }
        return mapping.get(carrier_code.lower())

    def track_order(self, increment_id: str) -> Dict[str, Any]:
        logger.info(f"OrderService received tracking request for ID: {increment_id}")
        
        # 1. Validate Order ID
        if not increment_id or not isinstance(increment_id, str) or not increment_id.strip():
            logger.warning("Invalid Order ID provided (empty or whitespace).")
            return {
                "success": False,
                "message": "Please enter a valid Order ID.",
                "status": None,
                "order": None
            }
            
        increment_id = increment_id.strip()
        import re
        if not re.match(r"^[a-zA-Z0-9_\-]+$", increment_id):
            logger.warning(f"Invalid Order ID format: {increment_id}")
            return {
                "success": False,
                "message": "Order ID contains invalid characters. Please check and try again.",
                "status": None,
                "order": None
            }

        # 2 & 3. Call Repository and Handle Responses
        try:
            parent_order = self.repository.get_order_by_increment_id(increment_id)
            
            # Select active order (child if exists, else parent)
            if parent_order.child_orders:
                active_order = next((c for c in parent_order.child_orders if c.increment_id == increment_id), parent_order.child_orders[0])
                logger.info(f"Using active child order {active_order.increment_id} for tracking.")
            else:
                active_order = parent_order
            
            # 4. Handle exact DB status and ETA
            eta_str = None
            if active_order.estimated_delivery_datetime:
                logger.info(f"ETA found: {active_order.estimated_delivery_datetime}")
                if active_order.estimated_delivery_datetime > datetime.now():
                    logger.info("ETA valid.")
                    eta_str = active_order.estimated_delivery_datetime.strftime("%d %B %Y, %I:%M %p")
                else:
                    logger.info("ETA expired.")
            else:
                logger.info("No ETA found.")
            
            logger.info(f"Exact DB status returned: {active_order.status}")
            
            # External Order Detection
            is_external = False
            if active_order.shipping_city and active_order.shipping_city.strip().lower() != "karachi":
                is_external = True
                
            logger.info(f"Order type: {'External' if is_external else 'Karachi'}")

            # 5. Format response message
            lines = [
                "Order ID:",
                f"{active_order.increment_id}",
                "\nShipment Status:",
                f"{active_order.status}"
            ]
            
            if eta_str:
                lines.append("\nEstimated Delivery:")
                lines.append(eta_str)
                
            has_unavailable = bool(parent_order.unavailable_items)
            if has_unavailable:
                logger.info(f"Formatting {len(parent_order.unavailable_items)} unavailable items.")
                lines.append("\nUnavailable Items:")
                for item in parent_order.unavailable_items:
                    qty = item['qty']
                    lines.append(f"• {item['name']} ({qty:g})")
                    
            is_cod = False
            if parent_order.payment_method:
                is_cod = "cashondelivery" in parent_order.payment_method.lower() or "cod" in parent_order.payment_method.lower()
                
            if has_unavailable:
                if is_cod:
                    lines.append("\nPayment:")
                    lines.append("This order was placed using Cash on Delivery. You will only pay for the items that were delivered. No refund is required for unavailable items.")
                else:
                    lines.append("\nRefund Status:")
                    if parent_order.refund_state == 2:
                        lines.append("• Completed")
                    elif parent_order.refund_state == 1:
                        lines.append("• Processing")
                    elif parent_order.refund_state:
                        lines.append("• Pending")
                    else:
                        lines.append("• No refund has been initiated yet.")
                        
            if is_external:
                lines.append("\nTracking Information:")
                if active_order.tracking_number:
                    lines.append(f"Courier: {active_order.carrier_code or 'Unknown'}")
                    lines.append(f"Tracking Number: {active_order.tracking_number}")
                    url = self._get_courier_url(active_order.carrier_code, active_order.tracking_number)
                    if url:
                        lines.append(f"Tracking Link: {url}")
                else:
                    lines.append("Your order has been handed over for external delivery. A tracking number will be shared once it becomes available.")
            
            notes = []
            if not has_unavailable:
                if eta_str:
                    notes.append("Your order is on its way. You can expect it to arrive before the estimated delivery time.")
                else:
                    notes.append("We'll continue processing your order and update its status as it progresses.")
            else:
                if not is_cod:
                    notes.append("Unavailable items are being refunded.")
            
            if notes:
                lines.append("\nNotes:")
                lines.extend(notes)
            
            friendly_message = "\n".join(lines)
            
            # 6. Return structured response
            return {
                "success": True,
                "message": friendly_message,
                "status": active_order.status,
                "order": {
                    "entity_id": active_order.entity_id,
                    "increment_id": active_order.increment_id,
                    "status": active_order.status,
                    "is_external": is_external
                }
            }
            
        except OrderNotFoundError:
            logger.info(f"OrderService: Order {increment_id} not found.")
            return {
                "success": False,
                "message": "We couldn't find an order with that ID. Please check and try again.",
                "status": None,
                "order": None
            }
            
        except Exception as e:
            logger.error(f"OrderService encountered an error fetching {increment_id}: {e}")
            return {
                "success": False,
                "message": "We are currently experiencing technical difficulties. Please try again later.",
                "status": None,
                "order": None
            }
