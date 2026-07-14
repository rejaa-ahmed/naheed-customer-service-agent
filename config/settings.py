import os
from dotenv import load_dotenv

load_dotenv()

required_vars = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]
missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Pool Configuration
DB_POOL_NAME = os.getenv("DB_POOL_NAME", "chatbot_pool")
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
DB_CONNECTION_TIMEOUT = int(os.getenv("DB_CONNECTION_TIMEOUT", "10"))
DB_POOL_RESET_SESSION = os.getenv("DB_POOL_RESET_SESSION", "True").lower() in ("true", "1", "yes")
