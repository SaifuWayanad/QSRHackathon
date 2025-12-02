"""
Inventory Agent for QSR (Quick Service Restaurant) System

This agent manages inventory with the following capabilities:
- Real-time ingredient level monitoring
- Predictive forecasting of ingredient demand using demand patterns
- Alerts for low stock levels
- Automatic purchase order generation
- Waste monitoring and anomaly detection
- Notifying other agents when items are limited/unavailable

Uses Google Gemini LLM for intelligent decision-making and prompt engineering.
"""

import redis
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try importing agno Agent and Gemini model
try:
    from agno.agent import Agent
    from agno.models.google import Gemini
    AGNO_AVAILABLE = True
except ImportError:
    AGNO_AVAILABLE = False
    logger.warning("Agno not available. Install with: pip install agno google-generativeai")


class InventoryAgent:
    """
    Intelligent Inventory Management Agent for QSR systems.
    Manages ingredient stock, predicts demand, and coordinates with other agents.
    """

    def __init__(self, redis_host: str = 'localhost', redis_port: int = 6379, 
                 gemini_api_key: str = None):
        """
        Initialize the Inventory Agent.
        
        Args:
            redis_host: Redis server host
            redis_port: Redis server port
            gemini_api_key: Google Generative AI API key
        """
        self.redis_host = redis_host
        self.redis_port = redis_port
        
        # Initialize Redis connection
        try:
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=0,
                decode_responses=True
            )
            self.redis_client.ping()
            logger.info("✓ Connected to Redis successfully")
        except redis.ConnectionError as e:
            logger.error(f"✗ Redis connection failed: {str(e)}")
            raise
        
        # Initialize Agno Agent with Gemini model
        self.agent = None
        if AGNO_AVAILABLE and gemini_api_key:
            try:
                # Create Gemini model instance
                self.gemini_model = Gemini(api_key=gemini_api_key)
                
                # Create Agno Agent with Gemini model
                self.agent = Agent(
                    name="InventoryAgent",
                    model=self.gemini_model,
                    description="Intelligent inventory management agent for QSR systems",
                    instructions=self._get_agent_instructions()
                )
                logger.info("✓ Agno Agent initialized with Gemini model")
            except Exception as e:
                logger.error(f"✗ Failed to initialize Agno Agent: {str(e)}")
                self.agent = None
        else:
            if not gemini_api_key:
                logger.warning("⚠ Gemini API key not provided. Using fallback logic.")
            elif not AGNO_AVAILABLE:
                logger.warning("⚠ Agno not available. Using fallback logic.")
        
        # Configuration constants
        self.LOW_STOCK_THRESHOLD = 0.25  # 25% of max capacity
        self.CRITICAL_STOCK_THRESHOLD = 0.10  # 10% of max capacity
        self.REORDER_POINT = 0.20  # Reorder at 20% capacity
        self.DEMAND_SPIKE_MULTIPLIER = 1.5  # 50% increase triggers alert
        self.WASTE_THRESHOLD = 0.15  # 15% waste threshold
        
        # Agent state
        self.alerts = []
        self.purchase_orders = []
        self.anomalies = []

    def _get_agent_instructions(self) -> str:
        """Get comprehensive instructions for the Agno Agent."""
        return """
You are an expert Inventory Management Agent for Quick Service Restaurants (QSR).

PRIMARY RESPONSIBILITIES:
1. Real-time ingredient level monitoring and analysis
2. Predictive demand forecasting using historical patterns
3. Intelligent low stock alerts and notifications
4. Automatic purchase order generation with priority assessment
5. Waste monitoring and anomaly detection
6. Coordinating with other agents (Kitchen, Management, Procurement)

KEY BEHAVIORS:
- Monitor ingredient stock levels continuously
- Detect sudden demand spikes or usage anomalies
- Forecast demand for the next 7 days based on historical patterns
- Generate alerts with appropriate severity levels (critical, warning, info)
- Create purchase orders automatically when stock approaches reorder points
- Track and analyze waste patterns to identify efficiency issues
- Communicate item availability status to kitchen agent

RESPONSE FORMAT:
Provide structured analysis in JSON format when available. Include:
- Current situation assessment
- Forecast/prediction with confidence level
- Recommended actions (if any)
- Priority level (high/medium/low)
- Reasoning behind recommendations

DECISION LOGIC:
- Critical Stock: Immediate action required, notify all stakeholders
- Low Stock: Schedule reorder within 24 hours
- Waste Anomaly: Investigate root cause and recommend solutions
- Demand Spike: Adjust forecasts and increase ordering
- Normal Stock: Monitor and maintain current patterns
"""

    # ==================== REAL-TIME MONITORING ====================

    def initialize_ingredient_inventory(self, food_item_id: str, 
                                       max_capacity: float, 
                                       current_stock: float = None,
                                       unit: str = 'units') -> Dict:
        """
        Initialize inventory tracking for an ingredient.
        
        Args:
            food_item_id: ID of the food item/ingredient
            max_capacity: Maximum storage capacity
            current_stock: Current stock level (defaults to max_capacity)
            unit: Unit of measurement (units, kg, liters, etc.)
        
        Returns:
            Dictionary with inventory data
        """
        if current_stock is None:
            current_stock = max_capacity
        
        inventory = {
            'food_item_id': food_item_id,
            'max_capacity': max_capacity,
            'current_stock': current_stock,
            'unit': unit,
            'last_updated': datetime.now().isoformat(),
            'reorder_point': max_capacity * self.REORDER_POINT,
            'low_stock_threshold': max_capacity * self.LOW_STOCK_THRESHOLD,
            'critical_threshold': max_capacity * self.CRITICAL_STOCK_THRESHOLD,
            'status': 'active',
            'usage_history': [],
            'waste_log': []
        }
        
        # Store in Redis
        self.redis_client.set(
            f'inventory:{food_item_id}',
            json.dumps(inventory)
        )
        self.redis_client.sadd('inventory_items', food_item_id)
        
        logger.info(f"✓ Initialized inventory for {food_item_id}")
        return inventory

    def update_stock_level(self, food_item_id: str, quantity_used: float, 
                          reason: str = 'usage') -> Dict:
        """
        Update ingredient stock level in real-time.
        
        Args:
            food_item_id: ID of the food item
            quantity_used: Quantity consumed
            reason: Reason for usage (usage, waste, adjustment, etc.)
        
        Returns:
            Updated inventory status
        """
        inventory_key = f'inventory:{food_item_id}'
        inventory_data = self.redis_client.get(inventory_key)
        
        if not inventory_data:
            logger.error(f"✗ Inventory not found for {food_item_id}")
            return None
        
        inventory = json.loads(inventory_data)
        old_stock = inventory['current_stock']
        
        # Update stock
        inventory['current_stock'] = max(0, inventory['current_stock'] - quantity_used)
        inventory['last_updated'] = datetime.now().isoformat()
        
        # Log usage history
        usage_entry = {
            'timestamp': datetime.now().isoformat(),
            'quantity_used': quantity_used,
            'stock_after': inventory['current_stock'],
            'reason': reason
        }
        inventory['usage_history'].append(usage_entry)
        
        # Keep only last 100 entries
        if len(inventory['usage_history']) > 100:
            inventory['usage_history'] = inventory['usage_history'][-100:]
        
        # Save updated inventory
        self.redis_client.set(inventory_key, json.dumps(inventory))
        
        logger.info(f"✓ Updated {food_item_id}: {old_stock} → {inventory['current_stock']} {inventory['unit']}")
        
        # Check stock levels and generate alerts
        self._check_stock_alerts(food_item_id, inventory)
        
        return inventory

    def get_real_time_status(self, food_item_id: str = None) -> Dict:
        """
        Get real-time inventory status.
        
        Args:
            food_item_id: Optional - specific item, or all items if None
        
        Returns:
            Dictionary with inventory status
        """
        if food_item_id:
            inventory_data = self.redis_client.get(f'inventory:{food_item_id}')
            if inventory_data:
                return json.loads(inventory_data)
            return None
        
        # Get all inventory items
        all_items = self.redis_client.smembers('inventory_items')
        status = {}
        
        for item_id in all_items:
            inventory_data = self.redis_client.get(f'inventory:{item_id}')
            if inventory_data:
                inventory = json.loads(inventory_data)
                status[item_id] = {
                    'current_stock': inventory['current_stock'],
                    'max_capacity': inventory['max_capacity'],
                    'percentage': (inventory['current_stock'] / inventory['max_capacity'] * 100),
                    'status': self._determine_stock_status(inventory)
                }
        
        return status

    # ==================== DEMAND FORECASTING ====================

    def forecast_demand(self, food_item_id: str, days_ahead: int = 7, 
                       use_llm: bool = True) -> Dict:
        """
        Predict ingredient demand using historical data and ML/LLM.
        
        Args:
            food_item_id: ID of the food item
            days_ahead: Number of days to forecast
            use_llm: Whether to use LLM for intelligent forecasting
        
        Returns:
            Forecast data with predicted demand
        """
        inventory = self.get_real_time_status(food_item_id)
        if not inventory:
            logger.error(f"✗ No inventory found for {food_item_id}")
            return None
        
        # Collect historical usage data
        historical_data = self._extract_historical_patterns(food_item_id)
        
        if use_llm and self.model:
            forecast = self._forecast_with_llm(
                food_item_id, 
                inventory, 
                historical_data, 
                days_ahead
            )
        else:
            forecast = self._forecast_with_heuristics(
                food_item_id, 
                inventory, 
                historical_data, 
                days_ahead
            )
        
        # Store forecast
        forecast_key = f'forecast:{food_item_id}:{datetime.now().strftime("%Y-%m-%d")}'
        self.redis_client.set(forecast_key, json.dumps(forecast))
        self.redis_client.expire(forecast_key, 86400 * days_ahead)  # Expire after forecast period
        
        return forecast

    def _forecast_with_llm(self, food_item_id: str, inventory: Dict, 
                          historical_data: Dict, days_ahead: int) -> Dict:
        """
        Use Agno Agent with Gemini for intelligent demand forecasting.
        """
        if not self.agent:
            return self._forecast_with_heuristics(
                food_item_id, inventory, historical_data, days_ahead
            )
        
        try:
            # Prepare forecast prompt
            forecast_prompt = f"""
Analyze the following inventory data and provide a demand forecast for the next {days_ahead} days:

INVENTORY STATUS:
- Current Stock: {inventory.get('current_stock', 0)} {inventory.get('unit', 'units')}
- Max Capacity: {inventory.get('max_capacity', 0)} {inventory.get('unit', 'units')}
- Stock Percentage: {(inventory.get('current_stock', 0) / inventory.get('max_capacity', 1) * 100):.1f}%

HISTORICAL PATTERNS (Last 30 days):
- Average Daily Usage: {historical_data.get('avg_daily_usage', 0):.2f} units
- Peak Daily Usage: {historical_data.get('peak_usage', 0):.2f} units
- Usage Trend: {historical_data.get('trend', 'stable')}
- Waste Rate: {historical_data.get('waste_rate', 0):.1f}%

FORECAST REQUIREMENTS:
1. Predict daily demand for next {days_ahead} days
2. Assess risk level (low/medium/high)
3. Recommend optimal stock level
4. Suggest reorder timing
5. Identify any concerns or anomalies

RESPONSE: Provide structured JSON with keys: daily_forecast (list), risk_level, recommended_stock, reorder_day, notes
"""
            
            # Use Agno Agent to analyze and forecast
            response = self.agent.run(forecast_prompt)
            
            # Parse response
            if response:
                response_text = response.content if hasattr(response, 'content') else str(response)
                
                try:
                    # Extract JSON from response
                    json_start = response_text.find('{')
                    json_end = response_text.rfind('}') + 1
                    if json_start != -1 and json_end > json_start:
                        forecast = json.loads(response_text[json_start:json_end])
                        forecast['method'] = 'agno_gemini_llm'
                        forecast['generated_at'] = datetime.now().isoformat()
                        logger.info(f"✓ LLM forecast generated for {food_item_id}")
                        return forecast
                except json.JSONDecodeError:
                    logger.warning("Could not parse LLM response, falling back to heuristics")
        
        except Exception as e:
            logger.error(f"LLM forecast error: {str(e)}")
        
        return self._forecast_with_heuristics(
            food_item_id, inventory, historical_data, days_ahead
        )

    def _forecast_with_heuristics(self, food_item_id: str, inventory: Dict, 
                                 historical_data: Dict, days_ahead: int) -> Dict:
        """
        Fallback demand forecasting using statistical heuristics.
        """
        avg_usage = historical_data.get('avg_daily_usage', 0)
        peak_usage = historical_data.get('peak_usage', 0)
        trend = historical_data.get('trend', 'stable')
        
        # Calculate trend multiplier
        trend_multiplier = {
            'increasing': 1.15,
            'decreasing': 0.85,
            'stable': 1.0
        }.get(trend, 1.0)
        
        # Generate daily forecast
        daily_forecast = []
        for day in range(1, days_ahead + 1):
            # Apply trend and add variability
            base_demand = avg_usage * trend_multiplier
            variability = (peak_usage - avg_usage) * 0.3 * (day % 3)  # Weekly pattern
            forecasted_demand = base_demand + variability
            daily_forecast.append(round(forecasted_demand, 2))
        
        total_predicted = sum(daily_forecast)
        current_stock = inventory.get('current_stock', 0)
        
        # Determine risk level
        if current_stock < total_predicted * 0.5:
            risk_level = 'high'
        elif current_stock < total_predicted * 0.75:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        # Calculate reorder day
        reorder_day = days_ahead
        cumulative = 0
        for day, demand in enumerate(daily_forecast, 1):
            cumulative += demand
            if cumulative > current_stock:
                reorder_day = day
                break
        
        return {
            'food_item_id': food_item_id,
            'forecast_period_days': days_ahead,
            'daily_forecast': daily_forecast,
            'total_predicted_demand': total_predicted,
            'current_stock': current_stock,
            'risk_level': risk_level,
            'recommended_stock': total_predicted * 1.2,  # 20% buffer
            'reorder_day': reorder_day,
            'method': 'heuristic',
            'generated_at': datetime.now().isoformat(),
            'notes': f"Trend: {trend}, Average daily usage: {avg_usage:.2f}"
        }

    def _extract_historical_patterns(self, food_item_id: str) -> Dict:
        """
        Extract usage patterns from historical data.
        """
        inventory_key = f'inventory:{food_item_id}'
        inventory_data = self.redis_client.get(inventory_key)
        
        if not inventory_data:
            return {
                'avg_daily_usage': 0,
                'peak_usage': 0,
                'trend': 'stable',
                'seasonality': 'normal',
                'waste_rate': 0
            }
        
        inventory = json.loads(inventory_data)
        usage_history = inventory.get('usage_history', [])
        
        if not usage_history:
            return {
                'avg_daily_usage': 0,
                'peak_usage': 0,
                'trend': 'stable',
                'seasonality': 'normal',
                'waste_rate': 0
            }
        
        # Calculate statistics
        total_usage = sum(u['quantity_used'] for u in usage_history)
        waste_usage = sum(u['quantity_used'] for u in usage_history if u['reason'] == 'waste')
        avg_daily = total_usage / max(1, len(usage_history))
        peak = max((u['quantity_used'] for u in usage_history), default=0)
        
        # Determine trend (simplified)
        if len(usage_history) > 10:
            recent_avg = sum(u['quantity_used'] for u in usage_history[-5:]) / 5
            older_avg = sum(u['quantity_used'] for u in usage_history[-10:-5]) / 5
            if recent_avg > older_avg * 1.1:
                trend = 'increasing'
            elif recent_avg < older_avg * 0.9:
                trend = 'decreasing'
            else:
                trend = 'stable'
        else:
            trend = 'stable'
        
        return {
            'avg_daily_usage': avg_daily,
            'peak_usage': peak,
            'trend': trend,
            'seasonality': 'normal',  # Can be enhanced with day-of-week analysis
            'waste_rate': (waste_usage / total_usage * 100) if total_usage > 0 else 0,
            'total_records': len(usage_history)
        }

    # ==================== ALERTS & NOTIFICATIONS ====================

    def _check_stock_alerts(self, food_item_id: str, inventory: Dict) -> List[Dict]:
        """
        Check stock levels and generate appropriate alerts.
        """
        alerts_generated = []
        current_stock = inventory['current_stock']
        max_capacity = inventory['max_capacity']
        stock_percentage = (current_stock / max_capacity * 100)
        
        # Get food item name
        food_data = self.redis_client.get(f'food:{food_item_id}')
        food_name = "Unknown Item"
        if food_data:
            food_name = json.loads(food_data).get('name', 'Unknown Item')
        
        # Critical alert
        if current_stock <= inventory['critical_threshold']:
            alert = {
                'alert_id': str(uuid.uuid4()),
                'food_item_id': food_item_id,
                'food_name': food_name,
                'severity': 'critical',
                'message': f"CRITICAL: {food_name} stock at {stock_percentage:.1f}%",
                'current_stock': current_stock,
                'threshold': inventory['critical_threshold'],
                'timestamp': datetime.now().isoformat(),
                'action_required': 'immediate_reorder',
                'status': 'unresolved'
            }
            self._store_alert(alert)
            self._notify_agents(alert, ['kitchen', 'management'])
            alerts_generated.append(alert)
            logger.warning(f"🚨 CRITICAL ALERT: {food_name} - {stock_percentage:.1f}%")
        
        # Low stock alert
        elif current_stock <= inventory['low_stock_threshold']:
            alert = {
                'alert_id': str(uuid.uuid4()),
                'food_item_id': food_item_id,
                'food_name': food_name,
                'severity': 'warning',
                'message': f"LOW STOCK: {food_name} at {stock_percentage:.1f}%",
                'current_stock': current_stock,
                'threshold': inventory['low_stock_threshold'],
                'timestamp': datetime.now().isoformat(),
                'action_required': 'schedule_reorder',
                'status': 'unresolved'
            }
            self._store_alert(alert)
            self._notify_agents(alert, ['kitchen', 'procurement'])
            alerts_generated.append(alert)
            logger.warning(f"⚠ LOW STOCK ALERT: {food_name} - {stock_percentage:.1f}%")
        
        # Approaching reorder point
        elif current_stock <= inventory['reorder_point']:
            alert = {
                'alert_id': str(uuid.uuid4()),
                'food_item_id': food_item_id,
                'food_name': food_name,
                'severity': 'info',
                'message': f"Approaching reorder point: {food_name} at {stock_percentage:.1f}%",
                'current_stock': current_stock,
                'threshold': inventory['reorder_point'],
                'timestamp': datetime.now().isoformat(),
                'action_required': 'monitor',
                'status': 'unresolved'
            }
            self._store_alert(alert)
            alerts_generated.append(alert)
            logger.info(f"ℹ REORDER POINT ALERT: {food_name} - {stock_percentage:.1f}%")
        
        return alerts_generated

    def _store_alert(self, alert: Dict) -> None:
        """Store alert in Redis."""
        alert_id = alert['alert_id']
        self.redis_client.set(f'alert:{alert_id}', json.dumps(alert))
        self.redis_client.sadd('alerts', alert_id)
        self.redis_client.sadd(f'alerts_unresolved', alert_id)

    def get_active_alerts(self, severity: str = None) -> List[Dict]:
        """
        Get all active alerts.
        
        Args:
            severity: Optional filter (critical, warning, info)
        
        Returns:
            List of active alerts
        """
        alert_ids = self.redis_client.smembers('alerts_unresolved')
        alerts = []
        
        for alert_id in alert_ids:
            alert_data = self.redis_client.get(f'alert:{alert_id}')
            if alert_data:
                alert = json.loads(alert_data)
                if severity is None or alert.get('severity') == severity:
                    alerts.append(alert)
        
        return sorted(alerts, key=lambda x: x['timestamp'], reverse=True)

    # ==================== PURCHASE ORDERS ====================

    def generate_purchase_order(self, food_item_id: str, quantity: float, 
                               reason: str = 'stock_replenishment',
                               supplier_id: str = None) -> Dict:
        """
        Generate automatic purchase order.
        
        Args:
            food_item_id: ID of the food item to reorder
            quantity: Quantity to order
            reason: Reason for order (stock_replenishment, demand_spike, etc.)
            supplier_id: Optional supplier ID
        
        Returns:
            Purchase order details
        """
        order_id = str(uuid.uuid4())
        
        # Get food item details
        food_data = self.redis_client.get(f'food:{food_item_id}')
        if not food_data:
            logger.error(f"✗ Food item {food_item_id} not found")
            return None
        
        food_item = json.loads(food_data)
        inventory = self.get_real_time_status(food_item_id)
        
        purchase_order = {
            'order_id': order_id,
            'food_item_id': food_item_id,
            'food_name': food_item.get('name', 'Unknown'),
            'category': food_item.get('category_name', 'Unknown'),
            'quantity': quantity,
            'unit': inventory.get('unit', 'units') if inventory else 'units',
            'reason': reason,
            'supplier_id': supplier_id,
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'estimated_delivery': (datetime.now() + timedelta(days=1)).isoformat(),
            'priority': 'high' if reason == 'critical_stock' else 'normal'
        }
        
        # Store purchase order
        self.redis_client.set(f'purchase_order:{order_id}', json.dumps(purchase_order))
        self.redis_client.sadd('purchase_orders', order_id)
        self.redis_client.sadd(f'purchase_orders_pending', order_id)
        
        self._notify_agents({
            'type': 'purchase_order_created',
            'order': purchase_order
        }, ['procurement', 'management'])
        
        logger.info(f"✓ Purchase order created: {order_id} for {food_item.get('name', 'Unknown')}")
        return purchase_order

    def receive_shipment(self, purchase_order_id: str, received_quantity: float) -> Dict:
        """
        Record shipment receipt and update inventory.
        """
        order_data = self.redis_client.get(f'purchase_order:{purchase_order_id}')
        if not order_data:
            logger.error(f"✗ Purchase order {purchase_order_id} not found")
            return None
        
        purchase_order = json.loads(order_data)
        food_item_id = purchase_order['food_item_id']
        
        # Update inventory
        inventory = self.get_real_time_status(food_item_id)
        if inventory:
            new_stock = min(
                inventory['current_stock'] + received_quantity,
                inventory['max_capacity']
            )
            
            # Update stock
            inventory_key = f'inventory:{food_item_id}'
            inventory_data = self.redis_client.get(inventory_key)
            if inventory_data:
                inv = json.loads(inventory_data)
                inv['current_stock'] = new_stock
                inv['last_updated'] = datetime.now().isoformat()
                self.redis_client.set(inventory_key, json.dumps(inv))
        
        # Update purchase order
        purchase_order['status'] = 'received'
        purchase_order['received_quantity'] = received_quantity,
        purchase_order['received_at'] = datetime.now().isoformat()
        self.redis_client.set(f'purchase_order:{purchase_order_id}', json.dumps(purchase_order))
        self.redis_client.srem('purchase_orders_pending', purchase_order_id)
        
        logger.info(f"✓ Shipment received for {purchase_order['food_name']}: {received_quantity} units")
        return purchase_order

    # ==================== WASTE MONITORING ====================

    def log_waste(self, food_item_id: str, quantity_wasted: float, 
                 reason: str = 'expired') -> Dict:
        """
        Log ingredient waste for monitoring and anomaly detection.
        
        Args:
            food_item_id: ID of the wasted item
            quantity_wasted: Amount wasted
            reason: Reason for waste (expired, damaged, spoilage, etc.)
        
        Returns:
            Waste log entry
        """
        waste_entry = {
            'waste_id': str(uuid.uuid4()),
            'food_item_id': food_item_id,
            'quantity_wasted': quantity_wasted,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        }
        
        # Update inventory - remove from stock
        self.update_stock_level(food_item_id, quantity_wasted, reason=f'waste:{reason}')
        
        # Store waste log
        inventory_key = f'inventory:{food_item_id}'
        inventory_data = self.redis_client.get(inventory_key)
        if inventory_data:
            inventory = json.loads(inventory_data)
            inventory['waste_log'].append(waste_entry)
            
            # Keep only last 50 waste entries
            if len(inventory['waste_log']) > 50:
                inventory['waste_log'] = inventory['waste_log'][-50:]
            
            self.redis_client.set(inventory_key, json.dumps(inventory))
        
        # Check for anomalies
        self._detect_waste_anomalies(food_item_id, inventory)
        
        logger.info(f"✓ Waste logged: {food_item_id} - {quantity_wasted} units ({reason})")
        return waste_entry

    def _detect_waste_anomalies(self, food_item_id: str, inventory: Dict) -> List[Dict]:
        """
        Detect anomalous waste patterns.
        """
        waste_log = inventory.get('waste_log', [])
        if len(waste_log) < 5:
            return []
        
        anomalies = []
        
        # Calculate recent waste rate
        total_waste = sum(w['quantity_wasted'] for w in waste_log[-10:])
        avg_waste = total_waste / 10
        
        # Get food item
        food_data = self.redis_client.get(f'food:{food_item_id}')
        food_name = "Unknown"
        if food_data:
            food_name = json.loads(food_data).get('name', 'Unknown')
        
        # High waste detection
        waste_rate = (total_waste / inventory.get('max_capacity', 1)) * 100
        if waste_rate > self.WASTE_THRESHOLD * 100:
            anomaly = {
                'anomaly_id': str(uuid.uuid4()),
                'food_item_id': food_item_id,
                'food_name': food_name,
                'type': 'high_waste',
                'waste_rate': waste_rate,
                'threshold': self.WASTE_THRESHOLD * 100,
                'timestamp': datetime.now().isoformat(),
                'severity': 'warning',
                'recommendation': 'Review storage conditions and expiry management'
            }
            self._store_anomaly(anomaly)
            self._notify_agents(anomaly, ['management', 'procurement'])
            anomalies.append(anomaly)
            logger.warning(f"⚠ ANOMALY DETECTED: High waste for {food_name} ({waste_rate:.1f}%)")
        
        return anomalies

    def _store_anomaly(self, anomaly: Dict) -> None:
        """Store anomaly record."""
        anomaly_id = anomaly['anomaly_id']
        self.redis_client.set(f'anomaly:{anomaly_id}', json.dumps(anomaly))
        self.redis_client.sadd('anomalies', anomaly_id)

    # ==================== INTER-AGENT COMMUNICATION ====================

    def _notify_agents(self, message: Dict, target_agents: List[str]) -> None:
        """
        Notify other agents (Kitchen, Management, etc.) about inventory issues.
        
        Args:
            message: Message to send
            target_agents: List of agent names to notify
        """
        notification = {
            'from_agent': 'inventory',
            'timestamp': datetime.now().isoformat(),
            'message': message
        }
        
        for agent in target_agents:
            channel = f'agent_notification:{agent}'
            self.redis_client.lpush(channel, json.dumps(notification))
            self.redis_client.expire(channel, 86400)  # Expire after 24 hours
        
        logger.info(f"✓ Notification sent to: {', '.join(target_agents)}")

    def get_item_availability(self, food_item_id: str) -> Dict:
        """
        Check if an item is available and notify if unavailable.
        """
        inventory = self.get_real_time_status(food_item_id)
        
        if not inventory:
            return {'available': False, 'reason': 'not_tracked'}
        
        current_stock = inventory['current_stock']
        critical_threshold = inventory.get('critical_threshold', 0)
        
        is_available = current_stock > critical_threshold
        
        availability_status = {
            'food_item_id': food_item_id,
            'available': is_available,
            'current_stock': current_stock,
            'status_message': 'In stock' if is_available else 'Low stock / Unavailable',
            'checked_at': datetime.now().isoformat()
        }
        
        if not is_available:
            self._notify_agents({
                'type': 'item_unavailable',
                'food_item_id': food_item_id,
                'stock_level': current_stock
            }, ['kitchen'])
        
        return availability_status

    # ==================== REPORTING & ANALYTICS ====================

    def generate_inventory_report(self, days: int = 7) -> Dict:
        """
        Generate comprehensive inventory analysis report.
        """
        all_items = self.redis_client.smembers('inventory_items')
        
        report = {
            'report_generated_at': datetime.now().isoformat(),
            'period_days': days,
            'summary': {
                'total_items_tracked': len(all_items),
                'critical_items': 0,
                'low_stock_items': 0,
                'normal_items': 0,
                'total_waste_detected': 0,
                'total_anomalies': 0
            },
            'items_detail': [],
            'alerts_summary': self._get_alerts_summary(),
            'anomalies_summary': self._get_anomalies_summary(),
            'recommendations': []
        }
        
        for item_id in all_items:
            inventory = self.get_real_time_status(item_id)
            if inventory:
                status = self._determine_stock_status(inventory)
                
                # Update summary counts
                if status == 'critical':
                    report['summary']['critical_items'] += 1
                elif status == 'low':
                    report['summary']['low_stock_items'] += 1
                else:
                    report['summary']['normal_items'] += 1
                
                # Get food item name
                food_data = self.redis_client.get(f'food:{item_id}')
                food_name = "Unknown"
                if food_data:
                    food_name = json.loads(food_data).get('name', 'Unknown')
                
                report['items_detail'].append({
                    'food_item_id': item_id,
                    'food_name': food_name,
                    'current_stock': inventory['current_stock'],
                    'max_capacity': inventory['max_capacity'],
                    'stock_percentage': (inventory['current_stock'] / inventory['max_capacity'] * 100),
                    'status': status
                })
        
        return report

    def _get_alerts_summary(self) -> Dict:
        """Get summary of recent alerts."""
        alerts = self.get_active_alerts()
        summary = {
            'total_unresolved': len(alerts),
            'critical': len([a for a in alerts if a.get('severity') == 'critical']),
            'warning': len([a for a in alerts if a.get('severity') == 'warning']),
            'info': len([a for a in alerts if a.get('severity') == 'info'])
        }
        return summary

    def _get_anomalies_summary(self) -> Dict:
        """Get summary of anomalies."""
        anomaly_ids = self.redis_client.smembers('anomalies')
        anomalies = []
        
        for anomaly_id in anomaly_ids:
            anomaly_data = self.redis_client.get(f'anomaly:{anomaly_id}')
            if anomaly_data:
                anomalies.append(json.loads(anomaly_data))
        
        summary = {
            'total_anomalies': len(anomalies),
            'high_waste_detected': len([a for a in anomalies if a.get('type') == 'high_waste']),
            'demand_spike_detected': len([a for a in anomalies if a.get('type') == 'demand_spike']),
            'recent_anomalies': anomalies[-5:] if anomalies else []
        }
        return summary

    def _determine_stock_status(self, inventory: Dict) -> str:
        """Determine stock status based on thresholds."""
        current = inventory['current_stock']
        critical = inventory.get('critical_threshold', inventory['max_capacity'] * 0.1)
        low = inventory.get('low_stock_threshold', inventory['max_capacity'] * 0.25)
        
        if current <= critical:
            return 'critical'
        elif current <= low:
            return 'low'
        else:
            return 'normal'


