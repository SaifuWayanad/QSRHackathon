#!/usr/bin/env python3
import redis
import json
import uuid

# Connect to Redis
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Sample categories data for 20 food menu categories
categories_data = [
    {
        "name": "Appetizers",
        "description": "Starters and finger foods to begin your meal"
    },
    {
        "name": "Soups",
        "description": "Warm and comforting soup selections"
    },
    {
        "name": "Salads",
        "description": "Fresh and crisp salad combinations"
    },
    {
        "name": "Pasta & Noodles",
        "description": "Italian and Asian pasta dishes"
    },
    {
        "name": "Pizza",
        "description": "Wood-fired and oven-baked pizzas"
    },
    {
        "name": "Main Courses",
        "description": "Premium meat and seafood dishes"
    },
    {
        "name": "Grilled Items",
        "description": "Charcoal grilled specialties"
    },
    {
        "name": "Seafood",
        "description": "Fresh fish and shellfish preparations"
    },
    {
        "name": "Vegetarian",
        "description": "Plant-based and meat-free options"
    },
    {
        "name": "Asian Cuisine",
        "description": "Chinese, Thai, and Vietnamese dishes"
    },
    {
        "name": "Indian Curries",
        "description": "Spiced curries and tandoori specialties"
    },
    {
        "name": "Breads & Sides",
        "description": "Garlic breads, rice, and side dishes"
    },
    {
        "name": "Desserts",
        "description": "Sweet treats and pastries"
    },
    {
        "name": "Cakes & Pastries",
        "description": "Freshly baked cakes and pies"
    },
    {
        "name": "Ice Cream & Frozen",
        "description": "Ice cream and frozen desserts"
    },
    {
        "name": "Beverages",
        "description": "Soft drinks and beverages"
    },
    {
        "name": "Coffee & Tea",
        "description": "Hot coffee and tea selections"
    },
    {
        "name": "Smoothies",
        "description": "Fresh fruit and protein smoothies"
    },
    {
        "name": "Cocktails",
        "description": "Alcoholic and non-alcoholic cocktails"
    },
    {
        "name": "Kids Menu",
        "description": "Special meals for children"
    }
]

print("Adding food menu categories to Redis...")
print("-" * 60)

for category_data in categories_data:
    # Generate unique ID
    category_id = str(uuid.uuid4())
    
    # Store category data as JSON string (matches app.py format)
    category = {
        "id": category_id,
        "name": category_data["name"],
        "description": category_data["description"],
        "status": "active",
        "items_count": 0
    }
    
    category_key = f"category:{category_id}"
    r.set(category_key, json.dumps(category))
    
    # Add ID to categories set
    r.sadd("categories", category_id)
    
    print(f"✓ Added: {category_data['name']}")
    print(f"  ID: {category_id}")
    print(f"  Description: {category_data['description']}\n")

# Verify
total_categories = r.scard("categories")
print("-" * 60)
print(f"✓ Total categories in database: {total_categories}")
print("✓ Categories added successfully!")
