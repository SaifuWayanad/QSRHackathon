from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import pymysql
import pymysql.cursors
import json
import uuid
from datetime import datetime
import os
from constants import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE

# Import stream database integration
try:
    from stream_integration import push_order_to_stream
except ImportError:
    print("⚠️  Stream integration not available (optional)")
    push_order_to_stream = None

# Import Kitchen Agent
try:
    from Agents.KitchenAgent import kitchen_agent
except ImportError:
    print("⚠️  Kitchen Agent not available (optional)")
    kitchen_agent = None

# Import Inventory Agent
try:
    from Agents.InventoryAgent import kitchen_agent as inventory_agent
except ImportError:
    print("⚠️  Inventory Agent not available (optional)")
    inventory_agent = None

# Import Order Monitor
try:
    from Agents.order_monitor import start_order_monitor, stop_order_monitor, get_today_orders_count, get_today_summary
except ImportError:
    print("⚠️  Order Monitor not available (optional)")
    start_order_monitor = None
    stop_order_monitor = None
    get_today_orders_count = None
    get_today_summary = None

# Import Customer Agent
try:
    from Agents.CustomerAgent import customer_agent, chat_with_customer
except ImportError:
    print("⚠️  Customer Agent not available (optional)")
    customer_agent = None
    chat_with_customer = None

# Import Session Manager
try:
    from session_manager import (
        create_session, get_session, save_message, 
        get_conversation_history, update_session_customer
    )
except ImportError:
    print("⚠️  Session Manager not available (optional)")
    create_session = None
    get_session = None
    save_message = None
    get_conversation_history = None
    update_session_customer = None

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'

# Wrapper class to make PyMySQL behave like SQLAlchemy
class ConnectionWrapper:
    def __init__(self, conn):
        self._conn = conn
        self._cursor = None
    
    def execute(self, query, params=None):
        """Execute a query and return a cursor-like object"""
        cursor = self._conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor
    
    def cursor(self):
        """Get a cursor from the connection"""
        return self._conn.cursor()
    
    def commit(self):
        """Commit the transaction"""
        self._conn.commit()
    
    def rollback(self):
        """Rollback the transaction"""
        self._conn.rollback()
    
    def close(self):
        """Close the connection"""
        self._conn.close()

# MySQL database setup
def get_db_connection():
    """Get database connection"""
    conn = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
        ssl={'ssl': False}
    )
    return ConnectionWrapper(conn)

