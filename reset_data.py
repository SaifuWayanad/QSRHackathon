#!/usr/bin/env python3
"""
Reset Kitchens and Food Items Script
This script will clear all existing kitchens and food items, 
then create 4 kitchens and 10 food items with multiple kitchen assignments.
"""

import pymysql
import pymysql.cursors
from datetime import datetime
from constants import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE

def get_connection():
    """Get database connection"""
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )

def reset_data():
    """Reset kitchens and food items data"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        print("🗑️  Clearing existing data...")
        
        # Delete food item-kitchen mappings first (foreign key constraint)
        cursor.execute("DELETE FROM food_kitchen_mapping")
        print(f"   Deleted {cursor.rowcount} food-kitchen mappings")
        
        # Delete food items
        cursor.execute("DELETE FROM food_items")
        print(f"   Deleted {cursor.rowcount} food items")
        
        # Delete kitchens
        cursor.execute("DELETE FROM kitchens")
        print(f"   Deleted {cursor.rowcount} kitchens")
        
        conn.commit()
        print("✅ Existing data cleared\n")
        
        # ============================================
        # Create 4 Kitchens
        # ============================================
        print("🏪 Creating 4 kitchens...")
        
        kitchens = [
            ('k1-main-kitchen', 'Main Kitchen', 'Ground Floor - Central', 
             'Primary cooking station for main dishes, pasta, and rice preparations', 'active', '🍳'),
            ('k2-grill-station', 'Grill & BBQ Station', 'Ground Floor - West Wing', 
             'Dedicated station for grilled items, steaks, and barbecue', 'active', '🔥'),
            ('k3-pizza-oven', 'Pizza & Bakery', 'Ground Floor - East Wing', 
             'Wood-fired pizza oven and baking station', 'active', '🍕'),
            ('k4-cold-kitchen', 'Cold Kitchen & Salads', 'Ground Floor - North Wing', 
             'Salad preparation, cold appetizers, and desserts', 'active', '🥗'),
        ]
        
        for kitchen in kitchens:
            cursor.execute(
                """INSERT INTO kitchens (id, name, location, description, status, icon, created_at) 
                   VALUES (%s, %s, %s, %s, %s, %s, NOW())""",
                kitchen
            )
            print(f"   ✓ Created: {kitchen[1]}")
        
        conn.commit()
        print("✅ Kitchens created\n")
        
        # ============================================
        # Get a category ID (use first available)
        # ============================================
        cursor.execute("SELECT id FROM categories LIMIT 1")
        category_result = cursor.fetchone()
        default_category_id = category_result['id'] if category_result else None
        
        if not default_category_id:
            print("⚠️  Warning: No categories found. Please create categories first.")
            print("   Food items will be created without category assignment.")
        
        # ============================================
        # Create 10 Food Items
        # ============================================
        print("🍽️  Creating 10 food items with kitchen assignments...")
        
        food_items = [
            {
                'id': 'f1-margherita',
                'name': 'Margherita Pizza',
                'price': 12.99,
                'description': 'Classic Italian pizza with fresh mozzarella, tomato sauce, and basil',
                'specs': 'Size: 12 inch, Calories: 800, Allergens: Gluten, Dairy',
                'kitchens': ['k3-pizza-oven']
            },
            {
                'id': 'f2-grilled-chicken',
                'name': 'Grilled Chicken Breast',
                'price': 15.99,
                'description': 'Herb-marinated grilled chicken breast with seasonal vegetables',
                'specs': 'Serving: 250g, Calories: 450, Protein: 45g, Low-carb option available',
                'kitchens': ['k2-grill-station', 'k1-main-kitchen']
            },
            {
                'id': 'f3-caesar-salad',
                'name': 'Caesar Salad',
                'price': 9.99,
                'description': 'Fresh romaine lettuce with Caesar dressing, parmesan, and croutons',
                'specs': 'Serving: 1 bowl, Calories: 320, Add chicken: +$4, Allergens: Dairy, Gluten',
                'kitchens': ['k4-cold-kitchen']
            },
            {
                'id': 'f4-bbq-ribs',
                'name': 'BBQ Baby Back Ribs',
                'price': 22.99,
                'description': 'Slow-cooked baby back ribs with house BBQ sauce and coleslaw',
                'specs': 'Weight: 800g, Calories: 1200, Spice level: Medium',
                'kitchens': ['k2-grill-station']
            },
            {
                'id': 'f5-carbonara',
                'name': 'Spaghetti Carbonara',
                'price': 13.99,
                'description': 'Traditional carbonara with pancetta, eggs, parmesan, and black pepper',
                'specs': 'Serving: 350g, Calories: 650, Allergens: Gluten, Dairy, Eggs',
                'kitchens': ['k1-main-kitchen']
            },
            {
                'id': 'f6-pepperoni',
                'name': 'Pepperoni Pizza',
                'price': 14.99,
                'description': 'Classic pepperoni pizza with mozzarella and tomato sauce',
                'specs': 'Size: 12 inch, Calories: 950, Allergens: Gluten, Dairy, Pork',
                'kitchens': ['k3-pizza-oven']
            },
            {
                'id': 'f7-grilled-salmon',
                'name': 'Grilled Atlantic Salmon',
                'price': 18.99,
                'description': 'Fresh Atlantic salmon fillet with lemon butter sauce and asparagus',
                'specs': 'Serving: 200g, Calories: 520, Omega-3 rich, Allergens: Fish',
                'kitchens': ['k2-grill-station', 'k1-main-kitchen']
            },
            {
                'id': 'f8-greek-salad',
                'name': 'Greek Salad',
                'price': 10.99,
                'description': 'Fresh tomatoes, cucumbers, olives, feta cheese, and red onion',
                'specs': 'Serving: 1 bowl, Calories: 280, Vegetarian, Allergens: Dairy',
                'kitchens': ['k4-cold-kitchen']
            },
            {
                'id': 'f9-cheeseburger',
                'name': 'Classic Cheeseburger',
                'price': 11.99,
                'description': 'Angus beef patty with cheddar, lettuce, tomato, and fries',
                'specs': 'Serving: 1 burger + fries, Calories: 850, Allergens: Gluten, Dairy',
                'kitchens': ['k2-grill-station', 'k1-main-kitchen', 'k3-pizza-oven']
            },
            {
                'id': 'f10-tiramisu',
                'name': 'Classic Tiramisu',
                'price': 7.99,
                'description': 'Italian coffee-flavored dessert with mascarpone and cocoa',
                'specs': 'Serving: 1 slice, Calories: 450, Contains alcohol, Allergens: Dairy, Eggs, Gluten',
                'kitchens': ['k4-cold-kitchen', 'k3-pizza-oven']
            },
        ]
        
        for item in food_items:
            # Insert food item
            cursor.execute(
                """INSERT INTO food_items (id, name, category_id, price, description, specifications, status, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, 'available', NOW())""",
                (item['id'], item['name'], default_category_id, item['price'], 
                 item['description'], item['specs'])
            )
            
            # Insert kitchen assignments
            for kitchen_id in item['kitchens']:
                cursor.execute(
                    """INSERT INTO food_kitchen_mapping (food_id, kitchen_id)
                       VALUES (%s, %s)""",
                    (item['id'], kitchen_id)
                )
            
            kitchen_names = ', '.join([k.split('-', 1)[1].replace('-', ' ').title() for k in item['kitchens']])
            print(f"   ✓ {item['name']} (${item['price']}) → {kitchen_names}")
        
        conn.commit()
        print("✅ Food items created\n")
        
        # ============================================
        # Verify the data
        # ============================================
        print("📊 Verification:")
        print("\n🏪 KITCHENS:")
        cursor.execute("SELECT id, name, location, status FROM kitchens")
        kitchens_result = cursor.fetchall()
        for k in kitchens_result:
            print(f"   • {k['name']} ({k['location']}) - {k['status']}")
        
        print("\n🍽️  FOOD ITEMS WITH KITCHEN ASSIGNMENTS:")
        cursor.execute("""
            SELECT 
                fi.id,
                fi.name as food_name,
                fi.price,
                GROUP_CONCAT(k.name SEPARATOR ', ') as assigned_kitchens
            FROM food_items fi
            LEFT JOIN food_kitchen_mapping fkm ON fi.id = fkm.food_id
            LEFT JOIN kitchens k ON fkm.kitchen_id = k.id
            GROUP BY fi.id, fi.name, fi.price
            ORDER BY fi.name
        """)
        foods_result = cursor.fetchall()
        for f in foods_result:
            print(f"   • {f['food_name']} (${f['price']:.2f}) → {f['assigned_kitchens']}")
        
        print("\n✅ Data reset complete!")
        print(f"   Total Kitchens: {len(kitchens_result)}")
        print(f"   Total Food Items: {len(foods_result)}")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    print("=" * 60)
    print("🔄 RESET KITCHENS AND FOOD ITEMS")
    print("=" * 60)
    print()
    
    response = input("This will DELETE all existing kitchens and food items. Continue? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        reset_data()
    else:
        print("❌ Operation cancelled")
