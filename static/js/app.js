// ── App Controller ─────────────────────────────────────────────────────────
import { API, formatCurrency, formatDate, showToast, animateNumber, getCategoryColor, getCategoryIcon } from './utils.js';
import { renderSpendingLine, renderCategoryDonut, renderBudgetBar, renderForecastLine, renderMonthlyBar } from './charts.js';
import { initExpenses, loadCategories, renderExpensesTable, openAddModal } from './expenses.js';
import { initRAG } from './rag.js';

// ── Navigation ────────────────────────────────────────────────────────────

const NAV_SECTIONS = ['dashboard', 'expenses', 'analytics', 'budgets', 'assistant', 'settings'];

function navigate(sectionId) {
  NAV_SECTIONS.forEach(id => {
    document.getElementById(`section-${id}`)?.classList.toggle('active', id === sectionId);
    document.getElementById(`nav-${id}`)?.classList.toggle('active', id === sectionId);
  });
  if (sectionId === 'dashboard') loadDashboard();
  if (sectionId === 'analytics') loadAnalytics();
  if (sectionId === 'budgets')   loadBudgets();
  if (sectionId === 'settings')  loadSettings();
}

// ── Dashboard ─────────────────────────────────────────────────────────────

async function loadDashboard() {
  try {
    const [summary, byCat, byDate, recent, insights] = await Promise.all([
      API.get('/api/analytics/summary'),
      API.get('/api/analytics/by-category'),
      API.get('/api/analytics/by-date?period=daily&days=30'),
      API.get('/api/analytics/recent?limit=8'),
      API.get('/api/ml/insights'),
    ]);

    // KPI cards
    renderKPI('kpi-total',   summary.total_amount,   formatCurrency);
    renderKPI('kpi-month',   summary.this_month,     formatCurrency);
    renderKPI('kpi-week',    summary.this_week,       formatCurrency);
    renderKPI('kpi-avg',     summary.avg_per_day,     formatCurrency);

    const changePct = summary.month_change_pct;
    const changeEl  = document.getElementById('kpi-month-change');
    if (changeEl) {
      const up = changePct >= 0;
      changeEl.innerHTML = `<span class="${up ? 'badge-up' : 'badge-down'}">${up ? '▲' : '▼'} ${Math.abs(changePct)}% vs last month</span>`;
    }

    // Charts
    if (byDate.length)  renderSpendingLine('spending-line-chart', byDate);
    if (byCat.length)   renderCategoryDonut('category-donut-chart', byCat);

    // Recent transactions
    renderRecentTransactions(recent);

    // ML Insights
    renderInsights(insights);

  } catch (err) {
    console.error('Dashboard load error:', err);
    showToast('Failed to load dashboard data', 'error');
  }
}

function renderKPI(id, value, formatter) {
  const el = document.getElementById(id);
  if (el) animateNumber(el, 0, value, 800, (v) => formatter(v));
}

function renderRecentTransactions(expenses) {
  const el = document.getElementById('recent-transactions');
  if (!el) return;

  if (!expenses.length) {
    el.innerHTML = `<div class="empty-state"><div class="icon">💸</div><h3>No transactions yet</h3><p>Add your first expense to start tracking.</p><button class="btn btn-primary" id="add-first-btn">+ Add Expense</button></div>`;
    document.getElementById('add-first-btn')?.addEventListener('click', openAddModal);
    return;
  }

  el.innerHTML = expenses.map(e => {
    const color = getCategoryColor(e.category);
    const icon  = getCategoryIcon(e.category);
    return `
    <div class="budget-card" style="margin-bottom:8px;">
      <div style="display:flex;align-items:center;justify-content:space-between;">
        <div style="display:flex;align-items:center;gap:12px;">
          <div style="width:38px;height:38px;border-radius:10px;background:${color}20;
               display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0;">${icon}</div>
          <div>
            <div style="font-weight:600;font-size:13.5px;">${e.description}</div>
            <div style="font-size:11.5px;color:var(--text-muted);">
              <span class="category-badge" style="background:${color}22;color:${color};border:1px solid ${color}44;font-size:10.5px;">${e.category}</span>
              &nbsp;${formatDate(e.date)}
            </div>
          </div>
        </div>
        <span style="font-weight:700;color:var(--danger);font-size:15px;">${formatCurrency(e.amount)}</span>
      </div>
    </div>`;
  }).join('');
}

function renderInsights(insights) {
  const el = document.getElementById('ml-insights');
  if (!el || !insights.length) return;

  el.innerHTML = `<div class="insight-grid stagger-children">` +
    insights.map(i => `
      <div class="insight-card ${i.type}">
        <span class="insight-icon">${i.icon}</span>
        <div>
          <div class="insight-title">${i.title}</div>
          <div class="insight-text">${i.message}</div>
        </div>
      </div>`
    ).join('') +
  `</div>`;
}

