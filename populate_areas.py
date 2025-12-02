#!/usr/bin/env python3
"""
Populate dining areas in Redis database
"""
import redis
import json
import uuid

# Connect to Redis
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Define areas
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

# Add areas to Redis
created_count = 0
for area_data in areas_data:
    area_id = str(uuid.uuid4())
    area = {
        'id': area_id,
        'name': area_data['name'],
        'description': area_data['description'],
        'status': 'active',
        'tables_count': 0
    }
    
    redis_client.set(f'area:{area_id}', json.dumps(area))
    redis_client.sadd('areas', area_id)
    created_count += 1
    print(f"✓ Created area: {area_data['name']}")

print(f"\n✓ Successfully created {created_count} dining areas!")
