#!/usr/bin/env python3
import redis
import json
import uuid

# Connect to Redis
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Sample kitchens data for 10 sections
kitchens_data = [
    {
        "name": "Main Kitchen - Section A",
        "location": "Ground Floor, Section A",
        "description": "Primary cooking station for main dishes and preparations",
        "status": "active"
    },
    {
        "name": "Grill Station - Section B",
        "location": "Ground Floor, Section B",
        "description": "Dedicated grilling and barbecue station",
        "status": "active"
    },
    {
        "name": "Pastry & Desserts - Section C",
        "location": "Ground Floor, Section C",
        "description": "Baking and dessert preparation area",
        "status": "active"
    },
    {
        "name": "Sauce & Prep - Section D",
        "location": "Ground Floor, Section D",
        "description": "Sauce making and ingredient preparation",
        "status": "active"
    },
    {
        "name": "Pizza Oven - Section E",
        "location": "Ground Floor, Section E",
        "description": "Wood-fired pizza oven station",
        "status": "active"
    },
    {
        "name": "Cold Kitchen - Section F",
        "location": "Ground Floor, Section F",
        "description": "Salad preparation and cold dishes",
        "status": "active"
    },
    {
        "name": "Fryer Station - Section G",
        "location": "Ground Floor, Section G",
        "description": "Deep fryer and crispy items preparation",
        "status": "active"
    },
    {
        "name": "Soup & Broth - Section H",
        "location": "Ground Floor, Section H",
        "description": "Soup, stock, and broth preparation",
        "status": "active"
    },
    {
        "name": "Plating & Finishing - Section I",
        "location": "Ground Floor, Section I",
        "description": "Plating, garnishing, and final finishing",
        "status": "active"
    },
    {
        "name": "Beverage Station - Section J",
        "location": "Ground Floor, Section J",
        "description": "Beverages, drinks, and smoothie preparation",
        "status": "active"
    }
]

print("Adding kitchens to Redis...")
print("-" * 50)

for kitchen_data in kitchens_data:
    # Generate unique ID
    kitchen_id = str(uuid.uuid4())
    
    # Store kitchen data as JSON string (matches app.py format)
    kitchen = {
        "id": kitchen_id,
        "name": kitchen_data["name"],
        "location": kitchen_data["location"],
        "description": kitchen_data["description"],
        "status": kitchen_data["status"],
        "items_count": 0
    }
    
    kitchen_key = f"kitchen:{kitchen_id}"
    r.set(kitchen_key, json.dumps(kitchen))
    
    # Add ID to kitchens set
    r.sadd("kitchens", kitchen_id)
    
    print(f"✓ Added: {kitchen_data['name']}")
    print(f"  ID: {kitchen_id}")
    print(f"  Location: {kitchen_data['location']}\n")

# Verify
total_kitchens = r.scard("kitchens")
print("-" * 50)
print(f"✓ Total kitchens in database: {total_kitchens}")
print("✓ Kitchens added successfully!")
