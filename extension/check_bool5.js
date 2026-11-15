// Test the boolean issue
const STATE = {
  open: false,
  docked: false,
  submitting: false,
  sessionId: null,
  messageId: 0,
};
const API_BASE = "http://127.0.0.1:8000";
const CHAT_URL = `${API_BASE}/chat`;
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
    body: JSON.stringify(body),
  };
  const res = await fetch(CHAT_URL, opts);
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    throw new Error(detail);
  }
  return res.json();
}
const WIDGET_HTML = `
  <div id="jarvis-root">
    <div class="test">test</div>
  </div>
`;
function injectWidget() {
  const root = document.createElement("div");
  root.innerHTML = WIDGET_HTML;
  const widget = root.firstElementChild;
  document.body.appendChild(widget);

  const jarvisRoot = document.getElementById("jarvis-root");
  const jarvisBubble = document.getElementById("jarvis-bubble");
  const jarvisCard = document.getElementById("jarvis-card");
  const jarvisMessages = document.getElementById("jarvis-messages");
  const jarvisTextarea = document.getElementById("jarvis-textarea");
  const jarvisSendBtn = document.getElementById("jarvis-send-btn");
  const jarvisQuickRepl = document.getElementById("jarvis-quick-replies");
  const jarvisHint = document.getElementById("jarvis-hint");
  const jarvisBtnFloat = document.getElementById("jarvis-btn-floating");
  const jarvisBtnSide = document.getElementById("jarvis-btn-sidebar");
  const jarvisBtnBack = document.getElementById("jarvis-btn-back");
}
