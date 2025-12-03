from agno.agent import Agent
from agno.models.google import Gemini
import os
import sys
import json
import sqlite3
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from Agents.instructions import kitchen_instructions
from Agents.capabilities import kitchen_caps
from Agents.db_schema import DatabaseSchema



# Initialize Google Gemini model
gemini_model = Gemini("gemini-2.5-flash", api_key="AIzaSyD6v6dOt-hxwzcZWhwrizKfgM_oiwJjXTw")
os.environ["GOOGLE_API_KEY"] = "AIzaSyD6v6dOt-hxwzcZWhwrizKfgM_oiwJjXTw"

# Database path for kitchen operations
DB_PATH = "my_db.db"




def get_main_db_connection():
    """Get connection to main database (my_db.db)"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"Error connecting to main database: {e}")
        return None


def get_kitchen_knowledge():
    """Retrieve kitchen knowledge from database"""
    conn = get_main_db_connection()
    if not conn:
        return {}
    
    knowledge = {}
    try:
        # Get all kitchens
        cursor = conn.execute("SELECT id, name, description, status FROM kitchens")
        knowledge['kitchens'] = [dict(row) for row in cursor.fetchall()]
        
        # Get all food items with kitchen assignments
        cursor = conn.execute("""
            SELECT id, name, category_name, kitchen_id, kitchen_name, price, description 
            FROM food_items ORDER BY kitchen_name, category_name
        """)
        knowledge['food_items'] = [dict(row) for row in cursor.fetchall()]
        
        # Get kitchen appliances
        cursor = conn.execute("""
            SELECT ka.id, ka.kitchen_id, a.name as appliance_name, a.type, 
                   ka.quantity, ka.location, ka.status
            FROM kitchen_appliances ka
            JOIN appliances a ON ka.appliance_id = a.id
            ORDER BY ka.kitchen_id
        """)
        knowledge['kitchen_appliances'] = [dict(row) for row in cursor.fetchall()]
        
        # Get current orders
        cursor = conn.execute("""
            SELECT id, order_number, customer_name, table_number, status, items_count, 
                   total_amount, created_at FROM orders 
            WHERE status IN ('pending', 'preparing') 
            ORDER BY created_at DESC LIMIT 20
        """)
        knowledge['active_orders'] = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
    except Exception as e:
        print(f"Error retrieving kitchen knowledge: {e}")
    
    return knowledge


def query_kitchen_database(query: str, params: tuple = None) -> list:
    """Execute a query against the main kitchen database"""
    conn = get_main_db_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        if query.strip().upper().startswith("SELECT"):
            results = cursor.fetchall()
            return [dict(row) for row in results]
        else:
            conn.commit()
            return [{"status": "success", "rows_affected": cursor.rowcount}]
    except Exception as e:
        print(f"Error executing database query: {e}")
        return []
    finally:
        conn.close()


def get_database_schema() -> dict:
    """Get comprehensive database schema information"""
    conn = get_main_db_connection()
    if not conn:
        return {}
    
    schema = {}
    try:
        # Get all tables
        cursor = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        # Get schema for each table
        for table_name in tables:
            cursor = conn.execute(f"PRAGMA table_info({table_name})")
            columns = []
            for row in cursor.fetchall():
                columns.append({
                    'name': row[1],
                    'type': row[2],
                    'not_null': bool(row[3]),
                    'default': row[4],
                    'pk': bool(row[5])
                })
            schema[table_name] = columns
        
        conn.close()
    except Exception as e:
        print(f"Error retrieving database schema: {e}")
    
    return schema


def get_schema_documentation() -> str:
    """Generate readable documentation of the database schema"""
    schema = get_database_schema()
    
    doc = """
╔════════════════════════════════════════════════════════════════════════╗
║                    DATABASE SCHEMA DOCUMENTATION                       ║
║                          (my_db.db)                                    ║
╚════════════════════════════════════════════════════════════════════════╝

