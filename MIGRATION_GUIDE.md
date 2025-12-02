# QSR Hackathon - Migration from Redis to SQLite

## Overview
This document describes the migration from Redis to SQLite database for the QSR Hackathon application.

## Changes Made

### 1. **Updated Dependencies** (`requirements.txt`)
- Removed: `redis==5.0.1`
- SQLite3 is included with Python by default, no additional package needed

### 2. **Migrated Application** (`app.py`)
- **Replaced Redis client** with SQLite database connections
- **Created database schema** with 8 tables:
  - `areas` - Dining areas
  - `categories` - Food categories
  - `kitchens` - Kitchen stations
  - `food_items` - Food menu items
  - `tables` - Dining tables
  - `order_types` - Order types (Dine-in, Takeaway, etc.)
  - `orders` - Customer orders
  - `daily_production` - Daily production tracking

- **Updated all API endpoints** to use SQLite queries instead of Redis commands:
  - `/api/categories` - Create, read, delete food categories
  - `/api/kitchens` - Create, read, delete kitchens
  - `/api/food-items` - Create, read, delete food items
  - `/api/areas` - Create, read, delete dining areas
  - `/api/tables` - Create, read, delete dining tables
  - `/api/order-types` - Create, read, delete order types
  - `/api/orders` - Create, read, update, delete orders
  - `/api/daily-production` - Create, read, update production items

- **Database initialization** is automatic on app startup

### 3. **Created Database Initialization Script** (`init_database.py`)
Unified script that consolidates all populate files and populates the database with:
- **5 Dining Areas** (Main Dining Hall, VIP Lounge, Outdoor Patio, Bar & Counter, Meeting Room)
- **20 Food Categories** (Appetizers, Soups, Salads, Pizza, Desserts, Beverages, etc.)
- **10 Kitchen Stations** (Main Kitchen, Grill Station, Pastry, Pizza Oven, Cold Kitchen, Fryer, etc.)
- **5 Order Types** (Dine-in, Takeaway, Delivery, Drive-thru, Catering)
- **25 Dining Tables** (distributed across areas with various capacities)
- **27 Food Items** (sample menu items across all categories)

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Initialize Database
```bash
python init_database.py
```
This will:
- Create the SQLite database (`my_database.db`)
- Create all necessary tables
- Populate sample data (areas, categories, kitchens, tables, order types, food items)

### 3. Run the Application
```bash
python app.py
```

The app will start on `http://localhost:5100`

- **Login credentials**: 
  - Username: `manager`
  - Password: `123`

## Database Structure

### Tables Overview

#### `areas`
```
id (TEXT, PRIMARY KEY)
name (TEXT)
description (TEXT)
status (TEXT) - 'active' by default
tables_count (INTEGER)
created_at (TIMESTAMP)
```

#### `categories`
```
id (TEXT, PRIMARY KEY)
name (TEXT)
description (TEXT)
status (TEXT)
items_count (INTEGER)
created_at (TIMESTAMP)
```

#### `kitchens`
```
id (TEXT, PRIMARY KEY)
name (TEXT)
location (TEXT)
description (TEXT)
status (TEXT)
items_count (INTEGER)
created_at (TIMESTAMP)
```

#### `food_items`
```
id (TEXT, PRIMARY KEY)
name (TEXT)
category_id (TEXT, FOREIGN KEY)
category_name (TEXT)
kitchen_id (TEXT, FOREIGN KEY)
kitchen_name (TEXT)
price (REAL)
description (TEXT)
specifications (TEXT)
status (TEXT)
created_at (TIMESTAMP)
```

#### `tables`
```
id (TEXT, PRIMARY KEY)
number (INTEGER)
area_id (TEXT, FOREIGN KEY)
area_name (TEXT)
capacity (INTEGER)
status (TEXT)
created_at (TIMESTAMP)
```

#### `order_types`
```
id (TEXT, PRIMARY KEY)
name (TEXT)
description (TEXT)
status (TEXT)
created_at (TIMESTAMP)
```

#### `orders`
```
id (TEXT, PRIMARY KEY)
order_number (TEXT, UNIQUE)
table_id (TEXT, FOREIGN KEY)
table_number (TEXT)
order_type_id (TEXT, FOREIGN KEY)
order_type_name (TEXT)
customer_name (TEXT)
items_count (INTEGER)
total_amount (REAL)
status (TEXT)
notes (TEXT)
created_at (TIMESTAMP)
updated_at (TIMESTAMP)
```

#### `daily_production`
```
id (TEXT, PRIMARY KEY)
food_id (TEXT, FOREIGN KEY)
food_name (TEXT)
category_name (TEXT)
date (DATE)
planned_quantity (INTEGER)
produced (INTEGER)
notes (TEXT)
created_at (TIMESTAMP)
```

## API Endpoints

All endpoints work the same as before, but now use SQLite:

### Categories
- `GET /api/categories` - List all categories
- `POST /api/categories` - Create new category
- `DELETE /api/categories/<id>` - Delete category

### Kitchens
- `GET /api/kitchens` - List all kitchens
- `POST /api/kitchens` - Create new kitchen
- `DELETE /api/kitchens/<id>` - Delete kitchen

### Food Items
- `GET /api/food-items` - List all food items
- `POST /api/food-items` - Create new food item
- `DELETE /api/food-items/<id>` - Delete food item

### Areas
- `GET /api/areas` - List all areas
- `POST /api/areas` - Create new area
- `DELETE /api/areas/<id>` - Delete area

### Tables
- `GET /api/tables` - List all tables
- `POST /api/tables` - Create new table
- `DELETE /api/tables/<id>` - Delete table

### Order Types
- `GET /api/order-types` - List all order types
- `POST /api/order-types` - Create new order type
- `DELETE /api/order-types/<id>` - Delete order type

### Orders
- `GET /api/orders` - List all orders
- `POST /api/orders` - Create new order
- `GET /api/orders/<id>` - Get order details
- `PUT /api/orders/<id>` - Update order
- `DELETE /api/orders/<id>` - Delete order

### Daily Production
- `GET /api/daily-production?date=YYYY-MM-DD` - Get production for date
- `POST /api/daily-production` - Create production item
- `PUT /api/daily-production/<id>` - Update production
- `DELETE /api/daily-production/<id>` - Delete production

## Migration Notes

### Advantages of SQLite over Redis
1. **Persistent Storage** - Data survives application restarts
2. **ACID Compliance** - Guarantees data integrity
3. **No Server Required** - Embedded database, no separate Redis server needed
4. **Foreign Keys** - Enforce data relationships
5. **Simpler Deployment** - Single file database
6. **Built-in Python Support** - No additional dependencies

### Removed Redis Dependencies
- No need to run Redis server
- Removed all Redis-specific commands (SET, SADD, SMEMBERS, etc.)
- Simplified connection management

## Data Types
- UUID format for all IDs (ensures uniqueness across systems)
- ISO format timestamps for all date/time fields
- Proper relationship handling through foreign keys

## Future Enhancements
- Add database migrations for schema changes
- Add backups and recovery procedures
- Add data export functionality
- Add transaction handling for complex operations
- Add indexes for performance optimization

## Troubleshooting

### Database Lock Error
If you encounter a "database is locked" error:
```bash
# Remove the database and reinitialize
rm my_database.db
python init_database.py
```

### Import Errors
Make sure all dependencies are installed:
```bash
pip install -r requirements.txt
```

### Port Already in Use
If port 5100 is already in use, edit `app.py` and change the port:
```python
app.run(debug=True, host='0.0.0.0', port=5101)
```
