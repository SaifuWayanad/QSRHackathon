"""
Inventory Agent for QSR (Quick Service Restaurant) System
6 Core Capabilities: 1) Stock monitoring, 2) Low stock alerts, 3) Demand forecasting,
4) Anomaly detection, 5) Waste prevention, 6) Purchase order generation
"""

from agno.agent import Agent
from agno.models.google import Gemini
import os
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List

# Import instructions and capabilities
from inventory_mng_instructions import inventory_instructions
from inventory_mng_capabilities import inventory_capabilities

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyD6v6dOt-hxwzcZWhwrizKfgM_oiwJjXTw")
DB_PATH = os.getenv("DB_PATH", "my_database.db")

# Initialize SQLite connection
def get_db_connection():
    """Get SQLite database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Initialize Gemini Model
gemini_model = Gemini("gemini-2.5-flash", api_key=GEMINI_API_KEY)

# Create Agno Agent with Gemini
inventory_agent = Agent(
    name="InventoryManagementAgent",
    model=gemini_model,
    capabilities=inventory_capabilities,
    instructions=inventory_instructions
)


class InventoryManager:
    """Inventory management helper for SQLite-based inventory operations"""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
    
    # ===== CAPABILITY 1: CURRENT STOCK MONITORING (SQLite) =====
    def get_current_stock_status(self) -> Dict:
        """Get real-time stock levels based on daily_production and order_items"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Query: Get production and sales data for today
            cursor.execute("""
                SELECT 
                    fi.id,
                    fi.name,
                    fi.kitchen_id,
                    fi.kitchen_name,
                    COALESCE(dp.produced, 0) as produced_today,
                    COALESCE(SUM(oi.quantity), 0) as sold_today
                FROM food_items fi
                LEFT JOIN daily_production dp ON fi.id = dp.food_id AND dp.date = DATE('now')
                LEFT JOIN order_items oi ON fi.id = oi.food_item_id AND DATE(oi.created_at) = DATE('now')
                GROUP BY fi.id
                ORDER BY fi.name
            """)
            
            results = cursor.fetchall()
            stock_status = {
                'timestamp': datetime.now().isoformat(),
                'total_items': len(results),
                'items': []
            }
            
            for row in results:
                availability = row['produced_today'] - row['sold_today']
                status = 'critical' if availability <= 0 else 'low' if availability < 5 else 'normal'
                
                stock_status['items'].append({
                    'food_id': row['id'],
                    'food_name': row['name'],
                    'kitchen': row['kitchen_name'],
                    'produced_today': row['produced_today'],
                    'sold_today': row['sold_today'],
                    'availability': max(0, availability),
                    'status': status
                })
            
            return stock_status
        
        finally:
            conn.close()
    
    # ===== CAPABILITY 2: LOW STOCK ALERTS =====
    def generate_low_stock_alerts(self) -> List[Dict]:
        """Generate alerts for low/critical stock items"""
        conn = get_db_connection()
        cursor = conn.cursor()
        alerts = []
        
        try:
            stock_status = self.get_current_stock_status()
            
            for item in stock_status['items']:
                if item['status'] in ['low', 'critical']:
                    severity = 'critical' if item['status'] == 'critical' else 'warning'
                    alert = {
                        'alert_id': f"alert_{item['food_id']}_{datetime.now().timestamp()}",
                        'timestamp': datetime.now().isoformat(),
                        'food_id': item['food_id'],
                        'food_name': item['food_name'],
                        'severity': severity,
                        'availability': item['availability'],
                        'threshold': 0 if severity == 'critical' else 5,
                        'action': 'immediate_production' if severity == 'critical' else 'schedule_production',
                        'recipient_agents': ['KitchenAgent', 'CustomerHandlingAgent'] if severity == 'warning' 
                                           else ['KitchenAgent', 'CustomerHandlingAgent', 'ManagerAgent']
                    }
                    
                    # Update food_items status if critical
                    if severity == 'critical':
                        cursor.execute("UPDATE food_items SET status = 'unavailable' WHERE id = ?", (item['food_id'],))
                        conn.commit()
                    
                    alerts.append(alert)
            
            return alerts
        
        finally:
            conn.close()
    
    # ===== CAPABILITY 3: DEMAND FORECASTING (1-WEEK) =====
    def forecast_demand_1week(self, food_id: str) -> Dict:
        """Forecast demand for 1 week based on order history"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Get last 7 days of orders for this food item
            cursor.execute("""
                SELECT DATE(oi.created_at) as order_date, SUM(oi.quantity) as daily_quantity
                FROM order_items oi
                WHERE oi.food_item_id = ? AND oi.created_at >= DATE('now', '-7 days')
                GROUP BY DATE(oi.created_at)
                ORDER BY order_date
            """, (food_id,))
            
            results = cursor.fetchall()
            daily_data = {row['order_date']: row['daily_quantity'] for row in results}
            
            # Calculate average
            total_demand = sum(daily_data.values()) if daily_data else 0
            daily_avg = total_demand / 7 if total_demand > 0 else 1
            
            # Get food item details
            cursor.execute("SELECT name FROM food_items WHERE id = ?", (food_id,))
            food_row = cursor.fetchone()
            food_name = food_row['name'] if food_row else 'Unknown'
            
            # Get current availability
            cursor.execute("""
                SELECT 
                    COALESCE(dp.produced, 0) - COALESCE(SUM(oi.quantity), 0) as availability
                FROM food_items fi
                LEFT JOIN daily_production dp ON fi.id = dp.food_id AND dp.date = DATE('now')
                LEFT JOIN order_items oi ON fi.id = oi.food_item_id AND DATE(oi.created_at) = DATE('now')
                WHERE fi.id = ?
            """, (food_id,))
            
            stock_row = cursor.fetchone()
            current_availability = max(0, stock_row['availability'] if stock_row else 0)
            
            # Generate 7-day forecast with day-of-week multipliers
            forecast = []
            for day in range(7):
                # 0=Mon, 1=Tue, ... 4=Fri, 5=Sat, 6=Sun
                multiplier = 1.0
                if day in [4, 5]:  # Friday, Saturday
                    multiplier = 1.4
                elif day == 6:  # Sunday
                    multiplier = 1.2
                
                daily_demand = daily_avg * multiplier
                forecast.append(round(daily_demand, 2))
            
            days_until_stockout = current_availability / max(1, max(forecast))
            
            return {
                'food_id': food_id,
                'food_name': food_name,
                'daily_forecast': forecast,
                'total_predicted_demand': sum(forecast),
                'current_availability': current_availability,
                'days_until_stockout': round(days_until_stockout, 1),
                'confidence_level': 0.8 if daily_data else 0.5
            }
        
        finally:
            conn.close()
    
    # ===== CAPABILITY 4: ANOMALY DETECTION (SPIKES) =====
    def detect_demand_spikes(self) -> List[Dict]:
        """Detect sudden demand spikes in rush hours"""
        conn = get_db_connection()
        cursor = conn.cursor()
        anomalies = []
        
        try:
            # Get recent orders (last 1 hour)
            cursor.execute("""
                SELECT oi.food_item_id, SUM(oi.quantity) as hourly_quantity
                FROM order_items oi
                WHERE oi.created_at >= DATETIME('now', '-1 hour')
                GROUP BY oi.food_item_id
            """)
            
            recent_orders = cursor.fetchall()
            
            # Get baseline (last 24 hours average per hour)
            cursor.execute("""
                SELECT COUNT(DISTINCT oi.id) / 24.0 as baseline_hourly_orders
                FROM order_items oi
                WHERE oi.created_at >= DATETIME('now', '-24 hours')
            """)
            
            baseline_result = cursor.fetchone()
            baseline_hourly = baseline_result['baseline_hourly_orders'] if baseline_result else 1
            current_hourly = len(recent_orders)
            spike_percentage = ((current_hourly - baseline_hourly) / max(1, baseline_hourly)) * 100
            
            if spike_percentage > 50:  # 50% spike threshold
                anomalies.append({
                    'anomaly_id': f"spike_{datetime.now().timestamp()}",
                    'timestamp': datetime.now().isoformat(),
                    'type': 'demand_spike',
                    'spike_percentage': round(spike_percentage, 1),
                    'orders_baseline_hourly': baseline_hourly,
                    'orders_current_hourly': current_hourly,
                    'affected_items': [r['food_item_id'] for r in recent_orders[:5]],
                    'status': 'active',
                    'recommended_action': 'expedited_production|staff_alert'
                })
            
            return anomalies
        
        finally:
            conn.close()
    
    # ===== CAPABILITY 5: SURPLUS STOCK & WASTE PREVENTION =====
    def detect_surplus_stock(self) -> List[Dict]:
        """Identify surplus inventory and waste prevention opportunities"""
        conn = get_db_connection()
        cursor = conn.cursor()
        surplus_items = []
        
        try:
            stock_status = self.get_current_stock_status()
            
            for item in stock_status['items']:
                # Check for over-production (produced > 20 units with low sales)
                if item['produced_today'] > 20 and item['sold_today'] < (item['produced_today'] * 0.3):
                    forecast = self.forecast_demand_1week(item['food_id'])
                    
                    surplus_items.append({
                        'food_id': item['food_id'],
                        'food_name': item['food_name'],
                        'produced_today': item['produced_today'],
                        'sold_today': item['sold_today'],
                        'availability': item['availability'],
                        'forecast_7day_demand': forecast['total_predicted_demand'],
                        'waste_risk': 'high' if item['availability'] > forecast['total_predicted_demand'] else 'medium',
                        'recommendation': 'promotional_offer|staff_usage|reduce_production'
                    })
            
            return surplus_items
        
        finally:
            conn.close()
    
    # ===== CAPABILITY 6: AUTOMATIC PURCHASE ORDER GENERATION =====
    def generate_purchase_orders(self) -> List[Dict]:
        """Generate automatic purchase orders for low/critical items"""
        conn = get_db_connection()
        cursor = conn.cursor()
        purchase_orders = []
        
        try:
            stock_status = self.get_current_stock_status()
            
            for item in stock_status['items']:
                if item['status'] in ['low', 'critical']:
                    forecast = self.forecast_demand_1week(item['food_id'])
                    
                    # Determine priority and lead time
                    if item['status'] == 'critical':
                        priority = 'critical'
                        lead_time_hours = 4
                    else:
                        priority = 'high'
                        lead_time_hours = 24
                    
                    # Recommended production quantity based on 7-day forecast
                    recommended_qty = max(20, int(forecast['total_predicted_demand'] * 1.2))
                    
                    po = {
                        'purchase_order_id': f"PO_{item['food_id']}_{datetime.now().timestamp()}",
                        'timestamp': datetime.now().isoformat(),
                        'food_id': item['food_id'],
                        'food_name': item['food_name'],
                        'recommended_production_qty': recommended_qty,
                        'current_availability': item['availability'],
                        '7day_forecast': forecast['total_predicted_demand'],
                        'priority': priority,
                        'estimated_ready_time': (datetime.now() + timedelta(hours=lead_time_hours)).isoformat(),
                        'status': 'pending',
                        'target_kitchen': item['kitchen']
                    }
                    
                    purchase_orders.append(po)
            
            return purchase_orders
        
        finally:
            conn.close()


# Initialize manager
inventory_manager = InventoryManager()


def run_inventory_agent_analysis():
    """Run full inventory agent analysis with all 6 capabilities"""
    print("\n" + "="*80)
    print("INVENTORY MANAGEMENT AGENT - FULL ANALYSIS")
    print("="*80)
    
    try:
        # Capability 1: Current Stock
        print("\n[1] CURRENT STOCK MONITORING")
        print("-" * 80)
        stock = inventory_manager.get_current_stock_status()
        print(f"Total items tracked: {stock['total_items']}")
        for item in stock['items'][:5]:
            print(f"  • {item['food_name']}: {item['current_stock']:.1f}/{item['max_capacity']} ({item['stock_percentage']:.1f}%) - {item['status'].upper()}")
        
        # Capability 2: Low Stock Alerts
        print("\n[2] LOW STOCK ALERTS")
        print("-" * 80)
        alerts = inventory_manager.generate_low_stock_alerts()
        if alerts:
            for alert in alerts[:3]:
                print(f"  🚨 {alert['severity'].upper()}: {alert['food_name']} - {alert['action']}")
        else:
            print("  ✓ All items in normal stock")
        
        # Capability 3: Demand Forecasting
        print("\n[3] DEMAND FORECASTING (1-WEEK)")
        print("-" * 80)
        if stock['items']:
            forecast = inventory_manager.forecast_demand_1week(stock['items'][0]['food_id'])
            print(f"  Item: {forecast['food_name']}")
            print(f"  Daily Forecast: {forecast['daily_forecast']}")
            print(f"  Total 7-day demand: {forecast['total_predicted_demand']:.1f} units")
            print(f"  Days until stockout: {forecast['days_until_stockout']}")
        
        # Capability 4: Anomaly Detection
        print("\n[4] ANOMALY DETECTION (DEMAND SPIKES)")
        print("-" * 80)
        anomalies = inventory_manager.detect_demand_spikes()
        if anomalies:
            for anom in anomalies:
                print(f"  ⚡ SPIKE DETECTED: {anom['spike_percentage']:.1f}% increase")
                print(f"    Action: {anom['recommended_action']}")
        else:
            print("  ✓ No demand spikes detected")
        
        # Capability 5: Surplus & Waste
        print("\n[5] SURPLUS STOCK & WASTE PREVENTION")
        print("-" * 80)
        surplus = inventory_manager.detect_surplus_stock()
        if surplus:
            for item in surplus[:3]:
                print(f"  ⚠ {item['food_name']}: {item['excess_quantity']:.1f} units excess")
                print(f"    Recommendation: {item['recommendation']}")
        else:
            print("  ✓ No surplus items detected")
        
        # Capability 6: Purchase Orders
        print("\n[6] AUTOMATIC PURCHASE ORDER GENERATION")
        print("-" * 80)
        purchase_orders = inventory_manager.generate_purchase_orders()
        if purchase_orders:
            for po in purchase_orders[:3]:
                print(f"  📦 Order: {po['food_name']}")
                print(f"    Quantity: {po['quantity']} {po['unit']}")
                print(f"    Priority: {po['priority'].upper()}")
                print(f"    Delivery: {po['estimated_delivery']}")
        else:
            print("  ✓ No purchase orders needed")
        
        print("\n" + "="*80)
        print("✓ INVENTORY ANALYSIS COMPLETE")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")


if __name__ == '__main__':
    run_inventory_agent_analysis()
