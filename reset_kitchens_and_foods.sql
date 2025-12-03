-- Reset Kitchens and Food Items for MariaDB/MySQL
-- This script will delete all existing kitchens and food items, then create 4 kitchens and 10 food items

-- ============================================
-- STEP 1: Clear existing data
-- ============================================

-- Delete food item-kitchen mappings first (foreign key constraint)
DELETE FROM food_kitchen_mapping;

-- Delete food items
DELETE FROM food_items;

-- Delete kitchens
DELETE FROM kitchens;

-- ============================================
-- STEP 2: Create 4 Kitchens
-- ============================================

INSERT INTO kitchens (id, name, location, description, status, icon, created_at) VALUES
('k1-main-kitchen', 'Main Kitchen', 'Ground Floor - Central', 'Primary cooking station for main dishes, pasta, and rice preparations', 'active', '🍳', NOW()),
('k2-grill-station', 'Grill & BBQ Station', 'Ground Floor - West Wing', 'Dedicated station for grilled items, steaks, and barbecue', 'active', '🔥', NOW()),
('k3-pizza-oven', 'Pizza & Bakery', 'Ground Floor - East Wing', 'Wood-fired pizza oven and baking station', 'active', '🍕', NOW()),
('k4-cold-kitchen', 'Cold Kitchen & Salads', 'Ground Floor - North Wing', 'Salad preparation, cold appetizers, and desserts', 'active', '🥗', NOW());

-- ============================================
-- STEP 3: Create 10 Food Items with Multiple Kitchen Assignments
-- ============================================

-- Food Item 1: Margherita Pizza (Pizza Oven only)
INSERT INTO food_items (id, name, category_id, price, description, specifications, status, created_at) VALUES
('f1-margherita', 'Margherita Pizza', (SELECT id FROM categories WHERE name LIKE '%Pizza%' LIMIT 1), 12.99, 
'Classic Italian pizza with fresh mozzarella, tomato sauce, and basil', 
'Size: 12 inch, Calories: 800, Allergens: Gluten, Dairy', 'available', NOW());

INSERT INTO food_kitchen_mapping (food_id, kitchen_id) VALUES
('f1-margherita', 'k3-pizza-oven');

-- Food Item 2: Grilled Chicken Breast (Grill Station & Main Kitchen)
INSERT INTO food_items (id, name, category_id, price, description, specifications, status, created_at) VALUES
('f2-grilled-chicken', 'Grilled Chicken Breast', (SELECT id FROM categories WHERE name LIKE '%Main%' OR name LIKE '%Entree%' LIMIT 1), 15.99,
'Herb-marinated grilled chicken breast with seasonal vegetables',
'Serving: 250g, Calories: 450, Protein: 45g, Low-carb option available', 'available', NOW());

INSERT INTO food_kitchen_mapping (food_id, kitchen_id) VALUES
('f2-grilled-chicken', 'k2-grill-station'),
('f2-grilled-chicken', 'k1-main-kitchen');

-- Food Item 3: Caesar Salad (Cold Kitchen only)
INSERT INTO food_items (id, name, category_id, price, description, specifications, status, created_at) VALUES
('f3-caesar-salad', 'Caesar Salad', (SELECT id FROM categories WHERE name LIKE '%Salad%' OR name LIKE '%Appetizer%' LIMIT 1), 9.99,
'Fresh romaine lettuce with Caesar dressing, parmesan, and croutons',
'Serving: 1 bowl, Calories: 320, Add chicken: +$4, Allergens: Dairy, Gluten', 'available', NOW());

INSERT INTO food_kitchen_mapping (food_id, kitchen_id) VALUES
('f3-caesar-salad', 'k4-cold-kitchen');

-- Food Item 4: BBQ Ribs (Grill Station only)
INSERT INTO food_items (id, name, category_id, price, description, specifications, status, created_at) VALUES
('f4-bbq-ribs', 'BBQ Baby Back Ribs', (SELECT id FROM categories WHERE name LIKE '%Main%' OR name LIKE '%BBQ%' LIMIT 1), 22.99,
'Slow-cooked baby back ribs with house BBQ sauce and coleslaw',
'Weight: 800g, Calories: 1200, Spice level: Medium', 'available', NOW());

INSERT INTO food_kitchen_mapping (food_id, kitchen_id) VALUES
('f4-bbq-ribs', 'k2-grill-station');

-- Food Item 5: Spaghetti Carbonara (Main Kitchen only)
INSERT INTO food_items (id, name, category_id, price, description, specifications, status, created_at) VALUES
('f5-carbonara', 'Spaghetti Carbonara', (SELECT id FROM categories WHERE name LIKE '%Pasta%' OR name LIKE '%Main%' LIMIT 1), 13.99,
'Traditional carbonara with pancetta, eggs, parmesan, and black pepper',
'Serving: 350g, Calories: 650, Allergens: Gluten, Dairy, Eggs', 'available', NOW());

