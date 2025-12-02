from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import redis
import json
import uuid
import sqlite3

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'

# Initialize Redis connection
try:
    conn = sqlite3.connect("my_database.db")
    
    redis_client = redis.Redis(
        host='localhost',
        port=6379,
        db=0,
        decode_responses=True
    )
    redis_client.ping()
    print("✓ Connected to Redis successfully")
except redis.ConnectionError:
    print("✗ Redis connection failed. Make sure Redis is running.")
    redis_client = None

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

# Redis API endpoints
@app.route('/api/redis/set', methods=['POST'])
def redis_set():
    if not redis_client:
        return jsonify({'error': 'Redis not connected'}), 500
    
    data = request.get_json()
    key = data.get('key')
    value = data.get('value')
    
    if not key or value is None:
        return jsonify({'error': 'Key and value required'}), 400
    
    redis_client.set(key, json.dumps(value))
    return jsonify({'success': True, 'message': f'Key "{key}" set successfully'})

@app.route('/api/redis/get/<key>', methods=['GET'])
def redis_get(key):
    if not redis_client:
        return jsonify({'error': 'Redis not connected'}), 500
    
    value = redis_client.get(key)
    if value is None:
        return jsonify({'error': 'Key not found'}), 404
    
    try:
        value = json.loads(value)
    except:
        pass
    
    return jsonify({'key': key, 'value': value})

@app.route('/api/redis/delete/<key>', methods=['DELETE'])
def redis_delete(key):
    if not redis_client:
        return jsonify({'error': 'Redis not connected'}), 500
    
    result = redis_client.delete(key)
    if result:
        return jsonify({'success': True, 'message': f'Key "{key}" deleted'})
    return jsonify({'error': 'Key not found'}), 404

@app.route('/api/redis/keys', methods=['GET'])
def redis_keys():
    if not redis_client:
        return jsonify({'error': 'Redis not connected'}), 500
    
    keys = redis_client.keys('*')
    return jsonify({'keys': keys, 'count': len(keys)})

# Menu Categories API
@app.route('/api/categories', methods=['GET', 'POST'])
def categories():
    if not redis_client:
        return jsonify({'error': 'Redis not connected'}), 500
    
    if request.method == 'POST':
        data = request.get_json()
        category_id = str(uuid.uuid4())
        category = {
            'id': category_id,
            'name': data.get('name'),
            'description': data.get('description', ''),
            'status': data.get('status', 'active'),
            'items_count': 0
        }
        redis_client.set(f'category:{category_id}', json.dumps(category))
        redis_client.sadd('categories', category_id)
        return jsonify({'success': True, 'category': category})
    
    # GET all categories
    category_ids = redis_client.smembers('categories')
    categories = []
    for cat_id in category_ids:
        cat_data = redis_client.get(f'category:{cat_id}')
        if cat_data:
            categories.append(json.loads(cat_data))
    
    return jsonify({'categories': categories})

@app.route('/api/categories/<category_id>', methods=['DELETE'])
def delete_category(category_id):
    if not redis_client:
        return jsonify({'error': 'Redis not connected'}), 500
    
    redis_client.delete(f'category:{category_id}')
    redis_client.srem('categories', category_id)
    return jsonify({'success': True})

# Kitchen API
@app.route('/api/kitchens', methods=['GET', 'POST'])
def kitchens():
    if not redis_client:
        return jsonify({'error': 'Redis not connected'}), 500
    
    if request.method == 'POST':
        data = request.get_json()
        kitchen_id = str(uuid.uuid4())
        kitchen = {
            'id': kitchen_id,
            'name': data.get('name'),
            'location': data.get('location', ''),
            'description': data.get('description', ''),
            'status': data.get('status', 'active'),
            'items_count': 0
        }
        redis_client.set(f'kitchen:{kitchen_id}', json.dumps(kitchen))
        redis_client.sadd('kitchens', kitchen_id)
        return jsonify({'success': True, 'kitchen': kitchen})
    
    # GET all kitchens
    kitchen_ids = redis_client.smembers('kitchens')
    kitchens = []
    for kitchen_id in kitchen_ids:
        kitchen_data = redis_client.get(f'kitchen:{kitchen_id}')
        if kitchen_data:
            kitchens.append(json.loads(kitchen_data))
    
    return jsonify({'kitchens': kitchens})

