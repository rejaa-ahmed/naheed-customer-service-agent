# Naheed Chat Bot

A robust, AI-powered customer support chatbot designed to handle user inquiries dynamically. Built with Streamlit, Python, and integrated with Gemini (and Groq fallback) LLMs, it leverages conversational flow orchestration to process specific intents seamlessly—currently specializing in robust, real-time Order Tracking backed by a live MySQL database.

## 🚀 Features

- **Order Tracking Flow:** Connects to a live Magento database to securely fetch real-time shipping statuses, intelligent ETA estimation, and courier routing. Accurately categorizes external and local (Karachi) shipments, offering corresponding live tracking links (Leopards Courier, Mulphi Log, etc.).
- **Roman Urdu & English Support:** Employs advanced Natural Language Processing to accurately detect intent across both English and Roman Urdu inquiries.
- **Conversational Flow Orchestration:** Uses a layered architecture with an `IntentParser`, `ConversationManager`, and dedicated Flow Managers (like `OrderTrackingFlow`), ensuring code is easily extensible for future phases (Refunds, Complaints, etc.).
- **High-Performance DB Polling:** Utilizes a globally shared, thread-safe MySQL Connection Pool (`mysql.connector.pooling`), guaranteeing near-instant (< 2s) query execution and zero connection leaks under load.
- **Multi-LLM Fallback:** Integrated with both Gemini and Groq with automatic failover to gracefully survive infrastructure errors (429 Rate Limits, 503 Server Errors).

## 🏗️ Architecture

The chatbot relies on a structured, modular design pattern:
1. **Streamlit UI (`developer_console.py`):** Acts as the interactive presentation layer.
2. **Conversation Manager (`core/conversation_manager.py`):** The orchestration brain that logs the state, routes the chat, and executes business processes.
3. **Intent Parser (`ai/intent_parser.py`):** Resolves free-form inputs (across multiple languages) to specific predefined intents.
4. **Flow Manager (`core/flow_manager.py` & `flows/`):** Executes intent-specific logic (e.g., retrieving missing information, updating context, and constructing a response).
5. **Database Manager (`database/`):** Manages a thread-safe connection pool strictly configured via `.env` to execute queries securely against the Magento MySQL database.

## ⚙️ Environment Variables

The application relies heavily on environment variables for sensitive settings. Create a `.env` file in the root of the project to match the following configuration block:

```env
# Database Credentials
DB_HOST=your_database_host
DB_PORT=3306
DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_database_password

# Database Connection Pooling
DB_POOL_NAME=chatbot_pool
DB_POOL_SIZE=5
DB_CONNECTION_TIMEOUT=10
DB_POOL_RESET_SESSION=True

# LLM API Keys
GEMINI_API_KEY=your_gemini_key
GROQ_API_KEY=your_groq_key
```

## 🛠️ Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/naheed-chatbot.git
   cd naheed-chatbot
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   
   # Windows:
   .\.venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   *(Ensure you have a `requirements.txt` file configured with streamlit, mysql-connector-python, etc.)*
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure the Environment Variables:**
   Rename `.env.example` to `.env` or create a new `.env` file containing your configurations as described above.

## ▶️ Running the Project

Start the local server using Streamlit. This will launch the developer console simulating a real conversation.

```bash
streamlit run developer_console.py
```

## 🧪 Testing

To ensure the business logic, SQL integrations, and UI mappings are functioning correctly, run the provided unit tests:

```bash
python -m unittest discover tests/
```
