"""
Database Configuration Constants
"""
import os

# MySQL Database Configuration
MYSQL_HOST = '72.60.223.64'
MYSQL_PORT = 3306
MYSQL_USER = 'qsr_user'
MYSQL_PASSWORD = 'l*V2aA1gaee%9Yho'
MYSQL_DATABASE = 'qsr_db'  # Changed to lowercase
# MySQL Connection URL
MYSQL_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
