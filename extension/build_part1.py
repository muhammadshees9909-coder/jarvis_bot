
lines = []

# Write header
lines.append('/**')
lines.append(' * content.js - Floating glassmorphism JARVIS assistant')
lines.append(' * Manifest V3 content script')
lines.append(' */')
lines.append("\"use strict\";")
lines.append('')
lines.append('const STATE = {')
lines.append('  open: false,')
lines.append('  docked: false,')
lines.append('  submitting: false,')
lines.append('  sessionId: null,')
lines.append('  messageId: 0')
lines.append('};')
lines.append('')
lines.append('const API_BASE = "http://127.0.0.1:8000";')
lines.append('const CHAT_URL = API_BASE + "/chat";')
lines.append('')

# injectCss
lines.append('async function injectCss(cssText) {')
lines.append('  const style = document.createElement("style");')
lines.append('  style.id = "jarvis-style";')
lines.append('  style.textContent = cssText;')
lines.append('  document.head.appendChild(style);')
lines.append('}')

# chatFetch
lines.append('')
lines.append('async function chatFetch(body) {')
lines.append('  const opts = {')
lines.append('    method: "POST",')
lines.append('    headers: { "Content-Type": "application/json" },')
lines.append('    body: JSON.stringify(body)')
lines.append('  };')
lines.append('  const res = await fetch(CHAT_URL, opts);')
lines.append('  if (!res.ok) {')
lines.append('    let detail = "HTTP " + res.status;')
lines.append('    try {')
lines.append('      const json = await res.json();')
lines.append('      detail = json.detail || detail;')
lines.append('    } catch (_) {}')
lines.append('    throw new Error(detail);')
lines.append('  }')
lines.append('  return res.json();')
lines.append('}')

# DOM refs
lines.append('')
lines.append("const $ = function(sel) {")
lines.append("  return document.getElementById(sel);")
lines.append("};")

with open(r"c:/jarvis-bot/extension/part1.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
