from flows.base import BaseFlow, FlowResponse
from ai.schemas import IntentResult
from core.state_manager import ConversationState
from flows.knowledge_base import GENERAL_POLICY_KB
from utils.logger import get_logger

logger = get_logger(__name__)

class GeneralPolicyFlow(BaseFlow):
    def __init__(self):
        super().__init__()

    def _format_policy(self, topic_data: dict) -> str:
        lines = [f"**{topic_data.get('title', 'Policy Information')}**\n"]
        for section in topic_data.get('sections', []):
            if 'subtitle' in section:
                lines.append(f"*{section['subtitle']}*")
            for point in section.get('points', []):
                lines.append(f"• {point}")
            lines.append("")  # Empty line between sections
        return "\n".join(lines).strip()

    def handle(self, intent_result: IntentResult, state: ConversationState) -> FlowResponse:
        entities = intent_result.entities if isinstance(intent_result.entities, dict) else intent_result.entities.model_dump()
        topic = entities.get("policy_topic")
        
        logger.info(f"Intent detected: {intent_result.intent}")
        logger.info(f"Policy topic extracted: {topic}")
        
        if not topic or topic not in GENERAL_POLICY_KB:
            logger.info("Knowledge base mapped: Fallback Triggered")
            fallback_msg = "I'm sorry, I don't have information on that specific policy right now. Please call us at (021) 111-624-333 for further assistance."
            return FlowResponse(status="completed", response=fallback_msg)
            
        logger.info("Knowledge base mapped: Yes")
        
        # Zero LLM usage for standard responses.
        # Format the response from the structured KB.
        topic_data = GENERAL_POLICY_KB[topic]
        formatted_response = self._format_policy(topic_data)
        
        return FlowResponse(status="completed", response=formatted_response)
