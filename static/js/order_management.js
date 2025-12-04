// Order Management JavaScript
// Manages order listing, selection, and kitchen assignment functionality

let selectedOrder = null;

// Load and display active orders
function loadOrdersList() {
    console.log('📋 Loading orders list...');
    const statusFilter = document.getElementById('order-filter-status').value;
    console.log('  Filter: ' + (statusFilter || 'ALL'));
    
    // Fetch all orders directly
    fetch('/api/orders')
        .then(res => res.json())
        .then(ordersData => {
            console.log('  Fetched orders:', ordersData);
            if (!ordersData.orders || ordersData.orders.length === 0) {
                console.log('  ℹ️  No orders found');
                document.getElementById('orders-list-container').innerHTML = 
                    '<div style="text-align: center; color: #ccc; padding: 20px;">No orders yet. Create your first order!</div>';
                return;
            }
            
            let filteredOrders = ordersData.orders;
            
            // Filter by status if selected
            if (statusFilter) {
                filteredOrders = filteredOrders.filter(o => o.status === statusFilter);
            }
            
            // Sort by created_at, newest first
            filteredOrders.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
            
            const container = document.getElementById('orders-list-container');
            container.innerHTML = '';
            
            if (filteredOrders.length === 0) {
                container.innerHTML = '<div style="text-align: center; color: #ccc; padding: 20px;">No orders match the selected filter</div>';
                return;
            }
            
            filteredOrders.forEach(order => {
                const orderDiv = document.createElement('div');
                orderDiv.className = 'order-item-row';
                if (selectedOrder && selectedOrder.id === order.id) {
                    orderDiv.classList.add('active');
                }
                
                const statusColors = {
                    'pending': '#ff6b6b',
                    'preparing': '#ffa502',
                    'ready': '#00ff88',
                    'served': '#2ecc71',
                    'completed': '#667eea',
                    'confirmed': '#3498db'
                };
                
                orderDiv.innerHTML = `
                    <div class="order-number">Order #${order.order_number}</div>
                    <div class="order-customer">👤 ${order.customer_name || 'Guest'}</div>
                    <div class="order-info">
                        <span>Items: ${order.items_count || 0}</span>
                        <span class="order-status-badge" style="background: ${statusColors[order.status] || '#999'}20; color: ${statusColors[order.status] || '#999'};">
                            ${order.status.toUpperCase()}
                        </span>
                    </div>
                `;
                
                orderDiv.addEventListener('click', () => {
                    selectedOrder = order;
                    document.querySelectorAll('.order-item-row').forEach(o => o.classList.remove('active'));
                    orderDiv.classList.add('active');
                    displayOrderDetails(order);
                });
                
                container.appendChild(orderDiv);
            });
        })
        .catch(error => {
            console.error('Error loading orders:', error);
            document.getElementById('orders-list-container').innerHTML = 
                '<div style="text-align: center; color: #ff6b6b; padding: 20px;">Error loading orders. Please try again.</div>';
        });
}

// Display order details and kitchen assignment interface
function displayOrderDetails(order) {
    console.log('📝 Displaying order details for:', order);
    const container = document.getElementById('order-details-container');
    
    // Fetch order items
    fetch(`/api/orders/${order.id}`)
        .then(res => res.json())
        .then(data => {
            console.log('  Order details response:', data);
            const orderData = data.order || order;
            
            let html = `
                <div style="margin-bottom: 16px;">
                    <h4 style="color: #333; margin: 0 0 8px 0;">Order #${orderData.order_number}</h4>
                    <div style="font-size: 12px; color: #666;">
                        <p style="margin: 4px 0;"><strong>Customer:</strong> ${orderData.customer_name}</p>
                        <p style="margin: 4px 0;"><strong>Items:</strong> ${orderData.items_count}</p>
                        <p style="margin: 4px 0;"><strong>Total:</strong> $${orderData.total_amount || 0}</p>
                        <p style="margin: 4px 0;"><strong>Status:</strong> ${orderData.status.toUpperCase()}</p>
                    </div>
                </div>
                
                <div class="assignment-section">
                    <h4 style="color: #333; margin: 0 0 12px 0;">🏪 Assign Items to Kitchens</h4>
                    <div id="items-assignment-list"></div>
                </div>
            `;
            
            container.innerHTML = html;
            
            // Load food items and kitchens for assignment
            loadItemsForAssignment(orderData);
        })
        .catch(error => {
            console.error('Error fetching order details:', error);
            container.innerHTML = '<div style="color: #f00;">Error loading order details</div>';
        });
}

