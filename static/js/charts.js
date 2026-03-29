// ── Chart.js Visualisations ────────────────────────────────────────────────
import { formatCurrency, formatDateShort, getCategoryColor } from './utils.js';

const CHART_DEFAULTS = {
  color: '#94a3b8',
  font: { family: 'Inter, system-ui, sans-serif', size: 12 },
};

if (window.Chart) {
  Chart.defaults.color = CHART_DEFAULTS.color;
  Chart.defaults.font  = CHART_DEFAULTS.font;
  Chart.defaults.plugins.legend.labels.usePointStyle = true;
  Chart.defaults.plugins.legend.labels.padding = 16;
}

const GRID_COLOR = 'rgba(255,255,255,0.05)';
const instances  = {};

function destroy(id) {
  if (instances[id]) { instances[id].destroy(); delete instances[id]; }
}

// ── Spending Over Time (Line) ─────────────────────────────────────────────

export function renderSpendingLine(canvasId, data) {
  destroy(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx || !data.length) return;

  const labels = data.map(d => formatDateShort(d.date));
  const values = data.map(d => d.total);

  instances[canvasId] = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Daily Spending',
        data: values,
        borderColor: '#6366f1',
        backgroundColor: 'rgba(99,102,241,0.08)',
        borderWidth: 2.5,
        pointBackgroundColor: '#6366f1',
        pointRadius: 4,
        pointHoverRadius: 6,
        fill: true,
        tension: 0.4,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { intersect: false, mode: 'index' },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(14,14,26,0.95)',
          borderColor: 'rgba(255,255,255,0.1)',
          borderWidth: 1,
          padding: 12,
          callbacks: {
            label: (ctx) => ` ${formatCurrency(ctx.parsed.y)}`,
          },
        },
      },
      scales: {
        x: { grid: { color: GRID_COLOR }, ticks: { maxTicksLimit: 10 } },
        y: {
          grid: { color: GRID_COLOR },
          ticks: { callback: (v) => `$${v}` },
          beginAtZero: true,
        },
      },
    },
  });
}

// ── Category Donut ────────────────────────────────────────────────────────

export function renderCategoryDonut(canvasId, data) {
  destroy(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx || !data.length) return;

  const labels = data.map(d => d.category);
  const values = data.map(d => d.total);
  const colors = labels.map(getCategoryColor);

  instances[canvasId] = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: colors.map(c => c + 'cc'),
        borderColor: colors,
        borderWidth: 2,
        hoverOffset: 8,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '68%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: { padding: 12, font: { size: 11 } },
        },
        tooltip: {
          backgroundColor: 'rgba(14,14,26,0.95)',
          borderColor: 'rgba(255,255,255,0.1)',
          borderWidth: 1,
          padding: 12,
          callbacks: {
            label: (ctx) => ` ${ctx.label}: ${formatCurrency(ctx.parsed)} (${data[ctx.dataIndex].percentage}%)`,
          },
        },
      },
    },
  });
}

// ── Budget vs Actual (Horizontal Bar) ────────────────────────────────────

export function renderBudgetBar(canvasId, data) {
  destroy(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx || !data.length) return;

  const labels = data.map(d => d.category);
  const spent   = data.map(d => d.spent);
  const budgets = data.map(d => d.budget);

  instances[canvasId] = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: 'Spent',
          data: spent,
          backgroundColor: data.map(d => d.over_budget ? 'rgba(239,68,68,0.65)' : 'rgba(99,102,241,0.65)'),
          borderRadius: 5,
          barThickness: 14,
        },
        {
          label: 'Budget',
          data: budgets,
          backgroundColor: 'rgba(255,255,255,0.08)',
          borderRadius: 5,
          barThickness: 14,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: 'y',
      plugins: {
        legend: { position: 'top' },
        tooltip: {
          backgroundColor: 'rgba(14,14,26,0.95)',
          borderColor: 'rgba(255,255,255,0.1)',
          borderWidth: 1,
          padding: 12,
          callbacks: {
            label: (ctx) => ` ${ctx.dataset.label}: ${formatCurrency(ctx.parsed.x)}`,
          },
        },
      },
      scales: {
        x: { grid: { color: GRID_COLOR }, ticks: { callback: (v) => `$${v}` }, beginAtZero: true },
        y: { grid: { display: false } },
      },
    },
  });
}

