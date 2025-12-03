"""
Database Schema Documentation for QSR Kitchen Management System
SQLite3 Database: my_db.db

This module provides complete schema documentation and information about
the kitchen management database structure.
"""

import sqlite3
import json
from typing import Dict, List, Any

# Database path
DB_PATH = "my_db.db"


class DatabaseSchema:
    """
    Comprehensive database schema documentation and utilities
    for the QSR Kitchen Management System
    """
    
    # Complete schema definition
    SCHEMA_DEFINITION = {
        "areas": {
            "description": "Restaurant areas/sections",
            "columns": {
                "id": {"type": "TEXT", "pk": True, "description": "Unique identifier"},
                "name": {"type": "TEXT", "not_null": True, "description": "Area name (e.g., 'Dining Hall', 'Patio')"},
                "description": {"type": "TEXT", "description": "Area description"},
                "status": {"type": "TEXT", "default": "'active'", "description": "Status: active/inactive"},
                "tables_count": {"type": "INTEGER", "default": "0", "description": "Number of tables in area"},
                "created_at": {"type": "TIMESTAMP", "default": "CURRENT_TIMESTAMP", "description": "Creation timestamp"}
            }
        },
        "categories": {
            "description": "Food item categories",
            "columns": {
                "id": {"type": "TEXT", "pk": True, "description": "Unique identifier"},
                "name": {"type": "TEXT", "not_null": True, "description": "Category name (e.g., 'Main Course', 'Appetizers')"},
                "description": {"type": "TEXT", "description": "Category description"},
                "status": {"type": "TEXT", "default": "'active'", "description": "Status: active/inactive"},
                "items_count": {"type": "INTEGER", "default": "0", "description": "Number of items in category"},
                "created_at": {"type": "TIMESTAMP", "default": "CURRENT_TIMESTAMP", "description": "Creation timestamp"}
            }
        },
        "kitchens": {
            "description": "Kitchen stations/areas",
            "columns": {
                "id": {"type": "TEXT", "pk": True, "description": "Unique identifier"},
                "name": {"type": "TEXT", "not_null": True, "description": "Kitchen name (e.g., 'Main Kitchen', 'Grill Station')"},
                "location": {"type": "TEXT", "description": "Physical location"},
                "description": {"type": "TEXT", "description": "Kitchen description"},
                "status": {"type": "TEXT", "default": "'active'", "description": "Status: active/inactive"},
                "items_count": {"type": "INTEGER", "default": "0", "description": "Number of food items prepared here"},
                "created_at": {"type": "TIMESTAMP", "default": "CURRENT_TIMESTAMP", "description": "Creation timestamp"}
            }
        },
        "food_items": {
            "description": "Menu items",
            "columns": {
                "id": {"type": "TEXT", "pk": True, "description": "Unique identifier"},
                "name": {"type": "TEXT", "not_null": True, "description": "Item name"},
                "category_id": {"type": "TEXT", "not_null": True, "fk": "categories.id", "description": "Category reference"},
                "category_name": {"type": "TEXT", "description": "Cached category name"},
                "kitchen_id": {"type": "TEXT", "not_null": True, "fk": "kitchens.id", "description": "Assigned kitchen reference"},
                "kitchen_name": {"type": "TEXT", "description": "Cached kitchen name"},
                "price": {"type": "REAL", "description": "Item price"},
                "description": {"type": "TEXT", "description": "Item description"},
                "specifications": {"type": "TEXT", "description": "Cooking specifications/requirements"},
                "status": {"type": "TEXT", "default": "'available'", "description": "Status: available/unavailable"},
                "created_at": {"type": "TIMESTAMP", "default": "CURRENT_TIMESTAMP", "description": "Creation timestamp"}
            }
        },
        "tables": {
            "description": "Restaurant tables",
            "columns": {
                "id": {"type": "TEXT", "pk": True, "description": "Unique identifier"},
                "number": {"type": "INTEGER", "not_null": True, "description": "Table number"},
                "area_id": {"type": "TEXT", "not_null": True, "fk": "areas.id", "description": "Area reference"},
                "area_name": {"type": "TEXT", "description": "Cached area name"},
                "capacity": {"type": "INTEGER", "description": "Seating capacity"},
                "status": {"type": "TEXT", "default": "'available'", "description": "Status: available/occupied"},
                "created_at": {"type": "TIMESTAMP", "default": "CURRENT_TIMESTAMP", "description": "Creation timestamp"}
            }
        },
        "order_types": {
            "description": "Order types (Dine-in, Takeout, Delivery, etc.)",
            "columns": {
                "id": {"type": "TEXT", "pk": True, "description": "Unique identifier"},
                "name": {"type": "TEXT", "not_null": True, "description": "Type name"},
                "description": {"type": "TEXT", "description": "Type description"},
                "status": {"type": "TEXT", "default": "'active'", "description": "Status: active/inactive"},
                "created_at": {"type": "TIMESTAMP", "default": "CURRENT_TIMESTAMP", "description": "Creation timestamp"}
            }
        },
        "orders": {
            "description": "Customer orders",
            "columns": {
                "id": {"type": "TEXT", "pk": True, "description": "Unique identifier (UUID)"},
                "order_number": {"type": "TEXT", "unique": True, "description": "Human-readable order number"},
                "table_id": {"type": "TEXT", "fk": "tables.id", "description": "Table reference (for dine-in)"},
                "table_number": {"type": "TEXT", "description": "Cached table number"},
                "order_type_id": {"type": "TEXT", "fk": "order_types.id", "description": "Order type reference"},
                "order_type_name": {"type": "TEXT", "description": "Cached order type name"},
                "customer_name": {"type": "TEXT", "description": "Customer name"},
                "items_count": {"type": "INTEGER", "default": "0", "description": "Number of items"},
                "total_amount": {"type": "REAL", "default": "0", "description": "Total order amount"},
                "status": {"type": "TEXT", "default": "'pending'", "description": "Status: pending/preparing/ready/completed/cancelled"},
                "notes": {"type": "TEXT", "description": "Special notes/requests"},
                "created_at": {"type": "TIMESTAMP", "default": "CURRENT_TIMESTAMP", "description": "Order creation time"},
                "updated_at": {"type": "TIMESTAMP", "default": "CURRENT_TIMESTAMP", "description": "Last update time"}
            }
        },
        "order_items": {
            "description": "Individual items within an order",
            "columns": {
                "id": {"type": "TEXT", "pk": True, "description": "Unique identifier"},
                "order_id": {"type": "TEXT", "not_null": True, "fk": "orders.id", "description": "Order reference"},
                "food_item_id": {"type": "TEXT", "not_null": True, "fk": "food_items.id", "description": "Food item reference"},
                "food_name": {"type": "TEXT", "description": "Cached food item name"},
                "category_name": {"type": "TEXT", "description": "Cached category name"},
                "quantity": {"type": "INTEGER", "not_null": True, "description": "Quantity ordered"},
                "price": {"type": "REAL", "not_null": True, "description": "Price per unit"},
                "notes": {"type": "TEXT", "description": "Special requests for this item"},
                "created_at": {"type": "TIMESTAMP", "default": "CURRENT_TIMESTAMP", "description": "Creation timestamp"}
            }
        },
        "kitchen_assignments": {
            "description": "Assignment of order items to specific kitchens",
            "columns": {
                "id": {"type": "TEXT", "pk": True, "description": "Unique identifier"},
                "item_id": {"type": "TEXT", "not_null": True, "fk": "order_items.id", "description": "Order item reference"},
                "kitchen_id": {"type": "TEXT", "not_null": True, "fk": "kitchens.id", "description": "Assigned kitchen"},
                "order_id": {"type": "TEXT", "not_null": True, "fk": "orders.id", "description": "Order reference"},
                "status": {"type": "TEXT", "default": "'pending'", "description": "Status: pending/preparing/ready/completed"},
                "assigned_at": {"type": "TIMESTAMP", "default": "CURRENT_TIMESTAMP", "description": "Assignment time"},
                "completed_at": {"type": "TIMESTAMP", "description": "Completion time"}
            }
        },
        "daily_production": {
            "description": "Daily production planning",
            "columns": {
                "id": {"type": "TEXT", "pk": True, "description": "Unique identifier"},
                "food_id": {"type": "TEXT", "not_null": True, "fk": "food_items.id", "description": "Food item reference"},
                "food_name": {"type": "TEXT", "description": "Cached food name"},
                "category_name": {"type": "TEXT", "description": "Cached category name"},
                "date": {"type": "DATE", "not_null": True, "description": "Production date"},
                "planned_quantity": {"type": "INTEGER", "description": "Planned quantity"},
                "produced": {"type": "INTEGER", "default": "0", "description": "Actually produced"},
                "notes": {"type": "TEXT", "description": "Notes"},
                "created_at": {"type": "TIMESTAMP", "default": "CURRENT_TIMESTAMP", "description": "Creation timestamp"}
            }
        },
        "appliances": {
            "description": "Kitchen appliances/equipment",
            "columns": {
                "id": {"type": "TEXT", "pk": True, "description": "Unique identifier"},
                "name": {"type": "TEXT", "not_null": True, "description": "Appliance name"},
                "type": {"type": "TEXT", "not_null": True, "description": "Type (Oven, Stove, Fryer, etc.)"},
                "model": {"type": "TEXT", "description": "Model number"},
                "serial_number": {"type": "TEXT", "description": "Serial number"},
                "description": {"type": "TEXT", "description": "Description"},
                "status": {"type": "TEXT", "default": "'active'", "description": "Status: active/inactive/maintenance"},
                "purchase_date": {"type": "DATE", "description": "Purchase date"},
                "last_maintenance": {"type": "DATE", "description": "Last maintenance date"},
                "notes": {"type": "TEXT", "description": "Notes"},
                "created_at": {"type": "TIMESTAMP", "default": "CURRENT_TIMESTAMP", "description": "Creation timestamp"}
            }
        },
        "kitchen_appliances": {
            "description": "Mapping of appliances to kitchens",
            "columns": {
                "id": {"type": "TEXT", "pk": True, "description": "Unique identifier"},
                "kitchen_id": {"type": "TEXT", "not_null": True, "fk": "kitchens.id", "description": "Kitchen reference"},
                "appliance_id": {"type": "TEXT", "not_null": True, "fk": "appliances.id", "description": "Appliance reference"},
                "quantity": {"type": "INTEGER", "default": "1", "description": "Number of this appliance"},
                "location": {"type": "TEXT", "description": "Location within kitchen"},
                "status": {"type": "TEXT", "default": "'active'", "description": "Status: active/inactive"},
                "assigned_date": {"type": "TIMESTAMP", "default": "CURRENT_TIMESTAMP", "description": "Assignment date"}
            }
        },
        "iot_devices": {
            "description": "IoT sensors and devices",
            "columns": {
                "id": {"type": "TEXT", "pk": True, "description": "Unique identifier"},
                "name": {"type": "TEXT", "not_null": True, "description": "Device name"},
                "device_type": {"type": "TEXT", "not_null": True, "description": "Type (Temperature, Humidity, Motion, etc.)"},
                "device_id": {"type": "TEXT", "unique": True, "description": "Physical device ID"},
                "location": {"type": "TEXT", "description": "Physical location"},
                "kitchen_id": {"type": "TEXT", "fk": "kitchens.id", "description": "Associated kitchen"},
                "description": {"type": "TEXT", "description": "Description"},
                "status": {"type": "TEXT", "default": "'active'", "description": "Status: active/inactive"},
                "battery_level": {"type": "INTEGER", "description": "Battery percentage"},
                "signal_strength": {"type": "INTEGER", "description": "Signal strength"},
                "last_sync": {"type": "TIMESTAMP", "description": "Last sync time"},
                "ip_address": {"type": "TEXT", "description": "IP address"},
                "mac_address": {"type": "TEXT", "description": "MAC address"},
                "firmware_version": {"type": "TEXT", "description": "Firmware version"},
                "notes": {"type": "TEXT", "description": "Notes"},
                "created_at": {"type": "TIMESTAMP", "default": "CURRENT_TIMESTAMP", "description": "Creation timestamp"}
            }
        },
        "staff": {
            "description": "Kitchen staff members",
            "columns": {
                "id": {"type": "TEXT", "pk": True, "description": "Unique identifier"},
                "name": {"type": "TEXT", "not_null": True, "description": "Staff member name"},
                "email": {"type": "TEXT", "unique": True, "description": "Email address"},
                "phone": {"type": "TEXT", "description": "Phone number"},
                "position": {"type": "TEXT", "not_null": True, "description": "Position/role"},
                "department": {"type": "TEXT", "description": "Department"},
                "kitchen_id": {"type": "TEXT", "fk": "kitchens.id", "description": "Assigned kitchen"},
                "hire_date": {"type": "DATE", "description": "Hire date"},
                "date_of_birth": {"type": "DATE", "description": "Date of birth"},
                "address": {"type": "TEXT", "description": "Address"},
                "city": {"type": "TEXT", "description": "City"},
                "state": {"type": "TEXT", "description": "State"},
                "postal_code": {"type": "TEXT", "description": "Postal code"},
                "emergency_contact_name": {"type": "TEXT", "description": "Emergency contact name"},
                "emergency_contact_phone": {"type": "TEXT", "description": "Emergency contact phone"},
                "status": {"type": "TEXT", "default": "'active'", "description": "Status: active/inactive"},
                "salary_type": {"type": "TEXT", "description": "Salary type"},
                "notes": {"type": "TEXT", "description": "Notes"},
                "created_at": {"type": "TIMESTAMP", "default": "CURRENT_TIMESTAMP", "description": "Creation timestamp"}
            }
        },
        "staff_kitchen_requests": {
            "description": "Staff requests to work in specific kitchens",
            "columns": {
                "id": {"type": "TEXT", "pk": True, "description": "Unique identifier"},
                "staff_id": {"type": "TEXT", "not_null": True, "fk": "staff.id", "description": "Staff member"},
                "staff_name": {"type": "TEXT", "description": "Cached staff name"},
                "kitchen_id": {"type": "TEXT", "not_null": True, "fk": "kitchens.id", "description": "Requested kitchen"},
                "kitchen_name": {"type": "TEXT", "description": "Cached kitchen name"},
                "position": {"type": "TEXT", "description": "Position requested"},
                "request_reason": {"type": "TEXT", "description": "Reason for request"},
                "requested_start_date": {"type": "DATE", "description": "Requested start date"},
                "status": {"type": "TEXT", "default": "'pending'", "description": "Status: pending/approved/rejected"},
                "approval_status": {"type": "TEXT", "default": "'pending'", "description": "Approval status"},
                "approved_by": {"type": "TEXT", "description": "Approver name"},
                "approval_notes": {"type": "TEXT", "description": "Approval notes"},
                "approval_date": {"type": "TIMESTAMP", "description": "Approval date"},
                "rejection_reason": {"type": "TEXT", "description": "Rejection reason if applicable"},
                "requested_date": {"type": "TIMESTAMP", "default": "CURRENT_TIMESTAMP", "description": "Request date"},
                "updated_at": {"type": "TIMESTAMP", "default": "CURRENT_TIMESTAMP", "description": "Update timestamp"}
            }
        },
        "staff_kitchen_assignments": {
            "description": "Active staff assignments to kitchens",
            "columns": {
                "id": {"type": "TEXT", "pk": True, "description": "Unique identifier"},
                "staff_id": {"type": "TEXT", "not_null": True, "fk": "staff.id", "description": "Staff member"},
                "staff_name": {"type": "TEXT", "description": "Cached staff name"},
                "kitchen_id": {"type": "TEXT", "not_null": True, "fk": "kitchens.id", "description": "Assigned kitchen"},
                "kitchen_name": {"type": "TEXT", "description": "Cached kitchen name"},
                "position": {"type": "TEXT", "description": "Position"},
                "request_id": {"type": "TEXT", "fk": "staff_kitchen_requests.id", "description": "Associated request"},
                "assigned_date": {"type": "TIMESTAMP", "default": "CURRENT_TIMESTAMP", "description": "Assignment date"},
                "end_date": {"type": "DATE", "description": "End date if temporary"},
                "status": {"type": "TEXT", "default": "'active'", "description": "Status: active/inactive"},
                "notes": {"type": "TEXT", "description": "Notes"},
                "created_at": {"type": "TIMESTAMP", "default": "CURRENT_TIMESTAMP", "description": "Creation timestamp"}
            }
        }
    }
    
    @staticmethod
    def get_schema_as_markdown() -> str:
        """Generate markdown documentation of the database schema"""
        md = "# Database Schema Documentation\n\n"
        md += "## SQLite3 Database: my_db.db\n\n"
        
        for table_name, table_info in sorted(DatabaseSchema.SCHEMA_DEFINITION.items()):
            md += f"### {table_name.upper()}\n"
            md += f"**{table_info.get('description', 'No description')}**\n\n"
            md += "| Column | Type | Constraints | Description |\n"
            md += "|--------|------|-------------|-------------|\n"
            
            for col_name, col_info in table_info['columns'].items():
                col_type = col_info['type']
                constraints = []
                if col_info.get('pk'):
                    constraints.append("🔑 PK")
                if col_info.get('not_null'):
                    constraints.append("NOT NULL")
                if col_info.get('unique'):
                    constraints.append("UNIQUE")
                if col_info.get('fk'):
                    constraints.append(f"FK → {col_info['fk']}")
                
                constraint_str = ", ".join(constraints) if constraints else ""
                description = col_info.get('description', '')
                
                md += f"| {col_name} | {col_type} | {constraint_str} | {description} |\n"
            
            md += "\n"
        
        return md
    
    @staticmethod
    def get_schema_as_json() -> str:
        """Get schema as formatted JSON"""
        return json.dumps(DatabaseSchema.SCHEMA_DEFINITION, indent=2)
    
    @staticmethod
    def get_table_relationships() -> Dict[str, List[str]]:
        """Get foreign key relationships between tables"""
        relationships = {}
        
        for table_name, table_info in DatabaseSchema.SCHEMA_DEFINITION.items():
            relationships[table_name] = []
            
            for col_name, col_info in table_info['columns'].items():
                if col_info.get('fk'):
                    relationships[table_name].append({
                        'column': col_name,
                        'references': col_info['fk']
                    })
        
        return relationships
    
    @staticmethod
    def get_primary_keys() -> Dict[str, List[str]]:
        """Get primary keys for all tables"""
        pks = {}
        
        for table_name, table_info in DatabaseSchema.SCHEMA_DEFINITION.items():
            pk_cols = [
                col_name for col_name, col_info in table_info['columns'].items()
                if col_info.get('pk')
            ]
            pks[table_name] = pk_cols
        
        return pks
    
    @staticmethod
    def print_schema():
        """Print complete schema documentation"""
        print("\n" + "="*80)
        print("DATABASE SCHEMA DOCUMENTATION")
        print("="*80 + "\n")
        print(DatabaseSchema.get_schema_as_markdown())


if __name__ == "__main__":
    # Print schema when run directly
    DatabaseSchema.print_schema()
    
    # Also show relationships
    print("\n" + "="*80)
    print("TABLE RELATIONSHIPS (Foreign Keys)")
    print("="*80 + "\n")
    
    relationships = DatabaseSchema.get_table_relationships()
    for table, refs in relationships.items():
        if refs:
            print(f"{table}:")
            for ref in refs:
                print(f"  └─ {ref['column']} → {ref['references']}")
