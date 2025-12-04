#!/usr/bin/env python3
"""
Initialize chat sessions tables in the database
"""

import pymysql
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

def create_chat_tables():
    """Create chat_sessions and chat_messages tables"""
    conn = get_connection()
    cursor = conn.cursor()
    
    print("📋 Creating chat_sessions table...")
    
    # Create chat_sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id VARCHAR(255) PRIMARY KEY,
            session_code VARCHAR(50) UNIQUE NOT NULL COMMENT 'Unique session code like SESS-001',
            customer_id VARCHAR(255) COMMENT 'Link to customer if identified',
            customer_phone VARCHAR(20) COMMENT 'Phone number for quick lookup',
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            status VARCHAR(50) DEFAULT 'active' COMMENT 'active, completed, abandoned',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            
            INDEX idx_session_code (session_code),
            INDEX idx_customer_id (customer_id),
            INDEX idx_customer_phone (customer_phone),
            INDEX idx_status (status),
            INDEX idx_started_at (started_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    
    print("✅ chat_sessions table created/verified")
    
    print("\n📋 Creating chat_messages table...")
    
    # Create chat_messages table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id VARCHAR(255) PRIMARY KEY,
            session_id VARCHAR(255) NOT NULL,
            sender VARCHAR(50) NOT NULL COMMENT 'customer or agent',
            message TEXT NOT NULL,
            metadata JSON COMMENT 'Additional data like tool calls, context, etc.',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            INDEX idx_session_id (session_id),
            INDEX idx_sender (sender),
            INDEX idx_created_at (created_at),
            
            FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE ON UPDATE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    
    print("✅ chat_messages table created/verified")
    
    # Try to add foreign key to customers if not exists
    try:
        print("\n📋 Checking foreign key to customers table...")
        cursor.execute("""
            SELECT COUNT(*) as fk_exists
            FROM information_schema.table_constraints
            WHERE constraint_type = 'FOREIGN KEY'
            AND table_schema = %s
            AND table_name = 'chat_sessions'
            AND constraint_name = 'fk_chat_sessions_customer'
        """, (MYSQL_DATABASE,))
        
        result = cursor.fetchone()
        
        if result['fk_exists'] == 0:
            print("➕ Adding foreign key constraint to customers table...")
            cursor.execute("""
                ALTER TABLE chat_sessions
                ADD CONSTRAINT fk_chat_sessions_customer 
                    FOREIGN KEY (customer_id) REFERENCES customers(id) 
                    ON DELETE SET NULL 
                    ON UPDATE CASCADE
            """)
            print("✅ Foreign key constraint added")
        else:
            print("✅ Foreign key constraint already exists")
    except Exception as e:
        print(f"⚠️  Foreign key constraint skipped: {e}")
    
    conn.commit()
    
    # Show table structure
    print("\n📊 Chat Sessions Table Structure:")
    cursor.execute("DESCRIBE chat_sessions")
    for row in cursor.fetchall():
        print(f"   {row['Field']}: {row['Type']}")
    
    print("\n📊 Chat Messages Table Structure:")
    cursor.execute("DESCRIBE chat_messages")
    for row in cursor.fetchall():
        print(f"   {row['Field']}: {row['Type']}")
    
    cursor.close()
    conn.close()

def main():
    """Main function"""
    print("=" * 60)
    print("🚀 CHAT SESSION TABLES SETUP")
    print("=" * 60)
    
    try:
        create_chat_tables()
        
        print("\n" + "=" * 60)
        print("✅ CHAT SESSION TABLES SETUP COMPLETE!")
        print("=" * 60)
        print("\nTables created:")
        print("  - chat_sessions: Stores chat session information")
        print("  - chat_messages: Stores all messages in each session")
        print("\nSession management is now enabled!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
