// Categories JavaScript

function openCategoryModal() {
    document.getElementById('categoryModal').classList.add('active');
}

function closeCategoryModal() {
    document.getElementById('categoryModal').classList.remove('active');
    document.getElementById('categoryForm').reset();
}

function saveCategory(event) {
    event.preventDefault();
    
    const category = {
        name: document.getElementById('categoryName').value,
        description: document.getElementById('categoryDescription').value,
        status: document.getElementById('categoryStatus').value
    };
    
    fetch('/api/categories', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(category)
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            closeCategoryModal();
            loadCategories();
            if (typeof updateCounts === 'function') updateCounts();
            alert('Category saved successfully!');
        } else {
            alert('Error: ' + (data.error || 'Could not save category'));
        }
    })
    .catch(error => {
        alert('Error saving category: ' + error);
    });
}

function loadCategories() {
    fetch('/api/categories')
        .then(res => res.json())
        .then(data => {
            const tbody = document.getElementById('categories-tbody');
            if (data.categories.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5"><div class="empty-state"><p>No categories yet. Add your first category!</p></div></td></tr>';
                return;
            }
            
            tbody.innerHTML = data.categories.map(cat => `
                <tr>
                    <td><strong>${cat.name}</strong></td>
                    <td>${cat.description || '-'}</td>
                    <td>${cat.items_count || 0}</td>
                    <td><span class="badge badge-${cat.status === 'active' ? 'success' : 'warning'}">${cat.status}</span></td>
                    <td>
                        <button class="btn btn-danger btn-small" onclick="deleteCategory('${cat.id}')">Delete</button>
                    </td>
                </tr>
            `).join('');
        });
}

function deleteCategory(id) {
    if (confirm('Are you sure you want to delete this category?')) {
        fetch(`/api/categories/${id}`, {method: 'DELETE'})
            .then(res => res.json())
            .then(() => {
                loadCategories();
                if (typeof updateCounts === 'function') updateCounts();
            });
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
