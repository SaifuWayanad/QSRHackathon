#!/usr/bin/env python3
"""
Unified database initialization script for SQLite
Populates all data from the populate_*.py files
"""
import sqlite3
import json
import uuid
from datetime import datetime

DB_PATH = "my_database.db"

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initialize database with all tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("Creating database tables...")
    
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
            staff_name TEXT NOT NULL,
            kitchen_id TEXT NOT NULL,
            kitchen_name TEXT NOT NULL,
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
            UNIQUE(staff_id, kitchen_id),
            FOREIGN KEY (staff_id) REFERENCES staff(id),
            FOREIGN KEY (kitchen_id) REFERENCES kitchens(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS staff_kitchen_assignments (
            id TEXT PRIMARY KEY,
            staff_id TEXT NOT NULL,
            staff_name TEXT NOT NULL,
            kitchen_id TEXT NOT NULL,
            kitchen_name TEXT NOT NULL,
            position TEXT,
            request_id TEXT,
            assigned_date DATE DEFAULT CURRENT_DATE,
            end_date DATE,
            status TEXT DEFAULT 'active',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(staff_id, kitchen_id),
            FOREIGN KEY (staff_id) REFERENCES staff(id),
            FOREIGN KEY (kitchen_id) REFERENCES kitchens(id),
            FOREIGN KEY (request_id) REFERENCES staff_kitchen_requests(id)
        )
    ''')
    
    conn.commit()
    print("✓ Database tables created successfully\n")
    return conn, cursor

def populate_areas(conn, cursor):
    """Populate dining areas"""
    print("Populating areas...")
    areas_data = [
        {
            'name': 'Main Dining Hall',
            'description': 'Large dining area with 20+ tables, perfect for family gatherings'
        },
        {
            'name': 'VIP Lounge',
            'description': 'Exclusive private dining area with premium ambiance'
        },
        {
            'name': 'Outdoor Patio',
            'description': 'Outdoor seating area with garden views'
        },
        {
            'name': 'Bar & Counter',
            'description': 'Counter seating for quick meals and drinks'
        },
        {
            'name': 'Meeting Room',
            'description': 'Private room suitable for small meetings and events'
        }
    ]
    
    created_count = 0
    for area_data in areas_data:
        area_id = str(uuid.uuid4())
        cursor.execute(
            'INSERT INTO areas (id, name, description, status) VALUES (?, ?, ?, ?)',
            (area_id, area_data['name'], area_data['description'], 'active')
        )
        created_count += 1
        print(f"  ✓ Added: {area_data['name']}")
    
    conn.commit()
    print(f"✓ Created {created_count} areas\n")

def populate_categories(conn, cursor):
    """Populate food categories"""
    print("Populating categories...")
    categories_data = [
        {"name": "Appetizers", "description": "Starters and finger foods to begin your meal"},
        {"name": "Soups", "description": "Warm and comforting soup selections"},
        {"name": "Salads", "description": "Fresh and crisp salad combinations"},
        {"name": "Pasta & Noodles", "description": "Italian and Asian pasta dishes"},
        {"name": "Pizza", "description": "Wood-fired and oven-baked pizzas"},
        {"name": "Main Courses", "description": "Premium meat and seafood dishes"},
        {"name": "Grilled Items", "description": "Charcoal grilled specialties"},
        {"name": "Seafood", "description": "Fresh fish and shellfish preparations"},
        {"name": "Vegetarian", "description": "Plant-based and meat-free options"},
        {"name": "Asian Cuisine", "description": "Chinese, Thai, and Vietnamese dishes"},
        {"name": "Burgers & Sandwiches", "description": "Hearty sandwiches and gourmet burgers"},
        {"name": "Wraps & Rolls", "description": "Fresh wraps and sushi rolls"},
        {"name": "Desserts", "description": "Sweet treats and desserts"},
        {"name": "Beverages", "description": "Non-alcoholic drinks and juices"},
        {"name": "Coffee & Tea", "description": "Hot and cold beverages"},
        {"name": "Smoothies", "description": "Fresh fruit and protein smoothies"},
        {"name": "Cocktails", "description": "Alcoholic beverages and mixed drinks"},
        {"name": "Wine", "description": "Selection of wines"},
        {"name": "Beer", "description": "Craft and regular beers"},
        {"name": "Specials", "description": "Daily specials and chef recommendations"},
    ]
    
    created_count = 0
    for cat_data in categories_data:
        cat_id = str(uuid.uuid4())
        cursor.execute(
            'INSERT INTO categories (id, name, description, status) VALUES (?, ?, ?, ?)',
            (cat_id, cat_data['name'], cat_data['description'], 'active')
        )
        created_count += 1
        print(f"  ✓ Added: {cat_data['name']}")
    
    conn.commit()
    print(f"✓ Created {created_count} categories\n")

def populate_kitchens(conn, cursor):
    """Populate kitchens"""
    print("Populating kitchens...")
    kitchens_data = [
        {
            "name": "Main Kitchen - Section A",
            "location": "Ground Floor, Section A",
            "description": "Primary cooking station for main dishes and preparations",
        },
        {
            "name": "Grill Station - Section B",
            "location": "Ground Floor, Section B",
            "description": "Dedicated grilling and barbecue station",
        },
        {
            "name": "Pastry & Desserts - Section C",
            "location": "Ground Floor, Section C",
            "description": "Baking and dessert preparation area",
        },
        {
            "name": "Sauce & Prep - Section D",
            "location": "Ground Floor, Section D",
            "description": "Sauce making and ingredient preparation",
        },
        {
            "name": "Pizza Oven - Section E",
            "location": "Ground Floor, Section E",
            "description": "Wood-fired pizza oven station",
        },
        {
            "name": "Cold Kitchen - Section F",
            "location": "Ground Floor, Section F",
            "description": "Salad preparation and cold dishes",
        },
        {
            "name": "Fryer Station - Section G",
            "location": "Ground Floor, Section G",
            "description": "Deep fryer and crispy items preparation",
        },
        {
            "name": "Soup & Broth - Section H",
            "location": "Ground Floor, Section H",
            "description": "Soup, stock, and broth preparation",
        },
        {
            "name": "Plating & Finishing - Section I",
            "location": "Ground Floor, Section I",
            "description": "Plating, garnishing, and final finishing",
        },
        {
            "name": "Beverage Station - Section J",
            "location": "Ground Floor, Section J",
            "description": "Beverages, drinks, and smoothie preparation",
        }
    ]
    
    created_count = 0
    for kitchen_data in kitchens_data:
        kitchen_id = str(uuid.uuid4())
        cursor.execute(
            'INSERT INTO kitchens (id, name, location, description, status) VALUES (?, ?, ?, ?, ?)',
            (kitchen_id, kitchen_data["name"], kitchen_data["location"], kitchen_data["description"], 'active')
        )
        created_count += 1
        print(f"  ✓ Added: {kitchen_data['name']}")
    
    conn.commit()
    print(f"✓ Created {created_count} kitchens\n")

def populate_order_types(conn, cursor):
    """Populate order types"""
    print("Populating order types...")
    order_types_data = [
        {'name': 'Dine-in', 'description': 'Customers dining at the restaurant'},
        {'name': 'Takeaway', 'description': 'Customers picking up food to go'},
        {'name': 'Delivery', 'description': 'Food delivered to customer location'},
        {'name': 'Drive-thru', 'description': 'Fast service for drive-thru customers'},
        {'name': 'Catering', 'description': 'Large orders for events and functions'},
    ]
    
    created_count = 0
    for order_type_data in order_types_data:
        order_type_id = str(uuid.uuid4())
        cursor.execute(
            'INSERT INTO order_types (id, name, description, status) VALUES (?, ?, ?, ?)',
            (order_type_id, order_type_data['name'], order_type_data['description'], 'active')
        )
        created_count += 1
        print(f"  ✓ Added: {order_type_data['name']}")
    
    conn.commit()
    print(f"✓ Created {created_count} order types\n")

def populate_tables(conn, cursor):
    """Populate dining tables"""
    print("Populating tables...")
    
    # Get all areas
    cursor.execute('SELECT id, name FROM areas')
    areas = cursor.fetchall()
    
    tables_per_area = {
        'Main Dining Hall': [
            {'number': 1, 'capacity': 2},
            {'number': 2, 'capacity': 4},
            {'number': 3, 'capacity': 4},
            {'number': 4, 'capacity': 6},
            {'number': 5, 'capacity': 2},
            {'number': 6, 'capacity': 8},
            {'number': 7, 'capacity': 4},
            {'number': 8, 'capacity': 6},
        ],
        'VIP Lounge': [
            {'number': 101, 'capacity': 4},
            {'number': 102, 'capacity': 6},
            {'number': 103, 'capacity': 8},
            {'number': 104, 'capacity': 4},
            {'number': 105, 'capacity': 6},
        ],
        'Outdoor Patio': [
            {'number': 201, 'capacity': 4},
            {'number': 202, 'capacity': 6},
            {'number': 203, 'capacity': 4},
            {'number': 204, 'capacity': 2},
            {'number': 205, 'capacity': 8},
            {'number': 206, 'capacity': 4},
        ],
        'Bar & Counter': [
            {'number': 301, 'capacity': 1},
            {'number': 302, 'capacity': 1},
            {'number': 303, 'capacity': 2},
            {'number': 304, 'capacity': 1},
        ],
        'Meeting Room': [
            {'number': 401, 'capacity': 10},
            {'number': 402, 'capacity': 15},
        ],
    }
    
    created_count = 0
    for area in areas:
        area_id = area['id']
        area_name = area['name']
        
        if area_name in tables_per_area:
            for table_config in tables_per_area[area_name]:
                table_id = str(uuid.uuid4())
                cursor.execute(
                    'INSERT INTO tables (id, number, area_id, area_name, capacity, status) VALUES (?, ?, ?, ?, ?, ?)',
                    (table_id, table_config['number'], area_id, area_name, table_config['capacity'], 'available')
                )
                created_count += 1
    
    conn.commit()
    print(f"✓ Created {created_count} tables\n")

def populate_food_items(conn, cursor):
    """Populate food items"""
    print("Populating food items...")
    
    # Get categories and kitchens
    cursor.execute('SELECT id, name FROM categories ORDER BY rowid LIMIT 20')
    categories = cursor.fetchall()
    cursor.execute('SELECT id, name FROM kitchens ORDER BY rowid LIMIT 10')
    kitchens = cursor.fetchall()
    
    if not categories or not kitchens:
        print("  ✗ No categories or kitchens found!")
        return
    
    food_items_data = [
        # Appetizers
        {"name": "Spring Rolls", "category": 0, "kitchen": 0, "price": 5.99, "specs": "Served with sweet chili sauce"},
        {"name": "Garlic Bread", "category": 0, "kitchen": 0, "price": 4.99, "specs": "Crispy with garlic butter"},
        {"name": "Mozzarella Sticks", "category": 0, "kitchen": 6, "price": 6.99, "specs": "6 pieces with marinara sauce"},
        
        # Soups
        {"name": "Tomato Soup", "category": 1, "kitchen": 7, "price": 5.99, "specs": "Creamy tomato bisque"},
        {"name": "Chicken Noodle Soup", "category": 1, "kitchen": 7, "price": 6.99, "specs": "Homemade broth with vegetables"},
        {"name": "Miso Soup", "category": 1, "kitchen": 7, "price": 4.99, "specs": "Traditional Japanese soup"},
        
        # Salads
        {"name": "Caesar Salad", "category": 2, "kitchen": 5, "price": 7.99, "specs": "Romaine, parmesan, croutons"},
        {"name": "Greek Salad", "category": 2, "kitchen": 5, "price": 8.99, "specs": "Feta, olives, tomatoes, cucumbers"},
        {"name": "Caprese Salad", "category": 2, "kitchen": 5, "price": 8.99, "specs": "Fresh mozzarella, basil, tomatoes"},
        
        # Pasta
        {"name": "Spaghetti Carbonara", "category": 3, "kitchen": 0, "price": 12.99, "specs": "Creamy sauce with pancetta"},
        {"name": "Penne Arrabbiata", "category": 3, "kitchen": 0, "price": 11.99, "specs": "Spicy tomato sauce"},
        {"name": "Fettuccine Alfredo", "category": 3, "kitchen": 0, "price": 11.99, "specs": "Creamy parmesan sauce"},
        
        # Pizza
        {"name": "Margherita Pizza", "category": 4, "kitchen": 4, "price": 12.99, "specs": "Fresh mozzarella, basil, tomato"},
        {"name": "Pepperoni Pizza", "category": 4, "kitchen": 4, "price": 13.99, "specs": "Classic pepperoni and cheese"},
        {"name": "Vegetarian Pizza", "category": 4, "kitchen": 4, "price": 12.99, "specs": "Mixed vegetables and cheese"},
        
        # Main Courses
        {"name": "Grilled Salmon", "category": 5, "kitchen": 1, "price": 18.99, "specs": "With lemon butter sauce"},
        {"name": "Steak Ribeye", "category": 5, "kitchen": 1, "price": 24.99, "specs": "12oz prime cut, cooked to order"},
        {"name": "Chicken Parmesan", "category": 5, "kitchen": 0, "price": 14.99, "specs": "Breaded and topped with marinara"},
        
        # Seafood
        {"name": "Shrimp Tempura", "category": 7, "kitchen": 6, "price": 13.99, "specs": "Crispy fried with dipping sauce"},
        {"name": "Fish and Chips", "category": 7, "kitchen": 6, "price": 12.99, "specs": "Beer battered with tartar sauce"},
        
        # Vegetarian
        {"name": "Veggie Burger", "category": 8, "kitchen": 2, "price": 9.99, "specs": "Plant-based patty with toppings"},
        {"name": "Eggplant Parmesan", "category": 8, "kitchen": 0, "price": 11.99, "specs": "Layers of eggplant and cheese"},
        
        # Desserts
        {"name": "Chocolate Cake", "category": 12, "kitchen": 2, "price": 5.99, "specs": "Rich chocolate with frosting"},
        {"name": "Cheesecake", "category": 12, "kitchen": 2, "price": 6.99, "specs": "New York style cheesecake"},
        {"name": "Tiramisu", "category": 12, "kitchen": 2, "price": 5.99, "specs": "Classic Italian dessert"},
        
        # Beverages
        {"name": "Iced Coffee", "category": 14, "kitchen": 9, "price": 3.99, "specs": "Cold brew with ice"},
        {"name": "Fresh Orange Juice", "category": 13, "kitchen": 9, "price": 3.49, "specs": "Freshly squeezed"},
    ]
    
    created_count = 0
    for item_data in food_items_data:
        try:
            cat_idx = item_data["category"] % len(categories)
            kitchen_idx = item_data["kitchen"] % len(kitchens)
            
            cat_id = categories[cat_idx]['id']
            cat_name = categories[cat_idx]['name']
            kitchen_id = kitchens[kitchen_idx]['id']
            kitchen_name = kitchens[kitchen_idx]['name']
            
            food_id = str(uuid.uuid4())
            cursor.execute(
                '''INSERT INTO food_items (id, name, category_id, category_name, kitchen_id, kitchen_name, 
                   price, description, specifications, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (food_id, item_data["name"], cat_id, cat_name, kitchen_id, kitchen_name,
                 item_data["price"], "", item_data["specs"], 'available')
            )
            
            # Update counts
            cursor.execute('UPDATE categories SET items_count = items_count + 1 WHERE id = ?', (cat_id,))
            cursor.execute('UPDATE kitchens SET items_count = items_count + 1 WHERE id = ?', (kitchen_id,))
            
            created_count += 1
            print(f"  ✓ Added: {item_data['name']}")
        except Exception as e:
            print(f"  ✗ Error adding {item_data['name']}: {str(e)}")
    
    conn.commit()
    print(f"✓ Created {created_count} food items\n")

def populate_appliances(conn, cursor):
    """Populate appliances table with sample data"""
    print("Populating appliances...")
    
    appliances_data = [
        # Cooking Appliances
        {"name": "Commercial Oven", "type": "Oven", "model": "CO-2000X", "serial_number": "CO001", 
         "description": "Large capacity commercial oven", "purchase_date": "2023-01-15", "last_maintenance": "2024-01-10"},
        {"name": "Gas Stove", "type": "Stove/Cooktop", "model": "GS-4B", "serial_number": "GS001", 
         "description": "4-burner gas stove with oven", "purchase_date": "2023-02-20", "last_maintenance": "2024-02-15"},
        {"name": "Heavy Duty Grill", "type": "Grill", "model": "GR-HDX", "serial_number": "GR001", 
         "description": "Double-sided electric grill", "purchase_date": "2023-03-10", "last_maintenance": "2024-01-20"},
        {"name": "Deep Fryer", "type": "Fryer", "model": "DF-500", "serial_number": "DF001", 
         "description": "Stainless steel deep fryer with thermostat", "purchase_date": "2023-04-05", "last_maintenance": "2024-02-05"},
        
        # Refrigeration
        {"name": "Walk-in Refrigerator", "type": "Refrigerator", "model": "WIR-L800", "serial_number": "WIR001", 
         "description": "Large walk-in refrigerator", "purchase_date": "2022-12-01", "last_maintenance": "2024-01-15"},
        {"name": "Reach-in Freezer", "type": "Freezer", "model": "RIF-4D", "serial_number": "FZ001", 
         "description": "4-door reach-in freezer", "purchase_date": "2023-01-20", "last_maintenance": "2024-01-25"},
        
        # Food Prep Equipment
        {"name": "Commercial Mixer", "type": "Mixer", "model": "MIX-200L", "serial_number": "MIX001", 
         "description": "200L planetary mixer for dough", "purchase_date": "2023-02-15", "last_maintenance": "2024-02-20"},
        {"name": "Food Processor", "type": "Food Processor", "model": "FP-30", "serial_number": "FP001", 
         "description": "30-cup food processor", "purchase_date": "2023-03-01", "last_maintenance": "2024-01-30"},
        {"name": "Blender Pro", "type": "Blender", "model": "BL-PRO3", "serial_number": "BL001", 
         "description": "High-speed commercial blender", "purchase_date": "2023-04-10", "last_maintenance": "2024-02-10"},
        
        # Cleaning Equipment
        {"name": "Industrial Dishwasher", "type": "Dishwasher", "model": "DW-IND500", "serial_number": "DW001", 
         "description": "High-capacity undercounter dishwasher", "purchase_date": "2023-05-20", "last_maintenance": "2024-02-01"},
        
        # Other Equipment
        {"name": "Commercial Microwave", "type": "Microwave", "model": "MW-C1000", "serial_number": "MW001", 
         "description": "1000W commercial microwave oven", "purchase_date": "2023-06-05", "last_maintenance": "2024-02-15"},
        {"name": "Steamer", "type": "Steamer", "model": "ST-CONV2", "serial_number": "ST001", 
         "description": "Convection steamer with timer", "purchase_date": "2023-07-15", "last_maintenance": "2024-01-05"},
        {"name": "Commercial Slicer", "type": "Slicer", "model": "SL-PRO", "serial_number": "SL001", 
         "description": "Automatic meat and cheese slicer", "purchase_date": "2023-08-20", "last_maintenance": "2024-02-08"},
        {"name": "Ventilation Hood", "type": "Ventilation Hood", "model": "VH-500CFM", "serial_number": "VH001", 
         "description": "500 CFM ventilation hood with filters", "purchase_date": "2023-09-10", "last_maintenance": "2024-01-30"},
    ]
    
    created_count = 0
    for appliance in appliances_data:
        try:
            appliance_id = str(uuid.uuid4())
            cursor.execute(
                '''INSERT INTO appliances (id, name, type, model, serial_number, description, status, 
                   purchase_date, last_maintenance, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (appliance_id, appliance["name"], appliance["type"], appliance.get("model", ""),
                 appliance.get("serial_number", ""), appliance.get("description", ""), 'active',
                 appliance.get("purchase_date"), appliance.get("last_maintenance"), "")
            )
            created_count += 1
            print(f"  ✓ Added: {appliance['name']}")
        except Exception as e:
            print(f"  ✗ Error adding {appliance['name']}: {str(e)}")
    
    conn.commit()
    print(f"✓ Created {created_count} appliances\n")

def populate_kitchen_appliances(conn, cursor):
    """Populate kitchen_appliances junction table with sample mappings"""
    print("Populating kitchen appliances assignments...")
    
    # Get all kitchens and appliances
    cursor.execute('SELECT id FROM kitchens')
    kitchens = cursor.fetchall()
    
    cursor.execute('SELECT id, type, name FROM appliances')
    appliances = cursor.fetchall()
    
    if not kitchens or not appliances:
        print("  ⚠ No kitchens or appliances found, skipping assignments")
        return
    
    # Create mappings: assign different appliances to different kitchens
    appliance_assignments = {
        'Oven': 2,
        'Stove/Cooktop': 2,
        'Grill': 1,
        'Fryer': 2,
        'Refrigerator': 3,
        'Freezer': 2,
        'Mixer': 1,
        'Food Processor': 2,
        'Blender': 1,
        'Dishwasher': 1,
        'Microwave': 2,
        'Steamer': 1,
        'Slicer': 1,
        'Ventilation Hood': 1
    }
    
    kitchen_list = [k[0] for k in kitchens]
    appliance_list = list(appliances)
    
    created_count = 0
    for appliance in appliance_list:
        appliance_id, appliance_type, appliance_name = appliance
        kitchen_count = appliance_assignments.get(appliance_type, 1)
        
        # Assign to first N kitchens (rotate through available kitchens)
        for i in range(min(kitchen_count, len(kitchen_list))):
            try:
                kitchen_id = kitchen_list[i]
                mapping_id = str(uuid.uuid4())
                location = f"Station {i+1}" if kitchen_count > 1 else "Main Station"
                
                cursor.execute(
                    '''INSERT INTO kitchen_appliances (id, kitchen_id, appliance_id, quantity, location, status)
                       VALUES (?, ?, ?, ?, ?, ?)''',
                    (mapping_id, kitchen_id, appliance_id, 1, location, 'active')
                )
                created_count += 1
                print(f"  ✓ Assigned {appliance_name} to Kitchen (Location: {location})")
            except sqlite3.IntegrityError:
                # Skip if already exists
                continue
            except Exception as e:
                print(f"  ✗ Error assigning {appliance_name}: {str(e)}")
    
    conn.commit()
    print(f"✓ Created {created_count} kitchen appliance assignments\n")

def populate_iot_devices(conn, cursor):
    """Populate iot_devices table with sample data"""
    print("Populating IoT devices...")
    
    # Get all kitchens
    cursor.execute('SELECT id FROM kitchens')
    kitchens = [k[0] for k in cursor.fetchall()]
    
    iot_devices_data = [
        # Temperature & Humidity Sensors
        {"name": "Temperature Sensor - Main Kitchen", "device_type": "Temperature Sensor", "device_id": "TEMP-001", 
         "location": "Main Storage", "description": "Real-time temperature monitoring", "firmware_version": "v2.1.0", 
         "battery_level": 85, "signal_strength": 90},
        {"name": "Humidity Sensor - Cold Room", "device_type": "Humidity Sensor", "device_id": "HUMID-001", 
         "location": "Walk-in Fridge", "description": "Monitor humidity levels", "firmware_version": "v1.5.2", 
         "battery_level": 75, "signal_strength": 85},
        
        # Security Sensors
        {"name": "Motion Detector - Entrance", "device_type": "Motion Detector", "device_id": "MOT-001", 
         "location": "Main Entrance", "description": "Security motion detection", "firmware_version": "v3.0.1", 
         "battery_level": 92, "signal_strength": 95},
        {"name": "Door Sensor - Freezer", "device_type": "Door Sensor", "device_id": "DOOR-001", 
         "location": "Freezer Room", "description": "Monitor freezer door status", "firmware_version": "v1.8.0", 
         "battery_level": 88, "signal_strength": 80},
        {"name": "Smoke Detector - Kitchen", "device_type": "Smoke Detector", "device_id": "SMOKE-001", 
         "location": "Main Kitchen Ceiling", "description": "Fire safety smoke detection", "firmware_version": "v2.0.0", 
         "battery_level": 100, "signal_strength": 92},
        
        # Monitoring Sensors
        {"name": "Weight Scale - Receiving", "device_type": "Weight Scale", "device_id": "SCALE-001", 
         "location": "Receiving Area", "description": "Ingredient weight tracking", "firmware_version": "v1.3.0", 
         "battery_level": 70, "signal_strength": 88},
        {"name": "Energy Meter - Mains", "device_type": "Energy Meter", "device_id": "ENERGY-001", 
         "location": "Electrical Panel", "description": "Overall energy consumption", "firmware_version": "v2.2.1", 
         "battery_level": 0, "signal_strength": 100},
        {"name": "Water Flow Meter", "device_type": "Water Flow Meter", "device_id": "WATER-001", 
         "location": "Water Main", "description": "Water consumption monitoring", "firmware_version": "v1.7.0", 
         "battery_level": 65, "signal_strength": 75},
        
        # Smart Devices
        {"name": "Smart Display - Counter", "device_type": "Smart Display", "device_id": "DISP-001", 
         "location": "Counter Area", "description": "Order and status display", "firmware_version": "v4.1.0", 
         "battery_level": 0, "signal_strength": 98},
        {"name": "RFID Reader - Inventory", "device_type": "RFID Reader", "device_id": "RFID-001", 
         "location": "Inventory Station", "description": "Inventory tracking RFID", "firmware_version": "v2.0.0", 
         "battery_level": 80, "signal_strength": 85},
        
        # Other Sensors
        {"name": "Gas Detector - Stove Area", "device_type": "Gas Detector", "device_id": "GAS-001", 
         "location": "Cooking Station", "description": "Natural gas leak detection", "firmware_version": "v1.9.0", 
         "battery_level": 95, "signal_strength": 90},
        {"name": "Light Sensor - Dining Hall", "device_type": "Light Sensor", "device_id": "LIGHT-001", 
         "location": "Dining Area", "description": "Ambient light level monitoring", "firmware_version": "v1.2.0", 
         "battery_level": 78, "signal_strength": 82},
    ]
    
    created_count = 0
    for device in iot_devices_data:
        try:
            device_id = str(uuid.uuid4())
            kitchen_id = kitchens[created_count % len(kitchens)] if kitchens else None
            
            cursor.execute(
                '''INSERT INTO iot_devices (id, name, device_type, device_id, location, kitchen_id, description, 
                   status, battery_level, signal_strength, firmware_version)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (device_id, device["name"], device["device_type"], device["device_id"],
                 device["location"], kitchen_id, device.get("description", ""), 'active',
                 device.get("battery_level"), device.get("signal_strength"), device.get("firmware_version", ""))
            )
            created_count += 1
            print(f"  ✓ Added: {device['name']}")
        except Exception as e:
            print(f"  ✗ Error adding {device['name']}: {str(e)}")
    
    conn.commit()
    print(f"✓ Created {created_count} IoT devices\n")

def populate_staff(conn, cursor):
    """Populate staff table with sample data"""
    print("Populating staff members...")
    
    # Get all kitchens
    cursor.execute('SELECT id FROM kitchens')
    kitchens = [k[0] for k in cursor.fetchall()]
    
    staff_data = [
        # Management
        {"name": "Maria Garcia", "position": "Manager", "department": "Management", "email": "maria.garcia@restaurant.com", 
         "phone": "(555) 101-1000", "hire_date": "2022-01-15"},
        {"name": "James Wilson", "position": "Assistant Manager", "department": "Management", "email": "james.wilson@restaurant.com", 
         "phone": "(555) 101-1001", "hire_date": "2022-06-20"},
        
        # Kitchen Staff
        {"name": "Chef Marco Romano", "position": "Chef", "department": "Kitchen", "email": "marco@restaurant.com", 
         "phone": "(555) 201-1000", "hire_date": "2021-03-10"},
        {"name": "Sophie Laurent", "position": "Sous Chef", "department": "Kitchen", "email": "sophie@restaurant.com", 
         "phone": "(555) 201-1001", "hire_date": "2021-08-15"},
        {"name": "Thomas Kim", "position": "Head Cook", "department": "Kitchen", "email": "thomas@restaurant.com", 
         "phone": "(555) 201-1002", "hire_date": "2022-02-01"},
        {"name": "Anna Mueller", "position": "Line Cook", "department": "Kitchen", "email": "anna@restaurant.com", 
         "phone": "(555) 201-1003", "hire_date": "2023-01-20"},
        {"name": "David Chen", "position": "Line Cook", "department": "Kitchen", "email": "david@restaurant.com", 
         "phone": "(555) 201-1004", "hire_date": "2023-03-15"},
        {"name": "Lisa Torres", "position": "Prep Cook", "department": "Kitchen", "email": "lisa@restaurant.com", 
         "phone": "(555) 201-1005", "hire_date": "2023-05-01"},
        {"name": "Robert Lee", "position": "Pastry Chef", "department": "Kitchen", "email": "robert@restaurant.com", 
         "phone": "(555) 201-1006", "hire_date": "2022-09-10"},
        {"name": "Miguel Santos", "position": "Dishwasher", "department": "Kitchen", "email": "miguel@restaurant.com", 
         "phone": "(555) 201-1007", "hire_date": "2023-07-01"},
        
        # Front of House
        {"name": "Emily Johnson", "position": "Server", "department": "Front of House", "email": "emily@restaurant.com", 
         "phone": "(555) 301-1000", "hire_date": "2023-02-01"},
        {"name": "Michael Brown", "position": "Server", "department": "Front of House", "email": "michael@restaurant.com", 
         "phone": "(555) 301-1001", "hire_date": "2023-04-15"},
        {"name": "Sarah Taylor", "position": "Server", "department": "Front of House", "email": "sarah@restaurant.com", 
         "phone": "(555) 301-1002", "hire_date": "2023-05-20"},
        {"name": "Jessica Davis", "position": "Host/Hostess", "department": "Front of House", "email": "jessica@restaurant.com", 
         "phone": "(555) 301-1003", "hire_date": "2023-06-01"},
        {"name": "Christopher Miller", "position": "Busser", "department": "Front of House", "email": "chris@restaurant.com", 
         "phone": "(555) 301-1004", "hire_date": "2023-07-15"},
        
        # Bar
        {"name": "Patrick O'Brien", "position": "Bartender", "department": "Bar", "email": "patrick@restaurant.com", 
         "phone": "(555) 401-1000", "hire_date": "2022-11-01"},
        {"name": "Nicole Anderson", "position": "Bartender", "department": "Bar", "email": "nicole@restaurant.com", 
         "phone": "(555) 401-1001", "hire_date": "2023-03-01"},
        
        # Additional Staff
        {"name": "Rachel White", "position": "Barista", "department": "Bar", "email": "rachel@restaurant.com", 
         "phone": "(555) 401-1002", "hire_date": "2023-08-01"},
        {"name": "Kevin Martinez", "position": "Maintenance", "department": "Maintenance", "email": "kevin@restaurant.com", 
         "phone": "(555) 501-1000", "hire_date": "2022-07-01"},
    ]
    
    created_count = 0
    for staff in staff_data:
        try:
            staff_id = str(uuid.uuid4())
            # Assign some kitchen staff to specific kitchens
            kitchen_id = None
            if staff.get("department") == "Kitchen":
                kitchen_id = kitchens[created_count % len(kitchens)] if kitchens else None
            
            cursor.execute(
                '''INSERT INTO staff (id, name, email, phone, position, department, kitchen_id, 
                   hire_date, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (staff_id, staff["name"], staff.get("email", ""), staff.get("phone", ""),
                 staff["position"], staff["department"], kitchen_id, 
                 staff.get("hire_date"), 'active')
            )
            created_count += 1
            print(f"  ✓ Added: {staff['name']} ({staff['position']})")
        except Exception as e:
            print(f"  ✗ Error adding {staff['name']}: {str(e)}")
    
    conn.commit()
    print(f"✓ Created {created_count} staff members\n")

def populate_staff_kitchen_requests(conn, cursor):
    """Populate staff kitchen requests"""
    print("Populating staff kitchen requests...")
    import uuid
    from datetime import datetime, timedelta
    
    # Get staff and kitchens for assignment
    cursor.execute("SELECT id, name FROM staff LIMIT 5")
    staff_list = cursor.fetchall()
    
    cursor.execute("SELECT id, name FROM kitchens LIMIT 3")
    kitchens_list = cursor.fetchall()
    
    requests_data = [
        {
            'staff_id': staff_list[0]['id'] if len(staff_list) > 0 else 'STAFF_001',
            'staff_name': staff_list[0]['name'] if len(staff_list) > 0 else 'John Doe',
            'kitchen_id': kitchens_list[0]['id'] if len(kitchens_list) > 0 else 'KITCHEN_001',
            'kitchen_name': kitchens_list[0]['name'] if len(kitchens_list) > 0 else 'Main Kitchen',
            'position': 'Head Chef',
            'request_reason': 'Requesting transfer for career advancement',
            'requested_start_date': (datetime.now() + timedelta(days=7)).date(),
            'approval_status': 'approved',
            'approved_by': 'admin',
            'approval_notes': 'Approved - suitable candidate'
        },
        {
            'staff_id': staff_list[1]['id'] if len(staff_list) > 1 else 'STAFF_002',
            'staff_name': staff_list[1]['name'] if len(staff_list) > 1 else 'Jane Smith',
            'kitchen_id': kitchens_list[1]['id'] if len(kitchens_list) > 1 else 'KITCHEN_002',
            'kitchen_name': kitchens_list[1]['name'] if len(kitchens_list) > 1 else 'Prep Kitchen',
            'position': 'Sous Chef',
            'request_reason': 'Seeking new kitchen environment',
            'requested_start_date': (datetime.now() + timedelta(days=14)).date(),
            'approval_status': 'pending',
            'approved_by': None,
            'approval_notes': None
        },
        {
            'staff_id': staff_list[2]['id'] if len(staff_list) > 2 else 'STAFF_003',
            'staff_name': staff_list[2]['name'] if len(staff_list) > 2 else 'Bob Johnson',
            'kitchen_id': kitchens_list[2]['id'] if len(kitchens_list) > 2 else 'KITCHEN_003',
            'kitchen_name': kitchens_list[2]['name'] if len(kitchens_list) > 2 else 'Dessert Kitchen',
            'position': 'Line Cook',
            'request_reason': 'Interested in pastry department',
            'requested_start_date': (datetime.now() + timedelta(days=21)).date(),
            'approval_status': 'rejected',
            'approved_by': None,
            'approval_notes': None
        }
    ]
    
    created_count = 0
    for request_data in requests_data:
        try:
            req_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO staff_kitchen_requests 
                (id, staff_id, staff_name, kitchen_id, kitchen_name, position, request_reason, 
                 requested_start_date, approval_status, approved_by, approval_notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                req_id,
                request_data['staff_id'],
                request_data['staff_name'],
                request_data['kitchen_id'],
                request_data['kitchen_name'],
                request_data['position'],
                request_data['request_reason'],
                request_data['requested_start_date'],
                request_data['approval_status'],
                request_data['approved_by'],
                request_data['approval_notes']
            ))
            created_count += 1
        except Exception as e:
            print(f"  ⚠ Skipped: {str(e)}")
    
    conn.commit()
    print(f"✓ Created {created_count} staff kitchen requests\n")

def populate_staff_kitchen_assignments(conn, cursor):
    """Populate staff kitchen assignments based on approved requests"""
    print("Populating staff kitchen assignments...")
    import uuid
    from datetime import datetime, timedelta
    
    # Get approved requests
    cursor.execute('''
        SELECT id, staff_id, staff_name, kitchen_id, kitchen_name, position 
        FROM staff_kitchen_requests 
        WHERE approval_status = 'approved'
    ''')
    approved_requests = cursor.fetchall()
    
    created_count = 0
    for request in approved_requests:
        try:
            assign_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO staff_kitchen_assignments 
                (id, staff_id, staff_name, kitchen_id, kitchen_name, position, request_id, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                assign_id,
                request['staff_id'],
                request['staff_name'],
                request['kitchen_id'],
                request['kitchen_name'],
                request['position'],
                request['id'],
                'active'
            ))
            created_count += 1
        except Exception as e:
            print(f"  ⚠ Skipped: {str(e)}")
    
    conn.commit()
    print(f"✓ Created {created_count} staff kitchen assignments\n")

def main():
    """Main initialization function"""
    print("=" * 70)
    print("QSR HACKATHON - DATABASE INITIALIZATION")
    print("=" * 70)
    print()
    
    try:
        conn, cursor = init_database()
        populate_areas(conn, cursor)
        populate_categories(conn, cursor)
        populate_kitchens(conn, cursor)
        populate_order_types(conn, cursor)
        populate_tables(conn, cursor)
        populate_food_items(conn, cursor)
        populate_appliances(conn, cursor)
        populate_kitchen_appliances(conn, cursor)
        populate_iot_devices(conn, cursor)
        populate_staff(conn, cursor)
        populate_staff_kitchen_requests(conn, cursor)
        populate_staff_kitchen_assignments(conn, cursor)
        
        conn.close()
        
        print("=" * 70)
        print("✓ DATABASE INITIALIZATION COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        print("\nYou can now run: python app.py")
        print()
        
    except Exception as e:
        print(f"✗ Error during initialization: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
