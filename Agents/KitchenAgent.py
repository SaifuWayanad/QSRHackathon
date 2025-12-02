from agno.agent import Agent
from agno.models.google import Gemini
import os

from instructions import kitchen_instructions
from capabilities import kitchen_caps

gemini_model = Gemini("gemini-2.5-flash", api_key="AIzaSyD6v6dOt-hxwzcZWhwrizKfgM_oiwJjXTw")

os.environ["GOOGLE_API_KEY"] = "AIzaSyD6v6dOt-hxwzcZWhwrizKfgM_oiwJjXTw"


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


kitchen_agent = Agent(model=gemini_model,
                      capabilities=kitchen_caps,
                       name="Kitchen Manage Agent",
                         instructions=kitchen_instructions)
