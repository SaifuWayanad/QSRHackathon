#!/usr/bin/env python3
"""
Populate customers table with sample data
"""

import pymysql
from datetime import datetime, date
from constants import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE

def get_connection():
    """Get database connection"""
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        cursorclass=pymysql.cursors.DictCursor
    )

def create_customers_table():
    """Create customers table if not exists"""
    conn = get_connection()
    cursor = conn.cursor()
    
    print("📋 Creating customers table...")
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS customers (
        id VARCHAR(255) PRIMARY KEY,
        customer_code VARCHAR(50) UNIQUE NOT NULL COMMENT 'Unique customer code like CUST-001',
        name VARCHAR(255) NOT NULL,
        email VARCHAR(255) UNIQUE,
        phone VARCHAR(20) UNIQUE,
        address TEXT,
        city VARCHAR(100),
        postal_code VARCHAR(20),
        
        dietary_preferences TEXT COMMENT 'JSON or comma-separated: vegetarian, vegan, gluten-free, etc.',
        allergens TEXT COMMENT 'Known allergens to avoid',
        favorite_items TEXT COMMENT 'JSON array of favorite food item IDs',
        notes TEXT COMMENT 'Special notes about customer preferences',
        
        total_orders INT DEFAULT 0,
        total_spent DECIMAL(10, 2) DEFAULT 0.00,
        loyalty_points INT DEFAULT 0,
        member_since DATE,
        last_order_date DATETIME,
        
        status VARCHAR(50) DEFAULT 'active' COMMENT 'active, inactive, blocked',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        
        INDEX idx_customer_code (customer_code),
        INDEX idx_email (email),
        INDEX idx_phone (phone),
        INDEX idx_status (status),
        INDEX idx_member_since (member_since)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
    
    cursor.execute(create_table_sql)
    conn.commit()
    print("✅ Customers table created/verified")
    
    # Check if customer_id column exists in orders table
    print("\n📋 Checking orders table for customer_id column...")
    cursor.execute("""
        SELECT COUNT(*) as col_exists
        FROM information_schema.columns 
        WHERE table_schema = %s 
        AND table_name = 'orders' 
        AND column_name = 'customer_id'
    """, (MYSQL_DATABASE,))
    
    result = cursor.fetchone()
    
    if result['col_exists'] == 0:
        print("➕ Adding customer_id column to orders table...")
        try:
            cursor.execute("""
                ALTER TABLE orders 
                ADD COLUMN customer_id VARCHAR(255) AFTER id,
                ADD INDEX idx_customer_id (customer_id)
            """)
            
            # Try to add foreign key constraint (may fail if there are existing orders)
            try:
                cursor.execute("""
                    ALTER TABLE orders
                    ADD CONSTRAINT fk_orders_customer 
                        FOREIGN KEY (customer_id) REFERENCES customers(id) 
                        ON DELETE SET NULL 
                        ON UPDATE CASCADE
                """)
                print("✅ Foreign key constraint added")
            except pymysql.err.IntegrityError:
                print("⚠️  Foreign key constraint skipped (existing data)")
            
            conn.commit()
            print("✅ customer_id column added to orders table")
        except Exception as e:
            print(f"⚠️  Error adding column: {e}")
    else:
        print("✅ customer_id column already exists in orders table")
    
    cursor.close()
    conn.close()

def populate_customers():
    """Populate customers table with sample data"""
    conn = get_connection()
    cursor = conn.cursor()
    
    print("\n📊 Populating customers table...")
    
    # Sample customers data
    customers = [
        {
            'id': 'cust-1',
            'customer_code': 'CUST-001',
            'name': 'John Doe',
            'email': 'john.doe@example.com',
            'phone': '+1234567890',
            'dietary_preferences': 'vegetarian',
            'status': 'active',
            'member_since': date(2024, 1, 15),
            'total_orders': 5,
            'total_spent': 125.50,
            'loyalty_points': 125,
            'last_order_date': datetime(2024, 12, 1, 18, 30, 0)
        },
        {
            'id': 'cust-2',
            'customer_code': 'CUST-002',
            'name': 'Jane Smith',
            'email': 'jane.smith@example.com',
            'phone': '+1234567891',
            'dietary_preferences': 'gluten-free',
            'status': 'active',
            'member_since': date(2024, 2, 20),
            'total_orders': 3,
            'total_spent': 78.25,
            'loyalty_points': 78,
            'last_order_date': datetime(2024, 12, 2, 12, 15, 0)
        },
        {
            'id': 'cust-3',
            'customer_code': 'CUST-003',
            'name': 'Mike Johnson',
            'email': 'mike.j@example.com',
            'phone': '+1234567892',
            'dietary_preferences': None,
            'status': 'active',
            'member_since': date(2024, 3, 10),
            'total_orders': 0,
            'total_spent': 0.00,
            'loyalty_points': 0,
            'last_order_date': None
        },
        {
            'id': 'cust-4',
            'customer_code': 'CUST-004',
            'name': 'Sarah Williams',
            'email': 'sarah.w@example.com',
            'phone': '+1234567893',
            'dietary_preferences': 'vegan,nut-free',
            'allergens': 'nuts,shellfish',
            'status': 'active',
            'member_since': date(2024, 4, 5),
            'total_orders': 0,
            'total_spent': 0.00,
            'loyalty_points': 0,
            'last_order_date': None
        },
        {
            'id': 'cust-5',
            'customer_code': 'CUST-005',
            'name': 'David Brown',
            'email': 'david.b@example.com',
            'phone': '+1234567894',
            'dietary_preferences': None,
            'status': 'active',
            'member_since': date(2024, 5, 12),
            'total_orders': 0,
            'total_spent': 0.00,
            'loyalty_points': 0,
            'last_order_date': None
        }
    ]
    
    # Insert customers
    insert_count = 0
    skip_count = 0
    
    for customer in customers:
        try:
            cursor.execute("""
                INSERT INTO customers 
                    (id, customer_code, name, email, phone, dietary_preferences, 
                     allergens, status, member_since, total_orders, total_spent, 
                     loyalty_points, last_order_date, created_at, updated_at)
                VALUES 
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                customer['id'],
                customer['customer_code'],
                customer['name'],
                customer['email'],
                customer['phone'],
                customer.get('dietary_preferences'),
                customer.get('allergens'),
                customer['status'],
                customer['member_since'],
                customer['total_orders'],
                customer['total_spent'],
                customer['loyalty_points'],
                customer.get('last_order_date'),
                datetime.now(),
                datetime.now()
            ))
            insert_count += 1
            print(f"✅ Inserted: {customer['customer_code']} - {customer['name']}")
        except pymysql.err.IntegrityError as e:
            skip_count += 1
            print(f"⚠️  Skipped (already exists): {customer['customer_code']} - {customer['name']}")
    
    conn.commit()
    
    print(f"\n📊 Summary:")
    print(f"   ✅ Inserted: {insert_count}")
    print(f"   ⚠️  Skipped: {skip_count}")
    
    # Show current customers
    print("\n📋 Current customers in database:")
    cursor.execute("SELECT customer_code, name, phone, total_orders, loyalty_points, status FROM customers ORDER BY customer_code")
    customers = cursor.fetchall()
    
    for customer in customers:
        print(f"   {customer['customer_code']}: {customer['name']} ({customer['phone']}) - Orders: {customer['total_orders']}, Points: {customer['loyalty_points']}")
    
    cursor.close()
    conn.close()

def main():
    """Main function"""
    print("=" * 60)
    print("🚀 CUSTOMER TABLE SETUP")
    print("=" * 60)
    
    try:
        # Create table
        create_customers_table()
        
        # Populate data
        populate_customers()
        
        print("\n" + "=" * 60)
        print("✅ CUSTOMER TABLE SETUP COMPLETE!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
