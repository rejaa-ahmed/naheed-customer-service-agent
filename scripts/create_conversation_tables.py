import sys
import os

# Add project root to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import DatabaseManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    create_sessions_table = """
    CREATE TABLE IF NOT EXISTS conversation_sessions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        session_id VARCHAR(255) UNIQUE NOT NULL,
        customer_identifier VARCHAR(255) NULL,
        summary TEXT NULL,
        started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_activity DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'closed', 'escalated')),
        INDEX (last_activity)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """

    create_messages_table = """
    CREATE TABLE IF NOT EXISTS chatbot_messages (
        id INT AUTO_INCREMENT PRIMARY KEY,
        conversation_id INT NOT NULL,
        sender VARCHAR(50) NOT NULL,
        message TEXT NOT NULL,
        message_type VARCHAR(50) NULL,
        intent VARCHAR(255) NULL,
        flow_name VARCHAR(255) NULL,
        confidence FLOAT NULL,
        metadata JSON NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (conversation_id) REFERENCES conversation_sessions(id) ON DELETE CASCADE,
        INDEX (conversation_id),
        INDEX (timestamp),
        INDEX (sender)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """

    create_audit_logs_table = """
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        request_id VARCHAR(50) NOT NULL,
        session_id VARCHAR(255) NOT NULL,
        conversation_id INT NULL,
        source VARCHAR(50) DEFAULT 'chatbot',
        actor VARCHAR(50) DEFAULT 'system',
        actor_id VARCHAR(100) NULL,
        event_type VARCHAR(100) NOT NULL,
        category VARCHAR(50) NOT NULL,
        outcome VARCHAR(20) NOT NULL,
        duration_ms INT NULL,
        error_code VARCHAR(100) NULL,
        order_id VARCHAR(100) NULL,
        complaint_id VARCHAR(100) NULL,
        metadata JSON NULL,
        INDEX (request_id),
        INDEX (session_id),
        INDEX (timestamp),
        INDEX (event_type),
        INDEX (source)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """

    try:
        db = DatabaseManager()
        with db as conn:
            cursor = conn.cursor()
            
            logger.info("Creating conversation_sessions table...")
            cursor.execute(create_sessions_table)
            
            logger.info("Creating chatbot_messages table...")
            cursor.execute(create_messages_table)
            
            logger.info("Creating audit_logs table...")
            cursor.execute(create_audit_logs_table)
            
            conn.commit()
            cursor.close()
            logger.info("Migration successful.")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    run_migration()