// ── Forecast Line ─────────────────────────────────────────────────────────

export function renderForecastLine(canvasId, historicalData, forecastData) {
  destroy(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  const histLabels = (historicalData || []).map(d => formatDateShort(d.date));
  const histValues = (historicalData || []).map(d => d.total);
  const foreLabels = (forecastData  || []).map(d => formatDateShort(d.date)).slice(0, 14);
  const foreValues = (forecastData  || []).map(d => d.predicted).slice(0, 14);

  const allLabels = [...histLabels, ...foreLabels];
  const histPad   = new Array(histValues.length).fill(null);
  const forePad   = new Array(histValues.length).fill(null);
  foreValues.forEach((v, i) => { histPad.push(null); forePad.push(v); });

  instances[canvasId] = new Chart(ctx, {
    type: 'line',
    data: {
      labels: allLabels,
      datasets: [
        {
          label: 'Actual',
          data: [...histValues, ...new Array(foreLabels.length).fill(null)],
          borderColor: '#6366f1',
          backgroundColor: 'rgba(99,102,241,0.06)',
          borderWidth: 2.5,
          fill: true,
          tension: 0.4,
          pointRadius: 3,
        },
        {
          label: 'Forecast',
          data: [...new Array(histLabels.length).fill(null), ...foreValues],
          borderColor: '#10b981',
          backgroundColor: 'rgba(16,185,129,0.06)',
          borderWidth: 2,
          borderDash: [6, 3],
          fill: true,
          tension: 0.4,
          pointRadius: 3,
          pointStyle: 'triangle',
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { intersect: false, mode: 'index' },
      plugins: {
        tooltip: {
          backgroundColor: 'rgba(14,14,26,0.95)',
          borderColor: 'rgba(255,255,255,0.1)',
          borderWidth: 1,
          padding: 12,
          callbacks: {
            label: (ctx) => ` ${ctx.dataset.label}: ${ctx.parsed.y != null ? formatCurrency(ctx.parsed.y) : 'N/A'}`,
          },
        },
      },
      scales: {
        x: { grid: { color: GRID_COLOR }, ticks: { maxTicksLimit: 12 } },
        y: { grid: { color: GRID_COLOR }, ticks: { callback: (v) => `$${v}` }, beginAtZero: true },
      },
    },
  });
}

// ── Monthly Bar ───────────────────────────────────────────────────────────

export function renderMonthlyBar(canvasId, data) {
  destroy(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx || !data.length) return;

  // Group by month, stack by category
  const months = [...new Set(data.map(d => d.month))].sort();
  const cats   = [...new Set(data.map(d => d.category))];

  const datasets = cats.map(cat => {
    const color = getCategoryColor(cat);
    return {
      label: cat,
      data: months.map(m => {
        const row = data.find(d => d.month === m && d.category === cat);
        return row ? row.amount : 0;
      }),
      backgroundColor: color + 'bb',
      borderColor: color,
      borderWidth: 1,
      borderRadius: 4,
    };
  });

  instances[canvasId] = new Chart(ctx, {
    type: 'bar',
    data: { labels: months, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom', labels: { font: { size: 11 } } },
        tooltip: {
          backgroundColor: 'rgba(14,14,26,0.95)',
          borderColor: 'rgba(255,255,255,0.1)',
          borderWidth: 1,
          padding: 12,
          callbacks: {
            label: (ctx) => ` ${ctx.dataset.label}: ${formatCurrency(ctx.parsed.y)}`,
          },
        },
      },
      scales: {
        x: { stacked: true, grid: { color: GRID_COLOR } },
        y: { stacked: true, grid: { color: GRID_COLOR }, ticks: { callback: (v) => `$${v}` }, beginAtZero: true },
      },
    },
  });
}
