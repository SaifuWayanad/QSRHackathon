from agno.agent import Agent
from agno.models.google import Gemini
import os
import sys
import json
import pymysql
from datetime import datetime
from urllib.parse import quote_plus
try:
    from agno.models.anthropic import Claude
except ImportError:
    Claude = None
# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from Agents.instructions import kitchen_instructions
from Agents.capabilities import kitchen_caps
from Agents.db_schema import DatabaseSchema
# Optional imports for vector storage
try:
    from agno.vectordb.pgvector import PgVector
except ImportError:
    PgVector = None
try:
    from agno.knowledge import Knowledge
    from agno.knowledge.embedder.openai import OpenAIEmbedder
except ImportError:
    Knowledge = None
    OpenAIEmbedder = None
try:
    from agno.db.mysql import MySQLDb
except ImportError:
    MySQLDb = None
from constants import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE

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


def get_kitchen_knowledge():
    """Retrieve kitchen knowledge from database"""
    conn = get_main_db_connection()
    if not conn:
        return {}
    
    knowledge = {}
    try:
        # Get all kitchens
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, description, status FROM kitchens")
        knowledge['kitchens'] = [dict(row) for row in cursor.fetchall()]
        
        # Get all food items with kitchen assignments
        cursor.execute("""
            SELECT id, name, category_name, kitchen_id, kitchen_name, price, description 
            FROM food_items ORDER BY kitchen_name, category_name
        """)
        knowledge['food_items'] = [dict(row) for row in cursor.fetchall()]
        
        # Get kitchen appliances
        cursor.execute("""
            SELECT ka.id, ka.kitchen_id, a.name as appliance_name, a.type, 
                   ka.quantity, ka.location, ka.status
            FROM kitchen_appliances ka
            JOIN appliances a ON ka.appliance_id = a.id
            ORDER BY ka.kitchen_id
        """)
        knowledge['kitchen_appliances'] = [dict(row) for row in cursor.fetchall()]
        
        # Get current orders
        cursor.execute("""
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
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = %s
            ORDER BY table_name
        """, (MYSQL_DATABASE,))
        tables = [row['table_name'] if isinstance(row, dict) else row[0] for row in cursor.fetchall()]
        
        # Get schema for each table
        for table_name in tables:
            cursor.execute("""
                SELECT column_name, data_type, is_nullable, column_default, column_key
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
            """, (MYSQL_DATABASE, table_name))
            columns = []
            for row in cursor.fetchall():
                if isinstance(row, dict):
                    columns.append({
                        'name': row['column_name'],
                        'type': row['data_type'],
                        'not_null': row['is_nullable'] == 'NO',
                        'default': row['column_default'],
                        'pk': row['column_key'] == 'PRI'
                    })
                else:
                    columns.append({
                        'name': row[0],
                        'type': row[1],
                        'not_null': row[2] == 'NO',
                        'default': row[3],
                        'pk': row[4] == 'PRI'
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
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            result = cursor.fetchone()
            count = result[0] if isinstance(result, tuple) else result['COUNT(*)']
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
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = %s
            ORDER BY table_name
        """, (MYSQL_DATABASE,))
        tables = [row['table_name'] if isinstance(row, dict) else row[0] for row in cursor.fetchall()]
        
        for table_name in tables:
            cursor.execute("""
                SELECT 
                    constraint_name,
                    column_name,
                    referenced_table_name,
                    referenced_column_name
                FROM information_schema.key_column_usage
                WHERE table_schema = %s 
                    AND table_name = %s
                    AND referenced_table_name IS NOT NULL
            """, (MYSQL_DATABASE, table_name))
            fks = cursor.fetchall()
            
            if fks:
                relationships += f"📍 {table_name.upper()}\n"
                for fk in fks:
                    if isinstance(fk, dict):
                        relationships += f"   └─ {fk['column_name']} → {fk['referenced_table_name']}.{fk['referenced_column_name']}\n"
                    else:
                        relationships += f"   └─ {fk[1]} → {fk[2]}.{fk[3]}\n"
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


def execute_database_query(query: str, params: list = None) -> dict:
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
    print(f"🔧 execute_database_query CALLED!")
    print(f"   Query: {query[:100]}...")
    print(f"   Params: {params}")
    
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
# PgVector already imported at top with try/except

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', "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")

# Global knowledge variable
knowledge = None

def get_knowledge():
    """Get or create the knowledge base using MySQL/MariaDB""" 
    global knowledge
    
    if knowledge is None and OPENAI_API_KEY:
        try:
            # Use MySQL as knowledge storage with URL-encoded password
            encoded_password = quote_plus(MYSQL_PASSWORD)
            mysql_url = f"mysql+pymysql://{MYSQL_USER}:{encoded_password}@{MYSQL_HOST}/{MYSQL_DATABASE}"
            
            # Note: Using MySQL for both content and vector storage
            # MySQL 8.0+ and MariaDB 10.7+ support vector operations with plugins
            from agno.db.mysql.mysql import MySQLDb
            
            db = MySQLDb(
                db_url=mysql_url,
                knowledge_table="knowledge_contents",
            )
            
            knowledge = Knowledge(
                name="ERP Data Analysis Knowledge Base",
                description="Knowledge base for analyzing ERP data, business insights, and reporting",
                contents_db=db,
                # Using MySQL for vector storage as well
                vector_db=PgVector(
                    table_name="vectors",
                    db_url=mysql_url,
                    embedder=OpenAIEmbedder(api_key=OPENAI_API_KEY),
                ),
            )
            print("✓ Knowledge base initialized with MySQL storage")
        except Exception as e:
            print(f"⚠️  Could not initialize knowledge base with vector storage: {e}")
            # Try without vector DB
            try:
                knowledge = Knowledge(
                    name="ERP Data Analysis Knowledge Base",
                    description="Knowledge base for analyzing ERP data, business insights, and reporting",
                )
                print("✓ Knowledge base initialized without vector storage")
            except Exception as e2:
                print(f"⚠️  Could not initialize basic knowledge base: {e2}")
                knowledge = None
    
    return knowledge

# Initialize kitchen agent with error handling
kitchen_agent = None
try:
    # Get knowledge base (will handle failures gracefully)
    kb = get_knowledge()
    
    if Claude is None:
        print("⚠️  Kitchen Agent initialization skipped: Claude not available")
        kitchen_agent = None
    elif ANTHROPIC_API_KEY is None:
        print("⚠️  Kitchen Agent initialization skipped: ANTHROPIC_API_KEY not set")
        kitchen_agent = None
    else:
        kitchen_agent = Agent(
                name="Kitchen Agent",
               model = Claude(
                        id="claude-sonnet-4-20250514",
                        api_key=ANTHROPIC_API_KEY
                    ),
                instructions=kitchen_instructions,
                knowledge=kb,  # Use the knowledge base if available (can be None)
                tools=[execute_database_query, get_kitchen_knowledge, get_database_schema, get_schema_documentation, get_table_relationships, get_schema_summary],  # Use list of functions
                markdown=False,  # Don't wrap responses in markdown
            )
        print("✓ Kitchen Agent initialized successfully")
except Exception as e:
    print(f"⚠️  Kitchen Agent initialization failed: {str(e)}")
    kitchen_agent = None

