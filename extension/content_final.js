/**
 * content.js - Floating glassmorphism JARVIS assistant
 * Manifest V3 content script
 */
"use strict";

const STATE = {
  open: false,
  docked: false,
  submitting: false,
  sessionId: null,
  messageId: 0
};

const API_BASE = "http://127.0.0.1:8000";
const CHAT_URL = API_BASE + "/chat";

async function injectCss(cssText) {
  const style = document.createElement("style");
  style.id = "jarvis-style";
  style.textContent = cssText;
  document.head.appendChild(style);
}

async function chatFetch(body) {
  const opts = {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  };
  const res = await fetch(CHAT_URL, opts);
  if (!res.ok) {
    let detail = "HTTP " + res.status;
    try {
      const json = await res.json();
      detail = json.detail || detail;
    } catch (_) {}
    throw new Error(detail);
  }
  return res.json();
}

const $ = function(sel) {
  return document.getElementById(sel);
};

const WIDGET_HTML = [
  '<div id="jarvis-root">',
  '  <button id="jarvis-bubble" aria-label="Toggle JARVIS assistant">',
  '    <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/></svg>',
  '  </button>',
  '  <div id="jarvis-card" class="closed">',
  '    <header>',
  '      <div class="jarvis-title">',
  '        <span class="jarvis-icon">',
  '          <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/></svg>',
  '        </span>',
  '        <span class="jarvis-label">JARVIS</span>',
  '      </div>',
  '      <div class="jarvis-actions">',
  '        <div class="jarvis-control-group">',
  '          <button class="jarvis-control-btn" id="jarvis-btn-floating">',
  '            <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z"/></svg>',
  '          </button>',
  '          <button class="jarvis-control-btn" id="jarvis-btn-sidebar">',
  '            <svg viewBox="0 0 24 24"><path d="M22 12h-6V7.5L18 2.5 16 4.5l-4 4v6h2v-2h4v2h2z"/></svg>',
  '          </button>',
  '          <button class="jarvis-control-btn" id="jarvis-btn-back">',
  '            <svg viewBox="0 0 24 24"><path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/></svg>',
  '          </button>',
  '        </div>',
  '      </div>',
  '    </header>',
  '    <div id="jarvis-messages">',
  '      <div class="jarvis-message jarvis-assistant">',
  '        <div class="jarvis-meta">Say something to get started...</div>',
  '      </div>',
  '    </div>',
  '    <div id="jarvis-input-area">',
  '      <textarea id="jarvis-textarea" rows="1" placeholder="Type your message..."></textarea>',
  '      <button class="jarvis-send-btn" id="jarvis-send-btn">',
  '        <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>',
  '      </button>',
  '    </div>',
  '  </div>',
  '</div>',
].join("\n");

