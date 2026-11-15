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
  } else {
    STATE.card.style.bottom = "auto";
    STATE.card.style.right = "auto";
    STATE.card.style.left = "auto";
  }
}
function bindEvents() {
  STATE.bubble.addEventListener("click", () => {
    if (STATE.docked) {
      STATE.card.classList.add("closed");
      STATE.card.style.opacity = "0";
      STATE.card.style.transform = "scale(1) translateY(100%)";
      STATE.bubble.style.display = "flex";
    } else {
      STATE.open ? closeCard() : openCard();
    }
  });

  STATE.card.addEventListener("click", (e) => {
    if (e.target.closest("#jarvis-card")) return;
    if (!STATE.docked && STATE.open) closeCard();
  });

  STATE.btnFloat.addEventListener("click", () => {
    if (STATE.docked) setMode(false);
  });
  STATE.btnSide.addEventListener("click", () => {
    if (!STATE.docked) setMode(true);
  });
  STATE.btnBack.addEventListener("click", () => {
    if (STATE.docked) setMode(false);
    else if (STATE.open) closeCard();
  });
}