@app.route('/api/kitchens/<kitchen_id>', methods=['DELETE'])
def delete_kitchen(kitchen_id):
    if not redis_client:
        return jsonify({'error': 'Redis not connected'}), 500
    
    redis_client.delete(f'kitchen:{kitchen_id}')
    redis_client.srem('kitchens', kitchen_id)
    return jsonify({'success': True})

# Food Items API
@app.route('/api/food-items', methods=['GET', 'POST'])
def food_items():
    if not redis_client:
        return jsonify({'error': 'Redis not connected'}), 500
    
    if request.method == 'POST':
        data = request.get_json()
        food_id = str(uuid.uuid4())
        category_id = data.get('category_id')
        kitchen_id = data.get('kitchen_id')
        
        # Validate kitchen is provided (MANDATORY)
        if not kitchen_id:
            return jsonify({'error': 'Kitchen assignment is mandatory!', 'success': False}), 400
        
        # Get category name
        category_data = redis_client.get(f'category:{category_id}')
        category_name = 'Unknown'
        if category_data:
            category = json.loads(category_data)
            category_name = category['name']
            # Update items count
            category['items_count'] = category.get('items_count', 0) + 1
            redis_client.set(f'category:{category_id}', json.dumps(category))
        
        # Get kitchen name and update kitchen items count
        kitchen_data = redis_client.get(f'kitchen:{kitchen_id}')
        kitchen_name = 'Unknown'
        if kitchen_data:
            kitchen = json.loads(kitchen_data)
            kitchen_name = kitchen['name']
            kitchen['items_count'] = kitchen.get('items_count', 0) + 1
            redis_client.set(f'kitchen:{kitchen_id}', json.dumps(kitchen))
        else:
            return jsonify({'error': 'Kitchen not found!', 'success': False}), 404
        
        # Create food item with kitchen mapping
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
        
        # Store food item
        redis_client.set(f'food:{food_id}', json.dumps(food_item))
        redis_client.sadd('food_items', food_id)
        
        # Create mapping: Add food item to kitchen's foods list
        redis_client.sadd(f'kitchen:{kitchen_id}:foods', food_id)
        
        # Create reverse mapping: Add kitchen to food's kitchens
        redis_client.sadd(f'food:{food_id}:kitchens', kitchen_id)
        
        return jsonify({'success': True, 'food_item': food_item})
    
    # GET all food items
    food_ids = redis_client.smembers('food_items')
    food_items_list = []
    for food_id in food_ids:
        food_data = redis_client.get(f'food:{food_id}')
        if food_data:
            food_items_list.append(json.loads(food_data))
    
    return jsonify({'food_items': food_items_list})

@app.route('/api/food-items/<food_id>', methods=['DELETE'])
def delete_food_item(food_id):
    if not redis_client:
        return jsonify({'error': 'Redis not connected'}), 500
    
    # Get food item to update category and kitchen count
    food_data = redis_client.get(f'food:{food_id}')
    if food_data:
        food_item = json.loads(food_data)
        
        # Update category count
        category_id = food_item.get('category_id')
        if category_id:
            category_data = redis_client.get(f'category:{category_id}')
            if category_data:
                category = json.loads(category_data)
                category['items_count'] = max(0, category.get('items_count', 1) - 1)
                redis_client.set(f'category:{category_id}', json.dumps(category))
        
        # Update kitchen count
        kitchen_id = food_item.get('kitchen_id')
        if kitchen_id:
            kitchen_data = redis_client.get(f'kitchen:{kitchen_id}')
            if kitchen_data:
                kitchen = json.loads(kitchen_data)
                kitchen['items_count'] = max(0, kitchen.get('items_count', 1) - 1)
                redis_client.set(f'kitchen:{kitchen_id}', json.dumps(kitchen))
    
    redis_client.delete(f'food:{food_id}')
    redis_client.srem('food_items', food_id)
    return jsonify({'success': True})

