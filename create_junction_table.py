#!/usr/bin/env python3
"""
Create food_item_kitchens junction table for many-to-many relationship
"""

import pymysql
import pymysql.cursors
from constants import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE

def get_connection():
    """Get database connection"""
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )

def create_junction_table():
    """Create food_item_kitchens junction table"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        print("🔧 Creating food_kitchen_mapping junction table...")
        
        # Create the junction table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS food_kitchen_mapping (
                id VARCHAR(255) PRIMARY KEY,
                food_id VARCHAR(255) NOT NULL,
                kitchen_id VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_food_kitchen (food_id, kitchen_id),
                FOREIGN KEY (food_id) REFERENCES food_items(id) ON DELETE CASCADE,
                FOREIGN KEY (kitchen_id) REFERENCES kitchens(id) ON DELETE CASCADE
            )
        """)
        
        conn.commit()
        print("✅ food_kitchen_mapping table created successfully")
        
        # Check if food_items table has old kitchen_id column
        cursor.execute("SHOW COLUMNS FROM food_items LIKE 'kitchen_id'")
        has_kitchen_id = cursor.fetchone() is not None
        
        if has_kitchen_id:
            print("\n🔄 Migrating existing food item-kitchen relationships...")
            
            # Get all food items with their kitchen assignments
            cursor.execute("""
                SELECT id, kitchen_id 
                FROM food_items 
                WHERE kitchen_id IS NOT NULL AND kitchen_id != ''
            """)
            food_items = cursor.fetchall()
            
            if food_items:
                # Insert into junction table
                for item in food_items:
                    try:
                        cursor.execute("""
                            INSERT IGNORE INTO food_kitchen_mapping (id, food_id, kitchen_id)
                            VALUES (UUID(), %s, %s)
                        """, (item['id'], item['kitchen_id']))
                    except Exception as e:
                        print(f"   ⚠️  Warning: Could not migrate {item['id']}: {e}")
                
                conn.commit()
                print(f"✅ Migrated {len(food_items)} food item-kitchen relationships")
            else:
                print("   No existing relationships to migrate")
            
            # We won't drop the old column yet - the app.py might still use it
            print("\n⚠️  Note: Old kitchen_id column kept for compatibility")
            print("   The app will use food_item_kitchens table for multiple kitchens")
        
        # Add icon column to kitchens if it doesn't exist
        cursor.execute("SHOW COLUMNS FROM kitchens LIKE 'icon'")
        has_icon = cursor.fetchone() is not None
        
        if not has_icon:
            print("\n🔧 Adding icon column to kitchens table...")
            cursor.execute("ALTER TABLE kitchens ADD COLUMN icon VARCHAR(10) DEFAULT '🍳'")
            conn.commit()
            print("✅ Icon column added to kitchens table")
        
        print("\n📊 Current database structure:")
        cursor.execute("SELECT COUNT(*) as count FROM kitchens")
        kitchen_count = cursor.fetchone()['count']
        cursor.execute("SELECT COUNT(*) as count FROM food_items")
        food_count = cursor.fetchone()['count']
        cursor.execute("SELECT COUNT(*) as count FROM food_kitchen_mapping")
        mapping_count = cursor.fetchone()['count']
        
        print(f"   Kitchens: {kitchen_count}")
        print(f"   Food Items: {food_count}")
        print(f"   Food-Kitchen Mappings: {mapping_count}")
        
        print("\n✅ Migration complete! You can now run reset_data.py")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    print("=" * 60)
    print("🔧 CREATE FOOD_KITCHEN_MAPPING JUNCTION TABLE")
    print("=" * 60)
    print()
    
    create_junction_table()
