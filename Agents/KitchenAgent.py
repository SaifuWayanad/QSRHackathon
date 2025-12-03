from agno.agent import Agent
from agno.models.google import Gemini
import os
import sys
import json
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stream_db import StreamDB
from order_monitor import OrderMonitor
from instructions import kitchen_instructions
from capabilities import kitchen_caps

gemini_model = Gemini("gemini-2.5-flash", api_key="AIzaSyD6v6dOt-hxwzcZWhwrizKfgM_oiwJjXTw")
os.environ["GOOGLE_API_KEY"] = "AIzaSyD6v6dOt-hxwzcZWhwrizKfgM_oiwJjXTw"


# Initialize Stream Database and Monitor
stream_db = StreamDB("stream_orders.db")
order_monitor = OrderMonitor(stream_db, check_interval=2)


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


def assign_order_to_kitchens(order_data: dict):
    """
    Process new order and assign items to appropriate kitchens
    Called by order monitor when new order arrives
    """
    print(f"\n📋 NEW ORDER RECEIVED: {order_data.get('order_number')}")
    print(f"   Customer: {order_data.get('customer_name')}")
    print(f"   Items: {order_data.get('items_count')}")
    
    # Get items organized by kitchen
    kitchen_items = order_monitor.get_items_by_kitchen(order_data)
    
    print(f"\n🏪 KITCHEN ASSIGNMENTS:")
    
    # Assign to each kitchen
    for kitchen_name, items in kitchen_items.items():
        assignment_id = stream_db.assign_to_kitchen(
            order_id=order_data.get('id'),
            kitchen_id=kitchen_name,
            kitchen_name=kitchen_name.replace('_', ' ').title(),
            items=items
        )
        
        print(f"   ✓ {kitchen_name.upper()}: {len(items)} item(s) assigned")
        for item in items:
            print(f"      - {item.get('food_name')} (qty: {item.get('quantity')})")
    
    # Provide order summary to agent
    order_summary = order_monitor.get_order_summary(order_data)
    
    # Agent processes the order
    agent_response = kitchen_agent.run(
        f"""
        New restaurant order received:
        
        Order #: {order_data.get('order_number')}
        Customer: {order_data.get('customer_name')}
        Total Items: {order_data.get('items_count')}
        Total Amount: ${order_data.get('total_amount')}
        Special Notes: {order_data.get('notes', 'None')}
        
        Items breakdown:
        {json.dumps(order_summary['categories'], indent=2)}
        
        Please:
        1. Acknowledge receipt of this order
        2. Provide preparation time estimate for each kitchen
        3. Identify any potential delays or issues
        4. Suggest optimizations if needed
        """
    )
    
    print(f"\n🤖 KITCHEN AGENT RESPONSE:")
    print(agent_response)
    
    return assignment_id


def monitor_stream_orders():
    """Start monitoring stream database for new orders"""
    # Register callback
    order_monitor.on_new_order(assign_order_to_kitchens)
    
    # Start monitoring
    order_monitor.start()
    
    print("✓ Kitchen Agent initialized and listening for orders...")
    
    # Keep running
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n✓ Shutting down Kitchen Agent...")
        order_monitor.stop()


# Create kitchen agent with streaming capabilities
kitchen_agent = Agent(
    model=gemini_model,
    capabilities=kitchen_caps,
    name="Kitchen Management Agent",
    instructions=kitchen_instructions
)


# For testing/manual order placement
def place_order_to_stream(order_data: dict):
    """Manually place an order to stream database for testing"""
    stream_db.add_order(order_data)
    print(f"✓ Order {order_data.get('order_number')} placed to stream")


if __name__ == '__main__':
    print("🍳 Kitchen Management Agent Starting...")
    monitor_stream_orders()
