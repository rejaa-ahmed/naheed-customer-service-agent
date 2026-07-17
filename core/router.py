import re
from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class IntentResult:
    intent: str
    confidence: float
    entities: Dict[str, Any] = field(default_factory=dict)

class IntentRouter:
    """
    Analyzes natural language messages to determine intent and extract entities.
    Designed to be modular so it can be seamlessly swapped with an LLM-based 
    intent classifier in the future.
    """
    def __init__(self):
        # Basic rule-based patterns for initial implementation
        self.patterns = {
            "order_tracking": [r"track.*order", r"where.*order", r"status.*order", r"order.*status"],
            "modify_order": [r"modify.*order", r"change.*order", r"edit.*order", r"order.*change", r"order.*modify"],
            "complaint": [r"complain", r"broken", r"damaged", r"wrong item", r"issue"],
            "greeting": [r"^hi\b", r"^hello\b", r"^hey\b", r"^good morning", r"^good afternoon"],
        }
        # Look for numbers that might be order IDs (assumed 5-10 digits)
        self.order_id_pattern = r"\b[0-9]{5,10}\b"

    def route(self, message: str) -> IntentResult:
        if not message or not isinstance(message, str):
            return IntentResult(intent="unknown", confidence=0.0)

        message_lower = message.lower().strip()
        
        # Extract entities
        entities = {}
        order_match = re.search(self.order_id_pattern, message_lower)
        if order_match:
            entities["order_id"] = order_match.group(0)

        # Determine Intent
        best_intent = "unknown"
        highest_confidence = 0.0

        for intent, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    best_intent = intent
                    highest_confidence = 0.85 # Mock confidence score
                    break
            if best_intent != "unknown":
                break

        # Fallbacks
        if best_intent == "unknown":
            if entities.get("order_id"):
                # If they just provided an order ID, assume they want tracking
                best_intent = "order_tracking"
                highest_confidence = 0.70
            else:
                # General query fallback
                best_intent = "general_query"
                highest_confidence = 0.50

        return IntentResult(
            intent=best_intent, 
            confidence=highest_confidence, 
            entities=entities
        )
