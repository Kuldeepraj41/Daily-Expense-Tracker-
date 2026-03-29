// ── Expense Management UI ──────────────────────────────────────────────────
import { API, formatCurrency, formatDate, showToast, today, getCategoryColor, getCategoryIcon, debounce } from './utils.js';

let _categories = [];
let _expenses   = [];
let _editingId  = null;

export async function initExpenses() {
  await loadCategories();
  await renderExpensesTable();
  bindExpenseEvents();
  setupMLCategorize();
}

export async function loadCategories() {
  try {
    _categories = await API.get('/api/expenses/categories');
    populateCategoryDropdowns();
  } catch (e) {
    console.error('Failed to load categories', e);
  }
}

function populateCategoryDropdowns() {
  document.querySelectorAll('.category-select').forEach(sel => {
    const current = sel.value;
    sel.innerHTML = '<option value="">Select category…</option>' +
      _categories.map(c => `<option value="${c.name}">${c.icon} ${c.name}</option>`).join('');
    if (current) sel.value = current;
  });

  const filterSel = document.getElementById('filter-category');
  if (filterSel) {
    filterSel.innerHTML = '<option value="">All Categories</option>' +
      _categories.map(c => `<option value="${c.name}">${c.icon} ${c.name}</option>`).join('');
  }

  const budgetCatSel = document.getElementById('budget-category');
  if (budgetCatSel) {
    budgetCatSel.innerHTML = '<option value="">Select category…</option>' +
      _categories.map(c => `<option value="${c.name}">${c.icon} ${c.name}</option>`).join('');
  }
}

// ── Render Table ──────────────────────────────────────────────────────────

export async function renderExpensesTable(filters = {}) {
  const tbody = document.getElementById('expenses-tbody');
  if (!tbody) return;

  tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:40px;color:var(--text-muted);">
    <div class="spinner" style="margin:0 auto 12px;"></div>Loading…</td></tr>`;

  try {
    const params = new URLSearchParams();
    if (filters.category)   params.set('category', filters.category);
    if (filters.start_date) params.set('start_date', filters.start_date);
    if (filters.end_date)   params.set('end_date', filters.end_date);
    if (filters.search)     params.set('search', filters.search);
    if (filters.sort_by)    params.set('sort_by', filters.sort_by);
    if (filters.order)      params.set('order', filters.order);

    _expenses = await API.get(`/api/expenses/?${params}`);

    if (!_expenses.length) {
      tbody.innerHTML = `<tr><td colspan="6">
        <div class="empty-state">
          <div class="icon">💸</div>
          <h3>No expenses found</h3>
          <p>Add your first expense to get started tracking your spending.</p>
        </div>
      </td></tr>`;
      return;
    }

    tbody.innerHTML = _expenses.map(e => {
      const color = getCategoryColor(e.category);
      const icon  = getCategoryIcon(e.category);
      return `
      <tr data-id="${e.id}">
        <td>${formatDate(e.date)}</td>
        <td>
          <div style="font-weight:500">${e.description}</div>
          ${e.notes ? `<div style="font-size:11.5px;color:var(--text-muted);margin-top:2px;">${e.notes}</div>` : ''}
        </td>
        <td>
          <span class="category-badge" style="background:${color}22;color:${color};border:1px solid ${color}44;">
            ${icon} ${e.category}
          </span>
        </td>
        <td><span class="amount-text">${formatCurrency(e.amount)}</span></td>
        <td>${e.is_recurring ? '<span style="color:var(--accent);font-size:12px;">🔄 Recurring</span>' : '<span style="color:var(--text-muted);font-size:12px;">One-time</span>'}</td>
        <td>
          <div style="display:flex;gap:6px;">
            <button class="btn btn-secondary btn-sm btn-icon edit-btn" data-id="${e.id}" title="Edit">✏️</button>
            <button class="btn btn-danger btn-sm btn-icon delete-btn" data-id="${e.id}" title="Delete">🗑️</button>
          </div>
        </td>
      </tr>`;
    }).join('');

    // Bind row actions
    tbody.querySelectorAll('.edit-btn').forEach(btn =>
      btn.addEventListener('click', () => openEditModal(parseInt(btn.dataset.id))));
    tbody.querySelectorAll('.delete-btn').forEach(btn =>
      btn.addEventListener('click', () => deleteExpense(parseInt(btn.dataset.id))));

  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:40px;color:var(--danger);">Failed to load expenses</td></tr>`;
    console.error(e);
  }
}

// ── Modals ────────────────────────────────────────────────────────────────

export function openAddModal() {
  _editingId = null;
  document.getElementById('expense-modal-title').textContent = '+ Add Expense';
  document.getElementById('expense-form').reset();
  document.getElementById('expense-date').value = today();
  document.getElementById('ml-suggestion').style.display = 'none';
  openModal('expense-modal');
}

