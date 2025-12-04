#!/usr/bin/env python3
"""
Script to migrate init_database.py from SQLite to MySQL
"""
import re

def migrate_init_database():
    with open('init_database.py', 'r') as f:
        content = f.read()
    
    # 1. Update imports and header
    content = content.replace(
        '"""Unified database initialization script for SQLite',
        '"""Unified database initialization script for MySQL'
    )
    
    content = content.replace(
        'import sqlite3',
        'import pymysql\nimport pymysql.cursors'
    )
    
    # Add MySQL constants import
    content = content.replace(
        'from datetime import datetime',
        'from datetime import datetime\nfrom constants import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE'
    )
    
    # 2. Replace database path and connection function
    old_conn = '''DB_PATH = "my_database.db"

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn'''
    
    new_conn = '''def get_db_connection():
    """Get database connection"""
    conn = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )
    return conn'''
    
    content = content.replace(old_conn, new_conn)
    
    # 3. Replace SQLite data types with MySQL types
    content = re.sub(r'\bid TEXT PRIMARY KEY\b', 'id VARCHAR(255) PRIMARY KEY', content)
    content = re.sub(r'\bTEXT NOT NULL\b', 'VARCHAR(255) NOT NULL', content)
    content = re.sub(r'\bTEXT UNIQUE\b', 'VARCHAR(255) UNIQUE', content)
    content = re.sub(r'\bTEXT DEFAULT\b', 'VARCHAR(255) DEFAULT', content)
    content = re.sub(r'\bname TEXT\b', 'name VARCHAR(255)', content)
    content = re.sub(r'\bemail TEXT\b', 'email VARCHAR(255)', content)
    content = re.sub(r'\bphone TEXT\b', 'phone VARCHAR(50)', content)
    content = re.sub(r'\bposition TEXT\b', 'position VARCHAR(100)', content)
    content = re.sub(r'\blocation TEXT\b', 'location VARCHAR(255)', content)
    content = re.sub(r'\btype TEXT\b', 'type VARCHAR(100)', content)
    content = re.sub(r'\bmodel TEXT\b', 'model VARCHAR(255)', content)
    content = re.sub(r'\bdevice_type TEXT\b', 'device_type VARCHAR(100)', content)
    content = re.sub(r'\bdevice_id TEXT\b', 'device_id VARCHAR(255)', content)
    content = re.sub(r'\bserial_number TEXT\b', 'serial_number VARCHAR(255)', content)
    content = re.sub(r'\bip_address TEXT\b', 'ip_address VARCHAR(50)', content)
    content = re.sub(r'\bmac_address TEXT\b', 'mac_address VARCHAR(50)', content)
    content = re.sub(r'\bfirmware_version TEXT\b', 'firmware_version VARCHAR(100)', content)
    content = re.sub(r'\bstatus TEXT\b', 'status VARCHAR(50)', content)
    content = re.sub(r'\bdepartment TEXT\b', 'department VARCHAR(100)', content)
    content = re.sub(r'\bcity TEXT\b', 'city VARCHAR(100)', content)
    content = re.sub(r'\bstate TEXT\b', 'state VARCHAR(100)', content)
    content = re.sub(r'\bpostal_code TEXT\b', 'postal_code VARCHAR(20)', content)
    content = re.sub(r'\bsalary_type TEXT\b', 'salary_type VARCHAR(50)', content)
    content = re.sub(r'\border_number TEXT\b', 'order_number VARCHAR(255)', content)
    content = re.sub(r'\btable_id TEXT\b', 'table_id VARCHAR(255)', content)
    content = re.sub(r'\btable_number TEXT\b', 'table_number VARCHAR(255)', content)
    content = re.sub(r'\border_type_id TEXT\b', 'order_type_id VARCHAR(255)', content)
    content = re.sub(r'\border_type_name TEXT\b', 'order_type_name VARCHAR(255)', content)
    content = re.sub(r'\bcustomer_name TEXT\b', 'customer_name VARCHAR(255)', content)
    content = re.sub(r'\barea_id TEXT\b', 'area_id VARCHAR(255)', content)
    content = re.sub(r'\barea_name TEXT\b', 'area_name VARCHAR(255)', content)
    content = re.sub(r'\bcategory_id TEXT\b', 'category_id VARCHAR(255)', content)
    content = re.sub(r'\bcategory_name TEXT\b', 'category_name VARCHAR(255)', content)
    content = re.sub(r'\bkitchen_id TEXT\b', 'kitchen_id VARCHAR(255)', content)
    content = re.sub(r'\bkitchen_name TEXT\b', 'kitchen_name VARCHAR(255)', content)
    content = re.sub(r'\bfood_item_id TEXT\b', 'food_item_id VARCHAR(255)', content)
    content = re.sub(r'\bfood_name TEXT\b', 'food_name VARCHAR(255)', content)
    content = re.sub(r'\bfood_id TEXT\b', 'food_id VARCHAR(255)', content)
    content = re.sub(r'\bappliance_id TEXT\b', 'appliance_id VARCHAR(255)', content)
    content = re.sub(r'\bstaff_id TEXT\b', 'staff_id VARCHAR(255)', content)
    content = re.sub(r'\bstaff_name TEXT\b', 'staff_name VARCHAR(255)', content)
    content = re.sub(r'\brequest_id TEXT\b', 'request_id VARCHAR(255)', content)
    content = re.sub(r'\bapproved_by TEXT\b', 'approved_by VARCHAR(255)', content)
    
    content = re.sub(r'\bINTEGER\b', 'INT', content)
    content = re.sub(r'\bREAL\b', 'DECIMAL(10, 2)', content)
    
    # Update TIMESTAMP fields for MySQL
    content = re.sub(
        r'updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\b',
        'updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP',
        content
    )
    content = re.sub(r'\blast_sync TIMESTAMP\b', 'last_sync TIMESTAMP NULL', content)
    content = re.sub(r'\bapproval_date TIMESTAMP\b', 'approval_date TIMESTAMP NULL', content)
    
    # 4. Replace ? placeholders with %s
    content = re.sub(r"VALUES \(\?,", "VALUES (%s,", content)
    content = re.sub(r", \?", ", %s", content)
    content = re.sub(r"= \?", "= %s", content)
    content = re.sub(r"VALUES \(\?", "VALUES (%s", content)
    content = re.sub(r"\(\?\)", "(%s)", content)
    
    # 5. Replace sqlite3.IntegrityError with pymysql.IntegrityError
    content = content.replace('sqlite3.IntegrityError', 'pymysql.IntegrityError')
    
    with open('init_database.py', 'w') as f:
        f.write(content)
    
    print("✓ Successfully migrated init_database.py to MySQL")

if __name__ == '__main__':
    migrate_init_database()
