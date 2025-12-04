"""
Order Monitor - Background task that runs every 5 seconds
Counts orders from the current day and tracks kitchen metrics
"""

import pymysql
import pymysql.cursors
import threading
import time
from datetime import datetime, date
from typing import Dict, Optional
from .communications import EventBus
import sys
import os

# Add parent directory to path to import constants
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from constants import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE


class OrderMonitor:
    """Background monitor that tracks today's orders"""
    
    def __init__(self):
        """Initialize the order monitor"""
        self.running = False
        self.thread = None
        self.poll_interval = 30  # Run every 30 seconds
        
        # Store current metrics
        self.current_metrics = {
            'total_orders_today': 0,
            'pending_orders': 0,
            'preparing_orders': 0,
            'ready_orders': 0,
            'completed_orders': 0,
            'cancelled_orders': 0,
            'total_items_today': 0,
            'timestamp': datetime.now().isoformat(),
            'total_amount_today': 0.0
        }
    
    def _get_db_connection(self):
        """Get database connection"""
        try:
            conn = pymysql.connect(
                host=MYSQL_HOST,
                port=MYSQL_PORT,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                database=MYSQL_DATABASE,
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=False,
                ssl={'ssl': False}
            )
            return conn
        except Exception as e:
            print(f"Error connecting to database: {e}")
            return None
    
    def _get_today_date_range(self):
        """Get today's date range for queries"""
        today = date.today()
        start_of_day = f"{today.isoformat()} 00:00:00"
        end_of_day = f"{today.isoformat()} 23:59:59"
        return start_of_day, end_of_day
    
    def count_orders_today(self) -> int:
        """
        Count total orders created today
        
        Returns:
            int: Number of orders created today
        """
        conn = self._get_db_connection()
        if not conn:
            return 0
        
        try:
            cursor = conn.cursor()
            today = date.today().isoformat()
            
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM orders 
                WHERE DATE(created_at) = %s
            """, (today,))
            
            result = cursor.fetchone()
            count = result['count'] if result else 0
            conn.close()
            return count
        
        except Exception as e:
            print(f"Error counting orders: {e}")
            conn.close()
            return 0
    
    def get_today_orders_by_status(self) -> Dict[str, int]:
        """
        Get breakdown of today's orders by status
        
        Returns:
            dict: Orders count by status
        """
        conn = self._get_db_connection()
        if not conn:
            return {}
        
        try:
            cursor = conn.cursor()
            today = date.today().isoformat()
            
            cursor.execute("""
                SELECT status, COUNT(*) as count 
                FROM orders 
                WHERE DATE(created_at) = %s
                GROUP BY status
            """, (today,))
            
            results = cursor.fetchall()
            status_breakdown = {row['status']: row['count'] for row in results}
            conn.close()
            return status_breakdown
        
        except Exception as e:
            print(f"Error getting order breakdown: {e}")
            conn.close()
            return {}
    
    def get_today_total_amount(self) -> float:
        """
        Get total amount for all orders today
        
        Returns:
            float: Total amount for today's orders
        """
        conn = self._get_db_connection()
        if not conn:
            return 0.0
        
        try:
            cursor = conn.cursor()
            today = date.today().isoformat()
            
            cursor.execute("""
                SELECT COALESCE(SUM(total_amount), 0) as total 
                FROM orders 
                WHERE DATE(created_at) = %s AND total_amount > 0
            """, (today,))
            
            result = cursor.fetchone()
            total = result['total'] if result else 0.0
            conn.close()
            return float(total)
        
        except Exception as e:
            print(f"Error getting total amount: {e}")
            conn.close()
            return 0.0
    
    def get_today_items_count(self) -> int:
        """
        Get total items count for today's orders
        
        Returns:
            int: Total items in today's orders
        """
        conn = self._get_db_connection()
        if not conn:
            return 0
        
        try:
            cursor = conn.cursor()
            today = date.today().isoformat()
            
            cursor.execute("""
                SELECT COALESCE(SUM(items_count), 0) as total 
                FROM orders 
                WHERE DATE(created_at) = %s
            """, (today,))
            
            result = cursor.fetchone()
            count = result['total'] if result else 0
            conn.close()
            return int(count)
        
        except Exception as e:
            print(f"Error getting items count: {e}")
            conn.close()
            return 0
    
    def update_metrics(self):
        """Update all metrics for today's orders"""
        try:
            # Get all metrics
            total_orders = self.count_orders_today()
            status_breakdown = self.get_today_orders_by_status()
            total_amount = self.get_today_total_amount()
            total_items = self.get_today_items_count()
            
            # Update current metrics
            self.current_metrics = {
                'total_orders_today': total_orders,
                'pending_orders': status_breakdown.get('pending', 0),
                'preparing_orders': status_breakdown.get('preparing', 0),
                'ready_orders': status_breakdown.get('ready', 0),
                'completed_orders': status_breakdown.get('completed', 0),
                'cancelled_orders': status_breakdown.get('cancelled', 0),
                'total_items_today': total_items,
                'total_amount_today': total_amount,
                'timestamp': datetime.now().isoformat(),
                'status_breakdown': status_breakdown
            }
            print(f"✓ Metrics updated - Pending: {self.current_metrics['pending_orders']}")
            
            # Trigger event asynchronously if there are pending orders
            if self.current_metrics["pending_orders"] > 0:
                print(f"🔔 There are {self.current_metrics['pending_orders']} pending orders!")
                try:
                    print("📤 Creating EventBus thread...")
                    # Run EventBus call in a separate thread to avoid blocking
                    event_thread = threading.Thread(
                        target=lambda: EventBus("new_order_recieved").process_event(),
                        daemon=True,
                        name="EventBusThread"
                    )
                    print("🚀 Starting EventBus thread...")
                    event_thread.start()
                    print(f"✓ Event thread started (is_alive: {event_thread.is_alive()})")
                except Exception as e:
                    print(f"⚠️  Error starting event thread: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print("ℹ️  No pending orders - skipping event trigger")

            return self.current_metrics
        
        except Exception as e:
            print(f"Error updating metrics: {e}")
            return self.current_metrics
    
    def _monitor_loop(self):
        """Main monitoring loop that runs every 5 seconds"""
        print(f"🔄 Order Monitor started (polling every {self.poll_interval} seconds)")
        
        while self.running:
            try:
                # Update metrics
                metrics = self.update_metrics()

                
                # Print current status
                # print(f"\n📊 [{datetime.now().strftime('%H:%M:%S')}] Daily Order Count")
                # print(f"   Total Orders: {metrics['total_orders_today']}")
                # print(f"   Pending: {metrics['pending_orders']} | Preparing: {metrics['preparing_orders']} | Ready: {metrics['ready_orders']} | Completed: {metrics['completed_orders']}")
                # print(f"   Total Items: {metrics['total_items_today']}")
                # print(f"   Revenue: ${metrics['total_amount_today']:.2f}")
                
                # Wait before next poll
                time.sleep(self.poll_interval)
            
            except Exception as e:
                print(f"❌ Error in monitor loop: {e}")
                time.sleep(self.poll_interval)
    
    def start(self):
        """Start the order monitor in a background thread"""
        if self.running:
            print("⚠️  Order Monitor already running")
            return
        
        # Immediately update metrics before starting the loop
        print("🔄 Running initial metrics update...")
        self.update_metrics()
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        print("✓ Order Monitor started in background thread")
    
    def stop(self):
        """Stop the order monitor"""
        if not self.running:
            print("⚠️  Order Monitor not running")
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("✓ Order Monitor stopped")
    
    def get_metrics(self) -> Dict:
        """
        Get current metrics
        
        Returns:
            dict: Current metrics snapshot
        """
        return self.current_metrics.copy()
    
    def get_today_summary(self) -> Dict:
        """
        Get a comprehensive summary of today's orders
        
        Returns:
            dict: Complete summary with all statistics
        """
        metrics = self.get_metrics()
        
        return {
            'success': True,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'summary': {
                'total_orders': metrics['total_orders_today'],
                'total_items': metrics['total_items_today'],
                'total_revenue': metrics['total_amount_today'],
                'orders_by_status': metrics.get('status_breakdown', {}),
                'average_order_value': round(
                    metrics['total_amount_today'] / metrics['total_orders_today'] 
                    if metrics['total_orders_today'] > 0 else 0, 2
                ),
                'last_updated': metrics['timestamp']
            }
        }


# Global instance
_order_monitor_instance = None


def get_order_monitor() -> OrderMonitor:
    """Get or create the global order monitor instance"""
    global _order_monitor_instance
    if _order_monitor_instance is None:
        _order_monitor_instance = OrderMonitor()
    return _order_monitor_instance


def start_order_monitor():
    """Start the order monitor"""
    monitor = get_order_monitor()
    monitor.start()


def stop_order_monitor():
    """Stop the order monitor"""
    monitor = get_order_monitor()
    monitor.stop()


def get_today_orders_count() -> int:
    """Convenience function to get today's order count"""
    monitor = get_order_monitor()
    return monitor.current_metrics['total_orders_today']


def get_today_summary() -> Dict:
    """Convenience function to get today's summary"""
    monitor = get_order_monitor()
    return monitor.get_today_summary()


# if __name__ == "__main__":
#     # Test the monitor
#     print("Testing Order Monitor...\n")
    
#     monitor = OrderMonitor()
    
#     # Get initial count
#     print(f"Initial order count today: {monitor.count_orders_today()}")
    
#     # Start monitor
#     monitor.start()
    
#     try:
#         # Let it run for 20 seconds
#         time.sleep(20)
#     except KeyboardInterrupt:
#         pass
#     finally:
#         monitor.stop()
#         print("\n✓ Monitor test complete")