def init_db():
    """Initialize database with all tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS areas (
            id VARCHAR(255) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            status VARCHAR(255) DEFAULT 'active',
            tables_count INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id VARCHAR(255) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            status VARCHAR(255) DEFAULT 'active',
            items_count INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS kitchens (
            id VARCHAR(255) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            location VARCHAR(255),
            description TEXT,
            status VARCHAR(255) DEFAULT 'active',
            items_count INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS food_items (
            id VARCHAR(255) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            category_id VARCHAR(255) NOT NULL,
            category_name VARCHAR(255),
            kitchen_id VARCHAR(255) NOT NULL,
            kitchen_name VARCHAR(255),
            price DECIMAL(10, 2),
            description TEXT,
            specifications TEXT,
            status VARCHAR(255) DEFAULT 'available',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id),
            FOREIGN KEY (kitchen_id) REFERENCES kitchens(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tables (
            id VARCHAR(255) PRIMARY KEY,
            number INT NOT NULL,
            area_id VARCHAR(255) NOT NULL,
            area_name VARCHAR(255),
            capacity INT,
            status VARCHAR(255) DEFAULT 'available',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (area_id) REFERENCES areas(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_types (
            id VARCHAR(255) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            status VARCHAR(255) DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id VARCHAR(255) PRIMARY KEY,
            order_number VARCHAR(255) UNIQUE,
            table_id VARCHAR(255),
            table_number VARCHAR(255),
            order_type_id VARCHAR(255),
            order_type_name VARCHAR(255),
            customer_name VARCHAR(255),
            items_count INT DEFAULT 0,
            total_amount DECIMAL(10, 2) DEFAULT 0,
            status VARCHAR(255) DEFAULT 'pending',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (table_id) REFERENCES tables(id),
            FOREIGN KEY (order_type_id) REFERENCES order_types(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id VARCHAR(255) PRIMARY KEY,
            order_id VARCHAR(255) NOT NULL,
            food_item_id VARCHAR(255) NOT NULL,
            food_name VARCHAR(255),
            category_name VARCHAR(255),
            quantity INT NOT NULL,
            price DECIMAL(10, 2) NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (food_item_id) REFERENCES food_items(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_production (
            id VARCHAR(255) PRIMARY KEY,
            food_id VARCHAR(255) NOT NULL,
            food_name VARCHAR(255),
            category_name VARCHAR(255),
            date DATE NOT NULL,
            planned_quantity INT,
            produced INT DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (food_id) REFERENCES food_items(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS appliances (
            id VARCHAR(255) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            type VARCHAR(255) NOT NULL,
            model VARCHAR(255),
            serial_number VARCHAR(255),
            description TEXT,
            status VARCHAR(255) DEFAULT 'active',
            purchase_date DATE,
            last_maintenance DATE,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS kitchen_appliances (
            id VARCHAR(255) PRIMARY KEY,
            kitchen_id VARCHAR(255) NOT NULL,
            appliance_id VARCHAR(255) NOT NULL,
            quantity INT DEFAULT 1,
            location VARCHAR(255),
            status VARCHAR(255) DEFAULT 'active',
            assigned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (kitchen_id) REFERENCES kitchens(id),
            FOREIGN KEY (appliance_id) REFERENCES appliances(id),
            UNIQUE(kitchen_id, appliance_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS iot_devices (
            id VARCHAR(255) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            device_type VARCHAR(255) NOT NULL,
            device_id VARCHAR(255) UNIQUE,
            location VARCHAR(255),
            kitchen_id VARCHAR(255),
            description TEXT,
            status VARCHAR(255) DEFAULT 'active',
            battery_level INT,
            signal_strength INT,
            last_sync TIMESTAMP NULL,
            ip_address VARCHAR(50),
            mac_address VARCHAR(50),
            firmware_version VARCHAR(100),
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (kitchen_id) REFERENCES kitchens(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS staff (
            id VARCHAR(255) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) UNIQUE,
            phone VARCHAR(50),
            position VARCHAR(255) NOT NULL,
            department VARCHAR(100),
            kitchen_id VARCHAR(255),
            hire_date DATE,
            date_of_birth DATE,
            address TEXT,
            city VARCHAR(100),
            state VARCHAR(100),
            postal_code VARCHAR(20),
            emergency_contact_name TEXT,
            emergency_contact_phone TEXT,
            status VARCHAR(255) DEFAULT 'active',
            salary_type VARCHAR(50),
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (kitchen_id) REFERENCES kitchens(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS staff_kitchen_requests (
            id VARCHAR(255) PRIMARY KEY,
            staff_id VARCHAR(255) NOT NULL,
            staff_name VARCHAR(255),
            kitchen_id VARCHAR(255) NOT NULL,
            kitchen_name VARCHAR(255),
            position VARCHAR(100),
            request_reason TEXT,
            requested_start_date DATE,
            status VARCHAR(255) DEFAULT 'pending',
            approval_status VARCHAR(255) DEFAULT 'pending',
            approved_by VARCHAR(255),
            approval_notes TEXT,
            approval_date TIMESTAMP NULL,
            rejection_reason TEXT,
            requested_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (staff_id) REFERENCES staff(id),
            FOREIGN KEY (kitchen_id) REFERENCES kitchens(id),
            UNIQUE(staff_id, kitchen_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS staff_kitchen_assignments (
            id VARCHAR(255) PRIMARY KEY,
            staff_id VARCHAR(255) NOT NULL,
            staff_name VARCHAR(255),
            kitchen_id VARCHAR(255) NOT NULL,
            kitchen_name VARCHAR(255),
            position VARCHAR(100),
            request_id VARCHAR(255),
            assigned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_date DATE,
            status VARCHAR(255) DEFAULT 'active',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (staff_id) REFERENCES staff(id),
            FOREIGN KEY (kitchen_id) REFERENCES kitchens(id),
            FOREIGN KEY (request_id) REFERENCES staff_kitchen_requests(id),
            UNIQUE(staff_id, kitchen_id)
        )
    ''')
    
    # Note: food_kitchen_mapping table created manually in MariaDB
    
    conn.commit()
    conn.close()
    print("✓ Database initialized successfully")

# ========================================================================
# KITCHEN AGENT HELPER FUNCTIONS
# ========================================================================

def ask_kitchen_agent(query: str, context: dict = None) -> dict:
    """
    Ask the kitchen agent a question or request regarding order management.
    
    Args:
        query (str): The question or request to ask the kitchen agent
        context (dict): Optional context data (order info, kitchen stats, etc.)
    
    Returns:
        dict: Response from the agent with status and message
    
    Example:
        ask_kitchen_agent("What's the current status of order ABC123?")
        ask_kitchen_agent("How many items are waiting in the main kitchen?")
        ask_kitchen_agent("Should we start preparing the next order?")
    """
    if not kitchen_agent:
        return {
            'success': False,
            'error': 'Kitchen Agent is not available',
            'message': 'The kitchen agent service is not configured'
        }
    
    try:
        # Build the prompt with context if provided
        prompt = query
        
        if context:
            prompt += "\n\nContext Information:"
            if 'order' in context:
                order = context['order']
                prompt += f"\n- Order ID: {order.get('id', 'N/A')}"
                prompt += f"\n- Table: {order.get('table_name', 'N/A')}"
                prompt += f"\n- Status: {order.get('status', 'N/A')}"
                prompt += f"\n- Items: {order.get('items_count', 0)}"
            
            if 'kitchen_stats' in context:
                stats = context['kitchen_stats']
                prompt += f"\n- Total Items in Kitchens: {stats.get('total_items', 0)}"
                prompt += f"\n- Pending Items: {stats.get('pending_items', 0)}"
                prompt += f"\n- Ready Items: {stats.get('ready_items', 0)}"
            
            if 'notes' in context:
                prompt += f"\n- Additional Notes: {context['notes']}"
        
        # Run the agent
        response = kitchen_agent.run(prompt)
        
        return {
            'success': True,
            'message': str(response),
            'query': query,
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as e:
        print(f"Error asking kitchen agent: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to process kitchen agent request',
            'query': query
        }

def ask_inventory_agent(query: str, context: dict = None) -> dict:
    """
    Ask the inventory agent a question about sustainability metrics, stock levels, waste analysis, etc.
    
    Args:
        query (str): The question or request to ask the inventory agent
        context (dict): Optional context data (date, kitchen_id, metrics type, etc.)
    
    Returns:
        dict: Response from the agent with sustainability insights and recommendations
    
    Example:
        ask_inventory_agent("What's the sustainability report for yesterday?")
        ask_inventory_agent("Show me real-time store-level metrics", {"kitchen_id": "KITCHEN_001"})
        ask_inventory_agent("Which menu items have high waste today?")
    """
    if not inventory_agent:
        return {
            'success': False,
            'error': 'Inventory Agent is not available',
            'message': 'The inventory agent service is not configured'
        }
    
    try:
        # Build the prompt with context if provided
        prompt = query
        
        if context:
            prompt += "\n\nContext Information:"
            if 'date' in context:
                prompt += f"\n- Analysis Date: {context['date']}"
            if 'kitchen_id' in context:
                prompt += f"\n- Kitchen ID: {context['kitchen_id']}"
            if 'metric_type' in context:
                prompt += f"\n- Metric Type: {context['metric_type']}"
            if 'include_levers' in context and context['include_levers']:
                prompt += f"\n- Include Operational Levers: Yes (menu mix, production, staffing)"
            if 'time_period' in context:
                prompt += f"\n- Time Period: {context['time_period']}"
            if 'notes' in context:
                prompt += f"\n- Additional Notes: {context['notes']}"
        
        # Run the agent
        response = inventory_agent.run(prompt)
        
        return {
            'success': True,
            'message': str(response),
            'query': query,
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as e:
        print(f"Error asking inventory agent: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to process inventory agent request',
            'query': query
        }

# Manager credentials
MANAGER_USERNAME = 'manager'
MANAGER_PASSWORD = '123'

@app.route('/')
def home():
    if 'logged_in' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == MANAGER_USERNAME and password == MANAGER_PASSWORD:
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Invalid username or password')
    
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', username=session.get('username'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/customer-chat')
def customer_chat():
    """Customer chat interface"""
    return render_template('customer_chat.html')


message = ""
@app.route('/api/customer-chat', methods=['POST'])
def api_customer_chat():
    """API endpoint for customer chat with streaming support"""
    try:
        data = request.get_json()
        single_message = data.get('message', '').strip()
        print("message. : ", message)
        session_id = data.get('session_id', str(uuid.uuid4()))
        message = message + "\nCustomer: " + single_message
        if not message:
            return jsonify({
                'success': False,
                'error': 'Message is required'
            }), 400
        
        # Check if customer agent is available
        if not chat_with_customer:
            return jsonify({
                'success': False,
                'error': 'Customer agent is not available'
            }), 503
        
        # Get response from customer agent
        response = chat_with_customer(message, session_id)
        message = message + "\nAgent: " + response
        
        return jsonify({
            'success': True,
            'response': response,
            'session_id': session_id,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"❌ Error in customer chat: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

import re

def remove_tool_calls(response_text: str) -> str:
    """
    Removes execute_database_query(...) logs from the chatbot response.
    Works with variations, including params and time logs.
    """
    # Remove full tool call lines like:
    # execute_database_query(query=...) completed in 0.123s
    pattern = r"execute_database_query\(.*?\)(?: completed in .*?s)?"
    
    cleaned = re.sub(pattern, "", response_text, flags=re.DOTALL)

    # Remove extra blank spaces caused by deletion
    cleaned = re.sub(r"\n\s*\n", "\n", cleaned).strip()

    return cleaned


@app.route('/api/customer-chat-stream', methods=['POST'])
def api_customer_chat_stream():
    """Streaming endpoint for customer chat with session management"""
    from flask import Response, stream_with_context
    
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        print("Streaming message: ", message)
        session_id = data.get('session_id')
        
        if not message:
            return jsonify({
                'success': False,
                'error': 'Message is required'
            }), 400
        
        # Check if customer agent is available
        if not customer_agent:
            return jsonify({
                'success': False,
                'error': 'Customer agent is not available'
            }), 503
        
        # Check if session manager is available
        if not create_session or not save_message:
            return jsonify({
                'success': False,
                'error': 'Session manager is not available'
            }), 503
        
        # Create or get session
        if not session_id:
            session_data = create_session()
            if session_data:
                session_id = session_data['id']
            else:
                session_id = str(uuid.uuid4())
        else:
            # Verify session exists
            session_data = get_session(session_id)
            if not session_data:
                # Create new session with provided ID
                session_data = create_session()
                if session_data:
                    session_id = session_data['id']
        
        # Save customer message
        save_message(session_id, 'customer', message)
        
        def generate():
            """Generate streaming response"""
            try:
                # Import necessary modules
                from Agents.customer_instructions import customer_instructions
                from Agents.CustomerAgent import get_customer_knowledge
                
                # Get conversation history
                history = get_conversation_history(session_id, format='text')
                
                # Get customer knowledge context
                knowledge = get_customer_knowledge()
                
                # Create enhanced message with context and history
                context_message = f"""
                    {history}

                    Current Customer Message: {message}

                    Available Context:
                    - {len(knowledge.get('available_items', []))} food items available
                    - {len(knowledge.get('categories', []))} categories active
                    - {len(knowledge.get('order_types', []))} order types available

                    Database Schema Available: Use execute_database_query tool to access data.

                    Remember: Continue the conversation naturally based on the history above.
                    """
                
                # Stream the response
                response = customer_agent.run(context_message, stream=True)
                
                full_response = ""
                
                # Yield chunks as they come
                response = customer_agent.run(context_message, stream=True)

                full_response = ""

                for chunk in response:
                    if hasattr(chunk, "content") and chunk.content:

                        raw = chunk.content

                        # Filter out tool calls or execution traces
                        if (
                            "execute_database_query(" in raw
                            or "completed in" in raw
                            or '"tool_calls"' in raw
                            or "AgentAction" in raw
                        ):
                            continue  # skip this part completely

                        # Append only clean assistant text
                        full_response += raw

                        yield f"data: {json.dumps({'chunk': raw, 'done': False})}\n\n"

                # for chunk in response:
                #     if hasattr(chunk, 'content') and chunk.content:
                        
                #         full_response += chunk.content
                #         yield f"data: {json.dumps({'chunk': chunk.content, 'done': False})}\n\n"
                
                # Save agent response
                if full_response:
                    save_message(session_id, 'agent', full_response)
                
                # Send completion message
                yield f"data: {json.dumps({'chunk': '', 'done': True, 'session_id': session_id})}\n\n"
                
            except Exception as e:
                error_msg = f"Error in streaming: {str(e)}"
                print(f"❌ {error_msg}")
                import traceback
                traceback.print_exc()
                yield f"data: {json.dumps({'error': error_msg, 'done': True})}\n\n"
        
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
                'Connection': 'keep-alive'
            }
        )
        
    except Exception as e:
        print(f"❌ Error in customer chat stream: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/hello', methods=['GET', 'POST'])
def hello():
    if request.method == 'POST':
        data = request.get_json()
        name = data.get('name', 'World')
        return jsonify({'greeting': f'Hello, {name}!'})
    return jsonify({'greeting': 'Hello, World!'})

@app.route('/about')
def about():
    return jsonify({
        'app': 'Flask Demo',
        'version': '1.0.0',
        'description': 'A simple Flask application'
    })


# Menu Categories API
@app.route('/api/categories', methods=['GET', 'POST'])
def categories():
    conn = get_db_connection()
    
    if request.method == 'POST':
        data = request.get_json()
        category_id = str(uuid.uuid4())
        
        conn.execute(
            'INSERT INTO categories (id, name, description, status) VALUES (%s, %s, %s, %s)',
            (category_id, data.get('name'), data.get('description', ''), data.get('status', 'active'))
        )
        conn.commit()
        
        category = {
            'id': category_id,
            'name': data.get('name'),
            'description': data.get('description', ''),
            'status': data.get('status', 'active'),
            'items_count': 0
        }
        conn.close()
        return jsonify({'success': True, 'category': category})
    
    # GET all categories
    cursor = conn.execute('SELECT * FROM categories')
    categories_list = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({'categories': categories_list})

@app.route('/api/categories/<category_id>', methods=['DELETE'])
def delete_category(category_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM categories WHERE id = %s', (category_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


# Kitchen API
@app.route('/api/kitchens', methods=['GET', 'POST'])
def kitchens():
    conn = get_db_connection()
    
    if request.method == 'POST':
        data = request.get_json()
        kitchen_id = str(uuid.uuid4())
        
        conn.execute(
            'INSERT INTO kitchens (id, name, location, description, status) VALUES (%s, %s, %s, %s, %s)',
            (kitchen_id, data.get('name'), data.get('location', ''), data.get('description', ''), data.get('status', 'active'))
        )
        conn.commit()
        
        kitchen = {
            'id': kitchen_id,
            'name': data.get('name'),
            'location': data.get('location', ''),
            'description': data.get('description', ''),
            'status': data.get('status', 'active'),
            'items_count': 0
        }
        conn.close()
        return jsonify({'success': True, 'kitchen': kitchen})
    
    # GET all kitchens
    cursor = conn.execute('SELECT * FROM kitchens')
    kitchens_list = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({'kitchens': kitchens_list})

@app.route('/api/kitchens/<kitchen_id>', methods=['DELETE'])
def delete_kitchen(kitchen_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM kitchens WHERE id = %s', (kitchen_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


# Food Items API
@app.route('/api/food-items', methods=['GET', 'POST'])
def food_items():
    conn = get_db_connection()
    
    if request.method == 'POST':
        data = request.get_json()
        food_id = str(uuid.uuid4())
        category_id = data.get('category_id')
        kitchen_ids = data.get('kitchen_ids', [])
        
        if not kitchen_ids or len(kitchen_ids) == 0:
            conn.close()
            return jsonify({'error': 'At least one kitchen assignment is required!', 'success': False}), 400
        
        # Get category name
        cat_row = conn.execute('SELECT name FROM categories WHERE id = %s', (category_id,)).fetchone()
        category_name = cat_row['name'] if cat_row else 'Unknown'
        
        # For backward compatibility, store primary kitchen in food_items
        primary_kitchen_id = kitchen_ids[0]
        kitchen_row = conn.execute('SELECT name FROM kitchens WHERE id = %s', (primary_kitchen_id,)).fetchone()
        if not kitchen_row:
            conn.close()
            return jsonify({'error': 'Kitchen not found!', 'success': False}), 404
        
        kitchen_name = kitchen_row['name']
        
        # Create food item
        conn.execute(
            '''INSERT INTO food_items (id, name, category_id, category_name, kitchen_id, kitchen_name, 
               price, description, specifications, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
            (food_id, data.get('name'), category_id, category_name, primary_kitchen_id, kitchen_name,
             data.get('price'), data.get('description', ''), data.get('specifications', ''),
             data.get('status', 'available'))
        )
        
        # Insert mappings for all selected kitchens
        for kitchen_id in kitchen_ids:
            mapping_id = str(uuid.uuid4())
            conn.execute(
                '''INSERT INTO food_kitchen_mapping (id, food_id, kitchen_id)
                   VALUES (%s, %s, %s)''',
                (mapping_id, food_id, kitchen_id)
            )
            # Update kitchen items_count
            conn.execute('UPDATE kitchens SET items_count = items_count + 1 WHERE id = %s', (kitchen_id,))
        
        # Update category items_count
        conn.execute('UPDATE categories SET items_count = items_count + 1 WHERE id = %s', (category_id,))
        
        conn.commit()
        conn.close()
        
        food_item = {
            'id': food_id,
            'name': data.get('name'),
            'category_id': category_id,
            'category_name': category_name,
            'kitchen_id': primary_kitchen_id,
            'kitchen_name': kitchen_name,
            'kitchen_ids': kitchen_ids,
            'price': data.get('price'),
            'description': data.get('description', ''),
            'specifications': data.get('specifications', ''),
            'status': data.get('status', 'available')
        }
        return jsonify({'success': True, 'food_item': food_item})
    
    # GET all food items with their kitchen mappings
    cursor = conn.execute('SELECT * FROM food_items')
    food_items_list = []
    
    for row in cursor.fetchall():
        item = dict(row)
        # Get all kitchens for this food item
        kitchen_cursor = conn.execute('''
            SELECT k.id, k.name, k.icon 
            FROM kitchens k
            INNER JOIN food_kitchen_mapping fkm ON k.id = fkm.kitchen_id
            WHERE fkm.food_id = %s
        ''', (item['id'],))
        
        item['kitchens'] = [dict(k) for k in kitchen_cursor.fetchall()]
        food_items_list.append(item)
    
    conn.close()
    return jsonify({'food_items': food_items_list})

@app.route('/api/food-items/<food_id>', methods=['DELETE'])
def delete_food_item(food_id):
    conn = get_db_connection()
    
    # Get food item details and all associated kitchens
    food_row = conn.execute('SELECT * FROM food_items WHERE id = %s', (food_id,)).fetchone()
    
    if food_row:
        category_id = food_row['category_id']
        
        # Get all kitchens associated with this food item
        kitchen_mappings = conn.execute(
            'SELECT kitchen_id FROM food_kitchen_mapping WHERE food_id = %s',
            (food_id,)
        ).fetchall()
        
        # Update category count
        conn.execute('UPDATE categories SET items_count = MAX(0, items_count - 1) WHERE id = %s', (category_id,))
        
        # Update each kitchen's count
        for mapping in kitchen_mappings:
            conn.execute('UPDATE kitchens SET items_count = MAX(0, items_count - 1) WHERE id = %s', (mapping['kitchen_id'],))
        
        # Delete mappings (will cascade if ON DELETE CASCADE is set)
        conn.execute('DELETE FROM food_kitchen_mapping WHERE food_id = %s', (food_id,))
    
    # Delete the food item
    conn.execute('DELETE FROM food_items WHERE id = %s', (food_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


# Daily Production API
@app.route('/api/daily-production', methods=['GET', 'POST'])
def daily_production():
    conn = get_db_connection()
    
    if request.method == 'POST':
        data = request.get_json()
        production_id = str(uuid.uuid4())
        date = data.get('date')
        
        conn.execute(
            '''INSERT INTO daily_production (id, food_id, food_name, category_name, date, planned_quantity, produced, notes)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''',
            (production_id, data.get('food_id'), data.get('food_name'), data.get('category_name'),
             date, data.get('planned_quantity'), data.get('produced', 0), data.get('notes', ''))
        )
        conn.commit()
        
        production_item = {
            'id': production_id,
            'food_id': data.get('food_id'),
            'food_name': data.get('food_name'),
            'category_name': data.get('category_name'),
            'date': date,
            'planned_quantity': data.get('planned_quantity'),
            'produced': data.get('produced', 0),
            'notes': data.get('notes', '')
        }
        conn.close()
        return jsonify({'success': True, 'production_item': production_item})
    
    # GET production items for a specific date
    date = request.args.get('date')
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')
    
    cursor = conn.execute('SELECT * FROM daily_production WHERE date = %s', (date,))
    production_items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({'production_items': production_items, 'date': date})

@app.route('/api/daily-production/<production_id>', methods=['PUT', 'DELETE'])
def update_delete_production(production_id):
    conn = get_db_connection()
    
    if request.method == 'PUT':
        data = request.get_json()
        prod_row = conn.execute('SELECT * FROM daily_production WHERE id = %s', (production_id,)).fetchone()
        
        if prod_row:
            conn.execute(
                'UPDATE daily_production SET produced = %s WHERE id = %s',
                (data.get('produced', prod_row['produced']), production_id)
            )
            conn.commit()
            
            updated = conn.execute('SELECT * FROM daily_production WHERE id = %s', (production_id,)).fetchone()
            conn.close()
            return jsonify({'success': True, 'production_item': dict(updated)})
        
        conn.close()
        return jsonify({'error': 'Production item not found'}), 404
    
    # DELETE
    conn.execute('DELETE FROM daily_production WHERE id = %s', (production_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


# Areas API
@app.route('/api/areas', methods=['GET', 'POST'])
def areas():
    conn = get_db_connection()
    
    if request.method == 'POST':
        data = request.get_json()
        area_id = str(uuid.uuid4())
        
        conn.execute(
            'INSERT INTO areas (id, name, description, status) VALUES (%s, %s, %s, %s)',
            (area_id, data.get('name'), data.get('description', ''), data.get('status', 'active'))
        )
        conn.commit()
        
        area = {
            'id': area_id,
            'name': data.get('name'),
            'description': data.get('description', ''),
            'status': data.get('status', 'active'),
            'tables_count': 0
        }
        conn.close()
        return jsonify({'success': True, 'area': area})
    
    # GET all areas
    cursor = conn.execute('SELECT * FROM areas')
    areas_list = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({'areas': areas_list})

@app.route('/api/areas/<area_id>', methods=['DELETE'])
def delete_area(area_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM areas WHERE id = %s', (area_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


# Tables API
@app.route('/api/tables', methods=['GET', 'POST'])
def tables():
    conn = get_db_connection()
    
    if request.method == 'POST':
        data = request.get_json()
        table_id = str(uuid.uuid4())
        area_id = data.get('area_id')
        
        # Get area name and update table count
        area_row = conn.execute('SELECT name FROM areas WHERE id = %s', (area_id,)).fetchone()
        area_name = area_row['name'] if area_row else ''
        
        conn.execute(
            'INSERT INTO tables (id, number, area_id, area_name, capacity, status) VALUES (%s, %s, %s, %s, %s, %s)',
            (table_id, data.get('number'), area_id, area_name, data.get('capacity'), data.get('status', 'available'))
        )
        
        conn.execute('UPDATE areas SET tables_count = tables_count + 1 WHERE id = %s', (area_id,))
        conn.commit()
        
        table = {
            'id': table_id,
            'number': data.get('number'),
            'area_id': area_id,
            'area_name': area_name,
            'capacity': data.get('capacity'),
            'status': data.get('status', 'available')
        }
        conn.close()
        return jsonify({'success': True, 'table': table})
    
    # GET all tables
    cursor = conn.execute('SELECT * FROM tables')
    tables_list = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({'tables': tables_list})

@app.route('/api/tables/<table_id>', methods=['DELETE'])
def delete_table(table_id):
    conn = get_db_connection()
    
    # Get table details
    table_row = conn.execute('SELECT area_id FROM tables WHERE id = %s', (table_id,)).fetchone()
    
    if table_row:
        area_id = table_row['area_id']
        conn.execute('UPDATE areas SET tables_count = MAX(0, tables_count - 1) WHERE id = %s', (area_id,))
    
    conn.execute('DELETE FROM tables WHERE id = %s', (table_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


# Order Types API
@app.route('/api/order-types', methods=['GET', 'POST'])
def order_types():
    conn = get_db_connection()
    
    if request.method == 'POST':
        data = request.get_json()
        order_type_id = str(uuid.uuid4())
        
        conn.execute(
            'INSERT INTO order_types (id, name, description, status) VALUES (%s, %s, %s, %s)',
            (order_type_id, data.get('name'), data.get('description', ''), data.get('status', 'active'))
        )
        conn.commit()
        
        order_type = {
            'id': order_type_id,
            'name': data.get('name'),
            'description': data.get('description', ''),
            'status': data.get('status', 'active')
        }
        conn.close()
        return jsonify({'success': True, 'order_type': order_type})
    
    # GET all order types
    cursor = conn.execute('SELECT * FROM order_types')
    order_types_list = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({'order_types': order_types_list})

@app.route('/api/order-types/<order_type_id>', methods=['DELETE'])
def delete_order_type(order_type_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM order_types WHERE id = %s', (order_type_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


# Orders API
@app.route('/api/orders', methods=['GET', 'POST'])
def orders():
    conn = get_db_connection()
    
    if request.method == 'POST':
        data = request.get_json()
        order_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        conn.execute(
            '''INSERT INTO orders (id, order_number, table_id, table_number, order_type_id, order_type_name,
               customer_name, items_count, total_amount, status, notes, created_at, updated_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
            (order_id, data.get('order_number'), data.get('table_id'), data.get('table_number', ''),
             data.get('order_type_id'), data.get('order_type_name', ''), data.get('customer_name', ''),
             data.get('items_count', 0), data.get('total_amount', 0), data.get('status', 'pending'),
             data.get('notes', ''), now, now)
        )
        
        # Save order items
        items = data.get('items', [])
        for item in items:
            item_id = str(uuid.uuid4())
            try:
                conn.execute(
                    '''INSERT INTO order_items (id, order_id, food_item_id, food_name, category_name, quantity, price, notes, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                    (item_id, order_id, item.get('food_item_id', ''), item.get('food_name', ''),
                     item.get('category_name', ''), item.get('quantity', 1), item.get('price', 0),
                     item.get('notes', ''), now)
                )
            except pymysql.IntegrityError as e:
                # Handle duplicate item (same food_item in same order)
                print(f"Note: Duplicate item in order - {e}")
                conn.rollback()
                continue
        
        conn.commit()
        
        order = {
            'id': order_id,
            'order_number': data.get('order_number'),
            'table_id': data.get('table_id'),
            'table_number': data.get('table_number', ''),
            'order_type_id': data.get('order_type_id'),
            'order_type_name': data.get('order_type_name', ''),
            'customer_name': data.get('customer_name', ''),
            'items_count': data.get('items_count', 0),
            'total_amount': data.get('total_amount', 0),
            'status': data.get('status', 'pending'),
            'notes': data.get('notes', ''),
            'created_at': now,
            'updated_at': now,
            'items': data.get('items', [])
        }
        
        # Push order to stream database for Kitchen Agent processing
        if push_order_to_stream:
            push_order_to_stream(order)
        
        conn.close()
        return jsonify({'success': True, 'order': order})
    
    # GET all orders
    cursor = conn.execute('SELECT * FROM orders')
    orders_list = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({'orders': orders_list})

@app.route('/api/orders/<order_id>', methods=['GET', 'PUT', 'DELETE'])
def order_detail(order_id):
    conn = get_db_connection()
    
    if request.method == 'DELETE':
        conn.execute('DELETE FROM orders WHERE id = %s', (order_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    if request.method == 'PUT':
        data = request.get_json()
        now = datetime.now().isoformat()
        
        order_row = conn.execute('SELECT * FROM orders WHERE id = %s', (order_id,)).fetchone()
        if order_row:
            conn.execute(
                '''UPDATE orders SET order_number = %s, table_id = %s, table_number = %s, 
                   order_type_id = %s, order_type_name = %s, customer_name = %s, items_count = %s, 
                   total_amount = %s, status = %s, notes = %s, updated_at = %s
                   WHERE id = %s''',
                (data.get('order_number', order_row['order_number']),
                 data.get('table_id', order_row['table_id']),
                 data.get('table_number', order_row['table_number']),
                 data.get('order_type_id', order_row['order_type_id']),
                 data.get('order_type_name', order_row['order_type_name']),
                 data.get('customer_name', order_row['customer_name']),
                 data.get('items_count', order_row['items_count']),
                 data.get('total_amount', order_row['total_amount']),
                 data.get('status', order_row['status']),
                 data.get('notes', order_row['notes']),
                 now, order_id)
            )
            conn.commit()
            
            updated = conn.execute('SELECT * FROM orders WHERE id = %s', (order_id,)).fetchone()
            updated_dict = dict(updated)
            # Fetch order items
            items_rows = conn.execute('SELECT * FROM order_items WHERE order_id = %s', (order_id,)).fetchall()
            updated_dict['items'] = [dict(row) for row in items_rows]
            conn.close()
            return jsonify({'success': True, 'order': updated_dict})
        
        conn.close()
        return jsonify({'error': 'Order not found'}), 404
    
    # GET single order
    order_row = conn.execute('SELECT * FROM orders WHERE id = %s', (order_id,)).fetchone()
    if order_row:
        order_dict = dict(order_row)
        # Fetch order items
        items_rows = conn.execute('SELECT * FROM order_items WHERE order_id = %s', (order_id,)).fetchall()
        order_dict['items'] = [dict(row) for row in items_rows]
        conn.close()
        return jsonify({'success': True, 'order': order_dict})
    
    conn.close()
    return jsonify({'success': False, 'error': 'Order not found'}), 404

@app.route('/api/orders/<order_id>/items', methods=['GET'])
def order_items(order_id):
    conn = get_db_connection()
    items_rows = conn.execute('SELECT * FROM order_items WHERE order_id = %s', (order_id,)).fetchall()
    conn.close()
    return jsonify({'items': [dict(row) for row in items_rows]})


# ============================================================================
# DAILY ORDERS MONITORING API
# ============================================================================

@app.route('/api/orders/today/count', methods=['GET'])
def get_today_orders_count_api():
    """Get the count of orders created today"""
    if get_today_orders_count:
        count = get_today_orders_count()
        return jsonify({
            'success': True,
            'today_orders_count': count,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'timestamp': datetime.now().isoformat()
        })
    
    return jsonify({
        'success': False,
        'error': 'Order monitor not available'
    }), 500


@app.route('/api/orders/today/summary', methods=['GET'])
def get_today_orders_summary_api():
    """Get comprehensive summary of today's orders"""
    if get_today_summary:
        summary = get_today_summary()
        return jsonify(summary)
    
    # Fallback: Get summary directly from database
    try:
        conn = get_db_connection()
        today = datetime.now().strftime('%Y-%m-%d')
        
        cursor = conn.execute(
            "SELECT COUNT(*) as count FROM orders WHERE DATE(created_at) = %s",
            (today,)
        )
        result = cursor.fetchone()
        count = result['count'] if result else 0
        
        conn.close()
        
        return jsonify({
            'success': True,
            'count': count,
            'date': today
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Appliances API
@app.route('/api/appliances', methods=['GET', 'POST'])
def appliances():
    conn = get_db_connection()
    
    if request.method == 'POST':
        data = request.get_json()
        appliance_id = str(uuid.uuid4())
        
        conn.execute(
            '''INSERT INTO appliances (id, name, type, model, serial_number, description, status, purchase_date, last_maintenance, notes)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
            (appliance_id, data.get('name'), data.get('type'), data.get('model', ''),
             data.get('serial_number', ''), data.get('description', ''), data.get('status', 'active'),
             data.get('purchase_date'), data.get('last_maintenance'), data.get('notes', ''))
        )
        conn.commit()
        
        appliance = {
            'id': appliance_id,
            'name': data.get('name'),
            'type': data.get('type'),
            'model': data.get('model', ''),
            'serial_number': data.get('serial_number', ''),
            'description': data.get('description', ''),
            'status': data.get('status', 'active'),
            'purchase_date': data.get('purchase_date'),
            'last_maintenance': data.get('last_maintenance'),
            'notes': data.get('notes', '')
        }
        conn.close()
        return jsonify({'success': True, 'appliance': appliance})
    
    # GET all appliances
    cursor = conn.execute('SELECT * FROM appliances')
    appliances_list = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({'appliances': appliances_list})

@app.route('/api/appliances/<appliance_id>', methods=['GET', 'PUT', 'DELETE'])
def appliance_detail(appliance_id):
    conn = get_db_connection()
    
    if request.method == 'DELETE':
        conn.execute('DELETE FROM appliances WHERE id = %s', (appliance_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    if request.method == 'PUT':
        data = request.get_json()
        appliance_row = conn.execute('SELECT * FROM appliances WHERE id = %s', (appliance_id,)).fetchone()
        
        if appliance_row:
            conn.execute(
                '''UPDATE appliances SET name = %s, type = %s, model = %s, serial_number = %s, 
                   description = %s, status = %s, purchase_date = %s, last_maintenance = %s, notes = %s
                   WHERE id = %s''',
                (data.get('name', appliance_row['name']),
                 data.get('type', appliance_row['type']),
                 data.get('model', appliance_row['model']),
                 data.get('serial_number', appliance_row['serial_number']),
                 data.get('description', appliance_row['description']),
                 data.get('status', appliance_row['status']),
                 data.get('purchase_date', appliance_row['purchase_date']),
                 data.get('last_maintenance', appliance_row['last_maintenance']),
                 data.get('notes', appliance_row['notes']),
                 appliance_id)
            )
            conn.commit()
            
            updated = conn.execute('SELECT * FROM appliances WHERE id = %s', (appliance_id,)).fetchone()
            conn.close()
            return jsonify({'success': True, 'appliance': dict(updated)})
        
        conn.close()
        return jsonify({'error': 'Appliance not found'}), 404
    
    # GET single appliance
    appliance_row = conn.execute('SELECT * FROM appliances WHERE id = %s', (appliance_id,)).fetchone()
    conn.close()
    
    if appliance_row:
        return jsonify({'appliance': dict(appliance_row)})
    return jsonify({'error': 'Appliance not found'}), 404


# Kitchen Appliances Mapping API
@app.route('/api/kitchens/<kitchen_id>/appliances', methods=['GET', 'POST'])
def kitchen_appliances(kitchen_id):
    conn = get_db_connection()
    
    # Verify kitchen exists
    kitchen_row = conn.execute('SELECT id FROM kitchens WHERE id = %s', (kitchen_id,)).fetchone()
    if not kitchen_row:
        conn.close()
        return jsonify({'error': 'Kitchen not found'}), 404
    
    if request.method == 'POST':
        data = request.get_json()
        appliance_id = data.get('appliance_id')
        quantity = data.get('quantity', 1)
        location = data.get('location', '')
        
        # Verify appliance exists
        appliance_row = conn.execute('SELECT name FROM appliances WHERE id = %s', (appliance_id,)).fetchone()
        if not appliance_row:
            conn.close()
            return jsonify({'error': 'Appliance not found'}), 404
        
        # Check if already exists
        existing = conn.execute(
            'SELECT id FROM kitchen_appliances WHERE kitchen_id = %s AND appliance_id = %s',
            (kitchen_id, appliance_id)
        ).fetchone()
        
        if existing:
            conn.close()
            return jsonify({'error': 'Appliance already assigned to this kitchen'}), 400
        
        mapping_id = str(uuid.uuid4())
        conn.execute(
            '''INSERT INTO kitchen_appliances (id, kitchen_id, appliance_id, quantity, location, status)
               VALUES (%s, %s, %s, %s, %s, %s)''',
            (mapping_id, kitchen_id, appliance_id, quantity, location, 'active')
        )
        conn.commit()
        
        mapping = {
            'id': mapping_id,
            'kitchen_id': kitchen_id,
            'appliance_id': appliance_id,
            'appliance_name': appliance_row['name'],
            'quantity': quantity,
            'location': location,
            'status': 'active'
        }
        conn.close()
        return jsonify({'success': True, 'mapping': mapping})
    
    # GET all appliances for this kitchen
    cursor = conn.execute(
        '''SELECT ka.id, ka.kitchen_id, ka.appliance_id, a.name as appliance_name, a.type, a.model,
           ka.quantity, ka.location, ka.status, ka.assigned_date
           FROM kitchen_appliances ka
           JOIN appliances a ON ka.appliance_id = a.id
           WHERE ka.kitchen_id = %s''',
        (kitchen_id,)
    )
    mappings = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({'kitchen_id': kitchen_id, 'appliances': mappings})

@app.route('/api/kitchens/<kitchen_id>/appliances/<mapping_id>', methods=['PUT', 'DELETE'])
def kitchen_appliance_detail(kitchen_id, mapping_id):
    conn = get_db_connection()
    
    if request.method == 'DELETE':
        # Verify mapping belongs to this kitchen
        mapping_row = conn.execute(
            'SELECT id FROM kitchen_appliances WHERE id = %s AND kitchen_id = %s',
            (mapping_id, kitchen_id)
        ).fetchone()
        
        if not mapping_row:
            conn.close()
            return jsonify({'error': 'Mapping not found'}), 404
        
        conn.execute('DELETE FROM kitchen_appliances WHERE id = %s', (mapping_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    if request.method == 'PUT':
        data = request.get_json()
        mapping_row = conn.execute(
            'SELECT * FROM kitchen_appliances WHERE id = %s AND kitchen_id = %s',
            (mapping_id, kitchen_id)
        ).fetchone()
        
        if mapping_row:
            conn.execute(
                '''UPDATE kitchen_appliances SET quantity = %s, location = %s, status = %s
                   WHERE id = %s''',
                (data.get('quantity', mapping_row['quantity']),
                 data.get('location', mapping_row['location']),
                 data.get('status', mapping_row['status']),
                 mapping_id)
            )
            conn.commit()
            
            updated = conn.execute(
                '''SELECT ka.id, ka.kitchen_id, ka.appliance_id, a.name as appliance_name, a.type, a.model,
                   ka.quantity, ka.location, ka.status, ka.assigned_date
                   FROM kitchen_appliances ka
                   JOIN appliances a ON ka.appliance_id = a.id
                   WHERE ka.id = %s''',
                (mapping_id,)
            ).fetchone()
            conn.close()
            return jsonify({'success': True, 'mapping': dict(updated)})
        
        conn.close()
        return jsonify({'error': 'Mapping not found'}), 404


# Get all appliance types (for filtering/reference)
@app.route('/api/appliance-types', methods=['GET'])
def appliance_types():
    appliance_types_list = [
        'Oven',
        'Stove/Cooktop',
        'Grill',
        'Fryer',
        'Microwave',
        'Refrigerator',
        'Freezer',
        'Dishwasher',
        'Food Processor',
        'Mixer',
        'Blender',
        'Coffee Maker',
        'Toaster',
        'Kettle',
        'Steamer',
        'Pressure Cooker',
        'Slow Cooker',
        'Rice Cooker',
        'Waffle Maker',
        'Juicer',
        'Slicer',
        'Chopper',
        'Scale',
        'Timer',
        'Ventilation Hood',
        'Prep Table',
        'Cutting Board',
        'Other'
    ]
    return jsonify({'types': appliance_types_list})


# IoT Devices API
@app.route('/api/iot-devices', methods=['GET', 'POST'])
def iot_devices():
    conn = get_db_connection()
    
    if request.method == 'POST':
        data = request.get_json()
        device_id = str(uuid.uuid4())
        
        conn.execute(
            '''INSERT INTO iot_devices (id, name, device_type, device_id, location, kitchen_id, description, 
               status, battery_level, signal_strength, ip_address, mac_address, firmware_version, notes)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
            (device_id, data.get('name'), data.get('device_type'), data.get('device_id', ''),
             data.get('location', ''), data.get('kitchen_id'), data.get('description', ''),
             data.get('status', 'active'), data.get('battery_level'), data.get('signal_strength'),
             data.get('ip_address', ''), data.get('mac_address', ''), data.get('firmware_version', ''),
             data.get('notes', ''))
        )
        conn.commit()
        
        device = {
            'id': device_id,
            'name': data.get('name'),
            'device_type': data.get('device_type'),
            'device_id': data.get('device_id', ''),
            'location': data.get('location', ''),
            'kitchen_id': data.get('kitchen_id'),
            'status': data.get('status', 'active')
        }
        conn.close()
        return jsonify({'success': True, 'device': device})
    
    # GET all IoT devices
    cursor = conn.execute('SELECT * FROM iot_devices')
    devices_list = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({'devices': devices_list})

@app.route('/api/iot-devices/<device_id>', methods=['GET', 'PUT', 'DELETE'])
def iot_device_detail(device_id):
    conn = get_db_connection()
    
    if request.method == 'DELETE':
        conn.execute('DELETE FROM iot_devices WHERE id = %s', (device_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    if request.method == 'PUT':
        data = request.get_json()
        device_row = conn.execute('SELECT * FROM iot_devices WHERE id = %s', (device_id,)).fetchone()
        
        if device_row:
            conn.execute(
                '''UPDATE iot_devices SET name = %s, device_type = %s, device_id = %s, location = %s, 
                   kitchen_id = %s, description = %s, status = %s, battery_level = %s, signal_strength = %s,
                   ip_address = %s, mac_address = %s, firmware_version = %s, notes = %s, last_sync = %s
                   WHERE id = %s''',
                (data.get('name', device_row['name']),
                 data.get('device_type', device_row['device_type']),
                 data.get('device_id', device_row['device_id']),
                 data.get('location', device_row['location']),
                 data.get('kitchen_id', device_row['kitchen_id']),
                 data.get('description', device_row['description']),
                 data.get('status', device_row['status']),
                 data.get('battery_level', device_row['battery_level']),
                 data.get('signal_strength', device_row['signal_strength']),
                 data.get('ip_address', device_row['ip_address']),
                 data.get('mac_address', device_row['mac_address']),
                 data.get('firmware_version', device_row['firmware_version']),
                 data.get('notes', device_row['notes']),
                 datetime.now() if data.get('last_sync') else device_row['last_sync'],
                 device_id)
            )
            conn.commit()
            
            updated = conn.execute('SELECT * FROM iot_devices WHERE id = %s', (device_id,)).fetchone()
            conn.close()
            return jsonify({'success': True, 'device': dict(updated)})
        
        conn.close()
        return jsonify({'error': 'Device not found'}), 404
    
    # GET single device
    device_row = conn.execute('SELECT * FROM iot_devices WHERE id = %s', (device_id,)).fetchone()
    conn.close()
    
    if device_row:
        return jsonify({'device': dict(device_row)})
    return jsonify({'error': 'Device not found'}), 404


# Get all IoT device types (for filtering/reference)
@app.route('/api/iot-device-types', methods=['GET'])
def iot_device_types():
    device_types = [
        'Temperature Sensor',
        'Humidity Sensor',
        'Motion Detector',
        'Door Sensor',
        'Smoke Detector',
        'Pressure Gauge',
        'Weight Scale',
        'RFID Reader',
        'Camera',
        'Smart Display',
        'Beacon',
        'Gas Detector',
        'Water Flow Meter',
        'Energy Meter',
        'Light Sensor',
        'Sound Sensor',
        'Other'
    ]
    return jsonify({'types': device_types})


# Staff API
@app.route('/api/staff', methods=['GET', 'POST'])
def staff():
    conn = get_db_connection()
    
    if request.method == 'POST':
        data = request.get_json()
        staff_id = str(uuid.uuid4())
        
        conn.execute(
            '''INSERT INTO staff (id, name, email, phone, position, department, kitchen_id, 
               hire_date, date_of_birth, address, city, state, postal_code, 
               emergency_contact_name, emergency_contact_phone, status, salary_type, notes)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
            (staff_id, data.get('name'), data.get('email'), data.get('phone'),
             data.get('position'), data.get('department'), data.get('kitchen_id'),
             data.get('hire_date'), data.get('date_of_birth'), data.get('address'),
             data.get('city'), data.get('state'), data.get('postal_code'),
             data.get('emergency_contact_name'), data.get('emergency_contact_phone'),
             data.get('status', 'active'), data.get('salary_type'), data.get('notes', ''))
        )
        conn.commit()
        
        staff_member = {
            'id': staff_id,
            'name': data.get('name'),
            'email': data.get('email'),
            'phone': data.get('phone'),
            'position': data.get('position'),
            'status': data.get('status', 'active')
        }
        conn.close()
        return jsonify({'success': True, 'staff': staff_member})
    
    # GET all staff
    cursor = conn.execute('SELECT * FROM staff ORDER BY name')
    staff_list = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({'staff': staff_list})

@app.route('/api/staff/<staff_id>', methods=['GET', 'PUT', 'DELETE'])
def staff_detail(staff_id):
    conn = get_db_connection()
    
    if request.method == 'DELETE':
        conn.execute('DELETE FROM staff WHERE id = %s', (staff_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    if request.method == 'PUT':
        data = request.get_json()
        staff_row = conn.execute('SELECT * FROM staff WHERE id = %s', (staff_id,)).fetchone()
        
        if staff_row:
            conn.execute(
                '''UPDATE staff SET name = %s, email = %s, phone = %s, position = %s, 
                   department = %s, kitchen_id = %s, hire_date = %s, date_of_birth = %s, 
                   address = %s, city = %s, state = %s, postal_code = %s, 
                   emergency_contact_name = %s, emergency_contact_phone = %s, 
                   status = %s, salary_type = %s, notes = %s
                   WHERE id = %s''',
                (data.get('name', staff_row['name']),
                 data.get('email', staff_row['email']),
                 data.get('phone', staff_row['phone']),
                 data.get('position', staff_row['position']),
                 data.get('department', staff_row['department']),
                 data.get('kitchen_id', staff_row['kitchen_id']),
                 data.get('hire_date', staff_row['hire_date']),
                 data.get('date_of_birth', staff_row['date_of_birth']),
                 data.get('address', staff_row['address']),
                 data.get('city', staff_row['city']),
                 data.get('state', staff_row['state']),
                 data.get('postal_code', staff_row['postal_code']),
                 data.get('emergency_contact_name', staff_row['emergency_contact_name']),
                 data.get('emergency_contact_phone', staff_row['emergency_contact_phone']),
                 data.get('status', staff_row['status']),
                 data.get('salary_type', staff_row['salary_type']),
                 data.get('notes', staff_row['notes']),
                 staff_id)
            )
            conn.commit()
            
            updated = conn.execute('SELECT * FROM staff WHERE id = %s', (staff_id,)).fetchone()
            conn.close()
            return jsonify({'success': True, 'staff': dict(updated)})
        
        conn.close()
        return jsonify({'error': 'Staff member not found'}), 404
    
    # GET single staff
    staff_row = conn.execute('SELECT * FROM staff WHERE id = %s', (staff_id,)).fetchone()
    conn.close()
    
    if staff_row:
        return jsonify({'staff': dict(staff_row)})
    return jsonify({'error': 'Staff member not found'}), 404


# Get staff positions (for filtering/reference)
@app.route('/api/staff-positions', methods=['GET'])
def staff_positions():
    positions = [
        'Chef',
        'Sous Chef',
        'Head Cook',
        'Line Cook',
        'Prep Cook',
        'Pastry Chef',
        'Dishwasher',
        'Server',
        'Host/Hostess',
        'Busser',
        'Bartender',
        'Barista',
        'Manager',
        'Assistant Manager',
        'Kitchen Manager',
        'Front of House Manager',
        'Sommelier',
        'Other'
    ]
    return jsonify({'positions': positions})


# Get staff departments (for filtering/reference)
@app.route('/api/staff-departments', methods=['GET'])
def staff_departments():
    departments = [
        'Kitchen',
        'Front of House',
        'Bar',
        'Pastry',
        'Management',
        'Maintenance',
        'Administrative',
        'Other'
    ]
    return jsonify({'departments': departments})


# Staff Kitchen Requests API (with Manager Approval)
@app.route('/api/staff-kitchen-requests', methods=['GET', 'POST'])
def staff_kitchen_requests():
    conn = get_db_connection()
    
    if request.method == 'POST':
        data = request.get_json()
        request_id = str(uuid.uuid4())
        
        # Get staff and kitchen details
        staff_row = conn.execute('SELECT name FROM staff WHERE id = %s', (data.get('staff_id'),)).fetchone()
        kitchen_row = conn.execute('SELECT name FROM kitchens WHERE id = %s', (data.get('kitchen_id'),)).fetchone()
        
        if not staff_row or not kitchen_row:
            conn.close()
            return jsonify({'error': 'Staff or kitchen not found'}), 404
        
        conn.execute(
            '''INSERT INTO staff_kitchen_requests 
               (id, staff_id, staff_name, kitchen_id, kitchen_name, position, request_reason, 
                requested_start_date, status, approval_status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
            (request_id, data.get('staff_id'), staff_row['name'], 
             data.get('kitchen_id'), kitchen_row['name'], data.get('position'),
             data.get('request_reason'), data.get('requested_start_date'), 
             'pending', 'pending')
        )
        conn.commit()
        
        result = {
            'id': request_id,
            'staff_id': data.get('staff_id'),
            'staff_name': staff_row['name'],
            'kitchen_id': data.get('kitchen_id'),
            'kitchen_name': kitchen_row['name'],
            'status': 'pending',
            'approval_status': 'pending'
        }
        conn.close()
        return jsonify({'success': True, 'request': result})
    
    # GET all requests
    cursor = conn.execute(
        '''SELECT * FROM staff_kitchen_requests ORDER BY requested_date DESC'''
    )
    requests_list = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({'requests': requests_list})

@app.route('/api/staff-kitchen-requests/<req_id>', methods=['GET', 'PUT', 'DELETE'])
def staff_kitchen_request_detail(req_id):
    conn = get_db_connection()
    
    if request.method == 'DELETE':
        conn.execute('DELETE FROM staff_kitchen_requests WHERE id = %s', (req_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    if request.method == 'PUT':
        data = request.get_json()
        req_row = conn.execute('SELECT * FROM staff_kitchen_requests WHERE id = %s', (req_id,)).fetchone()
        
        if req_row:
            conn.execute(
                '''UPDATE staff_kitchen_requests SET position = %s, request_reason = %s, 
                   requested_start_date = %s, updated_at = %s
                   WHERE id = %s''',
                (data.get('position', req_row['position']),
                 data.get('request_reason', req_row['request_reason']),
                 data.get('requested_start_date', req_row['requested_start_date']),
                 datetime.now(),
                 req_id)
            )
            conn.commit()
            
            updated = conn.execute('SELECT * FROM staff_kitchen_requests WHERE id = %s', (req_id,)).fetchone()
            conn.close()
            return jsonify({'success': True, 'request': dict(updated)})
        
        conn.close()
        return jsonify({'error': 'Request not found'}), 404
    
    # GET single request
    req_row = conn.execute('SELECT * FROM staff_kitchen_requests WHERE id = %s', (req_id,)).fetchone()
    conn.close()
    
    if req_row:
        return jsonify({'request': dict(req_row)})
    return jsonify({'error': 'Request not found'}), 404


# Manager Approval Endpoint
@app.route('/api/staff-kitchen-requests/<req_id>/approve', methods=['POST'])
def approve_staff_kitchen_request(req_id):
    conn = get_db_connection()
    data = request.get_json()
    
    req_row = conn.execute('SELECT * FROM staff_kitchen_requests WHERE id = %s', (req_id,)).fetchone()
    
    if not req_row:
        conn.close()
        return jsonify({'error': 'Request not found'}), 404
    
    # Update request status
    conn.execute(
        '''UPDATE staff_kitchen_requests SET approval_status = %s, approved_by = %s, 
           approval_notes = %s, approval_date = %s, updated_at = %s
           WHERE id = %s''',
        ('approved', data.get('approved_by', 'manager'), data.get('approval_notes', ''),
         datetime.now(), datetime.now(), req_id)
    )
    
    # Create assignment
    assignment_id = str(uuid.uuid4())
    conn.execute(
        '''INSERT INTO staff_kitchen_assignments 
           (id, staff_id, staff_name, kitchen_id, kitchen_name, position, request_id, status)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''',
        (assignment_id, req_row['staff_id'], req_row['staff_name'],
         req_row['kitchen_id'], req_row['kitchen_name'], req_row['position'],
         req_id, 'active')
    )
    
    # Update staff's kitchen_id
    conn.execute('UPDATE staff SET kitchen_id = %s WHERE id = %s', 
                (req_row['kitchen_id'], req_row['staff_id']))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Request approved and assignment created'})


# Manager Rejection Endpoint
@app.route('/api/staff-kitchen-requests/<req_id>/reject', methods=['POST'])
def reject_staff_kitchen_request(req_id):
    conn = get_db_connection()
    data = request.get_json()
    
    req_row = conn.execute('SELECT * FROM staff_kitchen_requests WHERE id = %s', (req_id,)).fetchone()
    
    if not req_row:
        conn.close()
        return jsonify({'error': 'Request not found'}), 404
    
    # Update request status
    conn.execute(
        '''UPDATE staff_kitchen_requests SET approval_status = %s, approved_by = %s, 
           rejection_reason = %s, approval_date = %s, updated_at = %s
           WHERE id = %s''',
        ('rejected', data.get('approved_by', 'manager'), data.get('rejection_reason', ''),
         datetime.now(), datetime.now(), req_id)
    )
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Request rejected'})


# Staff Kitchen Assignments API
@app.route('/api/staff-kitchen-assignments', methods=['GET', 'POST'])
def staff_kitchen_assignments():
    conn = get_db_connection()
    
    if request.method == 'POST':
        data = request.get_json()
        assignment_id = str(uuid.uuid4())
        
        staff_row = conn.execute('SELECT name FROM staff WHERE id = %s', (data.get('staff_id'),)).fetchone()
        kitchen_row = conn.execute('SELECT name FROM kitchens WHERE id = %s', (data.get('kitchen_id'),)).fetchone()
        
        if not staff_row or not kitchen_row:
            conn.close()
            return jsonify({'error': 'Staff or kitchen not found'}), 404
        
        conn.execute(
            '''INSERT INTO staff_kitchen_assignments 
               (id, staff_id, staff_name, kitchen_id, kitchen_name, position, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s)''',
            (assignment_id, data.get('staff_id'), staff_row['name'],
             data.get('kitchen_id'), kitchen_row['name'], data.get('position'),
             data.get('status', 'active'))
        )
        
        # Update staff's kitchen_id
        conn.execute('UPDATE staff SET kitchen_id = %s WHERE id = %s',
                    (data.get('kitchen_id'), data.get('staff_id')))
        
        conn.commit()
        
        result = {
            'id': assignment_id,
            'staff_id': data.get('staff_id'),
            'staff_name': staff_row['name'],
            'kitchen_id': data.get('kitchen_id'),
            'kitchen_name': kitchen_row['name'],
            'status': data.get('status', 'active')
        }
        conn.close()
        return jsonify({'success': True, 'assignment': result})
    
    # GET all assignments
    cursor = conn.execute(
        '''SELECT * FROM staff_kitchen_assignments WHERE status = 'active' 
           ORDER BY assigned_date DESC'''
    )
    assignments_list = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({'assignments': assignments_list})

@app.route('/api/staff-kitchen-assignments/<assign_id>', methods=['GET', 'PUT', 'DELETE'])
def staff_kitchen_assignment_detail(assign_id):
    conn = get_db_connection()
    
    if request.method == 'DELETE':
        assign_row = conn.execute('SELECT * FROM staff_kitchen_assignments WHERE id = %s', (assign_id,)).fetchone()
        if assign_row:
            conn.execute('UPDATE staff_kitchen_assignments SET status = %s WHERE id = %s', 
                        ('inactive', assign_id))
            # Optionally remove kitchen_id from staff if no other active assignment
            conn.execute('UPDATE staff SET kitchen_id = NULL WHERE id = %s AND id NOT IN (SELECT staff_id FROM staff_kitchen_assignments WHERE status = "active")',
                        (assign_row['staff_id'],))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    if request.method == 'PUT':
        data = request.get_json()
        assign_row = conn.execute('SELECT * FROM staff_kitchen_assignments WHERE id = %s', (assign_id,)).fetchone()
        
        if assign_row:
            conn.execute(
                '''UPDATE staff_kitchen_assignments SET position = %s, status = %s, 
                   end_date = %s, notes = %s
                   WHERE id = %s''',
                (data.get('position', assign_row['position']),
                 data.get('status', assign_row['status']),
                 data.get('end_date', assign_row['end_date']),
                 data.get('notes', assign_row['notes']),
                 assign_id)
            )
            conn.commit()
            
            updated = conn.execute('SELECT * FROM staff_kitchen_assignments WHERE id = %s', (assign_id,)).fetchone()
            conn.close()
            return jsonify({'success': True, 'assignment': dict(updated)})
        
        conn.close()
        return jsonify({'error': 'Assignment not found'}), 404
    
    # GET single assignment
    assign_row = conn.execute('SELECT * FROM staff_kitchen_assignments WHERE id = %s', (assign_id,)).fetchone()
    conn.close()
    
    if assign_row:
        return jsonify({'assignment': dict(assign_row)})
    return jsonify({'error': 'Assignment not found'}), 404


# Get pending requests for manager approval
@app.route('/api/staff-kitchen-requests/pending', methods=['GET'])
def pending_requests():
    conn = get_db_connection()
    cursor = conn.execute(
        '''SELECT * FROM staff_kitchen_requests WHERE approval_status = 'pending' 
           ORDER BY requested_date DESC'''
    )
    requests_list = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({'requests': requests_list, 'count': len(requests_list)})


# ============================================================================
# WEBHOOK API FOR EXTERNAL ORDER INTEGRATION
# ============================================================================

@app.route('/webhook/receive-order', methods=['POST'])
def receive_order_webhook():
    """
    Webhook endpoint to receive orders from external systems (POS, mobile apps, etc).
    
    Expected JSON payload (simplified):
    {
        "order_id": "ORD-2024-001",
        "customer_name": "John Doe",
        "phone_number": "555-1234",
        "created_date": "2024-12-03T10:30:00"
    }
    
    Returns:
    {
        "success": true,
        "order_id": "ORD-2024-001",
        "message": "Order received and stored",
        "created_at": "2024-12-03T10:30:00"
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('order_id'):
            return jsonify({
                'success': False,
                'error': 'Missing required field: order_id'
            }), 400
        
        if not data.get('customer_name'):
            return jsonify({
                'success': False,
                'error': 'Missing required field: customer_name'
            }), 400
        
        if not data.get('phone_number'):
            return jsonify({
                'success': False,
                'error': 'Missing required field: phone_number'
            }), 400
        
        if not data.get('created_date'):
            return jsonify({
                'success': False,
                'error': 'Missing required field: created_date'
            }), 400
        
        # Process order into database
        conn = get_db_connection()
        db_order_id = str(uuid.uuid4())
        created_date = data.get('created_date')
        
        # Insert order with webhook data
        conn.execute(
            '''INSERT INTO orders (id, order_number, customer_name, status, notes, created_at, updated_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s)''',
            (db_order_id, data.get('order_id'), data.get('customer_name'), 'pending',
             f"Phone: {data.get('phone_number')}", created_date, datetime.now().isoformat())
        )
        
        conn.commit()
        conn.close()
        
        # Build response
        response = {
            'success': True,
            'order_id': data.get('order_id'),
            'customer_name': data.get('customer_name'),
            'phone_number': data.get('phone_number'),
            'created_at': created_date,
            'message': 'Order received and stored'
        }
        
        # Push order to stream database for Kitchen Agent processing if available
        if push_order_to_stream:
            push_order_to_stream(response)
        
        return jsonify(response), 201
    
    except Exception as e:
        print(f"Error in receive_order_webhook: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to process webhook order'
        }), 500


# ============================================================================
# KITCHEN MANAGEMENT API
# ============================================================================

from kitchen_manager import KitchenManager

# Note: /api/kitchens GET and POST route is defined earlier in the file (around line 511)

@app.route('/api/kitchens/<kitchen_id>/assignments', methods=['GET'])
def get_kitchen_assignments(kitchen_id):
    """Get all assignments for a kitchen"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get kitchen assignments from stream database if available
    try:
        from stream_integration import get_kitchen_assignments as stream_get_assignments
        assignments = stream_get_assignments(kitchen_id)
        conn.close()
        return jsonify({'assignments': assignments})
    except:
        pass
    
    # Fallback to empty list if stream not available
    conn.close()
    return jsonify({'assignments': []})

@app.route('/api/kitchens/<kitchen_id>/current-assignments', methods=['GET'])
def get_kitchen_current_assignments(kitchen_id):
    """Get current active assignments for a kitchen (pending/preparing)"""
    conn = get_db_connection()
    
    try:
        cursor = conn.cursor()
        
        # Get current assignments with order and item details
        cursor.execute('''
            SELECT 
                ka.id as assignment_id,
                ka.status,
                ka.started,
                ka.completed,
                ka.assigned_at,
                ka.completed_at,
                oi.id as order_item_id,
                oi.food_item_id,
                oi.food_name,
                oi.category_name,
                oi.quantity,
                oi.price,
                oi.notes as item_notes,
                o.id as order_id,
                o.order_number,
                o.customer_name,
                o.table_number,
                o.status as order_status,
                o.created_at as order_created_at
            FROM kitchen_assignments ka
            INNER JOIN order_items oi ON ka.food_item_id = oi.id
            INNER JOIN orders o ON ka.order_id = o.id
            WHERE ka.kitchen_id = %s
            AND ka.completed = 0
            ORDER BY ka.assigned_at ASC
        ''', (kitchen_id,))
        
        assignments = cursor.fetchall()
        
        # Convert to list of dicts
        result = []
        for assignment in assignments:
            result.append(dict(assignment))
        
        conn.close()
        # print("result : ",result)
        return jsonify({
            'success': True,
            'assignments': result,
            'count': len(result)
        })
        
    except Exception as e:
        print(f"❌ Error in get_kitchen_current_assignments: {e}")
        import traceback
        traceback.print_exc()
        conn.close()
        return jsonify({
            'success': False,
            'error': str(e),
            'assignments': []
        }), 500

@app.route('/api/kitchen-assignments/<assignment_id>/status', methods=['PUT'])
def update_kitchen_assignment_status(assignment_id):
    """Update the status of a kitchen assignment (start/complete)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            conn.close()
            return jsonify({'success': False, 'error': 'Status is required'}), 400
        
        # Check if assignment exists
        cursor.execute('SELECT * FROM kitchen_assignments WHERE id = %s', (assignment_id,))
        assignment = cursor.fetchone()
        
        if not assignment:
            conn.close()
            return jsonify({'success': False, 'error': 'Assignment not found'}), 404
        
        # Update based on status
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if new_status == 'preparing':
            # Mark as started
            cursor.execute('''
                UPDATE kitchen_assignments 
                SET started = 1, status = 'preparing', assigned_at = %s
                WHERE id = %s
            ''', (current_time, assignment_id))
        elif new_status == 'completed':
            # Mark as completed
            cursor.execute('''
                UPDATE kitchen_assignments 
                SET completed = 1, status = 'completed', completed_at = %s
                WHERE id = %s
            ''', (current_time, assignment_id))
        else:
            # General status update
            cursor.execute('''
                UPDATE kitchen_assignments 
                SET status = %s
                WHERE id = %s
            ''', (new_status, assignment_id))
        
        conn.commit()
        
        # Get updated assignment
        cursor.execute('SELECT * FROM kitchen_assignments WHERE id = %s', (assignment_id,))
        updated_assignment = cursor.fetchone()
        
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Status updated to {new_status}',
            'assignment': dict(updated_assignment) if updated_assignment else None
        })
        
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/orders/<order_id>/assign-kitchens', methods=['POST'])
def assign_order_to_kitchens(order_id):
    """Assign order items to specific kitchens"""
    conn = get_db_connection()
    
    # Get order
    order_row = conn.execute('SELECT * FROM orders WHERE id = %s', (order_id,)).fetchone()
    if not order_row:
        conn.close()
        return jsonify({'error': 'Order not found'}), 404
    
    # Get request data
    data = request.get_json()
    assignments = data.get('assignments', [])
    
    order_data = dict(order_row)
    
    # If explicit assignments provided, use them
    if assignments and len(assignments) > 0:
        # Update order_items with kitchen assignments
        for assignment in assignments:
            item_id = assignment.get('item_id')
            kitchen_id = assignment.get('kitchen_id')
            
            if item_id and kitchen_id:
                # Update the order item with kitchen assignment
                conn.execute('''
                    UPDATE order_items 
                    SET status = 'preparing'
                    WHERE id = %s
                ''', (item_id,))
                
                # Store kitchen assignment
                assignment_id = str(uuid.uuid4())
                conn.execute('''
                    INSERT OR IGNORE INTO kitchen_assignments (id, item_id, kitchen_id, order_id, status)
                    VALUES (%s, %s, %s, %s, 'pending')
                ''', (assignment_id, item_id, kitchen_id, order_id))
        
        conn.commit()
    
    # Get updated items
    items_rows = conn.execute('SELECT * FROM order_items WHERE order_id = %s', (order_id,)).fetchall()
    items = [dict(row) for row in items_rows]
    order_data['items'] = items
    
    # Get kitchen assignments for this order
    assignment_rows = conn.execute('''
        SELECT DISTINCT ka.kitchen_id, k.name, k.icon
        FROM kitchen_assignments ka
        JOIN kitchens k ON ka.kitchen_id = k.id
        WHERE ka.order_id = %s
    ''', (order_id,)).fetchall()
    
    kitchen_assignments = {}
    for row in assignment_rows:
        kitchen_id = row[0]
        kitchen_name = row[1]
        kitchen_icon = row[2]
        
        items_for_kitchen = conn.execute('''
            SELECT oi.* FROM order_items oi
            JOIN kitchen_assignments ka ON oi.id = ka.item_id
            WHERE ka.kitchen_id = %s AND oi.order_id = %s
        ''', (kitchen_id, order_id)).fetchall()
        
        kitchen_assignments[kitchen_id] = {
            'kitchen_id': kitchen_id,
            'kitchen_name': kitchen_name,
            'icon': kitchen_icon,
            'items': [dict(item) for item in items_for_kitchen],
            'item_count': len(items_for_kitchen)
        }
    
    # If no explicit assignments, use KitchenManager to auto-assign
    if not assignments or len(assignments) == 0:
        auto_assignments = KitchenManager.assign_order_items(order_data)
        
        for kitchen_id, assigned_items in auto_assignments.items():
            for item in assigned_items:
                assignment_id = str(uuid.uuid4())
                conn.execute('''
                    INSERT OR IGNORE INTO kitchen_assignments (id, item_id, kitchen_id, order_id, status)
                    VALUES (%s, %s, %s, %s, 'pending')
                ''', (assignment_id, item['id'], kitchen_id, order_id))
            
            kitchen_info = KitchenManager.get_kitchen_details(kitchen_id)
            kitchen_assignments[kitchen_id] = {
                'kitchen_id': kitchen_id,
                'kitchen_name': kitchen_info['name'],
                'icon': kitchen_info['icon'],
                'items': assigned_items,
                'item_count': len(assigned_items)
            }
        
        conn.commit()
    
    # Push to stream if available
    if push_order_to_stream:
        try:
            from stream_integration import push_order_to_stream as stream_push
            stream_push(order_data)
        except:
            pass
    
    conn.close()
    return jsonify({'success': True, 'assignments': list(kitchen_assignments.values())})

@app.route('/api/orders/<order_id>/kitchen-status', methods=['GET', 'PUT'])
def order_kitchen_status(order_id):
    """Get or update kitchen item status for an order"""
    conn = get_db_connection()
    
    if request.method == 'PUT':
        data = request.get_json()
        item_id = data.get('item_id')
        new_status = data.get('status')
        
        # Update item status in order_items table
        conn.execute('''
            UPDATE order_items 
            SET status = %s, updated_at = %s
            WHERE id = %s
        ''', (new_status, datetime.now().isoformat(), item_id))
        
        conn.commit()
        
        # Check if all items are completed
        cursor = conn.execute('''
            SELECT COUNT(*) as total, 
                   SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed
            FROM order_items 
            WHERE order_id = %s
        ''', (order_id,)).fetchone()
        
        total = cursor['total']
        completed = cursor['completed'] or 0
        
        # Update order status if all items completed
        if total == completed:
            conn.execute('UPDATE orders SET status = %s WHERE id = %s', ('completed', order_id))
            conn.commit()
        
        conn.close()
        return jsonify({'success': True, 'item_id': item_id, 'status': new_status})
    
    # GET - retrieve all items and their status
    items = conn.execute('SELECT * FROM order_items WHERE order_id = %s', (order_id,)).fetchall()
    conn.close()
    
    items_data = []
    for item in items:
        item_dict = dict(item)
        item_dict['status_label'] = KitchenManager.STATUS_LABELS.get(item_dict.get('status', 'pending'), '⏳ Pending')
        item_dict['status_color'] = KitchenManager.STATUS_COLORS.get(item_dict.get('status', 'pending'), '#FFA500')
        items_data.append(item_dict)
    
    return jsonify({'items': items_data})

@app.route('/api/kitchen-item/<item_id>/transition', methods=['POST'])
def transition_item_status(item_id):
    """Transition item to next status in workflow"""
    data = request.get_json()
    new_status = data.get('status')
    
    if new_status not in KitchenManager.STATUS_FLOW:
        return jsonify({'error': 'Invalid status'}), 400
    
    conn = get_db_connection()
    
    # Update item
    conn.execute('''
        UPDATE order_items 
        SET status = %s, updated_at = %s
        WHERE id = %s
    ''', (new_status, datetime.now().isoformat(), item_id))
    
    conn.commit()
    
    # Get updated item
    item = conn.execute('SELECT * FROM order_items WHERE id = %s', (item_id,)).fetchone()
    conn.close()
    
    return jsonify({
        'success': True,
        'item_id': item_id,
        'status': new_status,
        'status_label': KitchenManager.STATUS_LABELS.get(new_status),
        'status_color': KitchenManager.STATUS_COLORS.get(new_status)
    })

@app.route('/api/kitchen-agent/ask', methods=['POST'])
def kitchen_agent_ask():
    """Ask the kitchen agent a question about orders and kitchen operations"""
    data = request.get_json()
    query = data.get('query')
    include_context = data.get('include_context', False)
    order_id = data.get('order_id')
    
    if not query:
        return jsonify({'error': 'Query is required'}), 400
    
    # Build context if requested
    context = {}
    
    if include_context and order_id:
        conn = get_db_connection()
        order = conn.execute('SELECT * FROM orders WHERE id = %s', (order_id,)).fetchone()
        
        if order:
            context['order'] = {
                'id': order['id'],
                'table_name': order['table_name'],
                'status': order['status'],
                'items_count': len(conn.execute('SELECT * FROM order_items WHERE order_id = %s', (order_id,)).fetchall())
            }
        
        # Get kitchen stats
        items = conn.execute('SELECT status FROM order_items').fetchall()
        context['kitchen_stats'] = {
            'total_items': len(items),
            'pending_items': len([i for i in items if i['status'] == 'pending']),
            'ready_items': len([i for i in items if i['status'] == 'ready'])
        }
        
        conn.close()
    elif include_context:
        # Get general kitchen stats
        conn = get_db_connection()
        items = conn.execute('SELECT status FROM order_items').fetchall()
        context['kitchen_stats'] = {
            'total_items': len(items),
            'pending_items': len([i for i in items if i['status'] == 'pending']),
            'ready_items': len([i for i in items if i['status'] == 'ready'])
        }
        conn.close()
    
    # Ask the agent
    response = ask_kitchen_agent(query, context if context else None)
    
    return jsonify(response)

@app.route('/api/kitchen-agent/suggest', methods=['POST']) 
def kitchen_agent_suggest():
    """Get suggestions from the kitchen agent for current operations"""
    data = request.get_json()
    
    conn = get_db_connection()
    
    # Get current kitchen status
    orders = conn.execute('SELECT COUNT(*) as count FROM orders WHERE status = "pending"').fetchone()
    items = conn.execute('SELECT status, COUNT(*) as count FROM order_items GROUP BY status').fetchall()
    
    stats = {
        'pending_orders': orders['count'],
        'items_by_status': {item['status']: item['count'] for item in items}
    }
    
    conn.close()
    
    # Ask agent for suggestions
    prompt = f"""
    Based on the current kitchen operations, provide helpful suggestions:
    - Pending Orders: {stats['pending_orders']}
    - Items by Status: {stats['items_by_status']}
    
    Please suggest ways to improve efficiency or address any bottlenecks.
    """
    
    response = ask_kitchen_agent(prompt, {'kitchen_stats': stats})
    
    return jsonify(response)


# ============================================================================
# INVENTORY AGENT ENDPOINTS - Sustainability & Inventory Management
# ============================================================================

@app.route('/api/inventory/ask', methods=['POST'])
def inventory_agent_ask():
    """
    Ask the inventory agent a general question about stock, sustainability, forecasting, etc.
    
    Request JSON:
    {
        "query": "What's the stock status for Chicken Teriyaki?",
        "kitchen_id": "KITCHEN_001" (optional),
        "date": "2025-12-03" (optional),
        "include_context": true (optional)
    }
    
    Response:
    {
        "success": true,
        "message": "Agent response with insights and recommendations",
        "query": "...",
        "timestamp": "ISO timestamp"
    }
    """
    data = request.get_json()
    query = data.get('query')
    
    if not query:
        return jsonify({'error': 'Query is required'}), 400
    
    # Build context
    context = {}
    if data.get('kitchen_id'):
        context['kitchen_id'] = data.get('kitchen_id')
    if data.get('date'):
        context['date'] = data.get('date')
    if data.get('metric_type'):
        context['metric_type'] = data.get('metric_type')
    if data.get('notes'):
        context['notes'] = data.get('notes')
    
    response = ask_inventory_agent(query, context if context else None)
    return jsonify(response)


@app.route('/api/inventory/sustainability-report', methods=['POST'])
def inventory_sustainability_report():
    """
    Get comprehensive sustainability report for previous day operations.
    Includes: Food Waste, Energy per Order, Idle Capacity %, On-Time Orders %
    
    Request JSON:
    {
        "date": "2025-12-03" (optional, defaults to yesterday),
        "kitchen_id": "KITCHEN_001" (optional),
        "include_recommendations": true (optional, default true)
    }
    
    Response:
    {
        "success": true,
        "report_type": "Previous Day Sustainability Report",
        "metrics": {
            "food_waste": {...},
            "energy_per_order": {...},
            "idle_capacity": {...},
            "on_time_orders": {...}
        },
        "summary": {
            "overall_sustainability_score": 72.5,
            "key_insight": "...",
            "top_3_actions": [...],
            "financial_impact": {...}
        },
        "timestamp": "ISO timestamp"
    }
    """
    data = request.get_json() or {}
    
    # Prepare query for the sustainability report
    report_date = data.get('date') or 'yesterday'
    kitchen_filter = ""
    if data.get('kitchen_id'):
        kitchen_filter = f" for kitchen {data.get('kitchen_id')}"
    
    query = f"""Generate a comprehensive Previous Day Sustainability Report for {report_date}{kitchen_filter}.
    
Provide detailed analysis of these 4 metrics:
1. Food Waste (kg) - Target < 5kg: Compare actual vs target, identify root causes
2. Energy per Order (kWh) - Target < 0.8 kWh: Energy consumption analysis and efficiency
3. Idle Cooking Capacity (%) - Target < 20%: Equipment utilization and underutilization
4. On-Time Orders (%) - Target > 90%: Service speed and fulfillment performance

For each metric:
- Show actual value vs target
- Classify status: Needs Improvement, Close to Target, Above Ideal, Promo Potential
- Identify root causes and trends
- Provide specific, actionable recommendations
- Include financial impact (cost of waste, excess energy, etc.)

End with Executive Summary including overall sustainability score and top 3 actions."""
    
    context = {
        'date': report_date,
        'metric_type': 'all_sustainability_metrics'
    }
    if data.get('kitchen_id'):
        context['kitchen_id'] = data.get('kitchen_id')
    
    response = ask_inventory_agent(query, context)
    response['report_type'] = 'Previous Day Sustainability Report'
    response['report_date'] = report_date
    
    return jsonify(response)


@app.route('/api/inventory/store-sustainability', methods=['POST'])
def inventory_store_sustainability():
    """
    Get real-time store-level sustainability dashboard with operational levers.
    Shows current metrics and how menu mix, production schedule, and staffing 
    allocation impact sustainability metrics WITHIN THIS SHIFT.
    
    Request JSON:
    {
        "kitchen_id": "KITCHEN_001" (optional),
        "time_period": "today_so_far" or "last_2_hours" or "current_shift" (optional),
        "include_levers": true (optional, default true)
    }
    
    Response:
    {
        "success": true,
        "view_type": "Store-Level Sustainability Dashboard",
        "current_metrics": {
            "food_waste_kg_so_far": 3.2,
            "projected_daily_waste_kg": 6.8,
            "energy_per_order_so_far": 0.82,
            "idle_capacity_pct": 22.5,
            "on_time_orders_pct": 89.2
        },
        "operational_levers": {
            "menu_mix": {...},
            "production_schedule": {...},
            "staffing_allocation": {...}
        },
        "integrated_insights": {
            "key_finding": "...",
            "actions_for_manager_now": [...],
            "expected_outcomes": [...]
        },
        "timestamp": "ISO timestamp"
    }
    """
    data = request.get_json() or {}
    
    time_period = data.get('time_period', 'today_so_far')
    kitchen_filter = ""
    if data.get('kitchen_id'):
        kitchen_filter = f" for kitchen {data.get('kitchen_id')}"
    
    query = f"""Generate a Store-Level Sustainability Dashboard for {time_period}{kitchen_filter}.
    
Provide REAL-TIME insights showing:

1. CURRENT METRICS (TODAY SO FAR):
   - Food Waste (kg) and projected daily total
   - Energy per Order (kWh)
   - Idle Cooking Capacity (%)
   - On-Time Orders (%)

2. OPERATIONAL LEVERS (Real-time impact analysis):

   A) MENU MIX - Which items to promote/reduce TODAY?
      - Show top 3 waste items with highest waste % and promotion recommendations
      - Show top 3 best-selling items (low waste, high sell-through) to feature
      - Include urgency level (HIGH: implement now, MEDIUM: within 30 min, LOW: consider for later)
      - Quantify expected waste reduction if actions taken
   
   B) PRODUCTION SCHEDULE - When/how to produce for optimal waste & energy?
      - Hourly breakdown: produced vs sold vs waste vs energy consumption
      - Identify peak efficiency hours and low-efficiency hours
      - Recommend production timing adjustments to reduce waste
      - Show forecast for next hour's demand
   
   C) STAFFING ALLOCATION - How does staffing impact performance?
      - Show staffing level by station (main kitchen, cold prep, dessert, etc.)
      - Current vs scheduled staff counts
      - Average prep times and on-time % by station
      - Recommendation: Add/reduce staff based on prep time and on-time metrics

3. INTEGRATED INSIGHTS:
   - Key finding: What's the #1 thing affecting sustainability RIGHT NOW?
   - Actions for manager: 3-5 immediate, specific, prioritized actions
   - Expected outcomes: What metrics will improve if actions taken?
   - Time frame: Which actions are HIGH urgency (now), MEDIUM (within 30 min), LOW (by end of shift)

Focus on SHIFT-LEVEL actions (not month-end reports). Manager should be able to act within minutes."""
    
    context = {
        'time_period': time_period,
        'include_levers': data.get('include_levers', True),
        'metric_type': 'real_time_operational'
    }
    if data.get('kitchen_id'):
        context['kitchen_id'] = data.get('kitchen_id')
    
    response = ask_inventory_agent(query, context)
    response['view_type'] = 'Store-Level Sustainability Dashboard'
    response['time_period'] = time_period
    
    return jsonify(response)


if __name__ == '__main__':
    # Initialize database on startup
    init_db()
    
    # Migration: Create order_items table if it doesn't exist (for existing databases)
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_items (
                id VARCHAR(255) PRIMARY KEY,
                order_id VARCHAR(255) NOT NULL,
                food_item_id VARCHAR(255) NOT NULL,
                food_name VARCHAR(255),
                category_name VARCHAR(255),
                quantity INT NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                notes TEXT,
                status VARCHAR(255) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (food_item_id) REFERENCES food_items(id)
            )
        ''')
        
        # Add status column if it doesn't exist (for existing tables)
        try:
            cursor.execute('ALTER TABLE order_items ADD COLUMN status VARCHAR(255) DEFAULT "pending"')
        except:
            pass  # Column already exists
        
        # Add updated_at column if it doesn't exist
        try:
            cursor.execute('ALTER TABLE order_items ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')
        except:
            pass  # Column already exists
        
        # Create kitchen_assignments table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS kitchen_assignments (
                id VARCHAR(255) PRIMARY KEY,
                item_id VARCHAR(255) NOT NULL,
                kitchen_id VARCHAR(255) NOT NULL,
                order_id VARCHAR(255) NOT NULL,
                status VARCHAR(255) DEFAULT 'pending',
                started TINYINT DEFAULT 0,
                completed TINYINT DEFAULT 0,
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (item_id) REFERENCES order_items(id),
                FOREIGN KEY (kitchen_id) REFERENCES kitchens(id),
                FOREIGN KEY (order_id) REFERENCES orders(id),
                UNIQUE(item_id, kitchen_id, order_id)
            )
        ''')
        
        # Add started and completed columns if they don't exist
        cursor = conn.cursor()
        try:
            cursor.execute("ALTER TABLE kitchen_assignments ADD COLUMN started TINYINT DEFAULT 0")
            print("✓ Added 'started' column to kitchen_assignments")
        except Exception as e:
            if "Duplicate column" not in str(e):
                print(f"Note: started column: {e}")
        
        try:
            cursor.execute("ALTER TABLE kitchen_assignments ADD COLUMN completed TINYINT DEFAULT 0")
            print("✓ Added 'completed' column to kitchen_assignments")
        except Exception as e:
            if "Duplicate column" not in str(e):
                print(f"Note: completed column: {e}")
        
        conn.commit()
        conn.close()
        print("✓ Database migration completed")
    except Exception as e:
        print(f"✓ Migration check: {e}")
    
    # Start Order Monitor if available
    print("🔍 Checking Order Monitor availability...")
    print(f"   start_order_monitor function: {start_order_monitor}")
    
    if start_order_monitor:
        try:
            print("🚀 Starting Order Monitor...")
            start_order_monitor()
            print("✓ Order Monitor started successfully")
        except Exception as e:
            print(f"❌ Could not start Order Monitor: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("⚠️  Order Monitor not available - import may have failed")
    
    print(f"\n{'='*60}")
    print("🌐 Starting Flask application on port 5100...")
    print(f"{'='*60}\n")
    
    app.run(debug=True, host='0.0.0.0', port=5100)
