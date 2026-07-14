import logging
from typing import Optional
from database.connection import DatabaseManager
from database.schema import Order
from utils.logger import get_logger

logger = get_logger(__name__)

class OrderNotFoundError(Exception):
    pass

class OrderRepository:
    def get_order_by_increment_id(self, increment_id: str) -> Order:
        query = """
        SELECT 
            o.entity_id, 
            o.increment_id, 
            o.status,
            a.delivery_due_date,
            a.courier,
            a.cn_number,
            addr.city,
            addr.firstname,
            addr.lastname,
            addr.telephone,
            addr.street
        FROM sales_order o
        LEFT JOIN nhd_sales_order_additionals a ON o.entity_id = a.order_id
        LEFT JOIN sales_order_address addr ON o.entity_id = addr.parent_id AND addr.address_type = 'shipping'
        WHERE o.increment_id = %s
        """
        try:
            with DatabaseManager() as conn:
                logger.info(f"Fetching order with increment_id: {increment_id}")
                cursor = conn.cursor(dictionary=True)
                cursor.execute(query, (increment_id,))
                result = cursor.fetchone()
                cursor.close()
                
                if not result:
                    logger.warning(f"Order not found for increment_id: {increment_id}")
                    raise OrderNotFoundError(f"Order with increment_id {increment_id} not found.")
                    
                order = Order(
                    entity_id=result["entity_id"],
                    increment_id=result["increment_id"],
                    status=result["status"],
                    estimated_delivery_datetime=result["delivery_due_date"],
                    shipping_city=result["city"],
                    recipient_name=f"{result['firstname'] or ''} {result['lastname'] or ''}".strip() if result['firstname'] or result['lastname'] else None,
                    recipient_phone=result["telephone"],
                    shipping_address=result["street"],
                    carrier_code=result["courier"],
                    tracking_number=result["cn_number"]
                )
                logger.info(f"Successfully retrieved order: {increment_id}")
                return order
        except OrderNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Database error while fetching order {increment_id}: {e}")
            raise RuntimeError(f"Database error: {e}") from e

    def get_order_status(self, increment_id: str) -> str:
        query = "SELECT status FROM sales_order WHERE increment_id = %s"
        try:
            with DatabaseManager() as conn:
                logger.info(f"Fetching order status for increment_id: {increment_id}")
                cursor = conn.cursor(dictionary=True)
                cursor.execute(query, (increment_id,))
                result = cursor.fetchone()
                cursor.close()
                
                if not result:
                    logger.warning(f"Order not found for increment_id: {increment_id}")
                    raise OrderNotFoundError(f"Order with increment_id {increment_id} not found.")
                
                status = result["status"]
                logger.info(f"Successfully retrieved status '{status}' for order: {increment_id}")
                return status
        except OrderNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Database error while fetching order status {increment_id}: {e}")
            raise RuntimeError(f"Database error: {e}") from e