# Daily Production API
@app.route('/api/daily-production', methods=['GET', 'POST'])
def daily_production():
    if not redis_client:
        return jsonify({'error': 'Redis not connected'}), 500
    
    if request.method == 'POST':
        data = request.get_json()
        production_id = str(uuid.uuid4())
        date = data.get('date')
        
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
        
        redis_client.set(f'production:{production_id}', json.dumps(production_item))
        redis_client.sadd(f'production_date:{date}', production_id)
        redis_client.sadd('all_productions', production_id)
        
        return jsonify({'success': True, 'production_item': production_item})
    
    # GET production items for a specific date
    date = request.args.get('date')
    if not date:
        from datetime import datetime
        date = datetime.now().strftime('%Y-%m-%d')
    
    production_ids = redis_client.smembers(f'production_date:{date}')
    production_items = []
    for prod_id in production_ids:
        prod_data = redis_client.get(f'production:{prod_id}')
        if prod_data:
            production_items.append(json.loads(prod_data))
    
    return jsonify({'production_items': production_items, 'date': date})

@app.route('/api/daily-production/<production_id>', methods=['PUT', 'DELETE'])
def update_delete_production(production_id):
    if not redis_client:
        return jsonify({'error': 'Redis not connected'}), 500
    
    if request.method == 'PUT':
        data = request.get_json()
        prod_data = redis_client.get(f'production:{production_id}')
        
        if prod_data:
            production = json.loads(prod_data)
            production['produced'] = data.get('produced', production['produced'])
            redis_client.set(f'production:{production_id}', json.dumps(production))
            return jsonify({'success': True, 'production_item': production})
        
        return jsonify({'error': 'Production item not found'}), 404
    
    # DELETE
    prod_data = redis_client.get(f'production:{production_id}')
    if prod_data:
        production = json.loads(prod_data)
        date = production.get('date')
        redis_client.srem(f'production_date:{date}', production_id)
    
    redis_client.delete(f'production:{production_id}')
    redis_client.srem('all_productions', production_id)
    return jsonify({'success': True})

# Areas API
@app.route('/api/areas', methods=['GET', 'POST'])
def areas():
    if not redis_client:
        return jsonify({'error': 'Redis not connected'}), 500
    
    if request.method == 'POST':
        data = request.get_json()
        area_id = str(uuid.uuid4())
        
        area = {
            'id': area_id,
            'name': data.get('name'),
            'description': data.get('description', ''),
            'status': data.get('status', 'active'),
            'tables_count': 0
        }
        redis_client.set(f'area:{area_id}', json.dumps(area))
        redis_client.sadd('areas', area_id)
        return jsonify({'success': True, 'area': area})
    
    # GET all areas
    area_ids = redis_client.smembers('areas')
    areas_list = []
    for area_id in area_ids:
        area_data = redis_client.get(f'area:{area_id}')
        if area_data:
            areas_list.append(json.loads(area_data))
    
    return jsonify({'areas': areas_list})

@app.route('/api/areas/<area_id>', methods=['DELETE'])
def delete_area(area_id):
    if not redis_client:
        return jsonify({'error': 'Redis not connected'}), 500
    
    redis_client.delete(f'area:{area_id}')
    redis_client.srem('areas', area_id)
    return jsonify({'success': True})

# Tables API
@app.route('/api/tables', methods=['GET', 'POST'])
def tables():
    if not redis_client:
        return jsonify({'error': 'Redis not connected'}), 500
    
    if request.method == 'POST':
        data = request.get_json()
        table_id = str(uuid.uuid4())
        area_id = data.get('area_id')
        
        # Update area's table count
        if area_id:
            area_data = redis_client.get(f'area:{area_id}')
            if area_data:
                area = json.loads(area_data)
                area['tables_count'] = area.get('tables_count', 0) + 1
                redis_client.set(f'area:{area_id}', json.dumps(area))
        
        table = {
            'id': table_id,
            'number': data.get('number'),
            'area_id': area_id,
            'area_name': data.get('area_name', ''),
            'capacity': data.get('capacity'),
            'status': data.get('status', 'available')
        }
        redis_client.set(f'table:{table_id}', json.dumps(table))
        redis_client.sadd('tables', table_id)
        redis_client.sadd(f'area:{area_id}:tables', table_id)
        return jsonify({'success': True, 'table': table})
    
    # GET all tables
    table_ids = redis_client.smembers('tables')
    tables_list = []
    for table_id in table_ids:
        table_data = redis_client.get(f'table:{table_id}')
        if table_data:
            tables_list.append(json.loads(table_data))
    
    return jsonify({'tables': tables_list})

