// Daily Production JavaScript

function openProductionModal() {
    loadFoodItemOptions();
    const date = document.getElementById('production-date').value;
    document.getElementById('productionDateInput').value = date;
    setTimeout(() => {
        document.getElementById('productionModal').classList.add('active');
    }, 100);
}

function closeProductionModal() {
    document.getElementById('productionModal').classList.remove('active');
    document.getElementById('productionForm').reset();
}

function saveProduction(event) {
    event.preventDefault();
    
    const select = document.getElementById('productionFoodItem');
    if (!select.value) {
        alert('Please select a food item');
        return;
    }
    
    const selectedOption = select.options[select.selectedIndex];
    
    const production = {
        food_id: select.value,
        food_name: selectedOption.getAttribute('data-name'),
        category_name: selectedOption.getAttribute('data-category'),
        date: document.getElementById('productionDateInput').value,
        planned_quantity: parseInt(document.getElementById('productionQuantity').value),
        produced: parseInt(document.getElementById('productionProduced').value) || 0,
        notes: document.getElementById('productionNotes').value
    };
    
    fetch('/api/daily-production', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(production)
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            closeProductionModal();
            loadDailyProduction();
            if (typeof updateCounts === 'function') updateCounts();
            alert('Production item saved successfully!');
        } else {
            alert('Error: ' + (data.error || 'Could not save production item'));
        }
    })
    .catch(error => {
        alert('Error saving production item: ' + error);
    });
}

function loadDailyProduction() {
    const date = document.getElementById('production-date').value;
    fetch(`/api/daily-production?date=${date}`)
        .then(res => res.json())
        .then(data => {
            const tbody = document.getElementById('production-tbody');
            if (data.production_items.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7"><div class="empty-state"><p>No production items for this date. Add your first production plan!</p></div></td></tr>';
                updateProductionSummary([]);
                return;
            }
            
            tbody.innerHTML = data.production_items.map(item => {
                const remaining = item.planned_quantity - item.produced;
                const status = item.produced >= item.planned_quantity ? 'Complete' : 'In Progress';
                const statusClass = status === 'Complete' ? 'success' : 'warning';
                
                return `
                <tr>
                    <td><strong>${item.food_name}</strong></td>
                    <td>${item.category_name}</td>
                    <td>${item.planned_quantity}</td>
                    <td>
                        <input type="number" value="${item.produced}" min="0" max="${item.planned_quantity}" 
                            style="width: 80px; padding: 5px; border: 1px solid #ddd; border-radius: 3px;"
                            onchange="updateProduced('${item.id}', this.value)">
                    </td>
                    <td>${remaining}</td>
                    <td><span class="badge badge-${statusClass}">${status}</span></td>
                    <td>
                        <button class="btn btn-danger btn-small" onclick="deleteProduction('${item.id}')">Delete</button>
                    </td>
                </tr>
            `}).join('');
            
            updateProductionSummary(data.production_items);
        })
        .catch(error => console.error('Error loading daily production:', error));
}

function updateProductionSummary(items) {
    const totalPlanned = items.reduce((sum, item) => sum + item.planned_quantity, 0);
    const totalProduced = items.reduce((sum, item) => sum + item.produced, 0);
    const totalRemaining = totalPlanned - totalProduced;
    const completionRate = totalPlanned > 0 ? Math.round((totalProduced / totalPlanned) * 100) : 0;
    
    document.getElementById('total-planned').textContent = totalPlanned;
    document.getElementById('total-produced').textContent = totalProduced;
    document.getElementById('total-remaining').textContent = totalRemaining;
    document.getElementById('completion-rate').textContent = completionRate + '%';
}

function updateProduced(id, produced) {
    fetch(`/api/daily-production/${id}`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({produced: parseInt(produced)})
    })
    .then(res => res.json())
    .then(() => {
        loadDailyProduction();
    })
    .catch(error => console.error('Error updating production:', error));
}

function deleteProduction(id) {
    if (confirm('Are you sure you want to delete this production item?')) {
        fetch(`/api/daily-production/${id}`, {method: 'DELETE'})
            .then(res => res.json())
            .then(() => {
                loadDailyProduction();
                if (typeof updateCounts === 'function') updateCounts();
            })
            .catch(error => console.error('Error deleting production:', error));
    }
}

// Initialize date picker on load
if (document.getElementById('production-date')) {
    document.getElementById('production-date').addEventListener('change', function() {
        loadDailyProduction();
    });
}
