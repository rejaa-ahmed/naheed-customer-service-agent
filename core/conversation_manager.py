import os
import uuid
from core.router import IntentRouter
from core.state_manager import StateManager
from core.flow_manager import FlowManager
from ai.intent_parser import IntentParser, IntentParserError
from services.order_service import OrderService
from services.complaint_service import ComplaintService
from utils.logger import get_logger
from utils.helpers import build_reassurance_prefix

logger = get_logger(__name__)

class ConversationManager:
    """
    Manages the flow of the conversation by utilizing the IntentRouter
    to determine the user's intent, and delegating business logic to Services.
    """
    def __init__(self, parser: IntentParser = None, router: IntentRouter = None, order_service: OrderService = None, complaint_service: ComplaintService = None, state_manager: StateManager = None, flow_manager: FlowManager = None):
        # Dependency injection allows easy mocking in tests
        self.parser = parser or IntentParser()
        self.router = router or IntentRouter()
        self.order_service = order_service or OrderService()
        self.complaint_service = complaint_service or ComplaintService()
        self.state_manager = state_manager or StateManager()
        self.flow_manager = flow_manager or FlowManager()
        
        threshold_env = os.getenv("AI_CONFIDENCE_THRESHOLD", "0.85")
        try:
            self.confidence_threshold = float(threshold_env)
        except ValueError:
            self.confidence_threshold = 0.85

    def process_message(self, message: str, session_id: str = "default") -> str:
        message_id = str(uuid.uuid4())
        logger.info(f"\n[REQUEST START]\nmessage_id={message_id}\nuser_message={message}")
        
        # 0. Check Cancellation
        if self.state_manager.check_cancellation(message):
            self.state_manager.clear_state(session_id)
            return "Conversation reset. How can I help you?"
            
        # 0.1 Check Consecutive User Messages
        state = self.state_manager.get_state(session_id)
        if state.conversation_history and state.conversation_history[-1]["role"] == "user":
            logger.warning(f"Consecutive user message blocked for session {session_id}")
            return "Please wait for my response before sending another message."
            
        # 0.5 Load State & add user message
        self.state_manager.add_message(session_id, "user", message)
        state = self.state_manager.get_state(session_id)
        
        # 1. Classify Intent via LLM
        intent_result = None
        try:
            logger.info(f"ConversationManager -> IntentParser (message_id={message_id})")
            ai_result = self.parser.parse_intent(message, state=state, message_id=message_id)
            if ai_result.confidence >= self.confidence_threshold:
                intent_result = ai_result
                logger.info(f"AI Detected Intent: {intent_result.intent} (Confidence: {intent_result.confidence})")
                logger.info(f"AI Extracted Entities: {intent_result.entities}")
                if getattr(intent_result, "tool", None):
                    logger.info(f"AI Recommended Tool: {intent_result.tool}")
            else:
                logger.warning(f"Fallback Reason: Low AI confidence ({ai_result.confidence} < {self.confidence_threshold})")
        except IntentParserError as e:
            logger.info("Gemini unavailable.")
        
        # 1.5 Fallback to rule-based router
        if not intent_result:
            logger.info("Switching to legacy router.")
            try:
                intent_result = self.router.route(message)
                if intent_result:
                    logger.info("Legacy router successfully classified intent.")
            except Exception as e:
                logger.error(f"Legacy router crashed: {e}")
                intent_result = None
                
            if not intent_result:
                response_text = "I'm having trouble understanding your request. Please try again."
                self.state_manager.add_message(session_id, "assistant", response_text)
                logger.info(f"[REQUEST END] message_id={message_id}\n")
                return response_text
        # Update entities in state
        if intent_result:
            entities = intent_result.entities if isinstance(intent_result.entities, dict) else intent_result.entities.model_dump()
            self.state_manager.update_entities(session_id, entities)

            # Track the AI-judged priority ("high"/"low") and mood ("happy"/"sad")
            # for this message so it can be attached to any ticket filed later.
            priority = getattr(intent_result, "priority", "low") or "low"
            mood = getattr(intent_result, "mood", "happy") or "happy"
            self.state_manager.update_state(session_id, {"priority": priority, "mood": mood})
            logger.info(f"Judged customer priority={priority}, mood={mood} (message_id={message_id})")

        state = self.state_manager.get_state(session_id)
        
        # 2. Execute Flow via FlowManager
        flow_response = self.flow_manager.execute_flow(intent_result, state)
        
        # 3. Apply state updates
        if flow_response.status == "completed":
            self.state_manager.clear_state(session_id)
        else:
            self.state_manager.update_state(session_id, flow_response.updated_state)
            
        response_text = flow_response.response
        
        # TEMPORARY TOOL EXECUTION (To be replaced by Tool Dispatcher in Phase 5)
        if flow_response.tool_request == "track_order":
            order_id = flow_response.tool_args.get("order_id")
            logger.info(f"Routing to OrderService for Order ID: {order_id}")
            service_response = self.order_service.track_order(order_id)
            response_text = service_response.get("message", "We encountered an issue checking your order.")
        elif flow_response.tool_request == "create_complaint":
            order_id = flow_response.tool_args.get("order_id")
            complaint_type = flow_response.tool_args.get("complaint_type")
            details = flow_response.tool_args.get("details")
            image_url = flow_response.tool_args.get("image_url")
            logger.info(f"Routing to ComplaintService for Order ID: {order_id} (priority={state.priority}, mood={state.mood})")
            service_response = self.complaint_service.create_complaint(
                order_id=order_id,
                complaint_type=complaint_type,
                details=details,
                image_url=image_url,
                priority=state.priority,
                mood=state.mood
            )
            ticket_msg = service_response.get("message", "")
            # If the flow already built a rich response (e.g. COD/refund status message),
            # append the ticket confirmation to it rather than replacing it.
            if response_text:
                response_text = f"{response_text}\n\n{ticket_msg}"
            else:
                response_text = ticket_msg

        # If the customer's message reads as upset/frustrated, lead with a short
        # empathetic reassurance before the substantive answer.
        reassurance = build_reassurance_prefix(state.mood, state.priority)
        if reassurance:
            response_text = f"{reassurance}{response_text}"

        self.state_manager.add_message(session_id, "assistant", response_text)

        logger.info(f"[REQUEST END] message_id={message_id}\n")
        return response_text
