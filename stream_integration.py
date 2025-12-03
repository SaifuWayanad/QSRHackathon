"""
Integration module to connect main Flask app with Kitchen Agent stream
Provides functions to push orders to stream when they're created
"""

from stream_db import StreamDB
import json

stream_db = StreamDB("stream_orders.db")


def push_order_to_stream(order_data: dict):
    """
    Push order from Flask app to stream database
    Called from app.py after order is created
    
    Args:
        order_data: Complete order dictionary with items
    """
    try:
        # Ensure order has all required fields
        order_payload = {
            'id': order_data.get('id'),
            'order_number': order_data.get('order_number'),
            'table_id': order_data.get('table_id'),
            'table_number': order_data.get('table_number'),
            'order_type_id': order_data.get('order_type_id'),
            'order_type_name': order_data.get('order_type_name'),
            'customer_name': order_data.get('customer_name'),
            'items_count': order_data.get('items_count'),
            'total_amount': order_data.get('total_amount'),
            'status': order_data.get('status', 'pending'),
            'notes': order_data.get('notes'),
            'items': order_data.get('items', []),
            'created_at': order_data.get('created_at'),
            'updated_at': order_data.get('updated_at')
        }
        
        # Add to stream
        stream_db.add_order(order_payload)
        return True
        
    except Exception as e:
        print(f"✗ Error pushing order to stream: {e}")
        return False


def get_kitchen_assignments(kitchen_id: str):
    """Get all pending assignments for a kitchen"""
    return stream_db.get_kitchen_assignments(kitchen_id)


def get_pending_orders():
    """Get all pending orders from stream"""
    return stream_db.get_pending_orders()


def complete_kitchen_assignment(assignment_id: str):
    """Mark a kitchen assignment as completed"""
    stream_db.complete_assignment(assignment_id)


def get_order_status(order_id: str) -> dict:
    """Get status of an order in the stream"""
    conn = stream_db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, status, assigned_to_kitchen, created_at
        FROM orders_stream
        WHERE id = ?
    ''', (order_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'order_id': row[0],
            'status': row[1],
            'assigned_to_kitchen': row[2],
            'created_at': row[3]
        }
    return None
