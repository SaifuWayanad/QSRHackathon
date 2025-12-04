// Food Items JavaScript

function openFoodModal() {
    // Open modal first
    document.getElementById('foodModal').classList.add('active');
    
    // Then load data
    loadCategoryOptions();
    loadKitchenCheckboxes();
}

function closeFoodModal() {
    document.getElementById('foodModal').classList.remove('active');
    document.getElementById('foodForm').reset();
    
    // Reset kitchens container to loading state
    const container = document.getElementById('foodKitchens');
    if (container) {
        container.innerHTML = '<p style="color: #999; grid-column: 1 / -1; text-align: center;">Loading kitchens...</p>';
    }
}

function loadCategoryOptions() {
    fetch('/api/categories')
        .then(res => res.json())
        .then(data => {
            const select = document.getElementById('foodCategory');
            if (select) {
                select.innerHTML = '<option value="">Select Category</option>';
                if (data.categories && data.categories.length > 0) {
                    data.categories.forEach(cat => {
                        select.innerHTML += `<option value="${cat.id}">${cat.name}</option>`;
                    });
                }
            }
        })
        .catch(error => console.error('Error loading categories:', error));
}

function loadKitchenCheckboxes() {
    const container = document.getElementById('foodKitchens');
    if (!container) {
        console.error('❌ foodKitchens container not found!');
        return;
    }
    
    console.log('🔄 Loading kitchens from API...');
    container.innerHTML = '<p style="color: #999; grid-column: 1 / -1; text-align: center;">Loading kitchens...</p>';
    
    fetch('/api/kitchens', {
        method: 'GET',
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache'
        }
    })
        .then(res => {
            console.log('📡 Response status:', res.status);
            console.log('📡 Content-Type:', res.headers.get('Content-Type'));
            if (!res.ok) {
                throw new Error(`HTTP error! status: ${res.status}`);
            }
            return res.text();
        })
        .then(text => {
            console.log('📡 Raw response:', text.substring(0, 200));
            const data = JSON.parse(text);
            console.log('✅ Kitchens data received:', data);
            if (data.kitchens && data.kitchens.length > 0) {
                container.innerHTML = data.kitchens.map(kitchen => `
                    <label style="display: flex; align-items: center; gap: 8px; padding: 8px; background: white; border: 1px solid #e0e0e0; border-radius: 4px; cursor: pointer; transition: all 0.2s;">
                        <input type="checkbox" name="kitchen" value="${kitchen.id}" style="cursor: pointer;">
                        <span>${kitchen.icon || '🍳'} ${kitchen.name}</span>
                    </label>
                `).join('');
                console.log(`✅ Loaded ${data.kitchens.length} kitchens successfully`);
            } else {
                console.warn('⚠️ No kitchens found in response');
                container.innerHTML = '<p style="color: #999; grid-column: 1 / -1; text-align: center;">No kitchens available</p>';
            }
        })
        .catch(error => {
            console.error('❌ Error loading kitchens:', error);
            container.innerHTML = '<p style="color: #f00; grid-column: 1 / -1; text-align: center;">Error loading kitchens: ' + error.message + '</p>';
        });
}

function saveFoodItem(event) {
    event.preventDefault();
    
    // Get selected kitchens
    const selectedKitchens = [];
    document.querySelectorAll('input[name="kitchen"]:checked').forEach(checkbox => {
        selectedKitchens.push(checkbox.value);
    });
    
    if (selectedKitchens.length === 0) {
        alert('Please select at least one kitchen');
        return;
    }
    
    const foodItem = {
        name: document.getElementById('foodName').value,
        category_id: document.getElementById('foodCategory').value,
        kitchen_ids: selectedKitchens,
        price: parseFloat(document.getElementById('foodPrice').value),
        specifications: document.getElementById('foodSpecs').value,
        status: document.getElementById('foodStatus').value
    };
    
    fetch('/api/food-items', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(foodItem)
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            closeFoodModal();
            loadFoodItems();
            if (typeof updateCounts === 'function') updateCounts();
            alert('Food item saved successfully!');
        } else {
            alert('Error: ' + (data.error || 'Could not save food item'));
        }
    })
    .catch(error => {
        alert('Error saving food item: ' + error);
    });
}

function loadFoodItems() {
    fetch('/api/food-items')
        .then(res => res.json())
        .then(data => {
            const tbody = document.getElementById('food-tbody');
            if (data.food_items.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7"><div class="empty-state"><p>No food items yet. Add your first item!</p></div></td></tr>';
                return;
            }
            
            tbody.innerHTML = data.food_items.map(item => {
                // Handle multiple kitchens display
                let kitchenDisplay = 'Not Assigned';
                if (item.kitchens && item.kitchens.length > 0) {
                    kitchenDisplay = item.kitchens.map(k => k.name).join(', ');
                    if (kitchenDisplay.length > 40) {
                        kitchenDisplay = kitchenDisplay.substring(0, 37) + '...';
                    }
                } else if (item.kitchen_name) {
                    kitchenDisplay = item.kitchen_name;
                }
                
                return `
                <tr>
                    <td><strong>${item.name}</strong></td>
                    <td>${item.category_name}</td>
                    <td title="${item.kitchens ? item.kitchens.map(k => k.name).join(', ') : kitchenDisplay}">${kitchenDisplay}</td>
                    <td>$${parseFloat(item.price).toFixed(2)}</td>
                    <td>${item.specifications ? item.specifications.substring(0, 50) + '...' : '-'}</td>
                    <td><span class="badge badge-${item.status === 'available' ? 'success' : 'warning'}">${item.status}</span></td>
                    <td>
                        <button class="btn btn-danger btn-small" onclick="deleteFoodItem('${item.id}')">Delete</button>
                    </td>
                </tr>
                `;
            }).join('');
        });
}

function deleteFoodItem(id) {
    if (confirm('Are you sure you want to delete this food item?')) {
        fetch(`/api/food-items/${id}`, {method: 'DELETE'})
            .then(res => res.json())
            .then(() => {
                loadFoodItems();
                if (typeof updateCounts === 'function') updateCounts();
            });
    }
}

function loadFoodItemOptions() {
    fetch('/api/food-items')
        .then(res => res.json())
        .then(data => {
            const select = document.getElementById('productionFoodItem');
            if (select) {
                select.innerHTML = '<option value="">Select Food Item</option>';
                if (data.food_items && data.food_items.length > 0) {
                    data.food_items.forEach(item => {
                        select.innerHTML += `<option value="${item.id}" data-name="${item.name}" data-category="${item.category_name}">${item.name} (${item.category_name})</option>`;
                    });
                }
            }
        })
        .catch(error => console.error('Error loading food items:', error));
}
