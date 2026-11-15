/**
 * content.js — Floating glassmorphism JARVIS assistant
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
  '  <button id="jarvis-bubble">',
  '    <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/></svg>',
  '  </button>',
  '  <div id="jarvis-card">',
  '    <header>',
  '      <div class="jarvis-title">',
  '        <span class="jarvis-icon">',
  '          <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/></svg>',
  '        </span>',
  '        <span class="jarvis-label">JARVIS</span>',
  '      </div>',
  '    </header>',
  '  </div>',
  '</div>'
].join("\n");
