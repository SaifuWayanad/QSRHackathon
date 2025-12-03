# Kitchen Management System

## Overview

Complete kitchen management system with intelligent order assignment, real-time status tracking, and multi-kitchen coordination.

## Features

### 1. **Smart Order Routing**
- Automatic assignment of food items to appropriate kitchens
- Category-based routing system
- Support for 7 different kitchen stations

### 2. **Kitchen Mapping**

| Kitchen | Type | Items | Capacity |
|---------|------|-------|----------|
| 👨‍🍳 Main Kitchen | General | Burgers, Steaks, Appetizers, Main Course, Pasta, Sandwiches | 15 |
| 🔥 Grill Station | Specialized | Grilled Items, Steaks | 8 |
| 🥗 Prep Kitchen | Fresh | Salads, Soups, Fresh Items | 10 |
| 🍕 Pizza Station | Specialized | Pizza | 6 |
| 🧁 Pastry Kitchen | Desserts | Desserts, Pastries | 8 |
| 🍹 Bar | Beverages | Drinks, Coffee, Juices, Smoothies | 12 |
| 🍴 General Kitchen | Fallback | Other items | 20 |

### 3. **Order Status Workflow**

```
⏳ Pending → 👨‍🍳 Preparing → ✓ Ready → 🍽️ Served → ✅ Completed
```

- **Pending**: Order received, not yet started
- **Preparing**: Kitchen is actively preparing items
- **Ready**: Items ready, waiting for service
- **Served**: Items delivered to customer
- **Completed**: Order fully processed

### 4. **Real-time Dashboard**

- Kitchen-specific views with tabbed interface
- Live assignment tracking
- Individual item status control
- Status workflow visualization

## API Endpoints

### Kitchen Management

```bash
# Get all kitchens
GET /api/kitchens
Response: {
  "kitchens": [
    {
      "id": "main_kitchen",
      "name": "Main Kitchen",
      "icon": "👨‍🍳",
      "capacity": 15,
      "specialties": ["Burgers", "Steaks", ...]
    }
  ]
}

# Get kitchen assignments
GET /api/kitchens/{kitchen_id}/assignments
Response: {
  "assignments": [
    {
      "id": "assignment_id",
      "order_id": "order_id",
      "items": [
        {
          "id": "item_id",
          "name": "Item Name",
          "quantity": 2,
          "status": "preparing",
          ...
        }
      ]
    }
  ]
}

# Assign order to kitchens
POST /api/orders/{order_id}/assign-kitchens
Response: {
  "success": true,
  "assignments": [
    {
      "kitchen_id": "main_kitchen",
      "kitchen_name": "Main Kitchen",
      "items": [...],
      "item_count": 3,
      "status": "pending"
    }
  ]
}

# Get order item status
GET /api/orders/{order_id}/kitchen-status
Response: {
  "items": [
    {
      "id": "item_id",
      "food_name": "Item Name",
      "status": "preparing",
      "status_label": "👨‍🍳 Preparing",
      "status_color": "#3498DB"
    }
  ]
}

# Update individual item status
POST /api/kitchen-item/{item_id}/transition
Body: { "status": "ready" }
Response: {
  "success": true,
  "item_id": "item_id",
  "status": "ready",
  "status_label": "✓ Ready",
  "status_color": "#2ECC71"
}
```

## UI Components

### 1. Kitchen Management Section

- **Location**: Main navigation menu as "🍳 Kitchen Management"
- **Kitchen Tabs**: Select between different kitchen stations
- **Live Assignments**: Real-time view of orders at each kitchen
- **Item Cards**: Shows individual items with current status

### 2. Kitchen Item Card

```
┌─ 👨‍🍳 main_k... (3 items)
├─ Grilled Chicken Burger
│  Qty: 1 | $12.99
│  [🍳 Preparing]
├─ Caesar Salad
│  Qty: 1 | $9.99
│  [⏳ Pending]
└─ Iced Tea × 2
   Qty: 2 | $2.99
   [✓ Ready]
```

### 3. Status Update Modal

- Current item details
- Status selection dropdown
- Visual workflow indicator
- Next status suggestion

### 4. Kitchen Assignment Modal

