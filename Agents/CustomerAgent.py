from agno.agent import Agent
from agno.models.google import Gemini
import os
import sys
import json
import pymysql
import uuid
from datetime import datetime
from urllib.parse import quote_plus

try:
    from agno.models.anthropic import Claude
except ImportError:
    Claude = None

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from Agents.customer_instructions import customer_instructions
from constants import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE

# Set API keys
ANTHROPIC_API_KEY = "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"
os.environ["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY

# Initialize Google Gemini model
gemini_model = Gemini("gemini-2.5-flash", api_key="AIzaSyD6v6dOt-hxwzcZWhwrizKfgM_oiwJjXTw")
os.environ["GOOGLE_API_KEY"] = "AIzaSyD6v6dOt-hxwzcZWhwrizKfgM_oiwJjXTw"


def get_main_db_connection():
    """Get connection to main MySQL database"""
    try:
        conn = pymysql.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
            cursorclass=pymysql.cursors.DictCursor
        )
        return conn
    except Exception as e:
        print(f"Error connecting to main database: {e}")
        return None


def execute_database_query(query: str, params: list = None) -> str:
    """
    Execute a database query against the MySQL QSR database.
    
    This is the PRIMARY tool for ALL database operations including:
    - Reading menu items, categories, orders
    - Inserting new orders and order items
    - Updating order status
    - Checking food availability
    
    Args:
        query: SQL query to execute (SELECT, INSERT, UPDATE)
        params: List of parameters for parameterized queries (use %s placeholders)
    
    Returns:
        JSON string with results or error message
    """
    conn = get_main_db_connection()
    if not conn:
        return json.dumps({"error": "Database connection failed"})
    
    try:
        cursor = conn.cursor()
        
        # Execute query with or without parameters
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        # Handle SELECT queries
        if query.strip().upper().startswith("SELECT"):
            results = cursor.fetchall()
            # Convert to list of dicts
            data = [dict(row) for row in results]
            return json.dumps({
                "success": True,
                "data": data,
                "count": len(data)
            }, default=str)  # default=str handles datetime serialization
        
        # Handle INSERT, UPDATE, DELETE queries
        else:
            conn.commit()
            return json.dumps({
                "success": True,
                "rows_affected": cursor.rowcount,
                "message": f"Query executed successfully. {cursor.rowcount} rows affected."
            })
            
    except Exception as e:
        conn.rollback()
        error_msg = str(e)
        print(f"❌ Database Error: {error_msg}")
        return json.dumps({
            "success": False,
            "error": error_msg,
            "message": "Database query failed. Please check your SQL syntax and try again."
        })
    finally:
        conn.close()


def get_customer_knowledge():
    """Retrieve customer-relevant knowledge from database"""
    conn = get_main_db_connection()
    if not conn:
        return {}
    
    knowledge = {}
    try:
        cursor = conn.cursor()
        
        # Get all available food items
        cursor.execute("""
            SELECT id, name, category_name, price, description, specifications, status 
            FROM food_items 
            WHERE status = 'available'
            ORDER BY category_name, name
        """)
        knowledge['available_items'] = [dict(row) for row in cursor.fetchall()]
        
        # Get all categories
        cursor.execute("""
            SELECT id, name, description 
            FROM categories 
            WHERE status = 'active'
            ORDER BY name
        """)
        knowledge['categories'] = [dict(row) for row in cursor.fetchall()]
        
        # Get order types
        cursor.execute("""
            SELECT id, name, description 
            FROM order_types 
            WHERE status = 'active'
            ORDER BY name
        """)
        knowledge['order_types'] = [dict(row) for row in cursor.fetchall()]
        
        # Get available tables
        cursor.execute("""
            SELECT id, number, area_name, capacity, status 
            FROM tables 
            WHERE status = 'available'
            ORDER BY area_name, number
        """)
        knowledge['available_tables'] = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
    except Exception as e:
        print(f"Error retrieving customer knowledge: {e}")
    
    return knowledge


def get_database_schema() -> dict:
    """Get comprehensive database schema information"""
    conn = get_main_db_connection()
    if not conn:
        return {}
    
    schema = {}
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = %s
            ORDER BY table_name
        """, (MYSQL_DATABASE,))
        tables = [row['table_name'] if isinstance(row, dict) else row[0] for row in cursor.fetchall()]
        
        # Get column details for each table
        for table in tables:
            cursor.execute("""
                SELECT column_name, column_type, is_nullable, column_key, extra
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
            """, (MYSQL_DATABASE, table))
            
            columns = []
            for col in cursor.fetchall():
                columns.append({
                    'name': col['column_name'] if isinstance(col, dict) else col[0],
                    'type': col['column_type'] if isinstance(col, dict) else col[1],
                    'nullable': col['is_nullable'] if isinstance(col, dict) else col[2],
                    'key': col['column_key'] if isinstance(col, dict) else col[3],
                    'extra': col['extra'] if isinstance(col, dict) else col[4]
                })
            schema[table] = columns
        
        conn.close()
    except Exception as e:
        print(f"Error retrieving database schema: {e}")
    
    return schema


def get_schema_documentation() -> str:
    """Get formatted schema documentation"""
    schema = get_database_schema()
    if not schema:
        return "Schema information unavailable"
    
    doc = "DATABASE SCHEMA:\n\n"
    for table, columns in schema.items():
        doc += f"Table: {table}\n"
        for col in columns:
            doc += f"  - {col['name']} ({col['type']}) {col['key']} {col['extra']}\n"
        doc += "\n"
    return doc


# Initialize CustomerAgent with tools
customer_agent = Agent(
    name="CustomerAgent",
    model=Claude(id="claude-3-5-haiku-20241022", api_key=ANTHROPIC_API_KEY) if Claude else gemini_model,
    instructions=customer_instructions,
    tools=[execute_database_query],
    markdown=False, # Hide backend query execution from user
    debug_mode=False
)

messages = ""
def chat_with_customer(message: str, session_id: str = None) -> str:
    """
    Main function to interact with customer agent
    
    Args:
        message: Customer's message
        session_id: Optional session ID to maintain conversation context
    
    Returns:
        Agent's response as string
    """
    try:
        # Add knowledge context if needed
        knowledge = get_customer_knowledge()
        
        # Create enhanced message with context
        context_message = f"""
Customer Message: {message}

Available Context:
- {len(knowledge.get('available_items', []))} food items available
- {len(knowledge.get('categories', []))} categories active
- {len(knowledge.get('order_types', []))} order types available

Database Schema Available: Use execute_database_query tool to access data.
"""
        
        # Run agent
        response = customer_agent.run(context_message)
        
        return response.content if hasattr(response, 'content') else str(response)
        
    except Exception as e:
        error_msg = f"Error in customer chat: {e}"
        print(f"❌ {error_msg}")
        return f"I apologize, but I'm having trouble processing your request right now. Please try again or speak with our staff. (Error: {str(e)})"


# if __name__ == "__main__":
#     """Test the customer agent"""
#     print("🤖 CustomerAgent Test Mode")
#     print("=" * 60)
#     print("Type 'quit' to exit")
#     print("=" * 60)
    
#     session_id = str(uuid.uuid4())
    
#     while True:
#         user_input = input("\n👤 You: ").strip()
        
#         if user_input.lower() in ['quit', 'exit', 'q']:
#             print("👋 Thanks for testing CustomerAgent!")
#             break
        
#         if not user_input:
#             continue
        
#         print("\n🤖 CustomerAgent: ", end="", flush=True)
#         response = chat_with_customer(user_input, session_id)
#         print(response)
