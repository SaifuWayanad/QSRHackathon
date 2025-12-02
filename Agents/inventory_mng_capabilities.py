"""
Inventory Management Agent Capabilities
Detailed capability definitions for inventory operations
"""

inventory_capabilities = """

PURPOSE:
The InventoryAgent manages ingredient stock levels, demand forecasting, anomaly detection,
waste prevention, and automatic purchase order generation for QSR kitchens. It ensures
optimal stock levels, prevents stockouts, minimizes waste, and coordinates with KitchenAgent,
CustomerHandlingAgent, and ProcurementAgent.

INPUTS:
- Current stock levels from Redis database
- Historical order data (last 7-30 days)
- Real-time order events from order bus
- Supplier information and pricing
- Food item specifications (shelf life, max capacity)
- Messages from KitchenAgent, CustomerHandlingAgent, ManagerAgent

OUTPUTS:
- Stock status reports (current levels, forecasts, anomalies)
- Low stock alerts to other agents
- Demand forecasts for 1-week planning
- Anomaly detection alerts (demand spikes)
- Waste prevention recommendations
- Automatic purchase orders to ProcurementAgent
- Notifications to ManagerAgent and KitchenAgent

-----------------------------------------------------
CAPABILITY 1: CURRENT STOCK MONITORING (Real-Time)
-----------------------------------------------------

PURPOSE: Track ingredient levels across all food items in real-time

OPERATIONS:
- Query Redis for all food items and their current stock levels
- Calculate stock percentage (current_stock / max_capacity * 100)
- Classify stock status: NORMAL (>30%), LOW (10-30%), CRITICAL (<10%)
- Build inventory dashboard view with all items and their status
- Identify items that need immediate attention

DATA STRUCTURE:
{
  "food_id": "uuid",
  "food_name": "Tomato",
  "kitchen_id": "uuid",
  "category": "vegetables",
  "current_stock": 45,
  "max_capacity": 100,
  "unit": "kg",
  "stock_percentage": 45,
  "status": "normal|low|critical",
  "last_updated": "ISO8601 timestamp"
}

METRICS TO TRACK:
- Total items in stock
- Items in normal stock (>30%)
- Items in low stock (10-30%)
- Items in critical stock (<10%)
- Average stock utilization rate

OUTPUT:
- Structured inventory status report
- Real-time dashboard data
- Items requiring immediate action


-----------------------------------------------------
CAPABILITY 2: LOW STOCK ALERTS (Threshold-Based)
-----------------------------------------------------

PURPOSE: Alert other agents when stock levels fall below safety thresholds

THRESHOLDS:
- LOW STOCK ALERT: When current_stock <= 30% of max_capacity
  * Action: Schedule reorder within 24 hours
  * Notify: KitchenAgent (reduce usage), CustomerHandlingAgent (limit availability)
  * Priority: MEDIUM

- CRITICAL STOCK ALERT: When current_stock <= 10% of max_capacity
  * Action: Execute emergency reorder immediately
  * Notify: All agents (KitchenAgent, CustomerHandlingAgent, ManagerAgent)
  * Priority: HIGH
  * Alternative: Suggest menu modifications

ALERT STRUCTURE:
{
  "alert_id": "uuid",
  "timestamp": "ISO8601",
  "food_id": "uuid",
  "food_name": "Tomato",
  "severity": "low|critical",
  "current_stock": 8,
  "threshold": 10,
  "max_capacity": 100,
  "stock_percentage": 8,
  "action_required": "reorder|menu_change|staff_alert",
  "recipient_agents": ["KitchenAgent", "CustomerHandlingAgent", "ManagerAgent"],
  "recommendation": "Place emergency purchase order with 4-6 hour delivery"
}

NOTIFICATION TYPES:
1. KitchenAgent: Reduce prep portions, shift to alternative ingredients
2. CustomerHandlingAgent: Mark item as "limited availability" or "unavailable"
3. ManagerAgent: Alert manager for strategic decision

OUTPUT:
- Alert messages sent to appropriate agents
- Alert history stored in Redis
- Escalation tracking (critical alerts get higher priority)


-----------------------------------------------------
CAPABILITY 3: DEMAND FORECASTING (1-Week Ahead)
-----------------------------------------------------

PURPOSE: Predict ingredient demand for next 7 days based on order history

DATA SOURCES:
- Order history (last 7-30 days from Redis)
- Day-of-week patterns (Monday vs Friday patterns)
- Seasonal trends (if available)
- Average order size and composition

FORECASTING LOGIC:
1. Retrieve all orders from Redis orders:* keys
2. Count occurrences of each food_item_id
3. Calculate average daily demand = total_count / 7 days
4. Identify peaks: Friday-Saturday (40% higher), Sunday (20% higher)
5. Apply day-of-week multipliers for forecast
6. Compare forecast vs current_stock
7. Determine if reorder needed

FORECAST MODEL:
- Base Demand = Average daily usage from historical data
- Day-of-Week Adjustment:
  * Monday-Thursday: 1.0x (baseline)
  * Friday-Saturday: 1.4x (peak dining)
  * Sunday: 1.2x (moderate peak)
- Confidence Level = based on data freshness and consistency

FORECAST OUTPUT:
{
  "food_id": "uuid",
  "food_name": "Tomato",
  "forecast_period": "7_days",
  "daily_forecast": [15, 16, 15, 14, 18, 22, 19],  // Day 1-7
  "total_predicted_demand": 119,
  "average_daily_demand": 17,
  "current_stock": 45,
  "days_until_stockout": 2.6,  // If no reorder
  "recommended_reorder_qty": 100,
  "confidence_level": 0.85,  // 0.0-1.0
  "peak_day": "Saturday (22 units)",
  "notes": "High weekend demand expected"
}

DECISION POINTS:
- If current_stock < total_predicted_demand: WARN - reorder needed
- If current_stock < total_predicted_demand * 0.5: CRITICAL - emergency reorder
- If days_until_stockout < 2: Schedule reorder immediately

OUTPUT:
- 7-day demand forecast for each item
- Stock sufficiency analysis
- Reorder recommendations with quantities
- Confidence metrics for decision-making


-----------------------------------------------------
CAPABILITY 4: ANOMALY DETECTION (Sudden Demand Spikes)
-----------------------------------------------------

PURPOSE: Detect unusual order patterns and sudden demand surges

MONITORING WINDOW:
- Real-time: Check last 1-hour order count
- Compare against baseline (average hourly demand)
- Spike detected if: current_orders > baseline * 1.5 (50% increase)

SPIKE ANALYSIS:
1. Monitor orders in 1-hour windows
2. Calculate hourly baseline from last 24 hours
3. Flag when current > baseline * 1.5
4. Identify which items are spiking
5. Estimate time to stockout at spike rate
6. Predict return to normal demand

ANOMALY RESPONSE TRIGGERS:
- If spike sustained > 30 minutes: Escalate to KitchenAgent
- If spike threatens stockout < 2 hours: Emergency purchase order
- If spike on specific item: Recommend prep alternatives
- Store anomaly in Redis for historical analysis

SPIKE STRUCTURE:
{
  "anomaly_id": "uuid",
  "timestamp": "ISO8601",
  "type": "demand_spike",
  "duration_minutes": 35,
  "food_id": "uuid",
  "food_name": "Chicken",
  "orders_baseline_hourly": 12,
  "orders_current_hourly": 18,
  "spike_percentage": 50,
  "predicted_depletion_hours": 1.8,
  "current_stock": 32,
  "recommended_action": "expedited_reorder|staff_alert|prep_alternatives",
  "status": "active|resolved"
}

RUSH HOUR PATTERNS:
- Peak hours (12-2pm, 6-8pm): Expect 1.5-2x normal demand
- Weekend rushes: Expect 2-3x normal demand
- Event-driven spikes: Special events, promotions

OUTPUT:
- Anomaly alerts with detection timestamp
- Spike predictions and impact estimates
- Recommended actions (staff allocation, expedited orders)
- Notifications to KitchenAgent and ManagerAgent


-----------------------------------------------------
CAPABILITY 5: SURPLUS STOCK & WASTE PREVENTION
-----------------------------------------------------

PURPOSE: Identify excess inventory and prevent waste

SURPLUS DETECTION:
1. Identify items with stock > 80% capacity
2. Check forecast demand vs current surplus
3. Calculate expected expiry date vs demand curve
4. Estimate waste if demand doesn't materialize

WASTE PREVENTION STRATEGIES:
- For surplus items with low demand: Recommend promotional offers
- For near-expiry items: Alert ManagerAgent to create special menu
- For slow-moving items: Reduce purchase orders, use in staff meals
- For seasonal items: Plan rotational usage

SURPLUS ANALYSIS:
{
  "food_id": "uuid",
  "food_name": "Lettuce",
  "current_stock": 85,
  "max_capacity": 100,
  "stock_percentage": 85,
  "forecast_7day_demand": 35,
  "excess_quantity": 50,
  "shelf_life_days": 5,
  "expiry_date": "ISO8601",
  "waste_risk": "high|medium|low",
  "recommendation": "promotional_offer|staff_usage|compost",
  "estimated_waste_value": 25.00,
  "prevention_action": "offer_20_discount"
}

WASTE PREVENTION ACTIONS:
1. Create promotion (e.g., "20% off Salads this week")
2. Suggest combo meals with surplus items
3. Use in staff meals or charity donations
4. Alert KitchenAgent to increase portions with surplus items

OUTPUT:
- Surplus inventory report
- Waste prevention recommendations
- Proposed promotions and menu adjustments
- Estimated cost savings from waste prevention


-----------------------------------------------------
CAPABILITY 6: AUTOMATIC PURCHASE ORDER GENERATION
-----------------------------------------------------

PURPOSE: Generate purchase orders automatically based on inventory thresholds

REORDER LOGIC:
1. Calculate reorder point = average_daily_demand * 7 days (1-week buffer)
2. Trigger order when current_stock <= reorder_point
3. Order quantity = max_capacity - current_stock (fill to max)
4. Select supplier (use rotation or lowest cost)
5. Set lead time based on urgency

PRIORITY LEVELS:
- CRITICAL (stock < 10%): Lead time 4-6 hours, Priority HIGH
- LOW (stock 10-30%): Lead time 24-48 hours, Priority MEDIUM
- NORMAL (stock > 30%): Lead time 48-72 hours, Priority NORMAL

PURCHASE ORDER STRUCTURE:
{
  "purchase_order_id": "uuid",
  "timestamp": "ISO8601",
  "food_id": "uuid",
  "food_name": "Tomato",
  "category": "vegetables",
  "quantity": 50,
  "unit": "kg",
  "unit_price": 2.50,
  "total_cost": 125.00,
  "supplier_id": "uuid",
  "supplier_name": "Fresh Produce Co.",
  "delivery_address": "Kitchen",
  "priority": "critical|high|medium|normal",
  "estimated_delivery": "ISO8601 (current_time + lead_time)",
  "status": "pending|confirmed|shipped|delivered",
  "created_by": "InventoryAgent",
  "notes": "Emergency reorder due to sudden demand spike"
}

SUPPLIER MANAGEMENT:
- Maintain list of suppliers per food category
- Rotate suppliers for competitive pricing
- Track delivery performance (on-time %)
- Prioritize reliable suppliers for critical orders

AUTOMATIC TRIGGERS:
1. Stock <= reorder_point: Generate normal order
2. Stock <= critical_threshold: Generate high-priority order
3. Demand spike > 50%: Generate expedited order
4. Near-expiry surplus: Reduce purchase order qty

OUTPUT:
- Generated purchase orders sent to ProcurementAgent
- Purchase order history stored in Redis
- Supplier performance tracking
- Cost analysis and optimization


-----------------------------------------------------
CONSTRAINTS & SAFETY RULES
-----------------------------------------------------

- Must use tools ONLY for critical operations (stock updates, alerts)
- Must not invent stock levels or food items—use only Redis data
- Must follow thresholds strictly (no hardcoding different values)
- Must ensure idempotent operations (safe to retry without duplicates)
- Must always provide clear reasoning behind decisions
- Must validate data before processing (non-negative stock, valid dates)
- Must handle missing data gracefully (fallback to defaults)
- Must respect supplier availability and minimum order quantities
- Must track all operations for audit trail


"""