- Order summary
- Per-kitchen assignment cards
- Item listing with details
- Assignment confirmation

## Integration Points

### 1. Order Creation

When an order is created:
1. Items saved to `order_items` table
2. Order pushed to stream database (optional)
3. Ready for kitchen assignment

### 2. Kitchen Assignment

When "Assign to Kitchens" clicked:
1. Items grouped by category
2. Assigned to appropriate kitchens based on mapping
3. Assignments stored in stream database
4. Kitchen dashboard updates

### 3. Status Updates

When item status changes:
1. Individual item status updated
2. Order status automatically updated if all items completed
3. Dashboard refreshes in real-time

## Database Schema

### order_items Table

```sql
CREATE TABLE order_items (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    food_item_id TEXT NOT NULL,
    food_name TEXT,
    category_name TEXT,
    quantity INTEGER NOT NULL,
    price REAL NOT NULL,
    notes TEXT,
    status TEXT DEFAULT 'pending',  -- NEW: Track item status
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (food_item_id) REFERENCES food_items(id)
)
```

### Stream Database Tables (Optional)

```sql
CREATE TABLE orders_stream (
    id TEXT PRIMARY KEY,
    order_data TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    assigned_to_kitchen TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)

CREATE TABLE kitchen_assignments (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    kitchen_id TEXT NOT NULL,
    kitchen_name TEXT,
    items TEXT NOT NULL,
    status TEXT DEFAULT 'assigned',
    assigned_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders_stream(id)
)

CREATE TABLE kitchen_status (
    id TEXT PRIMARY KEY,
    kitchen_id TEXT NOT NULL,
    kitchen_name TEXT NOT NULL,
    current_load INTEGER DEFAULT 0,
    max_capacity INTEGER DEFAULT 10,
    status TEXT DEFAULT 'idle',
    last_updated TIMESTAMP,
    UNIQUE(kitchen_id)
)
```

## Usage Flow

### For Order Manager

1. Click "Create New Order"
2. Add food items
3. Create order
4. Click "View" on order
5. Click "Assign to Kitchens"
6. Review kitchen assignments
7. Click "Confirm Assignments"

### For Kitchen Staff

1. Navigate to "Kitchen Management"
2. Select their kitchen tab
3. See real-time assignments
4. Click item status button
5. Select new status (Preparing → Ready → Served)
6. Confirm status change

## Configuration

### Add New Kitchen

Edit `kitchen_manager.py`:

```python
KITCHEN_MAPPING = {
    'Your Category': 'your_kitchen',
    ...
}

KITCHENS = {
    'your_kitchen': {
        'id': 'your_kitchen',
        'name': 'Your Kitchen',
        'icon': '🔥',
        'capacity': 10,
        'specialties': ['Your Category']
    }
}
```

### Modify Status Workflow

Edit `kitchen_manager.py`:

```python
STATUS_FLOW = [
    'pending',
    'preparing',
    'ready',
    'served',
    'completed'
]
```

## Color Coding

| Status | Color | Emoji |
|--------|-------|-------|
| Pending | #FFA500 (Orange) | ⏳ |
| Preparing | #3498DB (Blue) | 👨‍🍳 |
| Ready | #2ECC71 (Green) | ✓ |
| Served | #9B59B6 (Purple) | 🍽️ |
| Completed | #27AE60 (Dark Green) | ✅ |

## Performance Considerations

- Kitchen assignments stored in separate stream database for real-time access
- Status updates write to main database for persistence
- Optional stream database integration for high-volume operations
- Automatic order completion when all items done

## Testing

```bash
# Test order assignment
curl -X POST http://localhost:5100/api/orders/{order_id}/assign-kitchens

# Test status update
curl -X POST http://localhost:5100/api/kitchen-item/{item_id}/transition \
  -H "Content-Type: application/json" \
  -d '{"status": "ready"}'
```

## Future Enhancements

- [ ] Kitchen capacity monitoring
- [ ] Preparation time estimation
- [ ] Recipe/ingredient tracking
- [ ] Staff assignment to kitchens
- [ ] Performance analytics
- [ ] Order priority levels
- [ ] Batch processing optimization
- [ ] Mobile kitchen app
