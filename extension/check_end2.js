const fs = require("fs");
const content = fs.readFileSync("c:/jarvis-bot/extension/content_fixed.js", "utf8");
const lines = content.split("\n");
// Find the end of the WIDGET_HTML template
// Look for the closing </div> that matches the opening
for (let i = 800; i < lines.length; i++) {
  if (i >= 800 && i < 860) {
    console.log(`Line ${i + 1}: ${JSON.stringify(lines[i])}`);
  }
}
// Find any backtick at the end of a line
for (let i = 0; i < lines.length; i++) {
  const trimmed = lines[i].trim();
  if (trimmed.endsWith("`")) {
    console.log(`Line ${i + 1} ends with backtick: ${JSON.stringify(trimmed.slice(-20))}`);
  }
}
// Find the last few lines
console.log("\nLast 10 lines:");
for (let i = Math.max(0, lines.length - 10); i < lines.length; i++) {
  console.log(`Line ${i + 1}: ${JSON.stringify(lines[i])}`);
}
