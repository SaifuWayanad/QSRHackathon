"""
Session management for customer chat
Handles session creation, message storage, and conversation history
"""

import pymysql
import uuid
from datetime import datetime
from constants import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE


def get_db_connection():
    """Get database connection"""
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        cursorclass=pymysql.cursors.DictCursor
    )


def create_session(customer_phone=None, customer_id=None):
    """
    Create a new chat session
    
    Args:
        customer_phone: Customer phone number (optional)
        customer_id: Customer ID if already identified (optional)
    
    Returns:
        dict: Session data with id and session_code
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Generate session ID and code
        session_id = str(uuid.uuid4())
        
        # Get next session code
        cursor.execute("""
            SELECT MAX(CAST(SUBSTRING(session_code, 6) AS UNSIGNED)) as max_num 
            FROM chat_sessions WHERE session_code LIKE 'SESS-%'
        """)
        result = cursor.fetchone()
        max_num = result['max_num'] if result and result['max_num'] else 0
        session_code = f"SESS-{str(max_num + 1).zfill(3)}"
        
        # Insert session
        now = datetime.now()
        cursor.execute("""
            INSERT INTO chat_sessions 
                (id, session_code, customer_id, customer_phone, started_at, 
                 last_activity_at, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, 'active', %s, %s)
        """, (session_id, session_code, customer_id, customer_phone, now, now, now, now))
        
        conn.commit()
        
        return {
            'id': session_id,
            'session_code': session_code,
            'customer_id': customer_id,
            'customer_phone': customer_phone
        }
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error creating session: {e}")
        return None
    finally:
        conn.close()


def get_session(session_id):
    """
    Get session details
    
    Args:
        session_id: Session ID
    
    Returns:
        dict: Session data or None
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, session_code, customer_id, customer_phone, 
                   started_at, last_activity_at, status
            FROM chat_sessions 
            WHERE id = %s
        """, (session_id,))
        
        return cursor.fetchone()
    except Exception as e:
        print(f"❌ Error getting session: {e}")
        return None
    finally:
        conn.close()


def update_session_customer(session_id, customer_id, customer_phone):
    """
    Update session with customer information after identification
    
    Args:
        session_id: Session ID
        customer_id: Customer ID
        customer_phone: Customer phone number
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE chat_sessions 
            SET customer_id = %s, 
                customer_phone = %s,
                updated_at = %s
            WHERE id = %s
        """, (customer_id, customer_phone, datetime.now(), session_id))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"❌ Error updating session: {e}")
        return False
    finally:
        conn.close()


def save_message(session_id, sender, message, metadata=None):
    """
    Save a message to the session
    
    Args:
        session_id: Session ID
        sender: 'customer' or 'agent'
        message: Message text
        metadata: Optional metadata dict
    
    Returns:
        str: Message ID or None
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        message_id = str(uuid.uuid4())
        now = datetime.now()
        
        # Convert metadata to JSON string if provided
        import json
        metadata_json = json.dumps(metadata) if metadata else None
        
        cursor.execute("""
            INSERT INTO chat_messages 
                (id, session_id, sender, message, metadata, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (message_id, session_id, sender, message, metadata_json, now))
        
        # Update session last activity
        cursor.execute("""
            UPDATE chat_sessions 
            SET last_activity_at = %s 
            WHERE id = %s
        """, (now, session_id))
        
        conn.commit()
        return message_id
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error saving message: {e}")
        return None
    finally:
        conn.close()


def get_session_messages(session_id, limit=50):
    """
    Get all messages in a session
    
    Args:
        session_id: Session ID
        limit: Maximum number of messages to retrieve (default 50)
    
    Returns:
        list: List of message dicts
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, sender, message, metadata, created_at
            FROM chat_messages 
            WHERE session_id = %s
            ORDER BY created_at ASC
            LIMIT %s
        """, (session_id, limit))
        
        messages = cursor.fetchall()
        
        # Parse metadata JSON
        import json
        for msg in messages:
            if msg.get('metadata'):
                try:
                    msg['metadata'] = json.loads(msg['metadata'])
                except:
                    msg['metadata'] = None
        
        return messages
        
    except Exception as e:
        print(f"❌ Error getting messages: {e}")
        return []
    finally:
        conn.close()


def get_conversation_history(session_id, format='text'):
    """
    Get formatted conversation history for the agent
    
    Args:
        session_id: Session ID
        format: 'text' or 'messages' (default 'text')
    
    Returns:
        str or list: Formatted conversation history
    """
    messages = get_session_messages(session_id)
    
    if format == 'messages':
        # Return as list of message objects
        return [
            {
                'role': 'user' if msg['sender'] == 'customer' else 'assistant',
                'content': msg['message']
            }
            for msg in messages
        ]
    else:
        # Return as formatted text
        if not messages:
            return "No previous conversation."
        
        history = "Previous Conversation:\n" + "="*50 + "\n"
        for msg in messages:
            sender_label = "Customer" if msg['sender'] == 'customer' else "Agent"
            history += f"{sender_label}: {msg['message']}\n"
        history += "="*50 + "\n"
        
        return history


def close_session(session_id, status='completed'):
    """
    Close a session
    
    Args:
        session_id: Session ID
        status: 'completed' or 'abandoned'
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE chat_sessions 
            SET status = %s, updated_at = %s
            WHERE id = %s
        """, (status, datetime.now(), session_id))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"❌ Error closing session: {e}")
        return False
    finally:
        conn.close()


def get_active_sessions(customer_phone=None):
    """
    Get active sessions, optionally filtered by customer phone
    
    Args:
        customer_phone: Optional phone number to filter
    
    Returns:
        list: List of active sessions
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        if customer_phone:
            cursor.execute("""
                SELECT id, session_code, customer_id, customer_phone, 
                       started_at, last_activity_at
                FROM chat_sessions 
                WHERE status = 'active' AND customer_phone = %s
                ORDER BY last_activity_at DESC
            """, (customer_phone,))
        else:
            cursor.execute("""
                SELECT id, session_code, customer_id, customer_phone, 
                       started_at, last_activity_at
                FROM chat_sessions 
                WHERE status = 'active'
                ORDER BY last_activity_at DESC
                LIMIT 100
            """)
        
        return cursor.fetchall()
        
    except Exception as e:
        print(f"❌ Error getting active sessions: {e}")
        return []
    finally:
        conn.close()
