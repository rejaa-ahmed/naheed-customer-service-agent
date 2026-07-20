import os
from unittest.mock import MagicMock
from core.conversation_manager import ConversationManager
from ai.schemas import IntentResult

os.environ["LLM_PROVIDER_CHAIN"] = "mock1"

# Mock the parser so we don't need real API keys
mock_parser = MagicMock()
mock_intent = IntentResult(
    intent="complaint_tracking",
    confidence=0.99,
    entities={"ticket_no": "CT-10021"},
    tool="track_complaint"
)
mock_parser.parse_intent.return_value = mock_intent

cm = ConversationManager(parser=mock_parser)
response = cm.process_message("track complaint CT-10021")
print("\nFINAL RESPONSE:\n", response)
