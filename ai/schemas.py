from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any, Optional

class EntityExtraction(BaseModel):
    order_id: Optional[str] = Field(None, description="The alphanumeric order ID if present")
    policy_topic: Optional[str] = Field(None, description="The specific policy topic requested (e.g., delivery, payment)")
    response_mode: Optional[str] = Field(None, description="The requested response mode: 'standard' or 'complex'")

class IntentResult(BaseModel):
    intent: str = Field(..., description="The classified intent, e.g., order_tracking, complaint, general_policy, general_query, greeting, goodbye, refund, unknown")
    confidence: float = Field(..., description="Confidence score from 0.0 to 1.0")
    entities: EntityExtraction = Field(default_factory=EntityExtraction, description="Extracted entities from the message")
    tool: Optional[str] = Field(None, description="The recommended tool to invoke")
    priority: str = Field("low", description="AI-judged urgency of the customer's message: 'high' or 'low'")
    mood: str = Field("happy", description="AI-judged customer mood based on their wording: 'happy' or 'sad'")

    @field_validator("priority", mode="before")
    @classmethod
    def _normalize_priority(cls, v):
        if not isinstance(v, str) or v.strip().lower() not in ("high", "low"):
            return "low"
        return v.strip().lower()

    @field_validator("mood", mode="before")
    @classmethod
    def _normalize_mood(cls, v):
        if not isinstance(v, str) or v.strip().lower() not in ("happy", "sad"):
            return "happy"
        return v.strip().lower()

class ToolRequest(BaseModel):
    tool_name: str = Field(..., description="Name of the tool to invoke")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters to pass to the tool")

class ToolResponse(BaseModel):
    success: bool = Field(..., description="Whether the tool execution succeeded")
    message: str = Field(..., description="User-friendly message returned by the service")
    data: Optional[Dict[str, Any]] = Field(None, description="Raw data returned by the service")

class ConversationResponse(BaseModel):
    text: str = Field(..., description="The natural language response for the user")

class GeminiResponse(BaseModel):
    raw_response: str = Field(..., description="Raw text response from Gemini API")
    structured_data: Optional[Dict[str, Any]] = Field(None, description="Parsed JSON/structured data from the response if any")
