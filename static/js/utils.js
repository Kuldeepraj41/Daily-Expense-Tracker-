// ── Utility helpers ────────────────────────────────────────────────────────

export const API = {
  async get(path) {
    const res = await fetch(path);
    if (!res.ok) throw new Error(`API ${path} failed: ${res.status}`);
    return res.json();
  },
  async post(path, body) {
    const res = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `API ${path} failed: ${res.status}`);
    }
    return res.json();
  },
  async put(path, body) {
    const res = await fetch(path, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`API ${path} failed: ${res.status}`);
    return res.json();
  },
  async delete(path, body = null) {
    const options = { method: 'DELETE' };
    if (body) {
      options.headers = { 'Content-Type': 'application/json' };
      options.body = JSON.stringify(body);
    }
    const res = await fetch(path, options);
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || `API ${path} failed: ${res.status}`);
    }
    return res.json();
  },
};

export function formatCurrency(amount, currency = 'USD') {
  return new Intl.NumberFormat('en-US', {
    style: 'currency', currency, minimumFractionDigits: 2,
  }).format(amount);
}

export function formatDate(dateStr) {
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export function formatDateShort(dateStr) {
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export function today() {
  return new Date().toISOString().split('T')[0];
}

export function showToast(message, type = 'info', duration = 3500) {
  const container = document.getElementById('toast-container');
  const icons = { success: '✅', error: '❌', info: 'ℹ️' };
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<span>${icons[type] || '💬'}</span><span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(24px)';
    toast.style.transition = '0.3s';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

export function renderMarkdown(text) {
  // Light-weight markdown: bold, italic, code, line breaks
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/_(.+?)_/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br>');
}

export function debounce(fn, delay = 300) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

export function getCategoryColor(category) {
  const colors = {
    'Food & Dining': '#f59e0b',
    'Transportation': '#3b82f6',
    'Shopping': '#8b5cf6',
    'Entertainment': '#ec4899',
    'Health & Fitness': '#10b981',
    'Utilities': '#6366f1',
    'Housing': '#ef4444',
    'Education': '#14b8a6',
    'Travel': '#f97316',
    'Other': '#6b7280',
  };
  return colors[category] || '#6b7280';
}

export function getCategoryIcon(category) {
  const icons = {
    'Food & Dining': '🍽️', 'Transportation': '🚗', 'Shopping': '🛍️',
    'Entertainment': '🎬', 'Health & Fitness': '💪', 'Utilities': '⚡',
    'Housing': '🏠', 'Education': '📚', 'Travel': '✈️', 'Other': '📦',
  };
  return icons[category] || '💰';
}

export function animateNumber(element, from, to, duration = 800, formatter = (v) => v.toFixed(2)) {
  const start = performance.now();
  const update = (now) => {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3); // easeOutCubic
    element.textContent = formatter(from + (to - from) * eased);
    if (progress < 1) requestAnimationFrame(update);
  };
  requestAnimationFrame(update);
}
