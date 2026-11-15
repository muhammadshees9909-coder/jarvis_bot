const fs = require("fs");
const content = fs.readFileSync("c:/jarvis-bot/extension/content.js", "utf8");

// Find and replace template literals
let fixed = content;

// 1. Replace CHAT_URL template literal
fixed = fixed.replace(
  /const CHAT_URL = `\$\{API_BASE\}\/chat`;/,
  'const CHAT_URL = API_BASE + "/chat";'
);

// 2. Replace WIDGET_HTML template literal (everything between 'const WIDGET_HTML = `' and '`;\n')
const widgetMatch = fixed.match(/const WIDGET_HTML = `([\s\S]*?)`;/);
if (widgetMatch) {
  const widgetContent = widgetMatch[1];
  // Escape quotes inside the content
  const escapedContent = widgetContent.replace(/"/g, '\\"');
  fixed = fixed.replace(
    widgetMatch[0],
    `const WIDGET_HTML = "${escapedContent}";`
  );
}

fs.writeFileSync("c:/jarvis-bot/extension/content_fixed_v2.js", fixed);
console.log("Written content_fixed_v2.js");