@app.route('/api/tables/<table_id>', methods=['DELETE'])
def delete_table(table_id):
    if not redis_client:
        return jsonify({'error': 'Redis not connected'}), 500
    
    table_data = redis_client.get(f'table:{table_id}')
    if table_data:
        table = json.loads(table_data)
        area_id = table.get('area_id')
        
        # Update area's table count
        if area_id:
            area_data = redis_client.get(f'area:{area_id}')
            if area_data:
                area = json.loads(area_data)
                area['tables_count'] = max(0, area.get('tables_count', 1) - 1)
                redis_client.set(f'area:{area_id}', json.dumps(area))
        
        redis_client.srem(f'area:{area_id}:tables', table_id)
    
    redis_client.delete(f'table:{table_id}')
    redis_client.srem('tables', table_id)
    return jsonify({'success': True})

# Order Types API
@app.route('/api/order-types', methods=['GET', 'POST'])
def order_types():
    if not redis_client:
        return jsonify({'error': 'Redis not connected'}), 500
    
    if request.method == 'POST':
        data = request.get_json()
        order_type_id = str(uuid.uuid4())
        
        order_type = {
            'id': order_type_id,
            'name': data.get('name'),
            'description': data.get('description', ''),
            'status': data.get('status', 'active')
        }
        redis_client.set(f'order_type:{order_type_id}', json.dumps(order_type))
        redis_client.sadd('order_types', order_type_id)
        return jsonify({'success': True, 'order_type': order_type})
    
    # GET all order types
    order_type_ids = redis_client.smembers('order_types')
    order_types_list = []
    for order_type_id in order_type_ids:
        order_type_data = redis_client.get(f'order_type:{order_type_id}')
        if order_type_data:
            order_types_list.append(json.loads(order_type_data))
    
    return jsonify({'order_types': order_types_list})

@app.route('/api/order-types/<order_type_id>', methods=['DELETE'])
def delete_order_type(order_type_id):
    if not redis_client:
        return jsonify({'error': 'Redis not connected'}), 500
    
    redis_client.delete(f'order_type:{order_type_id}')
    redis_client.srem('order_types', order_type_id)
    return jsonify({'success': True})

# Orders API
@app.route('/api/orders', methods=['GET', 'POST'])
def orders():
    if not redis_client:
        return jsonify({'error': 'Redis not connected'}), 500
    
    if request.method == 'POST':
        data = request.get_json()
        order_id = str(uuid.uuid4())
        
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
            'created_at': data.get('created_at', ''),
            'updated_at': data.get('updated_at', '')
        }
        redis_client.set(f'order:{order_id}', json.dumps(order))
        redis_client.sadd('orders', order_id)
        return jsonify({'success': True, 'order': order})
    
    # GET all orders
    order_ids = redis_client.smembers('orders')
    orders_list = []
    for order_id in order_ids:
        order_data = redis_client.get(f'order:{order_id}')
        if order_data:
            orders_list.append(json.loads(order_data))
    
    return jsonify({'orders': orders_list})

@app.route('/api/orders/<order_id>', methods=['GET', 'PUT', 'DELETE'])
def order_detail(order_id):
    if not redis_client:
        return jsonify({'error': 'Redis not connected'}), 500
    
    if request.method == 'DELETE':
        redis_client.delete(f'order:{order_id}')
        redis_client.srem('orders', order_id)
        return jsonify({'success': True})
    
    if request.method == 'PUT':
        data = request.get_json()
        order_data = redis_client.get(f'order:{order_id}')
        if order_data:
            order = json.loads(order_data)
            order.update(data)
            redis_client.set(f'order:{order_id}', json.dumps(order))
            return jsonify({'success': True, 'order': order})
        return jsonify({'error': 'Order not found'}), 404
    
    # GET single order
    order_data = redis_client.get(f'order:{order_id}')
    if order_data:
        return jsonify({'order': json.loads(order_data)})
    return jsonify({'error': 'Order not found'}), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5100)