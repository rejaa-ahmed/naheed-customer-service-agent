import mysql.connector
from mysql.connector import Error, pooling
import threading
from config.settings import (
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD,
    DB_POOL_NAME, DB_POOL_SIZE, DB_CONNECTION_TIMEOUT, DB_POOL_RESET_SESSION
)
from utils.logger import get_logger

logger = get_logger(__name__)

_pool = None
_pool_lock = threading.Lock()

def get_connection_pool():
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                logger.info(f"Initializing MySQL Connection Pool: {DB_POOL_NAME} (size={DB_POOL_SIZE})")
                try:
                    _pool = pooling.MySQLConnectionPool(
                        pool_name=DB_POOL_NAME,
                        pool_size=DB_POOL_SIZE,
                        pool_reset_session=DB_POOL_RESET_SESSION,
                        host=DB_HOST,
                        port=DB_PORT,
                        database=DB_NAME,
                        user=DB_USER,
                        password=DB_PASSWORD,
                        connection_timeout=DB_CONNECTION_TIMEOUT
                    )
                except Error as e:
                    logger.error(f"Failed to create connection pool: {e}")
                    raise e
    return _pool

class DatabaseManager:
    def __init__(self):
        self.connection = None

    def __enter__(self):
        import time
        max_retries = 5
        for attempt in range(max_retries):
            try:
                pool = get_connection_pool()
                self.connection = pool.get_connection()
                # Validate connection before handing it off
                if not self.connection.is_connected():
                    logger.warning("Pooled connection is stale. Reconnecting...")
                    self.connection.reconnect(attempts=3, delay=1)
                return self.connection
            except mysql.connector.errors.PoolError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Connection pool exhausted! Retrying in 1s (Attempt {attempt+1}/{max_retries})")
                    time.sleep(1)
                else:
                    logger.error("Connection pool exhausted after max retries! No available connections.")
                    raise e
            except Error as e:
                logger.error(f"Error connecting to MySQL Database from pool: {e}")
                raise e

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection and self.connection.is_connected():
            self.connection.close()

class Database:
    def __init__(self):
        self.connection = None

    def connect(self):
        import time
        max_retries = 5
        for attempt in range(max_retries):
            try:
                if not self.connection or not self.connection.is_connected():
                    pool = get_connection_pool()
                    self.connection = pool.get_connection()
                    if not self.connection.is_connected():
                        self.connection.reconnect(attempts=3, delay=1)
                return
            except mysql.connector.errors.PoolError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Connection pool exhausted! Retrying in 1s (Attempt {attempt+1}/{max_retries})")
                    time.sleep(1)
                else:
                    logger.error("Connection pool exhausted after max retries! No available connections.")
                    raise e
            except Error as e:
                logger.error(f"Error connecting to MySQL Database via pool: {e}")
                raise e

    def disconnect(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()

    def health_check(self) -> dict:
        result = {
            "version": None,
            "database": None,
            "status": "Disconnected",
            "error": None
        }
        try:
            self.connect()
            if self.connection and self.connection.is_connected():
                cursor = self.connection.cursor()
                
                cursor.execute("SELECT VERSION();")
                version = cursor.fetchone()[0]
                result["version"] = version
                
                cursor.execute("SELECT DATABASE();")
                database = cursor.fetchone()[0]
                result["database"] = database
                
                result["status"] = "Connected"
                cursor.close()
        except Exception as e:
            result["error"] = str(e)
            result["status"] = "Error"
        finally:
            self.disconnect()
            
        return result