INSERT INTO food_kitchen_mapping (food_id, kitchen_id) VALUES
('f5-carbonara', 'k1-main-kitchen');

-- Food Item 6: Pepperoni Pizza (Pizza Oven only)
INSERT INTO food_items (id, name, category_id, price, description, specifications, status, created_at) VALUES
('f6-pepperoni', 'Pepperoni Pizza', (SELECT id FROM categories WHERE name LIKE '%Pizza%' LIMIT 1), 14.99,
'Classic pepperoni pizza with mozzarella and tomato sauce',
'Size: 12 inch, Calories: 950, Allergens: Gluten, Dairy, Pork', 'available', NOW());

INSERT INTO food_kitchen_mapping (food_id, kitchen_id) VALUES
('f6-pepperoni', 'k3-pizza-oven');

-- Food Item 7: Grilled Salmon (Grill Station & Main Kitchen)
INSERT INTO food_items (id, name, category_id, price, description, specifications, status, created_at) VALUES
('f7-grilled-salmon', 'Grilled Atlantic Salmon', (SELECT id FROM categories WHERE name LIKE '%Seafood%' OR name LIKE '%Main%' LIMIT 1), 18.99,
'Fresh Atlantic salmon fillet with lemon butter sauce and asparagus',
'Serving: 200g, Calories: 520, Omega-3 rich, Allergens: Fish', 'available', NOW());

INSERT INTO food_kitchen_mapping (food_id, kitchen_id) VALUES
('f7-grilled-salmon', 'k2-grill-station'),
('f7-grilled-salmon', 'k1-main-kitchen');

-- Food Item 8: Greek Salad (Cold Kitchen only)
INSERT INTO food_items (id, name, category_id, price, description, specifications, status, created_at) VALUES
('f8-greek-salad', 'Greek Salad', (SELECT id FROM categories WHERE name LIKE '%Salad%' OR name LIKE '%Appetizer%' LIMIT 1), 10.99,
'Fresh tomatoes, cucumbers, olives, feta cheese, and red onion',
'Serving: 1 bowl, Calories: 280, Vegetarian, Allergens: Dairy', 'available', NOW());

INSERT INTO food_kitchen_mapping (food_id, kitchen_id) VALUES
('f8-greek-salad', 'k4-cold-kitchen');

-- Food Item 9: Cheeseburger (Grill Station & Main Kitchen & Pizza Oven)
INSERT INTO food_items (id, name, category_id, price, description, specifications, status, created_at) VALUES
('f9-cheeseburger', 'Classic Cheeseburger', (SELECT id FROM categories WHERE name LIKE '%Burger%' OR name LIKE '%Main%' LIMIT 1), 11.99,
'Angus beef patty with cheddar, lettuce, tomato, and fries',
'Serving: 1 burger + fries, Calories: 850, Allergens: Gluten, Dairy', 'available', NOW());

INSERT INTO food_kitchen_mapping (food_id, kitchen_id) VALUES
('f9-cheeseburger', 'k2-grill-station'),
('f9-cheeseburger', 'k1-main-kitchen'),
('f9-cheeseburger', 'k3-pizza-oven');

-- Food Item 10: Tiramisu (Cold Kitchen & Pizza Oven)
INSERT INTO food_items (id, name, category_id, price, description, specifications, status, created_at) VALUES
('f10-tiramisu', 'Classic Tiramisu', (SELECT id FROM categories WHERE name LIKE '%Dessert%' LIMIT 1), 7.99,
'Italian coffee-flavored dessert with mascarpone and cocoa',
'Serving: 1 slice, Calories: 450, Contains alcohol, Allergens: Dairy, Eggs, Gluten', 'available', NOW());

INSERT INTO food_kitchen_mapping (food_id, kitchen_id) VALUES
('f10-tiramisu', 'k4-cold-kitchen'),
('f10-tiramisu', 'k3-pizza-oven');

-- ============================================
-- STEP 4: Verify the data
-- ============================================

-- Show kitchens
SELECT 'KITCHENS:' as Info;
SELECT id, name, location, status FROM kitchens;

-- Show food items with their kitchen assignments
SELECT 'FOOD ITEMS WITH KITCHENS:' as Info;
SELECT 
    fi.id,
    fi.name as food_name,
    fi.price,
    GROUP_CONCAT(k.name SEPARATOR ', ') as assigned_kitchens
FROM food_items fi
LEFT JOIN food_kitchen_mapping fkm ON fi.id = fkm.food_id
LEFT JOIN kitchens k ON fkm.kitchen_id = k.id
GROUP BY fi.id, fi.name, fi.price
ORDER BY fi.name;
