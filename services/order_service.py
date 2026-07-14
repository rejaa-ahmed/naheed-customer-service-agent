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
            order = self.repository.get_order_by_increment_id(increment_id)
            
            # 4. Handle exact DB status and ETA
            eta_str = None
            if order.estimated_delivery_datetime:
                logger.info(f"ETA found: {order.estimated_delivery_datetime}")
                if order.estimated_delivery_datetime > datetime.now():
                    eta_str = order.estimated_delivery_datetime.strftime("%d %B %Y, %I:%M %p")
                else:
                    logger.info("ETA expired. Omiting from response.")
            
            logger.info(f"Exact DB status returned: {order.status}")
            
            # External Order Detection
            is_external = False
            if order.shipping_city and order.shipping_city.strip().lower() != "karachi":
                is_external = True
                
            logger.info(f"Order type: {'External' if is_external else 'Karachi'}")

            # 5. Format response message
            lines = [
                "Your order has been found.\n",
                f"• Order ID: {order.increment_id}",
                f"• Current Status: {order.status}"
            ]
            
            if eta_str:
                lines.append(f"• Estimated Delivery: {eta_str}")
                
            lines.append("") # Empty line before closing paragraph
            
            if eta_str:
                lines.append("Your order is on its way. You can expect it to arrive before the estimated delivery time.")
            else:
                lines.append("We'll continue processing your order and update its status as it progresses.")
                
            if is_external:
                if order.tracking_number:
                    lines.append(f"\nCourier: {order.carrier_code or 'Unknown'}")
                    lines.append(f"Tracking Number: {order.tracking_number}")
                    url = self._get_courier_url(order.carrier_code, order.tracking_number)
                    if url:
                        lines.append(f"Tracking Link: {url}")
                else:
                    lines.append("\nYour order has been handed over for external delivery. A tracking number will be shared once it becomes available.")
            
            friendly_message = "\n".join(lines)
            
            # 6. Return structured response
            return {
                "success": True,
                "message": friendly_message,
                "status": order.status,
                "order": {
                    "entity_id": order.entity_id,
                    "increment_id": order.increment_id,
                    "status": order.status,
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
