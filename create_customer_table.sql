-- Create customers table for QSR system
-- This table stores customer information for order tracking, loyalty programs, and personalized service

CREATE TABLE IF NOT EXISTS customers (
    id VARCHAR(255) PRIMARY KEY,
    customer_code VARCHAR(50) UNIQUE NOT NULL COMMENT 'Unique customer code like CUST-001',
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(20) UNIQUE,
    address TEXT,
    city VARCHAR(100),
    postal_code VARCHAR(20),
    
    -- Customer preferences and notes
    dietary_preferences TEXT COMMENT 'JSON or comma-separated: vegetarian, vegan, gluten-free, etc.',
    allergens TEXT COMMENT 'Known allergens to avoid',
    favorite_items TEXT COMMENT 'JSON array of favorite food item IDs',
    notes TEXT COMMENT 'Special notes about customer preferences',
    
    -- Loyalty and statistics
    total_orders INT DEFAULT 0,
    total_spent DECIMAL(10, 2) DEFAULT 0.00,
    loyalty_points INT DEFAULT 0,
    member_since DATE,
    last_order_date DATETIME,
    
    -- Status and metadata
    status VARCHAR(50) DEFAULT 'active' COMMENT 'active, inactive, blocked',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Indexes for performance
    INDEX idx_customer_code (customer_code),
    INDEX idx_email (email),
    INDEX idx_phone (phone),
    INDEX idx_status (status),
    INDEX idx_member_since (member_since)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Add customer_id foreign key to orders table (if not already present)
-- This links orders to registered customers
ALTER TABLE orders 
ADD COLUMN customer_id VARCHAR(255) AFTER id,
ADD INDEX idx_customer_id (customer_id),
ADD CONSTRAINT fk_orders_customer 
    FOREIGN KEY (customer_id) REFERENCES customers(id) 
    ON DELETE SET NULL 
    ON UPDATE CASCADE;

-- Sample data for testing
INSERT INTO customers (id, customer_code, name, email, phone, dietary_preferences, status, member_since) VALUES
('cust-1', 'CUST-001', 'John Doe', 'john.doe@example.com', '+1234567890', 'vegetarian', 'active', '2024-01-15'),
('cust-2', 'CUST-002', 'Jane Smith', 'jane.smith@example.com', '+1234567891', 'gluten-free', 'active', '2024-02-20'),
('cust-3', 'CUST-003', 'Mike Johnson', 'mike.j@example.com', '+1234567892', NULL, 'active', '2024-03-10'),
('cust-4', 'CUST-004', 'Sarah Williams', 'sarah.w@example.com', '+1234567893', 'vegan,nut-free', 'active', '2024-04-05'),
('cust-5', 'CUST-005', 'David Brown', 'david.b@example.com', '+1234567894', NULL, 'active', '2024-05-12');

-- Update sample customers with some statistics
UPDATE customers SET 
    total_orders = 5,
    total_spent = 125.50,
    loyalty_points = 125,
    last_order_date = '2024-12-01 18:30:00'
WHERE customer_code = 'CUST-001';

UPDATE customers SET 
    total_orders = 3,
    total_spent = 78.25,
    loyalty_points = 78,
    last_order_date = '2024-12-02 12:15:00'
WHERE customer_code = 'CUST-002';

-- Query to check customer table
SELECT * FROM customers;

-- Query to get customer with their order history
SELECT 
    c.customer_code,
    c.name,
    c.email,
    c.phone,
    c.total_orders,
    c.total_spent,
    c.loyalty_points,
    o.order_number,
    o.total_amount,
    o.status as order_status,
    o.created_at as order_date
FROM customers c
LEFT JOIN orders o ON c.id = o.customer_id
ORDER BY c.customer_code, o.created_at DESC;
