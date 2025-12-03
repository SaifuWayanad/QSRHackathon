// Order Types JavaScript

function openOrderTypeModal() {
    document.getElementById('orderTypeModal').classList.add('active');
}

function closeOrderTypeModal() {
    document.getElementById('orderTypeModal').classList.remove('active');
    document.getElementById('orderTypeForm').reset();
}

function loadOrderTypes() {
    fetch('/api/order-types')
        .then(res => res.json())
        .then(data => {
            console.log('Order types data received:', data);
            const tbody = document.getElementById('order-types-tbody');
            if (!data.order_types || data.order_types.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4"><div class="empty-state"><p>No order types yet. Add your first order type!</p></div></td></tr>';
                return;
            }
            
            tbody.innerHTML = data.order_types.map(orderType => `
                <tr>
                    <td><strong>${orderType.name}</strong></td>
                    <td>${orderType.description || '-'}</td>
                    <td><span class="badge badge-${orderType.status === 'active' ? 'success' : 'warning'}">${orderType.status}</span></td>
                    <td>
                        <button class="btn btn-danger btn-small" onclick="deleteOrderType('${orderType.id}')">Delete</button>
                    </td>
                </tr>
            `).join('');
        })
        .catch(error => {
            console.error('Error loading order types:', error);
            const tbody = document.getElementById('order-types-tbody');
            tbody.innerHTML = '<tr><td colspan="4"><div class="empty-state"><p>Error loading order types</p></div></td></tr>';
        });
}

function saveOrderType(event) {
    event.preventDefault();
    const orderType = {
        name: document.getElementById('orderTypeName').value,
        description: document.getElementById('orderTypeDescription').value,
        status: document.getElementById('orderTypeStatus').value
    };
    
    fetch('/api/order-types', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(orderType)
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            closeOrderTypeModal();
            loadOrderTypes();
            alert('Order type saved successfully!');
        } else {
            alert('Error: ' + (data.error || 'Could not save order type'));
        }
    })
    .catch(error => {
        alert('Error saving order type: ' + error);
    });
}

function deleteOrderType(id) {
    if (confirm('Are you sure you want to delete this order type?')) {
        fetch(`/api/order-types/${id}`, {method: 'DELETE'})
            .then(res => res.json())
            .then(() => {
                loadOrderTypes();
            })
            .catch(error => console.error('Error deleting order type:', error));
    }
}

function loadOrderTypeOptions() {
    fetch('/api/order-types')
        .then(res => res.json())
        .then(data => {
            const select = document.getElementById('orderType');
            if (select) {
                select.innerHTML = '<option value="">Select Order Type</option>';
                if (data.order_types && data.order_types.length > 0) {
                    data.order_types.forEach(orderType => {
                        select.innerHTML += `<option value="${orderType.id}">${orderType.name}</option>`;
                    });
                }
            }
        });
}
