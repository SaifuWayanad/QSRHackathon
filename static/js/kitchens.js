// Kitchen Management JavaScript

function openKitchenModal() {
    document.getElementById('kitchenModal').classList.add('active');
}

function closeKitchenModal() {
    document.getElementById('kitchenModal').classList.remove('active');
    document.getElementById('kitchenForm').reset();
}

function saveKitchen(event) {
    event.preventDefault();
    
    const kitchen = {
        name: document.getElementById('kitchenName').value,
        location: document.getElementById('kitchenLocation').value,
        status: document.getElementById('kitchenStatus').value
    };
    
    fetch('/api/kitchens', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(kitchen)
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            closeKitchenModal();
            loadKitchens();
            if (typeof updateCounts === 'function') updateCounts();
            alert('Kitchen saved successfully!');
        } else {
            alert('Error: ' + (data.error || 'Could not save kitchen'));
        }
    })
    .catch(error => {
        alert('Error saving kitchen: ' + error);
    });
}

function loadKitchens() {
    fetch('/api/kitchens')
        .then(res => res.json())
        .then(data => {
            const tbody = document.getElementById('kitchens-tbody');
            if (data.kitchens.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5"><div class="empty-state"><p>No kitchens yet. Add your first kitchen!</p></div></td></tr>';
                return;
            }
            
            tbody.innerHTML = data.kitchens.map(kitchen => `
                <tr>
                    <td><strong>${kitchen.name}</strong></td>
                    <td>${kitchen.location || '-'}</td>
                    <td>${kitchen.items_count || 0}</td>
                    <td><span class="badge badge-${kitchen.status === 'active' ? 'success' : 'warning'}">${kitchen.status}</span></td>
                    <td>
                        <button class="btn btn-danger btn-small" onclick="deleteKitchen('${kitchen.id}')">Delete</button>
                    </td>
                </tr>
            `).join('');
        });
}

function deleteKitchen(id) {
    if (confirm('Are you sure you want to delete this kitchen?')) {
        fetch(`/api/kitchens/${id}`, {method: 'DELETE'})
            .then(res => res.json())
            .then(() => {
                loadKitchens();
                if (typeof updateCounts === 'function') updateCounts();
            });
    }
}

function loadKitchenOptions() {
    fetch('/api/kitchens')
        .then(res => res.json())
        .then(data => {
            const select = document.getElementById('foodKitchen');
            if (select) {
                select.innerHTML = '<option value="">Select Kitchen</option>';
                if (data.kitchens && data.kitchens.length > 0) {
                    data.kitchens.forEach(kitchen => {
                        select.innerHTML += `<option value="${kitchen.id}">${kitchen.name}</option>`;
                    });
                }
            }
        })
        .catch(error => console.error('Error loading kitchens:', error));
}