// Load items and display kitchen assignment options
function loadItemsForAssignment(order) {
    console.log('🔧 Loading items for assignment:', order);
    
    // Fetch both kitchens and existing assignments
    Promise.all([
        fetch('/api/kitchens').then(r => r.json()),
        fetch(`/api/orders/${order.id}/kitchen-assignments`).then(r => r.json()).catch(() => ({assignments: {}}))
    ])
    .then(([kitchenData, assignmentData]) => {
        console.log('  Kitchens:', kitchenData);
        console.log('  Existing assignments:', assignmentData);
        
        const assignmentList = document.getElementById('items-assignment-list');
        assignmentList.innerHTML = '';
        
        const kitchens = kitchenData.kitchens || [];
        const existingAssignments = assignmentData.assignments || {};
        
        // Use actual order items from the order object
        const orderItems = order.items || [];
        console.log('  Order items:', orderItems);
        
        if (orderItems.length === 0) {
            assignmentList.innerHTML = '<div style="color: #999; text-align: center; padding: 20px;">No items in this order</div>';
            return;
        }
        
        orderItems.forEach((item, index) => {
            const itemDiv = document.createElement('div');
            itemDiv.className = 'assignment-item';
            itemDiv.setAttribute('data-item-id', item.id);
            
            // Get the already assigned kitchen for this item
            const assignedKitchenId = existingAssignments[item.id] || '';
            
            itemDiv.innerHTML = `
                <div class="assignment-item-info">
                    <div class="assignment-food-name">${item.food_name || `Item ${index + 1}`}</div>
                    <div class="assignment-qty">Qty: ${item.quantity || 1}</div>
                </div>
                <select class="assignment-select" id="kitchen-${item.id}" data-item-id="${item.id}" onchange="updateKitchenAssignment('${order.id}', '${item.id}', this.value)">
                    <option value="">-- Select Kitchen --</option>
                    ${kitchens.map(k => `<option value="${k.id}" ${k.id === assignedKitchenId ? 'selected' : ''}>${k.name}</option>`).join('')}
                </select>
            `;
            
            assignmentList.appendChild(itemDiv);
        });
        
        // Add assign all button
        const assignAllDiv = document.createElement('div');
        assignAllDiv.style.marginTop = '12px';
        assignAllDiv.innerHTML = `
            <button class="assign-btn" style="width: 100%;" onclick="assignAllItems('${order.id}')">
                ✓ Assign All Items
            </button>
        `;
        assignmentList.appendChild(assignAllDiv);
    })
    .catch(error => console.error('Error loading assignment data:', error));
}

// Update kitchen assignment for an item
function updateKitchenAssignment(orderId, itemId, kitchenId) {
    console.log(`Assigning item ${itemId} from order ${orderId} to kitchen ${kitchenId}`);
}

// Assign all items to selected kitchens
function assignAllItems(orderId) {
    console.log('📤 Assigning items for order:', orderId);
    const selections = document.querySelectorAll('.assignment-select');
    console.log('  Found ' + selections.length + ' assignment selects');
    let allAssigned = true;
    const assignments = [];
    
    selections.forEach((select, idx) => {
        if (!select.value) {
            allAssigned = false;
            select.style.borderColor = '#ff6b6b';
        } else {
            select.style.borderColor = '#e0e0e0';
            // Get the actual item_id from data attribute
            const itemId = select.getAttribute('data-item-id');
            console.log('    Item ' + idx + ': ' + itemId + ' → Kitchen ' + select.value);
            assignments.push({
                item_id: itemId,
                kitchen_id: select.value
            });
        }
    });
    
    if (!allAssigned) {
        alert('⚠️ Please select a kitchen for all items');
        return;
    }
    
    console.log('  Sending assignments:', assignments);
    // Send assignments to backend
    fetch(`/api/orders/${orderId}/assign-kitchens`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ assignments })
    })
    .then(res => {
        console.log('  Response status:', res.status);
        return res.json();
    })
    .then(data => {
        console.log('  Response data:', data);
        if (data.success) {
            alert('✓ Items assigned to kitchens successfully!');
            loadOrdersList();
        } else {
            alert('❌ Error: ' + (data.error || 'Failed to assign items'));
        }
    })
    .catch(error => {
        console.error('Assignment error:', error);
        alert('❌ Error assigning items: ' + error.message);
    });
}

// Refresh orders list
function refreshOrdersList() {
    loadOrdersList();
}

// Initialize order management on page load
function initOrderManagement() {
    loadOrdersList();
    
    // Add event listener to status filter
    const filterSelect = document.getElementById('order-filter-status');
    if (filterSelect) {
        filterSelect.addEventListener('change', loadOrdersList);
    }
}