// ── Analytics ─────────────────────────────────────────────────────────────

async function loadAnalytics() {
  try {
    const [byDate, byCat, monthly, forecast, anomalies] = await Promise.all([
      API.get('/api/analytics/by-date?period=daily&days=30'),
      API.get('/api/analytics/by-category'),
      API.get('/api/analytics/monthly'),
      API.get('/api/ml/forecast?days=14'),
      API.get('/api/ml/anomalies'),
    ]);

    renderSpendingLine('analytics-line-chart', byDate);
    renderCategoryDonut('analytics-donut-chart', byCat);
    renderMonthlyBar('monthly-bar-chart', monthly);
    renderForecastLine('forecast-chart', byDate, forecast.forecast);
    renderAnomalies(anomalies);

    // Forecast stats
    if (forecast.avg_daily) {
      const el = document.getElementById('forecast-summary');
      if (el) el.textContent = `Avg. daily spend: ${formatCurrency(forecast.avg_daily)} · Method: ${forecast.method.replace(/_/g,' ')}`;
    }
  } catch (err) {
    console.error('Analytics load error:', err);
  }
}

function renderAnomalies(data) {
  const el = document.getElementById('anomaly-list');
  if (!el) return;

  if (!data.anomalies || !data.anomalies.length) {
    el.innerHTML = `<div style="color:var(--accent);text-align:center;padding:20px;">
      ✅ No anomalies detected in ${data.total_checked || 0} expenses checked.
    </div>`;
    return;
  }

  el.innerHTML = data.anomalies.map(a => `
    <div style="display:flex;align-items:center;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--border);">
      <div>
        <span class="anomaly-badge">⚠️ Anomaly</span>
        <span style="margin-left:8px;font-size:13.5px;">${a.description}</span>
        <span style="font-size:11.5px;color:var(--text-muted);margin-left:6px;">${a.category} · ${a.date}</span>
      </div>
      <span style="font-weight:700;color:var(--danger);">${formatCurrency(a.amount)}</span>
    </div>`
  ).join('');
}

// ── Budgets ───────────────────────────────────────────────────────────────

async function loadBudgets() {
  try {
    const [budgetVsActual, burnRate] = await Promise.all([
      API.get('/api/analytics/budget-vs-actual'),
      API.get('/api/ml/burn-rate'),
    ]);

    if (budgetVsActual.length) renderBudgetBar('budget-bar-chart', budgetVsActual);
    renderBudgetCards(budgetVsActual, burnRate);
  } catch (err) {
    console.error('Budget load error:', err);
  }
}

function renderBudgetCards(budgets, burnRates) {
  const el = document.getElementById('budget-cards');
  if (!el) return;

  if (!budgets.length) {
    el.innerHTML = `<div class="empty-state">
      <div class="icon">📋</div>
      <h3>No budgets set</h3>
      <p>Create budgets to track spending limits per category.</p>
    </div>`;
    return;
  }

  el.innerHTML = budgets.map(b => {
    const color  = getCategoryColor(b.category);
    const icon   = getCategoryIcon(b.category);
    const pct    = Math.min(b.pct_used, 100);
    const fillColor = b.over_budget ? '#ef4444' : (pct > 80 ? '#f59e0b' : '#10b981');
    const br     = burnRates.find(r => r.category === b.category);

    return `
    <div class="budget-card">
      <div class="budget-header">
        <div style="display:flex;align-items:center;gap:10px;">
          <span style="font-size:20px;">${icon}</span>
          <div>
            <div style="font-weight:700;font-size:14px;">${b.category}</div>
            <div style="font-size:11.5px;color:var(--text-muted);">
              ${b.over_budget ? '🔴 Over budget' : pct > 80 ? '🟡 Nearly exhausted' : '🟢 On track'}
            </div>
          </div>
        </div>
        <div style="text-align:right;">
          <div style="font-weight:700;color:${fillColor};font-size:15px;">${formatCurrency(b.spent)}</div>
          <div style="font-size:11.5px;color:var(--text-muted);">of ${formatCurrency(b.budget)}</div>
        </div>
      </div>
      <div class="progress-bar" style="margin-bottom:8px;">
        <div class="progress-fill" style="width:${pct}%;background:${fillColor};"></div>
      </div>
      <div class="budget-meta">
        ${formatCurrency(b.remaining)} remaining · ${b.pct_used}% used
        ${br ? ` · Daily rate: ${formatCurrency(br.daily_rate)}` : ''}
        ${br && br.will_exceed ? ` · ⚠️ Projected: ${formatCurrency(br.projected_month_total)}` : ''}
      </div>
      <div style="display:flex;justify-content:flex-end;">
        <button class="btn btn-danger btn-sm" data-budget-id="${b.budget_id || ''}"
          onclick="removeBudget(this)">Remove</button>
      </div>
    </div>`;
  }).join('');
}

