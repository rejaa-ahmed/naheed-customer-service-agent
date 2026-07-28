import logging
from typing import Optional
from database.connection import DatabaseManager
from database.schema import Order
from utils.logger import get_logger
import datetime
from typing import Optional

logger = get_logger(__name__)

class OrderNotFoundError(Exception):
    pass

class OrderRepository:
    def resolve_to_latest_order_id(self, increment_id: str) -> str:
        if not increment_id:
            return increment_id
        if "-" not in increment_id:
            child_query = """
            SELECT c.increment_id 
            FROM sales_order c
            JOIN sales_order p ON c.relation_parent_id = p.entity_id
            WHERE p.increment_id = %s
            ORDER BY c.entity_id DESC
            LIMIT 1
            """
            try:
                with DatabaseManager() as conn:
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute(child_query, (increment_id,))
                    res = cursor.fetchone()
                    cursor.close()
                    if res:
                        logger.info(f"Resolved parent order {increment_id} to child order {res['increment_id']}")
                        return res["increment_id"]
            except Exception as e:
                logger.error(f"Error resolving parent order: {e}")
        return increment_id

    def get_entity_id_by_increment_id(self, increment_id: str) -> Optional[int]:
        query = "SELECT entity_id FROM sales_order WHERE increment_id = %s"
        try:
            with DatabaseManager() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute(query, (increment_id,))
                res = cursor.fetchone()
                cursor.close()
                return res["entity_id"] if res else None
        except Exception:
            return None

    def get_order_phone(self, increment_id: str) -> Optional[str]:
        """
        Retrieves the billing phone number for a given order increment_id.
        """
        query = """
        SELECT a.telephone 
        FROM sales_order_address a
        JOIN sales_order o ON a.parent_id = o.entity_id
        WHERE o.increment_id = %s AND a.address_type = 'shipping'
        LIMIT 1
        """
        try:
            with DatabaseManager() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute(query, (increment_id,))
                res = cursor.fetchone()
                cursor.close()
                return res["telephone"] if res else None
        except Exception as e:
            logger.error(f"Error fetching order phone for {increment_id}: {e}")
            return None

    def get_items_by_entity_id(self, entity_id: int) -> list:
        query = "SELECT sku, name, qty_ordered FROM sales_order_item WHERE order_id = %s"
        try:
            with DatabaseManager() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute(query, (entity_id,))
                res = cursor.fetchall()
                cursor.close()
                return res
        except Exception:
            return []

    def get_unavailable_items(self, parent_increment_id: str, child_increment_id: str) -> list:
        parent_entity = self.get_entity_id_by_increment_id(parent_increment_id)
        child_entity = self.get_entity_id_by_increment_id(child_increment_id)
        if not parent_entity or not child_entity:
            return []
            
        parent_items = self.get_items_by_entity_id(parent_entity)
        child_items = self.get_items_by_entity_id(child_entity)
        
        child_map = {item['sku']: item['qty_ordered'] for item in child_items}
        
        unavailable = []
        for p_item in parent_items:
            sku = p_item['sku']
            name = p_item['name']
            p_qty = p_item['qty_ordered']
            
            c_qty = child_map.get(sku, 0)
            
            if p_qty > c_qty:
                diff_qty = int(p_qty - c_qty)
                unavailable.append(f"{name} (Qty: {diff_qty})")
                
        return unavailable

    def get_payment_method(self, increment_id: str) -> str:
        """
        Returns the payment method code for an order.
        e.g. 'cashondelivery', 'jazzcash', 'bankalfalah', etc.
        Returns empty string if not found.
        """
        query = """
        SELECT p.method 
        FROM sales_order o 
        JOIN sales_order_payment p ON o.entity_id = p.parent_id 
        WHERE o.increment_id = %s 
        LIMIT 1
        """
        try:
            with DatabaseManager() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute(query, (increment_id,))
                res = cursor.fetchone()
                cursor.close()
                return res["method"] if res else ""
        except Exception as e:
            logger.error(f"Error fetching payment method for {increment_id}: {e}")
            return ""

    def get_refund_status(self, child_increment_id: str) -> Optional[str]:
        """
        Checks if a refund has already been initiated for the given child order.
        Looks in nop_refund_products_info and sales_creditmemo.
        Returns a human-readable status string, or None if no refund found.
        """
        try:
            with DatabaseManager() as conn:
                cursor = conn.cursor(dictionary=True)
                
                # Check nop_refund_products_info
                cursor.execute(
                    "SELECT COUNT(*) as cnt FROM nop_refund_products_info WHERE ordernumber = %s",
                    (child_increment_id,)
                )
                row = cursor.fetchone()
                if row and row["cnt"] > 0:
                    cursor.close()
                    return "in progress"
                
                # Check sales_creditmemo (state: 1=open, 2=refunded, 3=cancelled)
                cursor.execute("""
                    SELECT cm.state 
                    FROM sales_creditmemo cm
                    JOIN sales_order o ON cm.order_id = o.entity_id
                    WHERE o.increment_id = %s
                    ORDER BY cm.created_at DESC
                    LIMIT 1
                """, (child_increment_id,))
                row = cursor.fetchone()
                cursor.close()
                if row:
                    state_map = {1: "in progress", 2: "completed", 3: "cancelled"}
                    return state_map.get(row["state"], "in progress")
                
                return None
        except Exception as e:
            logger.error(f"Error checking refund status for {child_increment_id}: {e}")
            return None

    def _fetch_order_data(self, cursor, identifier, is_increment=True):
        query = """
        SELECT 
            o.entity_id, 
            o.increment_id, 
            o.status,
            o.state,
            o.relation_parent_id,
            o.relation_parent_real_id,
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
        WHERE {} = %s
        """
        where_clause = "o.increment_id" if is_increment else "o.entity_id"
        cursor.execute(query.format(where_clause), (identifier,))
        result = cursor.fetchone()
        if not result:
            return None
            
        order = Order(
            entity_id=result["entity_id"],
            increment_id=result["increment_id"],
            status=result["status"],
            state=result["state"],
            estimated_delivery_datetime=result["delivery_due_date"],
            shipping_city=result["city"],
            recipient_name=f"{result['firstname'] or ''} {result['lastname'] or ''}".strip() if result['firstname'] or result['lastname'] else None,
            recipient_phone=result["telephone"],
            shipping_address=result["street"],
            carrier_code=result["courier"],
            tracking_number=result["cn_number"]
        )
        
        # Attach raw relation fields for internal repository use
        order._relation_parent_id = result.get("relation_parent_id")
        order._relation_parent_real_id = result.get("relation_parent_real_id")
        return order

    def get_order_by_increment_id(self, increment_id: str) -> Order:
        import os
        mock_fallback = os.getenv("DB_MOCK_FALLBACK", "false").lower() == "true"
        try:
            with DatabaseManager() as conn:
                logger.info(f"Fetching order with increment_id: {increment_id}")
                cursor = conn.cursor(dictionary=True)
                
                initial_order = self._fetch_order_data(cursor, increment_id, is_increment=True)
                if not initial_order:
                    logger.warning(f"Order not found for increment_id: {increment_id}")
                    raise OrderNotFoundError(f"Order with increment_id {increment_id} not found.")

                # Detect if the entered order is a parent or child
                if getattr(initial_order, "_relation_parent_id", None):
                    # It's a child order. Resolve parent.
                    parent_id = initial_order._relation_parent_id
                    logger.info(f"Entered order {increment_id} is a child. Resolving parent ID {parent_id}")
                    parent_order = self._fetch_order_data(cursor, parent_id, is_increment=False)
                    if not parent_order:
                        parent_order = initial_order
                else:
                    parent_order = initial_order

                logger.info(f"Successfully retrieved parent order: {parent_order.increment_id}")
                
                # Check for ALL child orders
                cursor.execute("SELECT entity_id FROM sales_order WHERE relation_parent_id = %s", (parent_order.entity_id,))
                child_rows = cursor.fetchall()
                logger.info(f"Parent order detection: found {len(child_rows)} child orders for {parent_order.increment_id}")
                
                for row in child_rows:
                    child_order = self._fetch_order_data(cursor, row["entity_id"], is_increment=False)
                    if child_order:
                        parent_order.child_orders.append(child_order)
                
                if parent_order.child_orders:
                    # Fetch unavailable items (comparing parent to ALL child orders)
                    child_entity_ids = [str(c.entity_id) for c in parent_order.child_orders]
                    child_ids_str = ",".join(child_entity_ids)
                    
                    logger.info(f"Parent Order ID: {parent_order.increment_id}")
                    logger.info(f"Child Order IDs: {[c.increment_id for c in parent_order.child_orders]}")
                    
                    query = f"""
                        SELECT p.name, (p.qty_ordered - COALESCE(c.child_qty, 0)) as unavailable_qty, p.sku, p.qty_ordered as parent_qty, c.child_qty
                        FROM sales_order_item p
                        LEFT JOIN (
                            SELECT sku, SUM(qty_ordered) as child_qty
                            FROM sales_order_item
                            WHERE order_id IN ({child_ids_str}) AND parent_item_id IS NULL
                            GROUP BY sku
                        ) c ON p.sku = c.sku
                        WHERE p.order_id = %s AND p.parent_item_id IS NULL
                        HAVING unavailable_qty > 0
                    """
                    cursor.execute(query, (parent_order.entity_id,))
                    for item in cursor.fetchall():
                        parent_order.unavailable_items.append({"name": item["name"], "qty": float(item["unavailable_qty"])})
                        logger.info(f"Unavailable calculation for SKU {item['sku']}: Parent Qty={item['parent_qty']}, Child Qty={item['child_qty']}, Unavailable={item['unavailable_qty']}")
                        
                    logger.info(f"Final unavailable_items list: {parent_order.unavailable_items}")
                    
                # Fetch Payment Method
                cursor.execute("SELECT method FROM sales_order_payment WHERE parent_id = %s", (parent_order.entity_id,))
                payment_row = cursor.fetchone()
                if payment_row:
                    parent_order.payment_method = payment_row.get("method")
                    logger.info(f"Payment method for {increment_id}: {parent_order.payment_method}")
                    
                # Fetch Refund Status
                if parent_order.payment_method and "cashondelivery" not in parent_order.payment_method.lower() and "cod" not in parent_order.payment_method.lower():
                    cursor.execute("SELECT state, grand_total, created_at FROM sales_creditmemo WHERE order_id = %s ORDER BY entity_id DESC LIMIT 1", (parent_order.entity_id,))
                    refund_row = cursor.fetchone()
                    if refund_row:
                        parent_order.refund_state = refund_row.get("state")
                        parent_order.refund_amount = float(refund_row.get("grand_total")) if refund_row.get("grand_total") else 0.0
                        parent_order.refund_date = refund_row.get("created_at")
                        logger.info(f"Refund status for {increment_id}: State={parent_order.refund_state}")
                    else:
                        logger.info(f"No refund found for {increment_id}")
                
                cursor.close()
                return parent_order
        except OrderNotFoundError:
            raise
        except Exception as e:
            if mock_fallback:
                logger.warning(f"Database error ({e}), but DB_MOCK_FALLBACK is enabled. Returning mock order.")
                last_char = increment_id[-1] if increment_id else "0"
                if last_char in ["0", "2", "4", "6", "8"]:
                    status = "shipped"
                elif last_char in ["1", "3", "5", "7"]:
                    status = "processing"
                else:
                    status = "packed"
                
                from database.schema import Order
                from datetime import datetime, timedelta
                return Order(
                    entity_id=99999,
                    increment_id=increment_id,
                    status=status,
                    estimated_delivery_datetime=datetime.now() + timedelta(days=2),
                    shipping_city="Karachi",
                    recipient_name="Mock Customer",
                    recipient_phone="03001234567",
                    shipping_address="123 Mock Street",
                    carrier_code="lcsshipping",
                    tracking_number="LCS12345678"
                )
            else:
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

    def get_delivery_date(self, increment_id: str) -> Optional[datetime.datetime]:
        """Fetch the actual completion/delivery datetime (completed_at) for the given order increment ID.
        Returns None if not found or if the field is unavailable."""
        query = """
        SELECT a.completed_at 
        FROM sales_order o
        LEFT JOIN nhd_sales_order_additionals a ON o.entity_id = a.order_id
        WHERE o.increment_id = %s
        """
        try:
            with DatabaseManager() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute(query, (increment_id,))
                result = cursor.fetchone()
                cursor.close()
                if result and result["completed_at"]:
                    return result["completed_at"]
                return None
        except Exception as e:
            logger.error(f"Error fetching delivery date for {increment_id}: {e}")
            return None

    def cancel_order(self, increment_id: str, cancel_reason: str = "Unknown reason") -> bool:
        """
        Cancels an order by updating its state and status to 'canceled' in sales_order and sales_order_grid,
        and inserts a history comment indicating cancellation.
        """
        try:
            with DatabaseManager() as conn:
                cursor = conn.cursor(dictionary=True)
                
                # 1. Retrieve entity_id, status, and state with FOR UPDATE to prevent race conditions
                select_query = "SELECT entity_id, status, state FROM sales_order WHERE increment_id = %s FOR UPDATE"
                cursor.execute(select_query, (increment_id,))
                order_row = cursor.fetchone()
                
                if not order_row:
                    logger.warning(f"Failed to cancel order {increment_id}: order not found.")
                    conn.rollback()
                    cursor.close()
                    return False
                
                entity_id = order_row["entity_id"]
                current_status = order_row["status"]
                current_state = order_row["state"]
                
                # Defensive validation: Do not update if already canceled
                if current_state == 'canceled' or current_status == 'canceled':
                    logger.info(f"Order {increment_id} is already canceled in the database.")
                    conn.rollback()
                    cursor.close()
                    return True
                
                cursor.close()
                cursor = conn.cursor()
                
                # 2. Update sales_order
                update_so_query = "UPDATE sales_order SET state = 'canceled', status = 'canceled', updated_at = NOW() WHERE entity_id = %s"
                cursor.execute(update_so_query, (entity_id,))
                
                # 3. Update sales_order_grid
                update_sog_query = "UPDATE sales_order_grid SET status = 'canceled', updated_at = NOW() WHERE entity_id = %s"
                cursor.execute(update_sog_query, (entity_id,))
                
                # 4. Insert into sales_order_status_history
                clean_reason = cancel_reason.replace('_', ' ').capitalize()
                formatted_comment = f"Order cancelled by Naheed AI Chatbot.\n\nCustomer reason: {clean_reason}.\n\nCancelled automatically via AI Customer Support."
                insert_history_query = """
                INSERT INTO sales_order_status_history 
                (parent_id, is_customer_notified, is_visible_on_front, comment, status, entity_name) 
                VALUES (%s, 0, 0, %s, 'canceled', 'order')
                """
                logger.info(f"PRE-INSERT SQL: {insert_history_query}")
                logger.info(f"PRE-INSERT PARAMS: parent_id={entity_id}, comment={formatted_comment}")
                cursor.execute(insert_history_query, (entity_id, formatted_comment))
                logger.info(f"POST-INSERT: cursor.rowcount={cursor.rowcount}, cursor.lastrowid={cursor.lastrowid}")
                
                conn.commit()
                logger.info(f"Successfully cancelled order {increment_id} (entity_id={entity_id}) in database via transaction.")
                cursor.close()
                return True
                
        except Exception as e:
            logger.exception(f"Database transaction error while cancelling order {increment_id}: {e}")
            return False

