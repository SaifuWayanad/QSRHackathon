// Areas Management JavaScript

function openAreaModal() {
    document.getElementById('areaModal').classList.add('active');
}

function closeAreaModal() {
    document.getElementById('areaModal').classList.remove('active');
    document.getElementById('areaForm').reset();
}

function saveArea(event) {
    event.preventDefault();
    
    const area = {
        name: document.getElementById('areaName').value,
        description: document.getElementById('areaDescription').value,
        status: document.getElementById('areaStatus').value
    };
    
    fetch('/api/areas', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(area)
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            closeAreaModal();
            loadAreas();
            alert('Area added successfully!');
        } else {
            alert('Error: ' + (data.error || 'Could not save area'));
        }
    })
    .catch(error => alert('Error saving area: ' + error));
}

function loadAreas() {
    fetch('/api/areas')
        .then(res => res.json())
        .then(data => {
            console.log('Areas data received:', data);
            const tbody = document.getElementById('areas-tbody');
            if (!data.areas || data.areas.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5"><div class="empty-state"><p>No areas yet. Add your first area!</p></div></td></tr>';
                return;
            }
            
            tbody.innerHTML = data.areas.map(area => `
                <tr>
                    <td><strong>${area.name}</strong></td>
                    <td>${area.description || '-'}</td>
                    <td>${area.tables_count || 0}</td>
                    <td><span class="badge badge-${area.status === 'active' ? 'success' : 'warning'}">${area.status}</span></td>
                    <td>
                        <button class="btn btn-danger btn-small" onclick="deleteArea('${area.id}')">Delete</button>
                    </td>
                </tr>
            `).join('');
        })
        .catch(error => {
            console.error('Error loading areas:', error);
            const tbody = document.getElementById('areas-tbody');
            tbody.innerHTML = '<tr><td colspan="5"><div class="empty-state"><p>Error loading areas</p></div></td></tr>';
        });
}

function deleteArea(id) {
    if (confirm('Are you sure you want to delete this area?')) {
        fetch(`/api/areas/${id}`, {method: 'DELETE'})
            .then(res => res.json())
            .then(() => {
                loadAreas();
            })
            .catch(error => console.error('Error deleting area:', error));
    }
}

function loadAreaOptions() {
    fetch('/api/areas')
        .then(res => res.json())
        .then(data => {
            const select = document.getElementById('tableArea');
            if (select) {
                select.innerHTML = '<option value="">Select Area</option>';
                if (data.areas && data.areas.length > 0) {
                    data.areas.forEach(area => {
                        select.innerHTML += `<option value="${area.id}" data-name="${area.name}">${area.name}</option>`;
                    });
                }
            }
        })
        .catch(error => console.error('Error loading areas:', error));
}