"""
    
    for table_name, columns in sorted(schema.items()):
        doc += f"\n📋 TABLE: {table_name.upper()}\n"
        doc += "─" * 70 + "\n"
        
        for col in columns:
            pk_mark = "🔑 " if col['pk'] else "   "
            nn_mark = "[NOT NULL]" if col['not_null'] else ""
            doc += f"{pk_mark}{col['name']:25} {col['type']:15} {nn_mark}\n"
        
        # Get sample data count
        try:
            conn = get_main_db_connection()
            cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            doc += f"   └─ Records: {count}\n"
            conn.close()
        except:
            pass
        
        doc += "\n"
    
    return doc


def get_table_relationships() -> str:
    """Document foreign key relationships between tables"""
    conn = get_main_db_connection()
    if not conn:
        return "No database connection"
    
    relationships = "\n╔════════════════════════════════════════════════════════════════════════╗\n"
    relationships += "║                    TABLE RELATIONSHIPS (FOREIGN KEYS)                   ║\n"
    relationships += "╚════════════════════════════════════════════════════════════════════════╝\n\n"
    
    try:
        cursor = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        for table_name in tables:
            cursor = conn.execute(f"PRAGMA foreign_key_list({table_name})")
            fks = cursor.fetchall()
            
            if fks:
                relationships += f"📍 {table_name.upper()}\n"
                for fk in fks:
                    relationships += f"   └─ {fk[3]} → {fk[2]}.{fk[4]}\n"
                relationships += "\n"
        
        conn.close()
    except Exception as e:
        print(f"Error retrieving relationships: {e}")
    
    return relationships


def get_schema_summary() -> dict:
    """Get a summary of the database schema"""
    schema = get_database_schema()
    summary = {}
    
    for table_name, columns in schema.items():
        summary[table_name] = {
            'total_columns': len(columns),
            'primary_keys': [c['name'] for c in columns if c['pk']],
            'columns': [c['name'] for c in columns],
            'column_types': {c['name']: c['type'] for c in columns}
        }
    
    return summary


def execute_database_query(query: str, params: tuple = None) -> dict:
    """
    Execute a SQL query against the kitchen database and return results.
    
    This function serves as a database tool for the Kitchen Agent.
    It can execute SELECT queries (returns data) and modification queries (INSERT, UPDATE, DELETE).
    
    Args:
        query (str): The SQL query to execute
        params (tuple): Optional parameters for parameterized queries
    
    Returns:
        dict: Result dictionary containing:
            - success (bool): Whether query executed successfully
            - data (list): Query results (for SELECT queries)
            - rows_affected (int): Number of rows affected (for INSERT/UPDATE/DELETE)
            - error (str): Error message if query failed
            - query_type (str): Type of query (SELECT, INSERT, UPDATE, DELETE)
    
    Example:
        # SELECT query
        result = execute_database_query("SELECT * FROM orders WHERE status = ?", ('pending',))
        
        # INSERT query
        result = execute_database_query("INSERT INTO orders (id, order_number) VALUES (?, ?)", 
                                      ('uuid123', 'ORD-001'))
    """
    conn = get_main_db_connection()
    if not conn:
        return {
            'success': False,
            'error': 'Failed to establish database connection',
            'data': [],
            'rows_affected': 0,
            'query_type': 'UNKNOWN'
        }
    
    try:
        # Determine query type
        query_upper = query.strip().upper()
        if query_upper.startswith('SELECT'):
            query_type = 'SELECT'
        elif query_upper.startswith('INSERT'):
            query_type = 'INSERT'
        elif query_upper.startswith('UPDATE'):
            query_type = 'UPDATE'
        elif query_upper.startswith('DELETE'):
            query_type = 'DELETE'
        else:
            query_type = 'OTHER'
        
        cursor = conn.cursor()
        
        # Execute query with optional parameters
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        # Handle different query types
        if query_type == 'SELECT':
            results = cursor.fetchall()
            data = [dict(row) for row in results]
            conn.close()
            return {
                'success': True,
                'data': data,
                'rows_affected': len(data),
                'query_type': query_type,
                'error': None
            }
        else:
            # For INSERT, UPDATE, DELETE
            conn.commit()
            conn.close()
            return {
                'success': True,
                'data': [],
                'rows_affected': cursor.rowcount,
                'query_type': query_type,
                'error': None
            }
    
    except Exception as e:
        error_msg = f"Database query error: {str(e)}"
        print(f"❌ {error_msg}")
        conn.close()
        return {
            'success': False,
            'error': error_msg,
            'data': [],
            'rows_affected': 0,
            'query_type': 'UNKNOWN'
        }


def db_run_query_tool(conn, query, params=None):
    """
    Runs a SQL query on a given SQLite connection and returns results.
    
    Args:
        conn: sqlite3 connection object.
        query: SQL query string.
        params: Optional tuple/list of parameters for parameterized queries.
    
    Returns:
        - List of result rows (as tuples)
        - None for queries that don't return results (INSERT/UPDATE/DELETE)
    """
    cursor = conn.cursor()

    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        # If it's a SELECT query → return results
        if query.strip().lower().startswith("select"):
            return cursor.fetchall()
        
        # Otherwise commit changes
        conn.commit()
        return None

    except Exception as e:
        print("Error executing query:", e)
        return None


# Create kitchen agent with agno
kitchen_agent = Agent(
        name="Kitchen Agent",
        model=gemini_model,
        instructions=kitchen_instructions,
        # capabilities=kitchen_caps,
        tools={
            "execute_database_query": execute_database_query,
            "get_kitchen_knowledge": get_kitchen_knowledge,
            "get_database_schema": get_database_schema,
            "get_schema_documentation": get_schema_documentation,
            "get_table_relationships": get_table_relationships,
            "get_schema_summary": get_schema_summary
        },
        # memory=agent_memory
    )