// ── Remove budget (global so onclick= can reach it) ──────────────────────

window.removeBudget = async function(btn) {
  const id = btn.dataset.budgetId;
  if (!id) { showToast('Budget ID not found', 'error'); return; }
  if (!confirm('Remove this budget?')) return;
  btn.disabled = true;
  btn.textContent = '…';
  try {
    await API.delete(`/api/expenses/budgets/${id}`);
    showToast('Budget removed', 'info');
    loadBudgets();
  } catch (err) {
    showToast('Failed to remove: ' + err.message, 'error');
    btn.disabled = false;
    btn.textContent = 'Remove';
  }
};

// ── Settings ──────────────────────────────────────────────────────────────

function loadSettings() { /* static page, no data to load */ }

// ── Clear Data Modal ────────────────────────────────────────────────────────

function openClearDataModal() {
  const modal = document.getElementById('clear-data-modal');
  if (!modal) return;
  
  const modeSelect = document.getElementById('clear-mode');
  modeSelect.value = 'all';
  modeSelect.dispatchEvent(new Event('change'));
  
  modal.classList.add('open');
}

function handleClearModeChange(e) {
  const mode = e.target.value;
  document.getElementById('clear-date-range-group').style.display = (mode === 'date_range') ? 'flex' : 'none';
  document.getElementById('clear-single-date-group').style.display = (mode === 'single_date') ? 'block' : 'none';
  document.getElementById('clear-category-group').style.display = (mode === 'category') ? 'block' : 'none';
  document.getElementById('clear-budgets-group').style.display = (mode === 'all') ? 'flex' : 'none';

  // Toggle required attributes dynamically
  document.getElementById('clear-date-from').required = (mode === 'date_range');
  document.getElementById('clear-date-to').required = (mode === 'date_range');
  document.getElementById('clear-single-date').required = (mode === 'single_date');
  document.getElementById('clear-category').required = (mode === 'category');
}

async function submitClearData(e) {
  e.preventDefault();
  
  const mode = document.getElementById('clear-mode').value;
  const body = { mode };
  
  if (mode === 'date_range') {
    body.date_from = document.getElementById('clear-date-from').value;
    body.date_to = document.getElementById('clear-date-to').value;
    if (body.date_from > body.date_to) {
      showToast('From Date must be before To Date', 'error');
      return;
    }
  } else if (mode === 'single_date') {
    body.single_date = document.getElementById('clear-single-date').value;
  } else if (mode === 'category') {
    body.categories = [document.getElementById('clear-category').value];
  } else if (mode === 'all') {
    body.clear_budgets = document.getElementById('clear-budgets').checked;
  }
  
  let confirmMsg = 'Are you sure you want to delete this data? This action cannot be undone.';
  if (mode === 'all') {
    confirmMsg = '⚠️ This will permanently delete ALL selected data.\n\nAre you absolutely sure?';
  }
  
  if (!confirm(confirmMsg)) return;

  const btn = document.getElementById('confirm-clear-btn');
  if (btn) { btn.disabled = true; btn.textContent = 'Clearing…'; }
  
  try {
    const res = await API.delete('/api/expenses/clear', body);
    showToast(res.message || 'Data cleared successfully', 'success');
    document.getElementById('clear-data-modal').classList.remove('open');
    loadDashboard();
    renderExpensesTable();
    if (mode === 'all' && body.clear_budgets) {
      loadBudgets();
    }
  } catch (err) {
    showToast('Clear failed: ' + err.message, 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '🗑️ Delete Data'; }
  }
}

// ── CSV Upload ────────────────────────────────────────────────────────────

