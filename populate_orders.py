#!/usr/bin/env python3
"""
Populate sample orders in Redis database
"""
import redis
import json
import uuid
from datetime import datetime, timedelta

# Connect to Redis
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Get all tables and order types
table_ids = list(redis_client.smembers('tables'))
order_type_ids = list(redis_client.smembers('order_types'))

if not table_ids or not order_type_ids:
    print("❌ No tables or order types found! Please create them first.")
    exit(1)

# Get actual data
tables_list = []
for table_id in table_ids:
    table_data = redis_client.get(f'table:{table_id}')
    if table_data:
        tables_list.append(json.loads(table_data))

order_types_list = []
for order_type_id in order_type_ids:
    order_type_data = redis_client.get(f'order_type:{order_type_id}')
    if order_type_data:
        order_types_list.append(json.loads(order_type_data))

# Sample order data
sample_orders = [
    {'number': 'ORD-001', 'customer': 'John Smith', 'items': 3, 'amount': 45.50},
    {'number': 'ORD-002', 'customer': 'Sarah Johnson', 'items': 2, 'amount': 32.99},
    {'number': 'ORD-003', 'customer': 'Mike Wilson', 'items': 5, 'amount': 67.75},
    {'number': 'ORD-004', 'customer': 'Emma Davis', 'items': 4, 'amount': 55.25},
    {'number': 'ORD-005', 'customer': 'James Brown', 'items': 3, 'amount': 48.00},
    {'number': 'ORD-006', 'customer': '', 'items': 2, 'amount': 28.50},
    {'number': 'ORD-007', 'customer': 'Lisa Anderson', 'items': 6, 'amount': 89.99},
    {'number': 'ORD-008', 'customer': '', 'items': 4, 'amount': 52.75},
]

# Create orders
created_count = 0
statuses = ['pending', 'confirmed', 'preparing', 'completed']

for idx, sample_order in enumerate(sample_orders):
    order_id = str(uuid.uuid4())
    table = tables_list[idx % len(tables_list)]
    order_type = order_types_list[idx % len(order_types_list)]
    status = statuses[idx % len(statuses)]
    
    order = {
        'id': order_id,
        'order_number': sample_order['number'],
        'table_id': table['id'],
        'table_number': table['number'],
        'order_type_id': order_type['id'],
        'order_type_name': order_type['name'],
        'customer_name': sample_order['customer'],
        'items_count': sample_order['items'],
        'total_amount': sample_order['amount'],
        'status': status,
        'notes': '',
        'created_at': (datetime.now() - timedelta(days=idx)).isoformat(),
        'updated_at': (datetime.now() - timedelta(days=idx)).isoformat()
    }
    
    redis_client.set(f'order:{order_id}', json.dumps(order))
    redis_client.sadd('orders', order_id)
    created_count += 1
    print(f"✓ Created order: {sample_order['number']} for {sample_order['customer'] or 'Table ' + str(table['number'])}")

print(f"\n✓ Successfully created {created_count} orders!")