class ComplaintRepository:
    def create_complaint_ticket(
        self,
        order_number: str,
        entity_id: int,
        name: str,
        email: str,
        phone: str,
        subject: str,
        complain: str,
        complain_type: str,
        priority: str = "low",
        mood: str = "happy"
    ) -> int:
        # AI-judged urgency ("high"/"low") and customer mood ("happy"/"sad"), captured
        # from the message that triggered this ticket. Stored in `priority`/`mood`
        # columns on nhd_complain_tickets - see migrations/add_priority_mood_to_complain_tickets.sql
        
        # Determine priority on the basis of customer's mood
        if mood.lower() in ["sad", "angry", "frustrated", "bad", "unhappy"]:
            priority = "high"
        elif mood.lower() == "happy":
            priority = "low"

        query = """
        INSERT INTO nhd_complain_tickets (
            order_number, entity_id, customer_name, customer_email, customer_phone, 
            subject, complain, type, status, action_taken, refund_amount, priority
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'New', '', '', %s)
        """
        try:
            with DatabaseManager() as conn:
                logger.info(f"Creating complaint ticket for order {order_number} (priority={priority}, mood={mood})")
                cursor = conn.cursor()
                cursor.execute(query, (order_number, entity_id, name, email, phone, subject, complain, complain_type, priority))
                conn.commit()
                ticket_no = cursor.lastrowid
                cursor.close()
                logger.info(f"Successfully created complaint ticket #{ticket_no}")
                return ticket_no
        except Exception as e:
            logger.error(f"Database error while creating complaint ticket: {e}")
            raise RuntimeError(f"Database error: {e}") from e

    def add_ticket_attachment(self, ticket_no: int, image_url: str):
        query = """
        INSERT INTO nhd_complain_tickets_attachments_info (
            ticket_no, image_url, status
        ) VALUES (%s, %s, 'New')
        """
        try:
            with DatabaseManager() as conn:
                logger.info(f"Adding attachment for ticket {ticket_no}: {image_url}")
                cursor = conn.cursor()
                cursor.execute(query, (ticket_no, image_url))
                conn.commit()
                cursor.close()
                logger.info(f"Successfully added attachment to ticket #{ticket_no}")
        except Exception as e:
            logger.error(f"Database error while adding ticket attachment: {e}")
            raise RuntimeError(f"Database error: {e}") from e

    def has_existing_complaint_type(self, order_number: str, complain_type: str) -> bool:
        query = "SELECT COUNT(*) as count FROM nhd_complain_tickets WHERE order_number = %s AND type = %s"
        try:
            with DatabaseManager() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute(query, (order_number, complain_type))
                result = cursor.fetchone()
                cursor.close()
                return (result["count"] > 0) if result else False
        except Exception as e:
            logger.error(f"Database error while checking existing complaints: {e}")
            raise RuntimeError(f"Database error: {e}") from e
