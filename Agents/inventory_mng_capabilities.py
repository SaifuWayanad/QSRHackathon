"""
Inventory Management Agent Capabilities (SQLite-Based)
Detailed capability definitions for inventory operations using SQLite database
"""

inventory_capabilities = """

PURPOSE:
The InventoryAgent manages food item stock levels, demand forecasting, anomaly detection,
waste prevention, and automatic production order generation for QSR kitchens. It uses SQLite
database (daily_production, food_items, order_items tables) to ensure optimal stock levels,
prevent stockouts, minimize waste, and coordinate with KitchenAgent, CustomerHandlingAgent, and ManagerAgent.

INPUTS:
- Current stock levels from SQLite food_items table
- Historical order data (last 7-30 days from order_items table)
- Production data from daily_production table
- Real-time order events from SQLite orders table
- Food item specifications (price, status, kitchen_id from food_items)
- Messages from KitchenAgent, CustomerHandlingAgent, ManagerAgent

OUTPUTS:
- Stock status reports (current levels, forecasts, anomalies)
- Low stock alerts to other agents (availability <= 0 critical, < 5 low)
- Demand forecasts for 1-week planning
- Anomaly detection alerts (demand spikes > 50%)
- Waste prevention recommendations (over-production detection)
- Automatic purchase orders to ProcurementAgent
- Notifications to ManagerAgent and KitchenAgent

-----------------------------------------------------
CAPABILITY 1: CURRENT STOCK MONITORING (Real-Time)
-----------------------------------------------------

PURPOSE: Track ingredient levels across all food items in real-time using SQLite

OPERATIONS:
- Query SQLite food_items table for all food items
- Query daily_production table for produced quantity (today)
- Query order_items table for sold quantity (today)
- Calculate availability = produced - sold
- Classify stock status: NORMAL (availability > 5), LOW (0 < availability <= 5), CRITICAL (availability <= 0)
- Build inventory dashboard view with all items and their status
- Identify items that need immediate attention

SQL QUERY PATTERN:
SELECT fi.id, fi.name, fi.kitchen_id, fi.kitchen_name,
       COALESCE(dp.produced, 0) as produced_today,
       COALESCE(SUM(oi.quantity), 0) as sold_today
FROM food_items fi
LEFT JOIN daily_production dp ON fi.id = dp.food_id AND dp.date = DATE('now')
LEFT JOIN order_items oi ON fi.id = oi.food_item_id AND DATE(oi.created_at) = DATE('now')
GROUP BY fi.id

DATA STRUCTURE:
{
  "food_id": 123,
  "food_name": "Tomato",
  "kitchen_id": 1,
  "kitchen_name": "Kitchen A",
  "produced_today": 50,
  "sold_today": 35,
  "availability": 15,
  "status": "normal|low|critical",
  "last_updated": "ISO8601 timestamp"
}

METRICS TO TRACK:
- Total items monitored
- Items with normal availability (>5 units)
- Items with low availability (0-5 units)
- Items with critical availability (<=0 units)
- Total production vs total sales

OUTPUT:
- Structured inventory status report from SQLite
- Real-time dashboard data
- Items requiring immediate action


-----------------------------------------------------
CAPABILITY 2: LOW STOCK ALERTS (Threshold-Based)
-----------------------------------------------------

PURPOSE: Alert other agents when stock levels fall below safety thresholds

THRESHOLDS (SQLite-based):
- LOW STOCK ALERT: When availability < 5 units
  * Action: Schedule reorder within 24 hours
  * Notify: KitchenAgent (reduce usage), CustomerHandlingAgent (limit availability)
  * Priority: MEDIUM
  * Update food_items status to 'limited'

- CRITICAL STOCK ALERT: When availability <= 0 units
  * Action: Execute emergency reorder immediately
  * Notify: All agents (KitchenAgent, CustomerHandlingAgent, ManagerAgent)
  * Priority: HIGH
  * Update food_items status to 'unavailable'
  * Alternative: Suggest menu modifications

ALERT STRUCTURE:
{
  "alert_id": 1,
  "timestamp": "ISO8601",
  "food_id": 123,
  "food_name": "Tomato",
  "severity": "low|critical",
  "availability": 2,
  "threshold": 5,
  "produced_today": 50,
  "sold_today": 48,
  "action_required": "reorder|menu_change|staff_alert",
  "recipient_agents": ["KitchenAgent", "CustomerHandlingAgent", "ManagerAgent"],
  "recommendation": "Place emergency purchase order immediately"
}

SQL UPDATE PATTERN:
UPDATE food_items SET status = 'unavailable' WHERE id = ? AND availability <= 0;
UPDATE food_items SET status = 'limited' WHERE id = ? AND availability < 5;

NOTIFICATION TYPES:
1. KitchenAgent: Reduce prep portions, shift to alternative ingredients
2. CustomerHandlingAgent: Mark item as "limited availability" or "unavailable"
3. ManagerAgent: Alert manager for strategic decision

OUTPUT:
- Alert messages sent to appropriate agents
- Alert history stored in SQLite
- Escalation tracking (critical alerts get higher priority)


-----------------------------------------------------
CAPABILITY 3: DEMAND FORECASTING (1-Week Ahead)
-----------------------------------------------------

PURPOSE: Predict ingredient demand for next 7 days using SQLite order history

DATA SOURCES:
- Order history (last 7 days from order_items table with created_at timestamps)
- Day-of-week patterns (Monday vs Friday patterns)
- Food item specifications from food_items table
- Daily production data from daily_production table

FORECASTING LOGIC:
1. Query SQLite: SELECT SUM(oi.quantity) FROM order_items WHERE food_item_id = ? AND created_at >= DATE('now', '-7 days')
2. Count orders per day for each food item
3. Calculate average daily demand = total_count / 7 days
4. Identify peaks: Friday-Saturday (1.4x multiplier), Sunday (1.2x multiplier)
5. Apply day-of-week multipliers for next 7-day forecast
6. Compare forecast vs current availability
7. Determine if reorder needed

FORECAST MODEL:
- Base Demand = Average daily usage from last 7 days of order_items
- Day-of-Week Adjustment (applied to next 7 days):
  * Monday-Thursday: 1.0x (baseline)
  * Friday-Saturday: 1.4x (peak dining)
  * Sunday: 1.2x (moderate peak)
- Confidence Level = based on data consistency (0.7-1.0)

SQL QUERY PATTERN:
SELECT DATE(created_at) as order_date, SUM(quantity) as total_sold
FROM order_items
WHERE food_item_id = ? AND created_at >= DATE('now', '-7 days')
GROUP BY DATE(created_at)
ORDER BY order_date DESC;

FORECAST OUTPUT:
{
  "food_id": 123,
  "food_name": "Tomato",
  "forecast_period": "7_days",
  "daily_forecast": [15, 16, 15, 14, 21, 28, 17],
  "total_predicted_demand": 126,
  "average_daily_demand": 18,
  "current_availability": 15,
  "days_until_stockout": 0.8,
  "recommended_production_qty": 150,
  "confidence_level": 0.9,
  "peak_day": "Saturday (28 units)",
  "notes": "High weekend demand expected"
}

DECISION POINTS:
- If current_availability < total_predicted_demand: WARN - production needed
- If current_availability < total_predicted_demand * 0.5: CRITICAL - emergency production
- If days_until_stockout < 1: Schedule production immediately

OUTPUT:
- 7-day demand forecast for each item
- Stock sufficiency analysis
- Production recommendations with quantities
- Confidence metrics for decision-making


-----------------------------------------------------
CAPABILITY 4: ANOMALY DETECTION (Sudden Demand Spikes)
-----------------------------------------------------

PURPOSE: Detect unusual order patterns and sudden demand surges using SQLite

MONITORING WINDOW:
- Real-time: Check last 1-hour order count from order_items table
- Compare against baseline (average hourly demand from last 24 hours)
- Spike detected if: current_orders > baseline * 1.5 (50% increase)

SPIKE ANALYSIS:
1. Query order_items: SELECT COUNT(*) FROM order_items WHERE created_at >= DATETIME('now', '-1 hour')
2. Calculate 24-hour baseline: SELECT COUNT(*) FROM order_items WHERE created_at >= DATETIME('now', '-24 hours')
3. Calculate hourly baseline = 24_hour_count / 24
4. Flag when current > baseline * 1.5
5. Identify which food items are spiking
6. Estimate time to stockout at spike rate
7. Predict return to normal demand

SQL QUERY PATTERN:
-- Last 1 hour orders
SELECT food_item_id, SUM(quantity) as spike_quantity
FROM order_items WHERE created_at >= DATETIME('now', '-1 hour')
GROUP BY food_item_id;

-- 24-hour baseline
SELECT food_item_id, SUM(quantity) as baseline_quantity
FROM order_items WHERE created_at >= DATETIME('now', '-24 hours')
GROUP BY food_item_id;

ANOMALY RESPONSE TRIGGERS:
- If spike sustained > 30 minutes: Escalate to KitchenAgent
- If spike threatens stockout < 2 hours: Emergency production order
- If spike on specific item: Recommend prep alternatives
- Store anomaly in SQLite for historical analysis

SPIKE STRUCTURE:
{
  "anomaly_id": 1,
  "timestamp": "ISO8601",
  "type": "demand_spike",
  "duration_minutes": 35,
  "food_id": 456,
  "food_name": "Chicken",
  "orders_baseline_hourly": 12,
  "orders_current_hourly": 18,
  "spike_percentage": 50,
  "predicted_depletion_minutes": 108,
  "current_availability": 32,
  "recommended_action": "expedited_production|staff_alert|prep_alternatives",
  "status": "active|resolved"
}

RUSH HOUR PATTERNS:
- Peak hours (12-2pm, 6-8pm): Expect 1.5-2x normal demand
- Weekend rushes: Expect 2-3x normal demand
- Event-driven spikes: Special events, promotions

OUTPUT:
- Anomaly alerts with detection timestamp
- Spike predictions and impact estimates
- Recommended actions (staff allocation, expedited production)
- Notifications to KitchenAgent and ManagerAgent


-----------------------------------------------------
CAPABILITY 5: SURPLUS STOCK & WASTE PREVENTION
-----------------------------------------------------

PURPOSE: Identify over-production and prevent waste using SQLite data

SURPLUS DETECTION:
1. Query daily_production: SELECT * WHERE produced > 20 AND DATE = TODAY()
2. Query corresponding order_items sales for same items
3. Calculate sell_through_rate = sold / produced
4. Flag surplus if produced > 20 AND sell_through_rate < 30%
5. Estimate waste if demand doesn't materialize
6. Track items with consistent over-production

SQL QUERY PATTERN:
SELECT dp.food_id, dp.food_name, dp.produced,
       COALESCE(SUM(oi.quantity), 0) as sold,
       ROUND(100.0 * SUM(oi.quantity) / dp.produced, 2) as sell_through_pct
FROM daily_production dp
LEFT JOIN order_items oi ON dp.food_id = oi.food_item_id AND DATE(oi.created_at) = dp.date
WHERE dp.date = DATE('now') AND dp.produced > 20
GROUP BY dp.food_id
HAVING sell_through_pct < 30;

WASTE PREVENTION STRATEGIES:
- For over-produced items with low sell-through: Recommend promotional offers
- For surplus items: Alert ManagerAgent to adjust next day's production
- For slow-moving items: Reduce planned_quantity in daily_production
- For high-waste items: Create special menu items

SURPLUS ANALYSIS:
{
  "food_id": 789,
  "food_name": "Lettuce",
  "produced_today": 85,
  "sold_today": 20,
  "sell_through_rate": 23.5,
  "excess_quantity": 65,
  "waste_risk": "high|medium|low",
  "recommendation": "promotional_offer|reduce_production|staff_usage",
  "estimated_waste_value": 65.00,
  "prevention_action": "reduce_tomorrow_production_by_50pct"
}

WASTE PREVENTION ACTIONS:
1. Alert ManagerAgent to reduce production for next day
2. Suggest combo meals with surplus items
3. Use in staff meals or compost
4. Update daily_production planned_quantity for next day

OUTPUT:
- Over-production report from daily_production table
- Waste prevention recommendations
- Production adjustments for next day
- Estimated cost savings from waste prevention


-----------------------------------------------------
CAPABILITY 6: AUTOMATIC PURCHASE ORDER GENERATION
-----------------------------------------------------

PURPOSE: Generate production orders automatically based on SQLite forecast

REORDER LOGIC:
1. Calculate forecast demand for next 7 days using forecast_demand_1week()
2. Trigger production when current_availability <= forecast * 1.2 (20% buffer)
3. Order quantity = forecast * 1.2 (ensure buffer stock)
4. Set priority based on availability levels
5. Store in database for tracking

PRIORITY LEVELS:
- CRITICAL (availability <= 0): Lead time immediate, Priority HIGH
- LOW (availability < 5): Lead time 4-6 hours, Priority MEDIUM
- NORMAL (availability >= 5): Lead time 24 hours, Priority NORMAL

PURCHASE ORDER STRUCTURE (stored in orders/order_items or custom table):
{
  "production_order_id": 1,
  "timestamp": "ISO8601",
  "food_id": 123,
  "food_name": "Tomato",
  "quantity": 150,
  "source": "InventoryAgent",
  "priority": "critical|high|medium|normal",
  "requested_by": "InventoryAgent",
  "reason": "7-day forecast demand with 1.2x buffer",
  "notes": "Based on 7-day average of 18 units/day + 20% buffer"
}

SQL INSERT PATTERN:
-- Insert into daily_production with planned_quantity
INSERT INTO daily_production (food_id, food_name, date, planned_quantity, notes)
VALUES (123, 'Tomato', DATE('now'), 150, 'Auto-generated: Forecast-based order');

-- Update food_items status to 'active'
UPDATE food_items SET status = 'active' WHERE id = 123 AND availability >= 5;

AUTOMATIC TRIGGERS:
1. Availability <= current_forecast: Generate normal production order
2. Availability <= 0: Generate high-priority production order
3. Demand spike > 50%: Generate expedited production order
4. Over-production detected: Reduce planned_quantity for next day

OUTPUT:
- Generated production orders stored in SQLite
- Production order history in daily_production
- Forecast-driven production planning
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
