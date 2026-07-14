# Developer Console

## Overview
To facilitate rapid testing, debugging, and prompt optimization without needing to modify backend production code, we have introduced a dedicated developer environment using Streamlit. The `developer_console.py` provides a visually split interface mimicking a live chat environment on the left, while exposing the internal pipeline metrics in a collapsible debug panel on the right.

## Features
- **Chat Interface:** Standard simulated user experience connecting directly to the Orchestration layer.
- **Controls Panel:** 
  - *Reset Conversation:* Generates a new session ID and wipes the UI context.
  - *Clear State:* Preserves the UI chat history but drops all tracked `ConversationState` variables in the `StateManager`, mimicking a stateless context reset.
  - *Export Conversation Log:* Dumps the active session messages to a `.json` file for prompt engineering evaluation.
- **Debug Inspection Toggles:**
  - *Internal State:* Live feed of `current_flow`, `current_stage`, and known variables mapped to the current `session_id`.
  - *Intent Parser Output:* Exposes the LLM's classification latency, raw string `intent`, parsed `confidence`, and any explicitly isolated entities prior to state modification.
  - *FlowManager Output:* Displays the deterministic routing logic result: `Flow Status`, `Tool Request`, and `Tool Arguments` bound inside the orchestration boundary.
  - *Raw Gemini JSON (Developer Mode):* Directly exposes the unmodified Pydantic schema dump for validation debugging.

## Security Constraints
This console is isolated exclusively to standard logic flows. 
- **NO API Keys** are hardcoded into the UI.
- **NO Database logic** or credentials are fundamentally altered or exposed.
- All testing runs purely through the localized application scope.

## How to Run
Navigate to the root directory and execute:
```bash
streamlit run developer_console.py
```
*(Ensure the virtual environment is active and the Google API Key is in the `.env` file)*
