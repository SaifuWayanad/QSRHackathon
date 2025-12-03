import sqlite3
import json
from datetime import datetime
import threading
import time
from typing import Optional, Dict, List

class StreamDB:
    """Stream database for real-time order processing"""
    
    def __init__(self, db_path: str = "stream_orders.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize stream database with tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create orders stream table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders_stream (
                id TEXT PRIMARY KEY,
                order_data TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                assigned_to_kitchen TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create kitchen assignments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS kitchen_assignments (
                id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                kitchen_id TEXT NOT NULL,
                kitchen_name TEXT,
                items TEXT NOT NULL,
                status TEXT DEFAULT 'assigned',
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders_stream(id)
            )
        ''')
        
        # Create kitchen status tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS kitchen_status (
                id TEXT PRIMARY KEY,
                kitchen_id TEXT NOT NULL,
                kitchen_name TEXT NOT NULL,
                current_load INTEGER DEFAULT 0,
                max_capacity INTEGER DEFAULT 10,
                status TEXT DEFAULT 'idle',
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(kitchen_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✓ Stream database initialized")
    
    def add_order(self, order_data: Dict) -> str:
        """Add a new order to the stream"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        order_id = order_data.get('id', str(datetime.now().timestamp()))
        order_json = json.dumps(order_data)
        
        cursor.execute('''
            INSERT INTO orders_stream (id, order_data, status)
            VALUES (?, ?, 'pending')
        ''', (order_id, order_json))
        
        conn.commit()
        conn.close()
        
        print(f"✓ Order {order_id} added to stream")
        return order_id
    
    def get_pending_orders(self) -> List[Dict]:
        """Get all pending orders from stream"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, order_data FROM orders_stream 
            WHERE status = 'pending' 
            ORDER BY created_at ASC
        ''')
        
        orders = []
        for row in cursor.fetchall():
            orders.append({
                'id': row['id'],
                'data': json.loads(row['order_data'])
            })
        
        conn.close()
        return orders
    
    def update_order_status(self, order_id: str, status: str, kitchen_id: Optional[str] = None):
        """Update order status in stream"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE orders_stream 
            SET status = ?, assigned_to_kitchen = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (status, kitchen_id, order_id))
        
        conn.commit()
        conn.close()
    
    def assign_to_kitchen(self, order_id: str, kitchen_id: str, kitchen_name: str, items: List[Dict]):
        """Create kitchen assignment"""
        import uuid
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        assignment_id = str(uuid.uuid4())
        items_json = json.dumps(items)
        
        cursor.execute('''
            INSERT INTO kitchen_assignments (id, order_id, kitchen_id, kitchen_name, items, status)
            VALUES (?, ?, ?, ?, ?, 'assigned')
        ''', (assignment_id, order_id, kitchen_id, kitchen_name, items_json))
        
        # Update order status
        cursor.execute('''
            UPDATE orders_stream 
            SET status = 'assigned', assigned_to_kitchen = ?
            WHERE id = ?
        ''', (kitchen_id, order_id))
        
        conn.commit()
        conn.close()
        
        return assignment_id
    
    def get_kitchen_assignments(self, kitchen_id: str) -> List[Dict]:
        """Get all assignments for a kitchen"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, order_id, items, status, assigned_at
            FROM kitchen_assignments
            WHERE kitchen_id = ? AND status != 'completed'
            ORDER BY assigned_at ASC
        ''', (kitchen_id,))
        
        assignments = []
        for row in cursor.fetchall():
            assignments.append({
                'id': row['id'],
                'order_id': row['order_id'],
                'items': json.loads(row['items']),
                'status': row['status'],
                'assigned_at': row['assigned_at']
            })
        
        conn.close()
        return assignments
    
    def update_kitchen_load(self, kitchen_id: str, load: int):
        """Update kitchen current load"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE kitchen_status 
            SET current_load = ?, last_updated = CURRENT_TIMESTAMP
            WHERE kitchen_id = ?
        ''', (load, kitchen_id))
        
        conn.commit()
        conn.close()
    
    def get_kitchen_status(self, kitchen_id: str) -> Optional[Dict]:
        """Get kitchen status"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM kitchen_status WHERE kitchen_id = ?
        ''', (kitchen_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def complete_assignment(self, assignment_id: str):
        """Mark assignment as completed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE kitchen_assignments 
            SET status = 'completed', completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (assignment_id,))
        
        conn.commit()
        conn.close()
