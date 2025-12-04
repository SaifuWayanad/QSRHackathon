-- Add customer_id column to orders table
-- This links orders to registered customers for tracking history and preferences

-- Step 1: Add customer_id column after id column
ALTER TABLE orders 
ADD COLUMN customer_id VARCHAR(255) AFTER id;

-- Step 2: Add index for better query performance
ALTER TABLE orders 
ADD INDEX idx_customer_id (customer_id);

-- Step 3: Add foreign key constraint (optional, but recommended)
-- This ensures referential integrity between orders and customers
ALTER TABLE orders
ADD CONSTRAINT fk_orders_customer 
    FOREIGN KEY (customer_id) REFERENCES customers(id) 
    ON DELETE SET NULL 
    ON UPDATE CASCADE;

-- Verify the changes
DESCRIBE orders;

-- Check if any orders need to be linked to existing customers
-- This query finds orders that might match existing customers by phone or name
SELECT 
    o.id as order_id,
    o.order_number,
    o.customer_name,
    o.customer_id,
    c.id as matching_customer_id,
    c.customer_code,
    c.name as customer_name_in_db
FROM orders o
LEFT JOIN customers c ON o.customer_name = c.name
WHERE o.customer_id IS NULL
LIMIT 20;

-- Optional: Update existing orders to link them with customers by name match
-- Uncomment the following if you want to automatically link existing orders
/*
UPDATE orders o
INNER JOIN customers c ON o.customer_name = c.name
SET o.customer_id = c.id
WHERE o.customer_id IS NULL;
*/

-- Query to verify orders with customer linkage
SELECT 
    o.order_number,
    o.customer_id,
    o.customer_name,
    c.customer_code,
    c.phone,
    o.total_amount,
    o.created_at
FROM orders o
LEFT JOIN customers c ON o.customer_id = c.id
ORDER BY o.created_at DESC
LIMIT 10;