function initCSVUpload() {
  const fileInput  = document.getElementById('csv-file-input');
  const uploadBar  = document.getElementById('csv-upload-bar');
  const filenameEl = document.getElementById('csv-filename');
  const uploadBtn  = document.getElementById('csv-upload-btn');
  const cancelBtn  = document.getElementById('csv-cancel-btn');
  const resultEl   = document.getElementById('csv-result');

  if (!fileInput) return;

  fileInput.addEventListener('change', () => {
    const file = fileInput.files[0];
    if (!file) return;
    filenameEl.textContent = file.name + '  (' + (file.size / 1024).toFixed(1) + ' KB)';
    uploadBar.style.display = 'flex';
    resultEl.style.display  = 'none';
  });

  cancelBtn?.addEventListener('click', () => {
    fileInput.value = '';
    uploadBar.style.display = 'none';
    resultEl.style.display  = 'none';
  });

  uploadBtn?.addEventListener('click', async () => {
    const file = fileInput.files[0];
    if (!file) { showToast('No file selected', 'error'); return; }

    uploadBtn.disabled = true;
    uploadBtn.textContent = '⏳ Importing…';

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('/api/expenses/upload', { method: 'POST', body: formData });
      const data = await res.json();

      if (!res.ok) {
        resultEl.style.display = 'block';
        resultEl.innerHTML = `
          <div style="padding:14px;background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.25);border-radius:8px;margin-bottom:8px;">
            <strong style="color:var(--danger);">❌ Import failed</strong><br>
            <span style="font-size:13px;color:var(--text-secondary);">${data.error || 'Unknown error'}</span>
          </div>`;
        showToast('Import failed: ' + (data.error || 'Unknown'), 'error');
      } else {
        const errHtml = data.errors?.length
          ? `<ul style="margin:8px 0 0 0;padding-left:18px;font-size:12px;color:var(--text-muted);">${data.errors.map(e => `<li>${e}</li>`).join('')}</ul>`
          : '';
        resultEl.style.display = 'block';
        resultEl.innerHTML = `
          <div style="padding:14px;background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.25);border-radius:8px;">
            <strong style="color:var(--accent);">✅ ${data.message}</strong>
            <div style="font-size:12.5px;color:var(--text-muted);margin-top:4px;">
              Imported: <strong style="color:var(--accent);">${data.imported}</strong> &nbsp;·&nbsp;
              Skipped: <strong style="color:var(--warning);">${data.skipped}</strong>
            </div>
            ${errHtml}
          </div>`;
        showToast(data.message, 'success');
        fileInput.value = '';
        uploadBar.style.display = 'none';
        loadDashboard();
        renderExpensesTable();
      }
    } catch (err) {
      showToast('Upload error: ' + err.message, 'error');
    } finally {
      uploadBtn.disabled = false;
      uploadBtn.textContent = '⬆️ Upload & Import';
    }
  });
}

// ── Seed data button ──────────────────────────────────────────────────────

async function seedSampleData() {
  const btn = document.getElementById('seed-btn');
  if (btn) { btn.disabled = true; btn.textContent = 'Loading…'; }
  try {
    const res = await API.post('/api/expenses/seed', {});
    showToast(res.message + ` (${res.count} expenses added)`, 'success');
    loadDashboard();
    renderExpensesTable();
  } catch (e) {
    showToast('Seed failed: ' + e.message, 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '🌱 Load Sample Data'; }
  }
}

// ── Budget form ───────────────────────────────────────────────────────────

async function saveBudget(e) {
  e.preventDefault();
  const category = document.getElementById('budget-category').value;
  const amount   = parseFloat(document.getElementById('budget-amount').value);
  if (!category || !amount) { showToast('Fill in all budget fields', 'error'); return; }
  try {
    await API.post('/api/expenses/budgets', { category, limit_amount: amount, period: 'monthly' });
    showToast('Budget saved!', 'success');
    document.getElementById('budget-form').reset();
    loadBudgets();
  } catch (err) { showToast('Failed to save budget', 'error'); }
}

// ── Init ──────────────────────────────────────────────────────────────────

async function init() {
  // Nav
  document.querySelectorAll('.nav-item[data-section]').forEach(item => {
    item.addEventListener('click', () => navigate(item.dataset.section));
  });

  // Boot
  await initExpenses();
  initRAG();
  loadDashboard();

  // Seed buttons (sidebar + settings)
  document.getElementById('seed-btn')?.addEventListener('click', seedSampleData);
  document.getElementById('seed-btn-settings')?.addEventListener('click', seedSampleData);

  // Clear Data Init
  document.getElementById('clear-all-btn')?.addEventListener('click', openClearDataModal);
  document.getElementById('clear-mode')?.addEventListener('change', handleClearModeChange);
  document.getElementById('clear-data-form')?.addEventListener('submit', submitClearData);

  // Budget form
  document.getElementById('budget-form')?.addEventListener('submit', saveBudget);

  // CSV upload
  initCSVUpload();

  // Reload dashboard when expenses change
  window.addEventListener('expense-changed', loadDashboard);

  // Analytics period toggle
  document.querySelectorAll('.period-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const days = parseInt(btn.dataset.days);
      const data = await API.get(`/api/analytics/by-date?period=daily&days=${days}`);
      renderSpendingLine('analytics-line-chart', data);
    });
  });
}

document.addEventListener('DOMContentLoaded', init);
