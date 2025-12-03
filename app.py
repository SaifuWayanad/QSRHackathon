from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import sqlite3
import json
import uuid
from datetime import datetime
import os

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

# Import Order Monitor
try:
    from Agents.order_monitor import start_order_monitor, stop_order_monitor, get_today_orders_count, get_today_summary
except ImportError:
    print("⚠️  Order Monitor not available (optional)")
    start_order_monitor = None
    stop_order_monitor = None
    get_today_orders_count = None
    get_today_summary = None

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'

# SQLite database setup
DB_PATH = "my_db.db"

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database with all tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS areas (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'active',
            tables_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'active',
            items_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS kitchens (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            location TEXT,
            description TEXT,
            status TEXT DEFAULT 'active',
            items_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS food_items (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category_id TEXT NOT NULL,
            category_name TEXT,
            kitchen_id TEXT NOT NULL,
            kitchen_name TEXT,
            price REAL,
            description TEXT,
            specifications TEXT,
            status TEXT DEFAULT 'available',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id),
            FOREIGN KEY (kitchen_id) REFERENCES kitchens(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tables (
            id TEXT PRIMARY KEY,
            number INTEGER NOT NULL,
            area_id TEXT NOT NULL,
            area_name TEXT,
            capacity INTEGER,
            status TEXT DEFAULT 'available',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (area_id) REFERENCES areas(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_types (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            order_number TEXT UNIQUE,
            table_id TEXT,
            table_number TEXT,
            order_type_id TEXT,
            order_type_name TEXT,
            customer_name TEXT,
            items_count INTEGER DEFAULT 0,
            total_amount REAL DEFAULT 0,
            status TEXT DEFAULT 'pending',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (table_id) REFERENCES tables(id),
            FOREIGN KEY (order_type_id) REFERENCES order_types(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL,
            food_item_id TEXT NOT NULL,
            food_name TEXT,
            category_name TEXT,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (food_item_id) REFERENCES food_items(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_production (
            id TEXT PRIMARY KEY,
            food_id TEXT NOT NULL,
            food_name TEXT,
            category_name TEXT,
            date DATE NOT NULL,
            planned_quantity INTEGER,
            produced INTEGER DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (food_id) REFERENCES food_items(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS appliances (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            model TEXT,
            serial_number TEXT,
            description TEXT,
            status TEXT DEFAULT 'active',
            purchase_date DATE,
            last_maintenance DATE,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS kitchen_appliances (
            id TEXT PRIMARY KEY,
            kitchen_id TEXT NOT NULL,
            appliance_id TEXT NOT NULL,
            quantity INTEGER DEFAULT 1,
            location TEXT,
            status TEXT DEFAULT 'active',
            assigned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (kitchen_id) REFERENCES kitchens(id),
            FOREIGN KEY (appliance_id) REFERENCES appliances(id),
            UNIQUE(kitchen_id, appliance_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS iot_devices (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            device_type TEXT NOT NULL,
            device_id TEXT UNIQUE,
            location TEXT,
            kitchen_id TEXT,
            description TEXT,
            status TEXT DEFAULT 'active',
            battery_level INTEGER,
            signal_strength INTEGER,
            last_sync TIMESTAMP,
            ip_address TEXT,
            mac_address TEXT,
            firmware_version TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (kitchen_id) REFERENCES kitchens(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS staff (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            phone TEXT,
            position TEXT NOT NULL,
            department TEXT,
            kitchen_id TEXT,
            hire_date DATE,
            date_of_birth DATE,
            address TEXT,
            city TEXT,
            state TEXT,
            postal_code TEXT,
            emergency_contact_name TEXT,
            emergency_contact_phone TEXT,
            status TEXT DEFAULT 'active',
            salary_type TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (kitchen_id) REFERENCES kitchens(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS staff_kitchen_requests (
            id TEXT PRIMARY KEY,
            staff_id TEXT NOT NULL,
            staff_name TEXT,
            kitchen_id TEXT NOT NULL,
            kitchen_name TEXT,
            position TEXT,
            request_reason TEXT,
            requested_start_date DATE,
            status TEXT DEFAULT 'pending',
            approval_status TEXT DEFAULT 'pending',
            approved_by TEXT,
            approval_notes TEXT,
            approval_date TIMESTAMP,
            rejection_reason TEXT,
            requested_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (staff_id) REFERENCES staff(id),
            FOREIGN KEY (kitchen_id) REFERENCES kitchens(id),
            UNIQUE(staff_id, kitchen_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS staff_kitchen_assignments (
            id TEXT PRIMARY KEY,
            staff_id TEXT NOT NULL,
            staff_name TEXT,
            kitchen_id TEXT NOT NULL,
            kitchen_name TEXT,
            position TEXT,
            request_id TEXT,
            assigned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_date DATE,
            status TEXT DEFAULT 'active',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (staff_id) REFERENCES staff(id),
            FOREIGN KEY (kitchen_id) REFERENCES kitchens(id),
            FOREIGN KEY (request_id) REFERENCES staff_kitchen_requests(id),
            UNIQUE(staff_id, kitchen_id)
        )
    ''')
    
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
            'INSERT INTO categories (id, name, description, status) VALUES (?, ?, ?, ?)',
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
    conn.execute('DELETE FROM categories WHERE id = ?', (category_id,))
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
            'INSERT INTO kitchens (id, name, location, description, status) VALUES (?, ?, ?, ?, ?)',
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
    conn.execute('DELETE FROM kitchens WHERE id = ?', (kitchen_id,))
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
        kitchen_id = data.get('kitchen_id')
        
        if not kitchen_id:
            conn.close()
            return jsonify({'error': 'Kitchen assignment is mandatory!', 'success': False}), 400
        
        # Get category name
        cat_row = conn.execute('SELECT name FROM categories WHERE id = ?', (category_id,)).fetchone()
        category_name = cat_row['name'] if cat_row else 'Unknown'
        
        # Get kitchen name
        kitchen_row = conn.execute('SELECT name FROM kitchens WHERE id = ?', (kitchen_id,)).fetchone()
        if not kitchen_row:
            conn.close()
            return jsonify({'error': 'Kitchen not found!', 'success': False}), 404
        
        kitchen_name = kitchen_row['name']
        
        # Create food item
        conn.execute(
            '''INSERT INTO food_items (id, name, category_id, category_name, kitchen_id, kitchen_name, 
               price, description, specifications, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (food_id, data.get('name'), category_id, category_name, kitchen_id, kitchen_name,
             data.get('price'), data.get('description', ''), data.get('specifications', ''),
             data.get('status', 'available'))
        )
        
        # Update category items_count
        conn.execute('UPDATE categories SET items_count = items_count + 1 WHERE id = ?', (category_id,))
        
        # Update kitchen items_count
        conn.execute('UPDATE kitchens SET items_count = items_count + 1 WHERE id = ?', (kitchen_id,))
        
        conn.commit()
        conn.close()
        
        food_item = {
            'id': food_id,
            'name': data.get('name'),
            'category_id': category_id,
            'category_name': category_name,
            'kitchen_id': kitchen_id,
            'kitchen_name': kitchen_name,
            'price': data.get('price'),
            'description': data.get('description', ''),
            'specifications': data.get('specifications', ''),
            'status': data.get('status', 'available')
        }
        return jsonify({'success': True, 'food_item': food_item})
    
    # GET all food items
    cursor = conn.execute('SELECT * FROM food_items')
    food_items_list = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({'food_items': food_items_list})

@app.route('/api/food-items/<food_id>', methods=['DELETE'])
def delete_food_item(food_id):
    conn = get_db_connection()
    
    # Get food item details
    food_row = conn.execute('SELECT * FROM food_items WHERE id = ?', (food_id,)).fetchone()
    
    if food_row:
        category_id = food_row['category_id']
        kitchen_id = food_row['kitchen_id']
        
        conn.execute('UPDATE categories SET items_count = MAX(0, items_count - 1) WHERE id = ?', (category_id,))
        conn.execute('UPDATE kitchens SET items_count = MAX(0, items_count - 1) WHERE id = ?', (kitchen_id,))
    
    conn.execute('DELETE FROM food_items WHERE id = ?', (food_id,))
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
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
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
    
    cursor = conn.execute('SELECT * FROM daily_production WHERE date = ?', (date,))
    production_items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({'production_items': production_items, 'date': date})

@app.route('/api/daily-production/<production_id>', methods=['PUT', 'DELETE'])
def update_delete_production(production_id):
    conn = get_db_connection()
    
    if request.method == 'PUT':
        data = request.get_json()
        prod_row = conn.execute('SELECT * FROM daily_production WHERE id = ?', (production_id,)).fetchone()
        
        if prod_row:
            conn.execute(
                'UPDATE daily_production SET produced = ? WHERE id = ?',
                (data.get('produced', prod_row['produced']), production_id)
            )
            conn.commit()
            
            updated = conn.execute('SELECT * FROM daily_production WHERE id = ?', (production_id,)).fetchone()
            conn.close()
            return jsonify({'success': True, 'production_item': dict(updated)})
        
        conn.close()
        return jsonify({'error': 'Production item not found'}), 404
    
    # DELETE
    conn.execute('DELETE FROM daily_production WHERE id = ?', (production_id,))
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
            'INSERT INTO areas (id, name, description, status) VALUES (?, ?, ?, ?)',
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
    conn.execute('DELETE FROM areas WHERE id = ?', (area_id,))
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
        area_row = conn.execute('SELECT name FROM areas WHERE id = ?', (area_id,)).fetchone()
        area_name = area_row['name'] if area_row else ''
        
        conn.execute(
            'INSERT INTO tables (id, number, area_id, area_name, capacity, status) VALUES (?, ?, ?, ?, ?, ?)',
            (table_id, data.get('number'), area_id, area_name, data.get('capacity'), data.get('status', 'available'))
        )
        
        conn.execute('UPDATE areas SET tables_count = tables_count + 1 WHERE id = ?', (area_id,))
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
    table_row = conn.execute('SELECT area_id FROM tables WHERE id = ?', (table_id,)).fetchone()
    
    if table_row:
        area_id = table_row['area_id']
        conn.execute('UPDATE areas SET tables_count = MAX(0, tables_count - 1) WHERE id = ?', (area_id,))
    
    conn.execute('DELETE FROM tables WHERE id = ?', (table_id,))
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
            'INSERT INTO order_types (id, name, description, status) VALUES (?, ?, ?, ?)',
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
    conn.execute('DELETE FROM order_types WHERE id = ?', (order_type_id,))
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
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
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
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (item_id, order_id, item.get('food_item_id', ''), item.get('food_name', ''),
                     item.get('category_name', ''), item.get('quantity', 1), item.get('price', 0),
                     item.get('notes', ''), now)
                )
            except sqlite3.IntegrityError as e:
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
            'items': [dict(i) if isinstance(i, sqlite3.Row) else i for i in data.get('items', [])]
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
        conn.execute('DELETE FROM orders WHERE id = ?', (order_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    if request.method == 'PUT':
        data = request.get_json()
        now = datetime.now().isoformat()
        
        order_row = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
        if order_row:
            conn.execute(
                '''UPDATE orders SET order_number = ?, table_id = ?, table_number = ?, 
                   order_type_id = ?, order_type_name = ?, customer_name = ?, items_count = ?, 
                   total_amount = ?, status = ?, notes = ?, updated_at = ?
                   WHERE id = ?''',
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
            
            updated = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
            updated_dict = dict(updated)
            # Fetch order items
            items_rows = conn.execute('SELECT * FROM order_items WHERE order_id = ?', (order_id,)).fetchall()
            updated_dict['items'] = [dict(row) for row in items_rows]
            conn.close()
            return jsonify({'success': True, 'order': updated_dict})
        
        conn.close()
        return jsonify({'error': 'Order not found'}), 404
    
    # GET single order
    order_row = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    if order_row:
        order_dict = dict(order_row)
        # Fetch order items
        items_rows = conn.execute('SELECT * FROM order_items WHERE order_id = ?', (order_id,)).fetchall()
        order_dict['items'] = [dict(row) for row in items_rows]
        conn.close()
        return jsonify({'success': True, 'order': order_dict})
    
    conn.close()
    return jsonify({'success': False, 'error': 'Order not found'}), 404

@app.route('/api/orders/<order_id>/items', methods=['GET'])
def order_items(order_id):
    conn = get_db_connection()
    items_rows = conn.execute('SELECT * FROM order_items WHERE order_id = ?', (order_id,)).fetchall()
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
    
    return jsonify({
        'success': False,
        'error': 'Order monitor not available'
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
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
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
        conn.execute('DELETE FROM appliances WHERE id = ?', (appliance_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    if request.method == 'PUT':
        data = request.get_json()
        appliance_row = conn.execute('SELECT * FROM appliances WHERE id = ?', (appliance_id,)).fetchone()
        
        if appliance_row:
            conn.execute(
                '''UPDATE appliances SET name = ?, type = ?, model = ?, serial_number = ?, 
                   description = ?, status = ?, purchase_date = ?, last_maintenance = ?, notes = ?
                   WHERE id = ?''',
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
            
            updated = conn.execute('SELECT * FROM appliances WHERE id = ?', (appliance_id,)).fetchone()
            conn.close()
            return jsonify({'success': True, 'appliance': dict(updated)})
        
        conn.close()
        return jsonify({'error': 'Appliance not found'}), 404
    
    # GET single appliance
    appliance_row = conn.execute('SELECT * FROM appliances WHERE id = ?', (appliance_id,)).fetchone()
    conn.close()
    
    if appliance_row:
        return jsonify({'appliance': dict(appliance_row)})
    return jsonify({'error': 'Appliance not found'}), 404


# Kitchen Appliances Mapping API
@app.route('/api/kitchens/<kitchen_id>/appliances', methods=['GET', 'POST'])
def kitchen_appliances(kitchen_id):
    conn = get_db_connection()
    
    # Verify kitchen exists
    kitchen_row = conn.execute('SELECT id FROM kitchens WHERE id = ?', (kitchen_id,)).fetchone()
    if not kitchen_row:
        conn.close()
        return jsonify({'error': 'Kitchen not found'}), 404
    
    if request.method == 'POST':
        data = request.get_json()
        appliance_id = data.get('appliance_id')
        quantity = data.get('quantity', 1)
        location = data.get('location', '')
        
        # Verify appliance exists
        appliance_row = conn.execute('SELECT name FROM appliances WHERE id = ?', (appliance_id,)).fetchone()
        if not appliance_row:
            conn.close()
            return jsonify({'error': 'Appliance not found'}), 404
        
        # Check if already exists
        existing = conn.execute(
            'SELECT id FROM kitchen_appliances WHERE kitchen_id = ? AND appliance_id = ?',
            (kitchen_id, appliance_id)
        ).fetchone()
        
        if existing:
            conn.close()
            return jsonify({'error': 'Appliance already assigned to this kitchen'}), 400
        
        mapping_id = str(uuid.uuid4())
        conn.execute(
            '''INSERT INTO kitchen_appliances (id, kitchen_id, appliance_id, quantity, location, status)
               VALUES (?, ?, ?, ?, ?, ?)''',
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
           WHERE ka.kitchen_id = ?''',
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
            'SELECT id FROM kitchen_appliances WHERE id = ? AND kitchen_id = ?',
            (mapping_id, kitchen_id)
        ).fetchone()
        
        if not mapping_row:
            conn.close()
            return jsonify({'error': 'Mapping not found'}), 404
        
        conn.execute('DELETE FROM kitchen_appliances WHERE id = ?', (mapping_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    if request.method == 'PUT':
        data = request.get_json()
        mapping_row = conn.execute(
            'SELECT * FROM kitchen_appliances WHERE id = ? AND kitchen_id = ?',
            (mapping_id, kitchen_id)
        ).fetchone()
        
        if mapping_row:
            conn.execute(
                '''UPDATE kitchen_appliances SET quantity = ?, location = ?, status = ?
                   WHERE id = ?''',
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
                   WHERE ka.id = ?''',
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
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
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
        conn.execute('DELETE FROM iot_devices WHERE id = ?', (device_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    if request.method == 'PUT':
        data = request.get_json()
        device_row = conn.execute('SELECT * FROM iot_devices WHERE id = ?', (device_id,)).fetchone()
        
        if device_row:
            conn.execute(
                '''UPDATE iot_devices SET name = ?, device_type = ?, device_id = ?, location = ?, 
                   kitchen_id = ?, description = ?, status = ?, battery_level = ?, signal_strength = ?,
                   ip_address = ?, mac_address = ?, firmware_version = ?, notes = ?, last_sync = ?
                   WHERE id = ?''',
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
            
            updated = conn.execute('SELECT * FROM iot_devices WHERE id = ?', (device_id,)).fetchone()
            conn.close()
            return jsonify({'success': True, 'device': dict(updated)})
        
        conn.close()
        return jsonify({'error': 'Device not found'}), 404
    
    # GET single device
    device_row = conn.execute('SELECT * FROM iot_devices WHERE id = ?', (device_id,)).fetchone()
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
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
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
        conn.execute('DELETE FROM staff WHERE id = ?', (staff_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    if request.method == 'PUT':
        data = request.get_json()
        staff_row = conn.execute('SELECT * FROM staff WHERE id = ?', (staff_id,)).fetchone()
        
        if staff_row:
            conn.execute(
                '''UPDATE staff SET name = ?, email = ?, phone = ?, position = ?, 
                   department = ?, kitchen_id = ?, hire_date = ?, date_of_birth = ?, 
                   address = ?, city = ?, state = ?, postal_code = ?, 
                   emergency_contact_name = ?, emergency_contact_phone = ?, 
                   status = ?, salary_type = ?, notes = ?
                   WHERE id = ?''',
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
            
            updated = conn.execute('SELECT * FROM staff WHERE id = ?', (staff_id,)).fetchone()
            conn.close()
            return jsonify({'success': True, 'staff': dict(updated)})
        
        conn.close()
        return jsonify({'error': 'Staff member not found'}), 404
    
    # GET single staff
    staff_row = conn.execute('SELECT * FROM staff WHERE id = ?', (staff_id,)).fetchone()
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
        staff_row = conn.execute('SELECT name FROM staff WHERE id = ?', (data.get('staff_id'),)).fetchone()
        kitchen_row = conn.execute('SELECT name FROM kitchens WHERE id = ?', (data.get('kitchen_id'),)).fetchone()
        
        if not staff_row or not kitchen_row:
            conn.close()
            return jsonify({'error': 'Staff or kitchen not found'}), 404
        
        conn.execute(
            '''INSERT INTO staff_kitchen_requests 
               (id, staff_id, staff_name, kitchen_id, kitchen_name, position, request_reason, 
                requested_start_date, status, approval_status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
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
        conn.execute('DELETE FROM staff_kitchen_requests WHERE id = ?', (req_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    if request.method == 'PUT':
        data = request.get_json()
        req_row = conn.execute('SELECT * FROM staff_kitchen_requests WHERE id = ?', (req_id,)).fetchone()
        
        if req_row:
            conn.execute(
                '''UPDATE staff_kitchen_requests SET position = ?, request_reason = ?, 
                   requested_start_date = ?, updated_at = ?
                   WHERE id = ?''',
                (data.get('position', req_row['position']),
                 data.get('request_reason', req_row['request_reason']),
                 data.get('requested_start_date', req_row['requested_start_date']),
                 datetime.now(),
                 req_id)
            )
            conn.commit()
            
            updated = conn.execute('SELECT * FROM staff_kitchen_requests WHERE id = ?', (req_id,)).fetchone()
            conn.close()
            return jsonify({'success': True, 'request': dict(updated)})
        
        conn.close()
        return jsonify({'error': 'Request not found'}), 404
    
    # GET single request
    req_row = conn.execute('SELECT * FROM staff_kitchen_requests WHERE id = ?', (req_id,)).fetchone()
    conn.close()
    
    if req_row:
        return jsonify({'request': dict(req_row)})
    return jsonify({'error': 'Request not found'}), 404


# Manager Approval Endpoint
@app.route('/api/staff-kitchen-requests/<req_id>/approve', methods=['POST'])
def approve_staff_kitchen_request(req_id):
    conn = get_db_connection()
    data = request.get_json()
    
    req_row = conn.execute('SELECT * FROM staff_kitchen_requests WHERE id = ?', (req_id,)).fetchone()
    
    if not req_row:
        conn.close()
        return jsonify({'error': 'Request not found'}), 404
    
    # Update request status
    conn.execute(
        '''UPDATE staff_kitchen_requests SET approval_status = ?, approved_by = ?, 
           approval_notes = ?, approval_date = ?, updated_at = ?
           WHERE id = ?''',
        ('approved', data.get('approved_by', 'manager'), data.get('approval_notes', ''),
         datetime.now(), datetime.now(), req_id)
    )
    
    # Create assignment
    assignment_id = str(uuid.uuid4())
    conn.execute(
        '''INSERT INTO staff_kitchen_assignments 
           (id, staff_id, staff_name, kitchen_id, kitchen_name, position, request_id, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (assignment_id, req_row['staff_id'], req_row['staff_name'],
         req_row['kitchen_id'], req_row['kitchen_name'], req_row['position'],
         req_id, 'active')
    )
    
    # Update staff's kitchen_id
    conn.execute('UPDATE staff SET kitchen_id = ? WHERE id = ?', 
                (req_row['kitchen_id'], req_row['staff_id']))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Request approved and assignment created'})


# Manager Rejection Endpoint
@app.route('/api/staff-kitchen-requests/<req_id>/reject', methods=['POST'])
def reject_staff_kitchen_request(req_id):
    conn = get_db_connection()
    data = request.get_json()
    
    req_row = conn.execute('SELECT * FROM staff_kitchen_requests WHERE id = ?', (req_id,)).fetchone()
    
    if not req_row:
        conn.close()
        return jsonify({'error': 'Request not found'}), 404
    
    # Update request status
    conn.execute(
        '''UPDATE staff_kitchen_requests SET approval_status = ?, approved_by = ?, 
           rejection_reason = ?, approval_date = ?, updated_at = ?
           WHERE id = ?''',
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
        
        staff_row = conn.execute('SELECT name FROM staff WHERE id = ?', (data.get('staff_id'),)).fetchone()
        kitchen_row = conn.execute('SELECT name FROM kitchens WHERE id = ?', (data.get('kitchen_id'),)).fetchone()
        
        if not staff_row or not kitchen_row:
            conn.close()
            return jsonify({'error': 'Staff or kitchen not found'}), 404
        
        conn.execute(
            '''INSERT INTO staff_kitchen_assignments 
               (id, staff_id, staff_name, kitchen_id, kitchen_name, position, status)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (assignment_id, data.get('staff_id'), staff_row['name'],
             data.get('kitchen_id'), kitchen_row['name'], data.get('position'),
             data.get('status', 'active'))
        )
        
        # Update staff's kitchen_id
        conn.execute('UPDATE staff SET kitchen_id = ? WHERE id = ?',
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
        assign_row = conn.execute('SELECT * FROM staff_kitchen_assignments WHERE id = ?', (assign_id,)).fetchone()
        if assign_row:
            conn.execute('UPDATE staff_kitchen_assignments SET status = ? WHERE id = ?', 
                        ('inactive', assign_id))
            # Optionally remove kitchen_id from staff if no other active assignment
            conn.execute('UPDATE staff SET kitchen_id = NULL WHERE id = ? AND id NOT IN (SELECT staff_id FROM staff_kitchen_assignments WHERE status = "active")',
                        (assign_row['staff_id'],))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    if request.method == 'PUT':
        data = request.get_json()
        assign_row = conn.execute('SELECT * FROM staff_kitchen_assignments WHERE id = ?', (assign_id,)).fetchone()
        
        if assign_row:
            conn.execute(
                '''UPDATE staff_kitchen_assignments SET position = ?, status = ?, 
                   end_date = ?, notes = ?
                   WHERE id = ?''',
                (data.get('position', assign_row['position']),
                 data.get('status', assign_row['status']),
                 data.get('end_date', assign_row['end_date']),
                 data.get('notes', assign_row['notes']),
                 assign_id)
            )
            conn.commit()
            
            updated = conn.execute('SELECT * FROM staff_kitchen_assignments WHERE id = ?', (assign_id,)).fetchone()
            conn.close()
            return jsonify({'success': True, 'assignment': dict(updated)})
        
        conn.close()
        return jsonify({'error': 'Assignment not found'}), 404
    
    # GET single assignment
    assign_row = conn.execute('SELECT * FROM staff_kitchen_assignments WHERE id = ?', (assign_id,)).fetchone()
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


if __name__ == '__main__':
    # Initialize database on startup
    if not os.path.exists(DB_PATH):
        init_db()
    else:
        # Ensure tables exist even if DB exists
        init_db()
    
    # Migration: Create order_items table if it doesn't exist (for existing databases)
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_items (
                id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                food_item_id TEXT NOT NULL,
                food_name TEXT,
                category_name TEXT,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                notes TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (food_item_id) REFERENCES food_items(id)
            )
        ''')
        
        # Add status column if it doesn't exist (for existing tables)
        try:
            cursor.execute('ALTER TABLE order_items ADD COLUMN status TEXT DEFAULT "pending"')
        except:
            pass  # Column already exists
        
        # Add updated_at column if it doesn't exist
        try:
            cursor.execute('ALTER TABLE order_items ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        except:
            pass  # Column already exists
        
        # Create kitchen_assignments table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS kitchen_assignments (
                id TEXT PRIMARY KEY,
                item_id TEXT NOT NULL,
                kitchen_id TEXT NOT NULL,
                order_id TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (item_id) REFERENCES order_items(id),
                FOREIGN KEY (kitchen_id) REFERENCES kitchens(id),
                FOREIGN KEY (order_id) REFERENCES orders(id),
                UNIQUE(item_id, kitchen_id, order_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✓ Database migration completed")
    except Exception as e:
        print(f"✓ Migration check: {e}")
    
    # Start Order Monitor if available
    if start_order_monitor:
        try:
            start_order_monitor()
            print("✓ Order Monitor started (runs every 5 seconds)")
        except Exception as e:
            print(f"⚠️  Could not start Order Monitor: {e}")
    
    app.run(debug=True, host='0.0.0.0', port=5100)# ============================================================================
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
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
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

@app.route('/api/kitchens', methods=['GET'])
def get_kitchens():
    """Get all kitchen information"""
    kitchens = KitchenManager.get_all_kitchens()
    return jsonify({'kitchens': kitchens})

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

@app.route('/api/orders/<order_id>/assign-kitchens', methods=['POST'])
def assign_order_to_kitchens(order_id):
    """Assign order items to specific kitchens"""
    conn = get_db_connection()
    
    # Get order
    order_row = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
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
                    WHERE id = ?
                ''', (item_id,))
                
                # Store kitchen assignment
                assignment_id = str(uuid.uuid4())
                conn.execute('''
                    INSERT OR IGNORE INTO kitchen_assignments (id, item_id, kitchen_id, order_id, status)
                    VALUES (?, ?, ?, ?, 'pending')
                ''', (assignment_id, item_id, kitchen_id, order_id))
        
        conn.commit()
    
    # Get updated items
    items_rows = conn.execute('SELECT * FROM order_items WHERE order_id = ?', (order_id,)).fetchall()
    items = [dict(row) for row in items_rows]
    order_data['items'] = items
    
    # Get kitchen assignments for this order
    assignment_rows = conn.execute('''
        SELECT DISTINCT ka.kitchen_id, k.name, k.icon
        FROM kitchen_assignments ka
        JOIN kitchens k ON ka.kitchen_id = k.id
        WHERE ka.order_id = ?
    ''', (order_id,)).fetchall()
    
    kitchen_assignments = {}
    for row in assignment_rows:
        kitchen_id = row[0]
        kitchen_name = row[1]
        kitchen_icon = row[2]
        
        items_for_kitchen = conn.execute('''
            SELECT oi.* FROM order_items oi
            JOIN kitchen_assignments ka ON oi.id = ka.item_id
            WHERE ka.kitchen_id = ? AND oi.order_id = ?
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
                    VALUES (?, ?, ?, ?, 'pending')
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
            SET status = ?, updated_at = ?
            WHERE id = ?
        ''', (new_status, datetime.now().isoformat(), item_id))
        
        conn.commit()
        
        # Check if all items are completed
        cursor = conn.execute('''
            SELECT COUNT(*) as total, 
                   SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed
            FROM order_items 
            WHERE order_id = ?
        ''', (order_id,)).fetchone()
        
        total = cursor['total']
        completed = cursor['completed'] or 0
        
        # Update order status if all items completed
        if total == completed:
            conn.execute('UPDATE orders SET status = ? WHERE id = ?', ('completed', order_id))
            conn.commit()
        
        conn.close()
        return jsonify({'success': True, 'item_id': item_id, 'status': new_status})
    
    # GET - retrieve all items and their status
    items = conn.execute('SELECT * FROM order_items WHERE order_id = ?', (order_id,)).fetchall()
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
        SET status = ?, updated_at = ?
        WHERE id = ?
    ''', (new_status, datetime.now().isoformat(), item_id))
    
    conn.commit()
    
    # Get updated item
    item = conn.execute('SELECT * FROM order_items WHERE id = ?', (item_id,)).fetchone()
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
        order = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
        
        if order:
            context['order'] = {
                'id': order['id'],
                'table_name': order['table_name'],
                'status': order['status'],
                'items_count': len(conn.execute('SELECT * FROM order_items WHERE order_id = ?', (order_id,)).fetchall())
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