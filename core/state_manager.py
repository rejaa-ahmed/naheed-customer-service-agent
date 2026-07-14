import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class ConversationState(BaseModel):
    current_flow: Optional[str] = None
    current_stage: Optional[str] = None
    waiting_for_order_id: bool = False
    waiting_for_complaint: bool = False
    waiting_for_confirmation: bool = False
    conversation_history: List[Dict[str, str]] = Field(default_factory=list)
    entities: Dict[str, Any] = Field(default_factory=dict)
    last_assistant_message: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)

class StateManager:
    def __init__(self, timeout_seconds: int = 300):
        # Maps session_id (e.g. user_id) to ConversationState
        self.sessions: Dict[str, ConversationState] = {}
        self.timeout_seconds = timeout_seconds
        
    def get_state(self, session_id: str = "default") -> ConversationState:
        """Retrieves active state or initializes a new one. Handles context expiration."""
        state = self.sessions.get(session_id)
        if not state:
            state = ConversationState()
            self.sessions[session_id] = state
            return state
            
        # Check timeout (Context Expiration)
        if time.time() - state.timestamp > self.timeout_seconds:
            self.clear_state(session_id)
            return self.sessions[session_id]
            
        # Refresh timestamp on access
        state.timestamp = time.time()
        return state

    def update_state(self, session_id: str, updates: Dict[str, Any]):
        state = self.get_state(session_id)
        for k, v in updates.items():
            if hasattr(state, k):
                setattr(state, k, v)
        state.timestamp = time.time()

    def add_message(self, session_id: str, role: str, content: str):
        """Adds a message to the conversation history."""
        state = self.get_state(session_id)
        state.conversation_history.append({"role": role, "content": content})
        if role == "assistant":
            state.last_assistant_message = content
        state.timestamp = time.time()

    def update_entities(self, session_id: str, new_entities: Dict[str, Any]):
        """Merges new extracted entities into the persistent session."""
        state = self.get_state(session_id)
        # Only update non-null entities
        for k, v in new_entities.items():
            if v is not None:
                state.entities[k] = v
        state.timestamp = time.time()
        
    def check_cancellation(self, message: str) -> bool:
        """Checks if the user wants to cancel the current workflow."""
        cancel_words = ["cancel", "start over", "never mind", "nevermind", "forget it", "reset", "abort"]
        msg_lower = message.lower().strip()
        # Ensure it's not a substring of a normal word by checking exact match or prefix/suffix handling.
        # But a simple `in` works well for this Phase 3 requirement.
        return any(word in msg_lower for word in cancel_words)
        
    def clear_state(self, session_id: str = "default"):
        """Resets the conversation to a clean slate."""
        if session_id in self.sessions:
            self.sessions[session_id] = ConversationState()
