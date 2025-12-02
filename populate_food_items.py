#!/usr/bin/env python3
import redis
import json
import uuid

# Connect to Redis
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Get all categories and kitchens from database
category_ids = list(r.smembers('categories'))
kitchen_ids = list(r.smembers('kitchens'))

if not category_ids or not kitchen_ids:
    print("Error: No categories or kitchens found in database")
    print(f"Categories: {len(category_ids)}, Kitchens: {len(kitchen_ids)}")
    exit(1)

# Sample food items with category and kitchen mappings
food_items_data = [
    # Appetizers (Category 1)
    {"name": "Spring Rolls", "category": 0, "kitchen": 0, "price": 5.99, "specs": "Served with sweet chili sauce"},
    {"name": "Garlic Bread", "category": 0, "kitchen": 0, "price": 4.99, "specs": "Crispy with garlic butter"},
    {"name": "Mozzarella Sticks", "category": 0, "kitchen": 6, "price": 6.99, "specs": "6 pieces with marinara sauce"},
    
    # Soups (Category 2)
    {"name": "Tomato Soup", "category": 1, "kitchen": 7, "price": 5.99, "specs": "Creamy tomato bisque"},
    {"name": "Chicken Noodle Soup", "category": 1, "kitchen": 7, "price": 6.99, "specs": "Homemade broth with vegetables"},
    {"name": "Miso Soup", "category": 1, "kitchen": 7, "price": 4.99, "specs": "Traditional Japanese soup"},
    
    # Salads (Category 3)
    {"name": "Caesar Salad", "category": 2, "kitchen": 5, "price": 7.99, "specs": "Romaine, parmesan, croutons"},
    {"name": "Greek Salad", "category": 2, "kitchen": 5, "price": 8.99, "specs": "Feta, olives, tomatoes, cucumbers"},
    {"name": "Caprese Salad", "category": 2, "kitchen": 5, "price": 8.99, "specs": "Fresh mozzarella, basil, tomatoes"},
    
    # Pasta (Category 4)
    {"name": "Spaghetti Carbonara", "category": 3, "kitchen": 0, "price": 12.99, "specs": "Creamy sauce with pancetta"},
    {"name": "Penne Arrabbiata", "category": 3, "kitchen": 0, "price": 11.99, "specs": "Spicy tomato sauce"},
    {"name": "Fettuccine Alfredo", "category": 3, "kitchen": 0, "price": 11.99, "specs": "Creamy parmesan sauce"},
    
    # Pizza (Category 5)
    {"name": "Margherita Pizza", "category": 4, "kitchen": 4, "price": 12.99, "specs": "Fresh mozzarella, basil, tomato"},
    {"name": "Pepperoni Pizza", "category": 4, "kitchen": 4, "price": 13.99, "specs": "Classic pepperoni and cheese"},
    {"name": "Vegetarian Pizza", "category": 4, "kitchen": 4, "price": 12.99, "specs": "Mixed vegetables and cheese"},
    
    # Main Courses (Category 6)
    {"name": "Grilled Salmon", "category": 5, "kitchen": 1, "price": 18.99, "specs": "With lemon butter sauce"},
    {"name": "Steak Ribeye", "category": 5, "kitchen": 1, "price": 24.99, "specs": "12oz prime cut, cooked to order"},
    {"name": "Chicken Parmesan", "category": 5, "kitchen": 0, "price": 14.99, "specs": "Breaded and topped with marinara"},
    
    # Seafood (Category 8)
    {"name": "Shrimp Tempura", "category": 7, "kitchen": 6, "price": 13.99, "specs": "Crispy fried with dipping sauce"},
    {"name": "Fish and Chips", "category": 7, "kitchen": 6, "price": 12.99, "specs": "Beer battered with tartar sauce"},
    
    # Vegetarian (Category 9)
    {"name": "Veggie Burger", "category": 8, "kitchen": 2, "price": 9.99, "specs": "Plant-based patty with toppings"},
    {"name": "Eggplant Parmesan", "category": 8, "kitchen": 0, "price": 11.99, "specs": "Layers of eggplant and cheese"},
    
    # Desserts (Category 13)
    {"name": "Chocolate Cake", "category": 12, "kitchen": 2, "price": 5.99, "specs": "Rich chocolate with frosting"},
    {"name": "Cheesecake", "category": 12, "kitchen": 2, "price": 6.99, "specs": "New York style cheesecake"},
    {"name": "Tiramisu", "category": 12, "kitchen": 2, "price": 5.99, "specs": "Classic Italian dessert"},
    
    # Beverages (Category 16)
    {"name": "Iced Coffee", "category": 16, "kitchen": 9, "price": 3.99, "specs": "Cold brew with ice"},
    {"name": "Smoothie Bowl", "category": 17, "kitchen": 9, "price": 7.99, "specs": "Mixed berry with granola"},
    {"name": "Fresh Orange Juice", "category": 15, "kitchen": 9, "price": 3.49, "specs": "Freshly squeezed"},
]

print("Adding 30 food items to Redis...")
print("-" * 70)

added_count = 0
for item_data in food_items_data:
    try:
        # Get actual category and kitchen IDs
        cat_id = category_ids[item_data["category"] % len(category_ids)]
        kitchen_id = kitchen_ids[item_data["kitchen"] % len(kitchen_ids)]
        
        # Get category and kitchen names
        cat_data = r.get(f'category:{cat_id}')
        kitchen_data = r.get(f'kitchen:{kitchen_id}')
        
        if not cat_data or not kitchen_data:
            print(f"✗ Skipping {item_data['name']} - Category or Kitchen not found")
            continue
        
        cat_info = json.loads(cat_data)
        kitchen_info = json.loads(kitchen_data)
        
        # Generate unique ID
        food_id = str(uuid.uuid4())
        
        # Create food item with kitchen mapping
        food_item = {
            "id": food_id,
            "name": item_data["name"],
            "category_id": cat_id,
            "category_name": cat_info["name"],
            "kitchen_id": kitchen_id,
            "kitchen_name": kitchen_info["name"],
            "price": item_data["price"],
            "description": f"Delicious {item_data['name']}",
            "specifications": item_data["specs"],
            "status": "available"
        }
        
        # Store food item
        r.set(f'food:{food_id}', json.dumps(food_item))
        r.sadd('food_items', food_id)
        
        # Create mapping: Add food item to kitchen's foods list
        r.sadd(f'kitchen:{kitchen_id}:foods', food_id)
        
        # Create reverse mapping: Add kitchen to food's kitchens
        r.sadd(f'food:{food_id}:kitchens', kitchen_id)
        
        # Update category items count
        cat_info['items_count'] = cat_info.get('items_count', 0) + 1
        r.set(f'category:{cat_id}', json.dumps(cat_info))
        
        # Update kitchen items count
        kitchen_info['items_count'] = kitchen_info.get('items_count', 0) + 1
        r.set(f'kitchen:{kitchen_id}', json.dumps(kitchen_info))
        
        print(f"✓ Added: {item_data['name']}")
        print(f"  Category: {cat_info['name']} | Kitchen: {kitchen_info['name']} | Price: ${item_data['price']}")
        added_count += 1
        
    except Exception as e:
        print(f"✗ Error adding {item_data['name']}: {str(e)}")

print("-" * 70)
print(f"✓ Successfully added {added_count} food items to database")
print(f"✓ Total food items: {r.scard('food_items')}")