function injectWidget() {
  const root = document.createElement('div');
  root.innerHTML = WIDGET_HTML;
  document.body.appendChild(root);

  STATE.root = $('#jarvis-root');
  STATE.bubble = $('#jarvis-bubble');
  STATE.card = $('#jarvis-card');
  STATE.messages = $('#jarvis-messages');
  STATE.textarea = $('#jarvis-textarea');
  STATE.sendBtn = $('#jarvis-send-btn');
  STATE.quickRepl = $('#jarvis-quick-replies');
  STATE.hint = $('#jarvis-hint');
  STATE.btnFloat = $('#jarvis-btn-floating');
  STATE.btnSide = $('#jarvis-btn-sidebar');
  STATE.btnBack = $('#jarvis-btn-back');

  STATE.card.classList.add('closed');
  STATE.card.style.opacity = "0";
  STATE.card.style.transform = "scale(0.88) translateY(20px)";
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function setLoading(loading) {
  STATE.submitting = loading;
  const list = STATE.messages;
  const last = list.lastElementChild;
  if (loading) {
    const el = document.createElement('div');
    el.className = "jarvis-message jarvis-loading";
    el.textContent = "Thinking...";
    list.appendChild(el);
  } else if (last && last.classList.contains('jarvis-loading')) {
    last.remove();
  }
  list.scrollTop = list.scrollHeight;
}

function renderResponse(text) {
  const list = STATE.messages;
  const el = document.createElement('div');
  el.className = "jarvis-message jarvis-assistant";
  el.innerHTML = escapeHtml(text) + '<span class="jarvis-meta">Just now</span>';
  list.appendChild(el);
  list.scrollTop = list.scrollHeight;
}

function renderQuickReplies(replies) {
  const container = STATE.quickRepl;
  if (!Array.isArray(replies) || replies.length === 0) {
    container.innerHTML = '';
    return;
  }
  container.innerHTML = '';
  for (const r of replies) {
    const btn = document.createElement('button');
    btn.className = "jarvis-quick-btn";
    btn.textContent = r.label || r.text || r;
    btn.addEventListener('click', function() {
      STATE.textarea.value = r.value || r;
      STATE.textarea.dispatchEvent(new Event('input'));
      sendMessage();
    });
    container.appendChild(btn);
  }

async function sendMessage() {
  const text = STATE.textarea.value.trim();
  if (!text || STATE.submitting) return;
  STATE.messageId += 1;

  const userEl = document.createElement('div');
  userEl.className = "jarvis-message jarvis-user";
  userEl.textContent = text;
  STATE.messages.appendChild(userEl);
  STATE.messages.scrollTop = STATE.messages.scrollHeight;

  STATE.textarea.value = '';
  STATE.textarea.dispatchEvent(new Event('input'));
  setLoading(true);
  STATE.btnSend.style.opacity = "0.5";
  STATE.btnSend.style.cursor = "default";

  try {
    const payload = {
      message: text,
      session_id: STATE.sessionId
    };
    const data = await chatFetch(payload);
    STATE.sessionId = data.session_id || STATE.sessionId;

    if (data.error) {
      showError(data.error);
    } else {
      renderResponse(data.response);
    }
    renderQuickReplies(data.quick_replies || data.quickReplies || []);
  } catch (err) {
    showError("Request failed: " + err.message);
  } finally {
    setLoading(false);
    STATE.btnSend.style.opacity = "1";
    STATE.btnSend.style.cursor = "pointer";
  }
}

function openCard() {
  if (STATE.docked || STATE.open) return;
  STATE.open = true;
  STATE.card.classList.remove('closed');
  STATE.card.style.opacity = "1";
  STATE.card.style.transform = "scale(1) translateY(0)";
  STATE.bubble.style.display = "none";
  setTimeout(function() { STATE.textarea.focus(); }, 100);
}

function closeCard() {
  if (!STATE.open) return;
  STATE.open = false;
  STATE.card.classList.add('closed');
  STATE.card.style.opacity = "0";
  STATE.card.style.transform = "scale(0.88) translateY(20px)";
  STATE.bubble.style.display = "flex";
}

function setMode(docked) {
  STATE.docked = docked;
  if (docked) {
    STATE.card.style.bottom = "0";
    STATE.card.style.right = "0";
    STATE.card.style.left = "0";
    STATE.card.style.width = "100%";
    STATE.card.style.height = "100%";
    STATE.card.style.minHeight = "auto";
    STATE.card.style.borderRadius = "0";
    STATE.card.style.boxShadow = "none";
    STATE.bubble.style.bottom = "16px";
    STATE.bubble.style.right = "16px";
    STATE.hint.textContent = "JARVIS is docked as a full side panel. Click the bubble to hide it.";
  } else {
    STATE.card.style.bottom = "calc(var(--bubble-gap) + var(--bubble-size) + var(--bubble-gap))";
    STATE.card.style.right = "var(--bubble-gap)";
    STATE.card.style.left = "auto";
    STATE.card.style.width = "var(--card-width)";
    STATE.card.style.height = "auto";
    STATE.card.style.minHeight = "var(--card-min-height)";
    STATE.card.style.borderRadius = "var(--radius-lg)";
    STATE.card.style.boxShadow = "var(--glass-shadow-lg)";
    STATE.bubble.style.bottom = "var(--bubble-gap)";
    STATE.bubble.style.right = "var(--bubble-gap)";
    STATE.hint.textContent = "Tip: dock as a side panel for a full conversation window. Click the card header to collapse.";
  }
  requestAnimationFrame(function() {
    if (!STATE.docked && STATE.open) {
      STATE.card.classList.remove('closed');
      STATE.card.style.opacity = "1";
      STATE.card.style.transform = "scale(1) translateY(0)";
    } else if (STATE.docked) {
      STATE.card.style.opacity = "1";
      STATE.card.style.transform = "scale(1) translateY(0)";
    }
  });
}

function bindEvents() {
  STATE.bubble.addEventListener('click', function() {
    if (STATE.docked) {
      STATE.card.classList.add('closed');
      STATE.card.style.opacity = "0";
      STATE.card.style.transform = "scale(1) translateY(100%)";
      STATE.bubble.style.display = "flex";
    } else {
      STATE.open ? closeCard() : openCard();
    }
  });

  STATE.card.addEventListener('click', function(e) {
    if (e.target.closest('#jarvis-card')) return;
    if (!STATE.docked && STATE.open) closeCard();
  });

  STATE.btnFloat.addEventListener('click', function() { if (STATE.docked) setMode(false); });
  STATE.btnSide.addEventListener('click', function() { if (!STATE.docked) setMode(true); });
  STATE.btnBack.addEventListener('click', function() {
    if (STATE.docked) setMode(false);
    else if (STATE.open) closeCard();
  });

  STATE.quickRepl.addEventListener('click', function() {
    if (STATE.open && !STATE.docked) closeCard();
  });

  STATE.sendBtn.addEventListener('click', sendMessage);

  STATE.textarea.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  STATE.textarea.addEventListener('input', function() {
    STATE.textarea.style.height = "auto";
    STATE.textarea.style.height = Math.min(STATE.textarea.scrollHeight, 120) + "px";
  });
}

function init() {
  injectWidget();
  bindEvents();
  fetch(chrome.runtime.getURL('content.css'))
    .then(function(r) { return r.text(); })
    .then(function(css) { return injectCss(css); })
    .catch(function(err) { console.warn('[JARVIS] Failed to load CSS:', err); });
  if (STATE.docked) setMode(true);
  console.log("[JARVIS] Floating glass assistant ready.");
}

if (!document.getElementById('jarvis-root')) {
  injectWidget();
  bindEvents();
  fetch(chrome.runtime.getURL('content.css'))
    .then(function(r) { return r.text(); })
    .then(function(css) { return injectCss(css); })
    .catch(function(err) { console.warn('[JARVIS] Failed to load CSS:', err); });
  console.log("[JARVIS] Floating glass assistant ready.");
}
