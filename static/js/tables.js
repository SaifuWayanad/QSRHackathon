// Tables Management JavaScript

function openTableModal() {
    loadAreaOptions();
    setTimeout(() => {
        document.getElementById('tableModal').classList.add('active');
    }, 100);
}

function closeTableModal() {
    document.getElementById('tableModal').classList.remove('active');
    document.getElementById('tableForm').reset();
}

function saveTable(event) {
    event.preventDefault();
    
    const areaSelect = document.getElementById('tableArea');
    if (!areaSelect.value) {
        alert('Please select an area');
        return;
    }
    
    const selectedArea = areaSelect.options[areaSelect.selectedIndex];
    
    const table = {
        number: document.getElementById('tableNumber').value,
        area_id: areaSelect.value,
        area_name: selectedArea.getAttribute('data-name'),
        capacity: parseInt(document.getElementById('tableCapacity').value),
        status: document.getElementById('tableStatus').value
    };
    
    fetch('/api/tables', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(table)
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            closeTableModal();
            loadTables();
            if (typeof loadAreas === 'function') loadAreas();
            alert('Table added successfully!');
        } else {
            alert('Error: ' + (data.error || 'Could not save table'));
        }
    })
    .catch(error => alert('Error saving table: ' + error));
}

function loadTables() {
    fetch('/api/tables')
        .then(res => res.json())
        .then(data => {
            const tbody = document.getElementById('tables-tbody');
            if (data.tables.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5"><div class="empty-state"><p>No tables yet. Add your first table!</p></div></td></tr>';
                return;
            }
            
            tbody.innerHTML = data.tables.map(table => `
                <tr>
                    <td><strong>${table.number}</strong></td>
                    <td>${table.area_name}</td>
                    <td>${table.capacity}</td>
                    <td><span class="badge badge-${table.status === 'available' ? 'success' : 'warning'}">${table.status}</span></td>
                    <td>
                        <button class="btn btn-danger btn-small" onclick="deleteTable('${table.id}')">Delete</button>
                    </td>
                </tr>
            `).join('');
        });
}

function deleteTable(id) {
    if (confirm('Are you sure you want to delete this table?')) {
        fetch(`/api/tables/${id}`, {method: 'DELETE'})
            .then(res => res.json())
            .then(() => {
                loadTables();
                if (typeof loadAreas === 'function') loadAreas();
            })
            .catch(error => console.error('Error deleting table:', error));
    }
}

function loadTableOptions() {
    fetch('/api/tables')
        .then(res => res.json())
        .then(data => {
            const select = document.getElementById('orderTable');
            if (select) {
                select.innerHTML = '<option value="">Select Table</option>';
                if (data.tables && data.tables.length > 0) {
                    data.tables.forEach(table => {
                        select.innerHTML += `<option value="${table.id}" data-number="${table.number}">${table.number} (${table.area_name})</option>`;
                    });
                }
            }
        });
}
