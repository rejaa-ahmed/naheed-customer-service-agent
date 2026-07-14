import time
import asyncio
from core.conversation_manager import ConversationManager

def run_tests():
    cm = ConversationManager()
    
    test_phrases = [
        "order kidhar hai",
        "mera order check karo",
        "mera parcel kahan hai",
        "mera order nahi mila",
        "mera order kab ayega",
        "tracking number batao",
        "Track my order",
        "Where is my order?",
        "Check order 20000000"
    ]
    
    print("--- Intent Testing ---")
    total_time = 0
    for phrase in test_phrases:
        start_time = time.time()
        # Mock LLM API if it is slow, but we want to measure actual LLM latency
        # The ConversationManager internally calls parser.parse_intent which calls Gemini
        # We will track how long it takes
        cm.process_message(phrase, session_id="test_session")
        elapsed = time.time() - start_time
        total_time += elapsed
        state = cm.state_manager.get_state("test_session")
        print(f"[{elapsed:.2f}s] '{phrase}' -> Flow: {state.current_flow} / Extracted: {state.entities}")
        
    print(f"Avg Response Time: {total_time/len(test_phrases):.2f}s")
    
if __name__ == "__main__":
    run_tests()
