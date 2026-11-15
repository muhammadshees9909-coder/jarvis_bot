// Line counting test
console.log("Start");
console.log("Before API_BASE");
const API_BASE = "http://127.0.0.1:8000";
console.log("After API_BASE");
const CHAT_URL = API_BASE + "/chat";
console.log("After CHAT_URL");
console.log("Before State");
const STATE = {
  open: false,
  docked: false,
  submitting: false,
  sessionId: null,
  messageId: 0,
};
console.log("After State");
console.log("Before injectCss");
async function injectCss(cssText) {
  const style = document.createElement("style");
  style.id = "jarvis-style";
  style.textContent = cssText;
  document.head.appendChild(style);
}
console.log("After injectCss");
console.log("Before chatFetch");
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
console.log("After chatFetch");
console.log("Before WIDGET_HTML");
const WIDGET_HTML = `
  <div id="jarvis-root">
  </div>
`;
console.log("After WIDGET_HTML");
