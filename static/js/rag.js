// ── RAG Chat Interface ─────────────────────────────────────────────────────
import { API, showToast, renderMarkdown } from './utils.js';

export function initRAG() {
  loadSuggestions();
  bindChatEvents();
  appendWelcomeMessage();
}

// ── Welcome message ───────────────────────────────────────────────────────

function appendWelcomeMessage() {
  appendBotMessage(
    "👋 **Welcome to your AI Finance Assistant!**\n\n" +
    "I'm powered by a **RAG (Retrieval-Augmented Generation)** system — I retrieve relevant facts from your expense data " +
    "and financial knowledge base, then generate accurate, personalised answers.\n\n" +
    "Try asking me anything about your spending! 💡"
  );
}

// ── Load suggested questions ──────────────────────────────────────────────

async function loadSuggestions() {
  const container = document.getElementById('suggestion-chips');
  if (!container) return;
  try {
    const { questions } = await API.get('/api/rag/suggestions');
    container.innerHTML = questions.map(q =>
      `<button class="suggestion-chip">${q}</button>`
    ).join('');
    container.querySelectorAll('.suggestion-chip').forEach(chip => {
      chip.addEventListener('click', () => sendQuery(chip.textContent));
    });
  } catch {}
}

// ── Chat Events ───────────────────────────────────────────────────────────

function bindChatEvents() {
  const input   = document.getElementById('chat-input');
  const sendBtn = document.getElementById('chat-send-btn');

  if (!input || !sendBtn) return;

  sendBtn.addEventListener('click', () => {
    const q = input.value.trim();
    if (q) { sendQuery(q); input.value = ''; }
  });

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      const q = input.value.trim();
      if (q) { sendQuery(q); input.value = ''; }
    }
  });

  // Auto-resize textarea
  input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 120) + 'px';
  });
}

// ── Send query through RAG pipeline ──────────────────────────────────────

async function sendQuery(query) {
  appendUserMessage(query);
  const typingId = appendTypingIndicator();

  try {
    const data = await API.post('/api/rag/query', { query });
    removeTypingIndicator(typingId);

    const sourceHtml = data.sources && data.sources.length
      ? `<div style="margin-top:12px;display:flex;flex-wrap:wrap;gap:6px;">
          ${data.sources.map(s =>
            `<span class="source-badge" style="
              font-size:10.5px;padding:2px 8px;border-radius:20px;
              background:rgba(99,102,241,0.1);border:1px solid rgba(99,102,241,0.2);
              color:var(--text-muted);">
              📄 ${s.type} · ${(s.relevance * 100).toFixed(0)}% match
            </span>`
          ).join('')}
         </div>
         <div style="font-size:11px;color:var(--text-muted);margin-top:6px;">
           Retrieved ${data.retrieved_count} documents · Intent: ${(data.intent || '').replace(/_/g,' ')}
         </div>`
      : '';

    appendBotMessage(data.answer + sourceHtml);
  } catch (err) {
    removeTypingIndicator(typingId);
    appendBotMessage('❌ Sorry, I encountered an error. Please try again.');
    showToast('RAG query failed: ' + err.message, 'error');
  }
}

// ── Message builders ──────────────────────────────────────────────────────

function appendUserMessage(text) {
  const messages = document.getElementById('chat-messages');
  if (!messages) return;
  const div = document.createElement('div');
  div.className = 'message user';
  div.innerHTML = `
    <div class="msg-avatar">👤</div>
    <div class="msg-bubble">${escapeHtml(text)}</div>
  `;
  messages.appendChild(div);
  scrollToBottom();
}

function appendBotMessage(text) {
  const messages = document.getElementById('chat-messages');
  if (!messages) return;
  const div = document.createElement('div');
  div.className = 'message bot';
  div.innerHTML = `
    <div class="msg-avatar">🤖</div>
    <div class="msg-bubble">${renderMarkdown(text)}</div>
  `;
  messages.appendChild(div);
  scrollToBottom();
}

function appendTypingIndicator() {
  const messages = document.getElementById('chat-messages');
  if (!messages) return null;
  const id = 'typing-' + Date.now();
  const div = document.createElement('div');
  div.className = 'message bot';
  div.id = id;
  div.innerHTML = `
    <div class="msg-avatar">🤖</div>
    <div class="msg-bubble">
      <div class="typing-indicator">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>
    </div>
  `;
  messages.appendChild(div);
  scrollToBottom();
  return id;
}

function removeTypingIndicator(id) {
  if (id) document.getElementById(id)?.remove();
}

function scrollToBottom() {
  const messages = document.getElementById('chat-messages');
  if (messages) messages.scrollTop = messages.scrollHeight;
}

function escapeHtml(str) {
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
