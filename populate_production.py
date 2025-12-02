#!/usr/bin/env python3
import redis
import json
import uuid
from datetime import datetime, timedelta

# Connect to Redis
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Get all food items from database
food_ids = list(r.smembers('food_items'))

if not food_ids:
    print("Error: No food items found in database")
    exit(1)

# Generate production data for the last 7 days
production_items = []
base_date = datetime.now()

for day_offset in range(7):
    current_date = (base_date - timedelta(days=day_offset)).strftime('%Y-%m-%d')
    
    # Add 3-5 production items per day
    num_items = 3 + (day_offset % 3)
    
    for i in range(num_items):
        food_id = food_ids[i % len(food_ids)]
        
        # Get food item details
        food_data = r.get(f'food:{food_id}')
        if not food_data:
            continue
        
        food_info = json.loads(food_data)
        
        # Create production item
        production_id = str(uuid.uuid4())
        planned_qty = 50 + (i * 10)
        produced_qty = planned_qty - (10 if day_offset > 0 else (planned_qty // 2))  # Some items not completed for today
        
        production = {
            'id': production_id,
            'food_id': food_id,
            'food_name': food_info['name'],
            'category_name': food_info['category_name'],
            'date': current_date,
            'planned_quantity': planned_qty,
            'produced': produced_qty,
            'notes': f'Production plan for {food_info["name"]} - {planned_qty} items planned'
        }
        
        # Store production item
        r.set(f'production:{production_id}', json.dumps(production))
        r.sadd('all_productions', production_id)
        r.sadd(f'production_date:{current_date}', production_id)
        
        production_items.append({
            'id': production_id,
            'date': current_date,
            'food_name': food_info['name'],
            'planned': planned_qty,
            'produced': produced_qty
        })

print("Adding production dummy data to Redis...")
print("-" * 70)

# Display summary by date
dates = {}
for item in production_items:
    if item['date'] not in dates:
        dates[item['date']] = []
    dates[item['date']].append(item)

for date in sorted(dates.keys(), reverse=True):
    items = dates[date]
    print(f"\n📅 Date: {date} - {len(items)} items")
    print("-" * 70)
    for item in items:
        remaining = item['planned'] - item['produced']
        completion = (item['produced'] / item['planned'] * 100) if item['planned'] > 0 else 0
        print(f"  ✓ {item['food_name']}")
        print(f"    Planned: {item['planned']} | Produced: {item['produced']} | Remaining: {remaining} | Completion: {completion:.0f}%")

print("\n" + "-" * 70)
print(f"✓ Total production entries: {r.scard('all_productions')}")
print(f"✓ Production dates covered: {len(dates)}")
print("✓ Dummy production data added successfully!")