function openEditModal(id) {
  const expense = _expenses.find(e => e.id === id);
  if (!expense) return;
  _editingId = id;
  document.getElementById('expense-modal-title').textContent = 'Edit Expense';
  document.getElementById('expense-description').value = expense.description;
  document.getElementById('expense-amount').value = expense.amount;
  document.getElementById('expense-category').value = expense.category;
  document.getElementById('expense-date').value = expense.date;
  document.getElementById('expense-notes').value = expense.notes || '';
  document.getElementById('expense-recurring').checked = expense.is_recurring;
  document.getElementById('ml-suggestion').style.display = 'none';
  openModal('expense-modal');
}

export function openModal(id) {
  document.getElementById(id).classList.add('open');
}

export function closeModal(id) {
  document.getElementById(id).classList.remove('open');
}

// ── Save Expense ───────────────────────────────────────────────────────────

async function saveExpense(e) {
  e.preventDefault();
  const payload = {
    description:  document.getElementById('expense-description').value.trim(),
    amount:       parseFloat(document.getElementById('expense-amount').value),
    category:     document.getElementById('expense-category').value,
    date:         document.getElementById('expense-date').value,
    notes:        document.getElementById('expense-notes').value.trim(),
    is_recurring: document.getElementById('expense-recurring').checked,
    currency:     'USD',
  };

  if (!payload.description || !payload.amount || !payload.category || !payload.date) {
    showToast('Please fill in all required fields', 'error');
    return;
  }

  const saveBtn = document.getElementById('save-expense-btn');
  saveBtn.disabled = true;
  saveBtn.textContent = 'Saving…';

  try {
    if (_editingId) {
      await API.put(`/api/expenses/${_editingId}`, payload);
      showToast('Expense updated!', 'success');
    } else {
      await API.post('/api/expenses/', payload);
      showToast('Expense added!', 'success');
    }
    closeModal('expense-modal');
    await renderExpensesTable();
    window.dispatchEvent(new CustomEvent('expense-changed'));
  } catch (err) {
    showToast(err.message || 'Failed to save expense', 'error');
  } finally {
    saveBtn.disabled = false;
    saveBtn.textContent = 'Save Expense';
  }
}

// ── Delete ────────────────────────────────────────────────────────────────

async function deleteExpense(id) {
  if (!confirm('Delete this expense?')) return;
  try {
    await API.delete(`/api/expenses/${id}`);
    showToast('Expense deleted', 'info');
    await renderExpensesTable();
    window.dispatchEvent(new CustomEvent('expense-changed'));
  } catch (e) {
    showToast('Failed to delete expense', 'error');
  }
}

// ── ML Auto-Categorize ────────────────────────────────────────────────────

function setupMLCategorize() {
  const descInput = document.getElementById('expense-description');
  if (!descInput) return;

  descInput.addEventListener('input', debounce(async () => {
    const desc = descInput.value.trim();
    const suggestion = document.getElementById('ml-suggestion');
    if (desc.length < 4) { suggestion.style.display = 'none'; return; }

    try {
      const result = await API.post('/api/ml/suggest-category', { description: desc });
      if (result.top_category && document.getElementById('expense-category').value === '') {
        suggestion.style.display = 'flex';
        document.getElementById('ml-cat-name').textContent = result.top_category;
        document.getElementById('ml-cat-conf').textContent =
          `${(result.confidence * 100).toFixed(0)}% confident · ${result.method.replace('_', ' ')}`;
        document.getElementById('ml-apply-btn').onclick = () => {
          document.getElementById('expense-category').value = result.top_category;
          suggestion.style.display = 'none';
        };
      }
    } catch {}
  }, 500));
}

// ── Filter Events ─────────────────────────────────────────────────────────

function bindExpenseEvents() {
  document.getElementById('expense-form')?.addEventListener('submit', saveExpense);
  document.getElementById('add-expense-btn')?.addEventListener('click', openAddModal);
  document.getElementById('add-expense-btn2')?.addEventListener('click', openAddModal);

  // Close modals on overlay click
  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) overlay.classList.remove('open');
    });
  });

  document.querySelectorAll('.modal-close-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      btn.closest('.modal-overlay').classList.remove('open');
    });
  });

  // Search and filters with debounce
  const doFilter = debounce(() => {
    renderExpensesTable({
      category:   document.getElementById('filter-category')?.value,
      start_date: document.getElementById('filter-start')?.value,
      end_date:   document.getElementById('filter-end')?.value,
      search:     document.getElementById('search-input')?.value,
    });
  }, 400);

  document.getElementById('search-input')?.addEventListener('input', doFilter);
  document.getElementById('filter-category')?.addEventListener('change', doFilter);
  document.getElementById('filter-start')?.addEventListener('change', doFilter);
  document.getElementById('filter-end')?.addEventListener('change', doFilter);
  document.getElementById('clear-filters-btn')?.addEventListener('click', () => {
    ['filter-category','filter-start','filter-end','search-input'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.value = '';
    });
    renderExpensesTable();
  });
}

export { _categories, _expenses };
