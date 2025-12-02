"""
Inventory Agent for QSR (Quick Service Restaurant) System
6 Core Capabilities: 1) Stock monitoring, 2) Low stock alerts, 3) Demand forecasting,
4) Anomaly detection, 5) Waste prevention, 6) Purchase order generation
"""

from agno.agent import Agent
from agno.models.google import Gemini
import os
import redis
import json
from datetime import datetime, timedelta
from typing import Dict, List

# Import instructions and capabilities
from inventory_mng_instructions import inventory_instructions
from inventory_mng_capabilities import inventory_capabilities

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyD6v6dOt-hxwzcZWhwrizKfgM_oiwJjXTw")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# Initialize Redis
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

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
    """Inventory management helper for executing agent actions"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    # ===== CAPABILITY 1: CURRENT STOCK MONITORING =====
    def get_current_stock_status(self) -> Dict:
        """Get real-time stock levels for all food items"""
        food_ids = self.redis.smembers('food_items')
        stock_status = {
            'timestamp': datetime.now().isoformat(),
            'total_items': len(food_ids),
            'items': []
        }
        
        for food_id in food_ids:
            food_data = self.redis.get(f'food:{food_id}')
            if food_data:
                food_info = json.loads(food_data)
                current_stock = float(self.redis.get(f'stock:{food_id}') or food_info.get('max_capacity', 0))
                max_capacity = food_info.get('max_capacity', 100)
                stock_pct = (current_stock / max_capacity * 100) if max_capacity > 0 else 0
                
                status = 'critical' if stock_pct < 10 else 'low' if stock_pct < 30 else 'normal'
                
                stock_status['items'].append({
                    'food_id': food_id,
                    'food_name': food_info.get('name', 'Unknown'),
                    'current_stock': current_stock,
                    'max_capacity': max_capacity,
                    'stock_percentage': round(stock_pct, 1),
                    'status': status,
                    'unit': food_info.get('unit', 'units'),
                    'last_updated': self.redis.get(f'stock_updated:{food_id}') or datetime.now().isoformat()
                })
        
        return stock_status
    
    # ===== CAPABILITY 2: LOW STOCK ALERTS =====
    def generate_low_stock_alerts(self) -> List[Dict]:
        """Generate alerts for low/critical stock items"""
        stock_status = self.get_current_stock_status()
        alerts = []
        
        for item in stock_status['items']:
            if item['status'] in ['low', 'critical']:
                severity = 'critical' if item['status'] == 'critical' else 'warning'
                alert = {
                    'alert_id': f"alert_{item['food_id']}_{datetime.now().timestamp()}",
                    'timestamp': datetime.now().isoformat(),
                    'food_id': item['food_id'],
                    'food_name': item['food_name'],
                    'severity': severity,
                    'current_stock': item['current_stock'],
                    'threshold': item['max_capacity'] * (0.1 if severity == 'critical' else 0.3),
                    'action': 'immediate_reorder' if severity == 'critical' else 'schedule_reorder',
                    'recipient_agents': ['KitchenAgent', 'CustomerHandlingAgent'] if severity == 'warning' 
                                       else ['KitchenAgent', 'CustomerHandlingAgent', 'ManagerAgent']
                }
                
                # Store alert in Redis
                self.redis.sadd('alerts:low_stock', json.dumps(alert))
                alerts.append(alert)
        
        return alerts
    
    # ===== CAPABILITY 3: DEMAND FORECASTING (1-WEEK) =====
    def forecast_demand_1week(self, food_id: str) -> Dict:
        """Forecast demand for 1 week based on order history"""
        orders = self.redis.smembers('orders')
        food_orders = []
        
        # Collect order counts for this food item
        for order_id in orders:
            order_data = self.redis.get(f'order:{order_id}')
            if order_data:
                order_info = json.loads(order_data)
                # Count if this food item in order (simplified)
                if food_id in str(order_info):
                    food_orders.append(order_info)
        
        # Calculate daily average
        daily_avg = len(food_orders) / max(1, len(orders)) * 10  # Normalize to daily
        
        # Apply day-of-week patterns
        forecast = []
        for day in range(7):
            day_name = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][day]
            multiplier = 1.0
            if day in [4, 5]:  # Friday, Saturday
                multiplier = 1.4
            elif day == 6:  # Sunday
                multiplier = 1.2
            
            daily_demand = daily_avg * multiplier
            forecast.append(round(daily_demand, 2))
        
        food_data = self.redis.get(f'food:{food_id}')
        food_info = json.loads(food_data) if food_data else {}
        current_stock = float(self.redis.get(f'stock:{food_id}') or 0)
        
        return {
            'food_id': food_id,
            'food_name': food_info.get('name', 'Unknown'),
            'daily_forecast': forecast,
            'total_predicted_demand': sum(forecast),
            'current_stock': current_stock,
            'days_until_stockout': round(current_stock / max(1, max(forecast)), 1),
            'recommended_reorder_qty': max(0, food_info.get('max_capacity', 100) - current_stock),
            'confidence_level': 0.8
        }
    
    # ===== CAPABILITY 4: ANOMALY DETECTION (SPIKES) =====
    def detect_demand_spikes(self) -> List[Dict]:
        """Detect sudden demand spikes in rush hours"""
        # Get recent orders (last 1 hour)
        now = datetime.now()
        one_hour_ago = (now - timedelta(hours=1)).isoformat()
        
        recent_orders = []
        all_orders = self.redis.smembers('orders')
        
        for order_id in all_orders:
            order_data = self.redis.get(f'order:{order_id}')
            if order_data:
                order_info = json.loads(order_data)
                created_at = order_info.get('created_at', '')
                if created_at > one_hour_ago:
                    recent_orders.append(order_info)
        
        # Compare against baseline
        baseline_hourly = len(all_orders) / 24  # Rough baseline
        current_hourly = len(recent_orders)
        spike_percentage = ((current_hourly - baseline_hourly) / max(1, baseline_hourly)) * 100
        
        anomalies = []
        if spike_percentage > 50:  # 50% spike threshold
            anomalies.append({
                'anomaly_id': f"spike_{now.timestamp()}",
                'timestamp': now.isoformat(),
                'type': 'demand_spike',
                'spike_percentage': round(spike_percentage, 1),
                'orders_baseline_hourly': baseline_hourly,
                'orders_current_hourly': current_hourly,
                'status': 'active',
                'recommended_action': 'expedited_reorder|staff_alert'
            })
            
            # Store anomaly in Redis
            self.redis.sadd('anomalies:demand_spike', json.dumps(anomalies[0]))
        
        return anomalies
    
    # ===== CAPABILITY 5: SURPLUS STOCK & WASTE PREVENTION =====
    def detect_surplus_stock(self) -> List[Dict]:
        """Identify surplus inventory and waste prevention opportunities"""
        stock_status = self.get_current_stock_status()
        surplus_items = []
        
        for item in stock_status['items']:
            if item['stock_percentage'] > 80:
                # Get forecast
                forecast = self.forecast_demand_1week(item['food_id'])
                
                if forecast['total_predicted_demand'] < item['current_stock'] * 0.5:
                    surplus_items.append({
                        'food_id': item['food_id'],
                        'food_name': item['food_name'],
                        'current_stock': item['current_stock'],
                        'stock_percentage': item['stock_percentage'],
                        'forecast_7day_demand': forecast['total_predicted_demand'],
                        'excess_quantity': item['current_stock'] - forecast['total_predicted_demand'],
                        'waste_risk': 'high',
                        'recommendation': 'promotional_offer|staff_usage'
                    })
                    
                    # Store in Redis
                    self.redis.sadd('surplus_items', json.dumps(surplus_items[-1]))
        
        return surplus_items
    
    # ===== CAPABILITY 6: AUTOMATIC PURCHASE ORDER GENERATION =====
    def generate_purchase_orders(self) -> List[Dict]:
        """Generate automatic purchase orders for low stock items"""
        stock_status = self.get_current_stock_status()
        purchase_orders = []
        
        for item in stock_status['items']:
            if item['stock_percentage'] < 30:
                # Determine priority
                if item['stock_percentage'] < 10:
                    priority = 'critical'
                    lead_time_hours = 6
                else:
                    priority = 'medium'
                    lead_time_hours = 48
                
                # Generate purchase order
                po = {
                    'purchase_order_id': f"PO_{item['food_id']}_{datetime.now().timestamp()}",
                    'timestamp': datetime.now().isoformat(),
                    'food_id': item['food_id'],
                    'food_name': item['food_name'],
                    'quantity': round(item['max_capacity'] - item['current_stock'], 2),
                    'unit': item['unit'],
                    'priority': priority,
                    'estimated_delivery': (datetime.now() + timedelta(hours=lead_time_hours)).isoformat(),
                    'status': 'pending',
                    'supplier_id': 'default_supplier'
                }
                
                # Store in Redis
                self.redis.sadd('purchase_orders', json.dumps(po))
                purchase_orders.append(po)
        
        return purchase_orders


# Initialize manager
inventory_manager = InventoryManager(redis_client)


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
