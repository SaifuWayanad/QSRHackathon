#!/usr/bin/env python3
"""
Test script to demonstrate Kitchen Agent with Stream Database
Shows how orders flow from creation → stream → agent → kitchen assignment
"""

import json
import time
import uuid
from datetime import datetime
from stream_db import StreamDB
from order_monitor import OrderMonitor

# Sample order data (matches the order.json structure)
SAMPLE_ORDER = {
    "id": str(uuid.uuid4()),
    "order_number": "ORD-2025-TEST-001",
    "table_id": "table-001",
    "table_number": "5",
    "table_area": "Main Dining",
    "order_type_id": "type-001",
    "order_type_name": "Dine-in",
    "customer_name": "John Doe",
    "items_count": 3,
    "total_amount": 45.99,
    "status": "pending",
    "notes": "No onions on the burger, extra sauce on the side",
    "created_at": datetime.now().isoformat(),
    "updated_at": datetime.now().isoformat(),
    "items": [
        {
            "id": str(uuid.uuid4()),
            "order_id": "",  # Will be set
            "food_item_id": "food-101",
            "food_name": "Grilled Chicken Burger",
            "category_name": "Burgers",
            "quantity": 1,
            "price": 12.99,
            "notes": "No onions, extra sauce on the side",
            "created_at": datetime.now().isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "order_id": "",  # Will be set
            "food_item_id": "food-102",
            "food_name": "Caesar Salad",
            "category_name": "Salads",
            "quantity": 1,
            "price": 9.99,
            "notes": "Dressing on the side",
            "created_at": datetime.now().isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "order_id": "",  # Will be set
            "food_item_id": "food-103",
            "food_name": "Iced Tea",
            "category_name": "Beverages",
            "quantity": 2,
            "price": 2.99,
            "notes": "Extra ice",
            "created_at": datetime.now().isoformat()
        }
    ]
}


def demo_order_flow():
    """Demonstrate complete order flow"""
    
    print("=" * 70)
    print("🍳 KITCHEN AGENT STREAM DEMO")
    print("=" * 70)
    
    # Initialize stream database
    stream_db = StreamDB("stream_orders_test.db")
    monitor = OrderMonitor(stream_db, check_interval=1)
    
    print("\n✓ Stream database initialized\n")
    
    # Define callback to process orders
    def process_order(order_data):
        print(f"\n{'='*70}")
        print(f"📋 ORDER RECEIVED BY AGENT")
        print(f"{'='*70}")
        print(f"Order #: {order_data.get('order_number')}")
        print(f"Customer: {order_data.get('customer_name')}")
        print(f"Items: {order_data.get('items_count')}")
        print(f"Total: ${order_data.get('total_amount')}")
        
        # Get items by kitchen
        kitchen_items = monitor.get_items_by_kitchen(order_data)
        
        print(f"\n🏪 KITCHEN ROUTING:")
        for kitchen, items in kitchen_items.items():
            assignment_id = stream_db.assign_to_kitchen(
                order_id=order_data.get('id'),
                kitchen_id=kitchen,
                kitchen_name=kitchen.replace('_', ' ').title(),
                items=items
            )
            print(f"   ✓ {kitchen.upper()}: {len(items)} items")
            for item in items:
                print(f"      - {item['food_name']} × {item['quantity']}")
            print(f"        → Assignment ID: {assignment_id[:8]}...")
    
    # Register callback
    monitor.on_new_order(process_order)
    
    # Start monitoring in background
    monitor.start()
    
    print("✓ Monitor started, waiting for orders...\n")
    
    # Simulate order placement
    print(f"{'='*70}")
    print("🚀 PLACING TEST ORDER")
    print(f"{'='*70}")
    
    order_copy = SAMPLE_ORDER.copy()
    order_copy['items'] = [
        {**item, 'order_id': order_copy['id']} 
        for item in order_copy['items']
    ]
    
    order_id = stream_db.add_order(order_copy)
    print(f"\n✓ Order {order_copy['order_number']} added to stream")
    print(f"  Order ID: {order_id}")
    
    # Wait for processing
    print("\n⏳ Processing order (5 seconds)...\n")
    time.sleep(5)
    
    # Display final status
    print(f"\n{'='*70}")
    print("📊 FINAL STATUS")
    print(f"{'='*70}")
    
    assignments = stream_db.get_kitchen_assignments('main_kitchen')
    print(f"\nMain Kitchen Assignments: {len(assignments)}")
    for a in assignments:
        print(f"  - Order: {a['order_id'][:8]}... | Status: {a['status']}")
    
    assignments = stream_db.get_kitchen_assignments('prep_kitchen')
    print(f"\nPrep Kitchen Assignments: {len(assignments)}")
    for a in assignments:
        print(f"  - Order: {a['order_id'][:8]}... | Status: {a['status']}")
    
    assignments = stream_db.get_kitchen_assignments('bar')
    print(f"\nBar Assignments: {len(assignments)}")
    for a in assignments:
        print(f"  - Order: {a['order_id'][:8]}... | Status: {a['status']}")
    
    # Stop monitor
    print(f"\n{'='*70}")
    monitor.stop()
    print("✓ Demo complete!")


if __name__ == '__main__':
    demo_order_flow()