# ==================== DEMO/TESTING ====================

def demo_inventory_agent():
    """
    Demonstration of the Inventory Agent capabilities.
    """
    print("\n" + "="*80)
    print("QSR INVENTORY AGENT - DEMONSTRATION")
    print("="*80)
    
    try:
        # Initialize agent (Gemini API key can be passed here)
        agent = InventoryAgent()
        
        print("\n✓ Inventory Agent initialized successfully")
        
        # Get all food items to work with
        redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        food_ids = list(redis_client.smembers('food_items'))
        
        if not food_ids:
            print("⚠ No food items found. Please run populate_food_items.py first.")
            return
        
        # Initialize inventory for first 5 food items
        print("\n" + "-"*80)
        print("INITIALIZING INVENTORY FOR FOOD ITEMS")
        print("-"*80)
        
        for food_id in food_ids[:5]:
            food_data = redis_client.get(f'food:{food_id}')
            if food_data:
                food_info = json.loads(food_data)
                agent.initialize_ingredient_inventory(
                    food_item_id=food_id,
                    max_capacity=100,
                    current_stock=75,
                    unit='units'
                )
                print(f"✓ Initialized: {food_info['name']}")
        
        # Simulate stock usage
        print("\n" + "-"*80)
        print("SIMULATING STOCK USAGE")
        print("-"*80)
        
        test_item = food_ids[0]
        for i in range(12):
            agent.update_stock_level(test_item, 5 + (i % 3), reason='usage')
        
        # Get real-time status
        print("\n" + "-"*80)
        print("REAL-TIME INVENTORY STATUS")
        print("-"*80)
        
        status = agent.get_real_time_status()
        for item_id, item_status in status.items():
            print(f"\nItem: {item_id}")
            print(f"  Stock: {item_status['current_stock']:.1f} / {item_status['max_capacity']:.1f} units")
            print(f"  Percentage: {item_status['percentage']:.1f}%")
            print(f"  Status: {item_status['status'].upper()}")
        
        # Forecast demand
        print("\n" + "-"*80)
        print("DEMAND FORECASTING")
        print("-"*80)
        
        forecast = agent.forecast_demand(test_item, days_ahead=7, use_llm=False)
        if forecast:
            print(f"\nItem: {forecast.get('food_item_id')}")
            print(f"Method: {forecast.get('method')}")
            print(f"Daily Forecast: {forecast.get('daily_forecast')}")
            print(f"Total Predicted Demand: {forecast.get('total_predicted_demand'):.1f} units")
            print(f"Risk Level: {forecast.get('risk_level')}")
            print(f"Recommended Stock: {forecast.get('recommended_stock'):.1f} units")
            print(f"Reorder on Day: {forecast.get('reorder_day')}")
        
        # Log waste
        print("\n" + "-"*80)
        print("WASTE MONITORING")
        print("-"*80)
        
        waste_entry = agent.log_waste(test_item, 5, reason='expired')
        print(f"✓ Waste logged: {waste_entry['quantity_wasted']} units ({waste_entry['reason']})")
        
        # Generate purchase order
        print("\n" + "-"*80)
        print("AUTOMATIC PURCHASE ORDER GENERATION")
        print("-"*80)
        
        purchase_order = agent.generate_purchase_order(
            test_item,
            quantity=30,
            reason='stock_replenishment'
        )
        if purchase_order:
            print(f"✓ Purchase Order Created:")
            print(f"  Order ID: {purchase_order['order_id']}")
            print(f"  Item: {purchase_order['food_name']}")
            print(f"  Quantity: {purchase_order['quantity']} {purchase_order['unit']}")
            print(f"  Priority: {purchase_order['priority']}")
        
        # Get active alerts
        print("\n" + "-"*80)
        print("ACTIVE ALERTS")
        print("-"*80)
        
        alerts = agent.get_active_alerts()
        if alerts:
            for alert in alerts[:5]:
                print(f"\n[{alert['severity'].upper()}] {alert['message']}")
                print(f"  Current Stock: {alert['current_stock']}")
                print(f"  Threshold: {alert['threshold']}")
                print(f"  Action: {alert['action_required']}")
        else:
            print("✓ No active alerts")
        
        # Generate report
        print("\n" + "-"*80)
        print("INVENTORY REPORT")
        print("-"*80)
        
        report = agent.generate_inventory_report()
        print(f"\nReport Generated: {report['report_generated_at']}")
        print(f"\nSummary:")
        print(f"  Total Items Tracked: {report['summary']['total_items_tracked']}")
        print(f"  Critical Items: {report['summary']['critical_items']}")
        print(f"  Low Stock Items: {report['summary']['low_stock_items']}")
        print(f"  Normal Items: {report['summary']['normal_items']}")
        
        print(f"\nAlerts:")
        print(f"  Total Unresolved: {report['alerts_summary']['total_unresolved']}")
        print(f"  Critical: {report['alerts_summary']['critical']}")
        print(f"  Warning: {report['alerts_summary']['warning']}")
        
        print("\n" + "="*80)
        print("✓ DEMONSTRATION COMPLETED SUCCESSFULLY")
        print("="*80 + "\n")
        
    except Exception as e:
        logger.error(f"✗ Demo failed: {str(e)}")
        raise


if __name__ == '__main__':
    demo_inventory_agent()
