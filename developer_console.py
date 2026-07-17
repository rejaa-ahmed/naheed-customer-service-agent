import streamlit as st
import time
import json
import uuid

from ai.intent_parser import IntentParser
from core.state_manager import StateManager
from core.flow_manager import FlowManager
from services.order_service import OrderService

# Initialize session state for Streamlit
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "state_manager" not in st.session_state:
    st.session_state.state_manager = StateManager()
if "intent_parser" not in st.session_state:
    st.session_state.intent_parser = IntentParser()
if "flow_manager" not in st.session_state:
    st.session_state.flow_manager = FlowManager()
if "order_service" not in st.session_state:
    st.session_state.order_service = OrderService()
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
        st.session_state.state_manager.clear_state(st.session_state.session_id)
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
    
    current_state = st.session_state.state_manager.get_state(st.session_state.session_id)
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
        
        # 1. State check
        session_id = st.session_state.session_id
        sm: StateManager = st.session_state.state_manager
        
        if sm.check_cancellation(current_input):
            sm.clear_state(session_id)
            response_text = "Conversation reset. How can I help you?"
            st.session_state.debug_data = {"cancellation": True}
        else:
            sm.add_message(session_id, "user", current_input)
            current_state = sm.get_state(session_id)
            
            # 2. Intent Parsing
            try:
                intent_result = st.session_state.intent_parser.parse_intent(current_input, state=current_state)
                # Ensure entities is dict for debug panel
                entities_dict = intent_result.entities if isinstance(intent_result.entities, dict) else intent_result.entities.model_dump()
                sm.update_entities(session_id, entities_dict)
                
                # 3. Flow Manager Execution
                refreshed_state = sm.get_state(session_id)
                flow_response = st.session_state.flow_manager.execute_flow(intent_result, refreshed_state)
                
                # 4. State updates
                if flow_response.status == "completed":
                    sm.clear_state(session_id)
                else:
                    sm.update_state(session_id, flow_response.updated_state)
                    
                response_text = flow_response.response
                
                # Mock Tool Dispatch
                if flow_response.tool_request == "track_order":
                    order_id = flow_response.tool_args.get("order_id")
                    service_response = st.session_state.order_service.track_order(order_id)
                    response_text = service_response.get("message", "We encountered an issue checking your order.")
                elif flow_response.tool_request == "modify_order":
                    order_id = flow_response.tool_args.get("order_id")
                    service_response = st.session_state.order_service.check_order_modifiable(order_id)
                    response_text = service_response.get("message", "We encountered an issue checking your order status.")
                    if not service_response.get("success"):
                        st.session_state.state_manager.update_state(st.session_state.session_id, {
                            "current_flow": "modify_order",
                            "waiting_for_order_id": True
                        })
                elif flow_response.tool_request == "create_complaint":
                    order_id = flow_response.tool_args.get("order_id")
                    complaint_type = flow_response.tool_args.get("complaint_type")
                    details = flow_response.tool_args.get("details")
                    image_url = flow_response.tool_args.get("image_url")
                    
                    if "complaint_service" not in st.session_state:
                        from services.complaint_service import ComplaintService
                        st.session_state.complaint_service = ComplaintService()
                        
                    service_response = st.session_state.complaint_service.create_complaint(
                        order_id=order_id,
                        complaint_type=complaint_type,
                        details=details,
                        image_url=image_url
                    )
                    ticket_msg = service_response.get("message", "")
                    # Preserve the flow's rich response (e.g. COD/refund status message)
                    # and append the ticket confirmation instead of overwriting it.
                    if response_text:
                        response_text = f"{response_text}\n\n{ticket_msg}"
                    else:
                        response_text = ticket_msg
                    
                latency = time.time() - start_time
                
                st.session_state.debug_data = {
                    "latency": f"{latency:.2f}s",
                    "intent": intent_result.intent,
                    "confidence": intent_result.confidence,
                    "entities": entities_dict,
                    "flow_status": flow_response.status,
                    "tool_request": flow_response.tool_request,
                    "tool_args": flow_response.tool_args,
                    "raw_json": intent_result.model_dump()
                }
                
            except Exception as e:
                response_text = "An error occurred connecting to the AI."
                st.session_state.debug_data = {"error": str(e)}
        
        sm.add_message(session_id, "assistant", response_text)
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
    
    current_state = st.session_state.state_manager.get_state(st.session_state.session_id)
    debug = st.session_state.debug_data
    
    if show_internal_state:
        with st.expander("Internal State", expanded=True):
            st.write(f"**Session ID:** {st.session_state.session_id}")
            st.write(f"**Current Flow:** {current_state.current_flow}")
            st.write(f"**Current Stage:** {current_state.current_stage}")
            st.write(f"**Waiting for Order ID:** {current_state.waiting_for_order_id}")
            st.write("**Extracted Entities:**", current_state.entities)
            
    if show_intent_parser and "intent" in debug:
        with st.expander("Intent Parser Output", expanded=True):
            st.write(f"**Response Latency:** {debug.get('latency')}")
            st.write(f"**Detected Intent:** {debug.get('intent')}")
            st.write(f"**Confidence Score:** {debug.get('confidence')}")
            st.write("**Parsed Entities:**", debug.get('entities'))
            
    if show_flow_manager and "flow_status" in debug:
        with st.expander("FlowManager Output", expanded=True):
            st.write(f"**Flow Status:** {debug.get('flow_status')}")
            st.write(f"**Tool Request:** {debug.get('tool_request')}")
            st.write("**Tool Arguments:**", debug.get('tool_args'))
            
    if dev_mode and "raw_json" in debug:
        with st.expander("Raw Gemini JSON", expanded=True):
            st.json(debug.get("raw_json"))
