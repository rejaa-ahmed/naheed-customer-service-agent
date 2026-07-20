import streamlit as st
import time
import json
import uuid

from core.conversation_manager import ConversationManager
from utils.helpers import build_reassurance_prefix

# Initialize session state for Streamlit
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_manager" not in st.session_state:
    st.session_state.conversation_manager = ConversationManager()
if "debug_data" not in st.session_state:
    st.session_state.debug_data = {}
if "processing" not in st.session_state:
    st.session_state.processing = False
if "pending_input" not in st.session_state:
    st.session_state.pending_input = None

st.set_page_config(page_title="Naheed Dev Console", layout="wide")

st.title("Naheed Conversational AI - Developer Console")

# Sidebar - Controls
with st.sidebar:
    st.header("Controls")
    if st.button("Reset Conversation"):
        st.session_state.messages = []
        st.session_state.debug_data = {}
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()
        
    if st.button("Clear State"):
        st.session_state.conversation_manager.state_manager.clear_state(st.session_state.session_id)
        st.success("State Cleared!")
        
    if st.button("Export Conversation Log"):
        log_data = json.dumps(st.session_state.messages, indent=2)
        st.download_button("Download JSON", log_data, "conversation_log.json", "application/json")
        
    st.header("Debug Toggles")
    show_internal_state = st.checkbox("Show Internal State", value=True)
    show_intent_parser = st.checkbox("Show Intent Parser Output", value=True)
    show_flow_manager = st.checkbox("Show FlowManager Output", value=True)
    dev_mode = st.checkbox("Developer Mode (Raw JSON)", value=False)

# Main Layout
chat_col, debug_col = st.columns([1, 1])

# Chat Interface
with chat_col:
    st.subheader("Chat Interface")
    
    # Display messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    # Display error if message exceeded word limit
    if st.session_state.get("word_limit_error"):
        st.error(st.session_state.word_limit_error)

    # Input
    user_input = st.chat_input("Type your message here...", disabled=st.session_state.processing)
    
    current_state = st.session_state.conversation_manager.state_manager.get_state(st.session_state.session_id)
    if current_state.entities.get("show_upload") or current_state.current_stage == "waiting_for_image":
        uploaded_file = st.file_uploader("Upload wrong item image", type=["png", "jpg", "jpeg"])
        if uploaded_file is not None:
            if st.button("Submit Image"):
                import os
                os.makedirs("static/uploads", exist_ok=True)
                file_path = os.path.join("static", "uploads", uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                user_input = f"[Image Uploaded: /static/uploads/{uploaded_file.name}]"

    # Capture new input and enter processing mode with word limit validation
    if user_input and not st.session_state.processing:
        import os
        word_limit = int(os.getenv("MAX_INPUT_WORDS", "100"))
        if not user_input.startswith("[Image Uploaded:") and len(user_input.split()) > word_limit:
            st.session_state.word_limit_error = f"Your message is too long ({len(user_input.split())} words). Please limit your message to {word_limit} words."
        else:
            st.session_state.word_limit_error = None
            st.session_state.processing = True
            st.session_state.pending_input = user_input
            st.rerun()

    # Process pending input if we are in processing mode
    if st.session_state.processing and st.session_state.pending_input:
        current_input = st.session_state.pending_input
        
        # Append user message
        st.session_state.messages.append({"role": "user", "content": current_input})
        with st.chat_message("user"):
            st.markdown(current_input)
            
        start_time = time.time()
        
        session_id = st.session_state.session_id
        cm = st.session_state.conversation_manager
        
        try:
            response_text, debug_data = cm.process_message_with_debug(current_input, session_id)
            latency = time.time() - start_time
            debug_data["latency"] = f"{latency:.2f}s"
            st.session_state.debug_data = debug_data
        except Exception as e:
            response_text = "An error occurred processing your message."
            st.session_state.debug_data = {"error": str(e)}
        
        # Note: cm.process_message_with_debug already adds the assistant message to StateManager.
        # We just need to append it to the Streamlit local cache.
        # Actually, cm also adds the user message! So we need to stop adding it twice?
        # Wait, developer_console added it in line 110: st.session_state.messages.append(...)
        # So we just append the assistant response here:
        st.session_state.messages.append({"role": "assistant", "content": response_text})
        
        with st.chat_message("assistant"):
            st.markdown(response_text)
            
        # Clean up processing state
        st.session_state.pending_input = None
        st.session_state.processing = False
        
        st.rerun()

# Debug Panel
with debug_col:
    st.subheader("Debug Panel")
    
    current_state = st.session_state.conversation_manager.state_manager.get_state(st.session_state.session_id)
    debug = st.session_state.debug_data
    
    if show_internal_state:
        with st.expander("Internal State", expanded=True):
            st.write(f"**Session ID:** {st.session_state.session_id}")
            st.write(f"**Current Flow:** {current_state.current_flow}")
            st.write(f"**Current Stage:** {current_state.current_stage}")
            st.write(f"**Waiting for Order ID:** {current_state.waiting_for_order_id}")
            st.write("**Extracted Entities:**", current_state.entities)
            st.write(f"**Session Priority:** {current_state.priority}")
            st.write(f"**Session Mood:** {current_state.mood}")
            
    if debug.get("used_fallback_router"):
        st.warning(f"All configured LLM providers failed - used the rule-based fallback router.\n\nLLM error: {debug.get('llm_error')}")
    if debug.get("error"):
        st.error(f"Unexpected error: {debug.get('error')}")

    if show_intent_parser and "intent" in debug:
        with st.expander("Intent Parser Output", expanded=True):
            st.write(f"**Response Latency:** {debug.get('latency')}")
            st.write(f"**Detected Intent:** {debug.get('intent')}")
            st.write(f"**Confidence Score:** {debug.get('confidence')}")
            st.write(f"**Source:** {'Rule-based fallback' if debug.get('used_fallback_router') else 'AI (LLM)'}")
            st.write("**Parsed Entities:**", debug.get('entities'))
            priority_label = "\U0001F534 High" if debug.get("priority") == "high" else "\U0001F7E2 Low"
            mood_label = "\U0001F60A Happy" if debug.get("mood") == "happy" else "\U0001F61E Sad"
            st.write(f"**Priority:** {priority_label}")
            st.write(f"**Customer Mood:** {mood_label}")
            
    if show_flow_manager and "flow_status" in debug:
        with st.expander("FlowManager Output", expanded=True):
            st.write(f"**Flow Status:** {debug.get('flow_status')}")
            st.write(f"**Tool Request:** {debug.get('tool_request')}")
            st.write("**Tool Arguments:**", debug.get('tool_args'))
            
    if dev_mode and "raw_json" in debug:
        with st.expander("Raw Gemini JSON", expanded=True):
            st.json(debug.get("raw_json"))
