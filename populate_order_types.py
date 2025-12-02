#!/usr/bin/env python3
"""
Populate order types in Redis database
"""
import redis
import json
import uuid

# Connect to Redis
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Define order types
order_types_data = [
    {
        'name': 'Dine-in',
        'description': 'Customers dining at the restaurant'
    },
    {
        'name': 'Takeaway',
        'description': 'Customers picking up food to go'
    },
    {
        'name': 'Delivery',
        'description': 'Food delivered to customer location'
    },
    {
        'name': 'Drive-thru',
        'description': 'Fast service for drive-thru customers'
    },
    {
        'name': 'Catering',
        'description': 'Large orders for events and functions'
    }
]

# Add order types to Redis
created_count = 0
for order_type_data in order_types_data:
    order_type_id = str(uuid.uuid4())
    order_type = {
        'id': order_type_id,
        'name': order_type_data['name'],
        'description': order_type_data['description'],
        'status': 'active'
    }
    
    redis_client.set(f'order_type:{order_type_id}', json.dumps(order_type))
    redis_client.sadd('order_types', order_type_id)
    created_count += 1
    print(f"✓ Created order type: {order_type_data['name']}")

print(f"\n✓ Successfully created {created_count} order types!")
