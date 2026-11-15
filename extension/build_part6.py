
lines = []

# Init
lines.append("")
lines.append("function init() {")
lines.append("  injectWidget();")
lines.append("  bindEvents();")
lines.append("  fetch(chrome.runtime.getURL('content.css'))")
lines.append("    .then(function(r) { return r.text(); })")
lines.append("    .then(function(css) { return injectCss(css); })")
lines.append("    .catch(function(err) { console.warn('[JARVIS] Failed to load CSS:', err); });")
lines.append("  if (STATE.docked) setMode(true);")
lines.append('  console.log("[JARVIS] Floating glass assistant ready.");')
lines.append("}")

lines.append("")
lines.append("if (!document.getElementById('jarvis-root')) {")
lines.append("  injectWidget();")
lines.append("  bindEvents();")
lines.append("  fetch(chrome.runtime.getURL('content.css'))")
lines.append("    .then(function(r) { return r.text(); })")
lines.append("    .then(function(css) { return injectCss(css); })")
lines.append("    .catch(function(err) { console.warn('[JARVIS] Failed to load CSS:', err); });")
lines.append('  console.log("[JARVIS] Floating glass assistant ready.");')
lines.append("}")

with open(r"c:/jarvis-bot/extension/part6.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
