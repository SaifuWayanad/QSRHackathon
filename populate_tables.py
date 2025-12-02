#!/usr/bin/env python3
"""
Populate dining tables under different areas in Redis database
"""
import redis
import json
import uuid

# Connect to Redis
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Get all areas first
area_ids = redis_client.smembers('areas')
areas_list = []
for area_id in area_ids:
    area_data = redis_client.get(f'area:{area_id}')
    if area_data:
        areas_list.append(json.loads(area_data))

if not areas_list:
    print("❌ No areas found! Please create areas first.")
    exit(1)

# Define tables per area (5-8 tables per area)
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
        {'number': 304, 'capacity': 2},
        {'number': 305, 'capacity': 1},
    ],
    'Meeting Room': [
        {'number': 401, 'capacity': 10},
        {'number': 402, 'capacity': 12},
        {'number': 403, 'capacity': 8},
        {'number': 404, 'capacity': 15},
        {'number': 405, 'capacity': 6},
    ]
}

# Add tables to Redis
total_tables = 0
for area in areas_list:
    area_name = area['name']
    area_id = area['id']
    
    if area_name in tables_per_area:
        tables_count = 0
        for table_info in tables_per_area[area_name]:
            table_id = str(uuid.uuid4())
            table = {
                'id': table_id,
                'number': table_info['number'],
                'area_id': area_id,
                'area_name': area_name,
                'capacity': table_info['capacity'],
                'status': 'available'
            }
            
            redis_client.set(f'table:{table_id}', json.dumps(table))
            redis_client.sadd('tables', table_id)
            redis_client.sadd(f'area:{area_id}:tables', table_id)
            tables_count += 1
            total_tables += 1
        
        # Update area's table count
        area['tables_count'] = tables_count
        redis_client.set(f'area:{area_id}', json.dumps(area))
        print(f"✓ Created {tables_count} tables in {area_name}")

print(f"\n✓ Successfully created {total_tables} dining tables across all areas!")
