import threading
import time
from typing import Callable, Dict, List
from stream_db import StreamDB
import json

class OrderMonitor:
    """Monitor stream database for new orders and notify agent"""
    
    def __init__(self, stream_db: StreamDB, check_interval: int = 2):
        self.stream_db = stream_db
        self.check_interval = check_interval
        self.running = False
        self.monitor_thread = None
        self.callbacks = []
        self.processed_orders = set()
    
    def on_new_order(self, callback: Callable):
        """Register callback for new orders"""
        self.callbacks.append(callback)
        return self
    
    def start(self):
        """Start monitoring stream database"""
        if self.running:
            print("⚠️  Monitor already running")
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print("✓ Order monitor started")
    
    def stop(self):
        """Stop monitoring"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        print("✓ Order monitor stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                # Get pending orders
                pending_orders = self.stream_db.get_pending_orders()
                
                for order in pending_orders:
                    order_id = order['id']
                    
                    # Skip if already processed
                    if order_id in self.processed_orders:
                        continue
                    
                    # Mark as processed
                    self.processed_orders.add(order_id)
                    
                    # Notify all callbacks
                    for callback in self.callbacks:
                        try:
                            callback(order['data'])
                        except Exception as e:
                            print(f"✗ Error in callback: {e}")
                
                # Check interval
                time.sleep(self.check_interval)
                
            except Exception as e:
                print(f"✗ Monitor error: {e}")
                time.sleep(self.check_interval)
    
    def get_order_summary(self, order_data: Dict) -> Dict:
        """Extract summary from order data"""
        items = order_data.get('items', [])
        
        # Group items by category
        categories = {}
        for item in items:
            category = item.get('category_name', 'Other')
            if category not in categories:
                categories[category] = []
            categories[category].append(item)
        
        return {
            'order_id': order_data.get('id'),
            'order_number': order_data.get('order_number'),
            'customer_name': order_data.get('customer_name'),
            'items_count': len(items),
            'categories': categories,
            'total_amount': order_data.get('total_amount'),
            'status': order_data.get('status'),
            'notes': order_data.get('notes'),
            'full_data': order_data
        }
    
    def get_items_by_kitchen(self, order_data: Dict) -> Dict[str, List]:
        """Organize order items by kitchen type"""
        items = order_data.get('items', [])
        
        # Map categories to kitchens
        kitchen_mapping = {
            'Burgers': 'main_kitchen',
            'Salads': 'prep_kitchen',
            'Beverages': 'bar',
            'Desserts': 'pastry_kitchen',
            'Appetizers': 'main_kitchen',
            'Main Course': 'main_kitchen',
            'Grilled Items': 'grill',
        }
        
        kitchen_items = {}
        
        for item in items:
            category = item.get('category_name', 'Other')
            kitchen = kitchen_mapping.get(category, 'general_kitchen')
            
            if kitchen not in kitchen_items:
                kitchen_items[kitchen] = []
            
            kitchen_items[kitchen].append(item)
        
        return kitchen_items
