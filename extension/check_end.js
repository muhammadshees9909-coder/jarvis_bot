const fs = require("fs");
const content = fs.readFileSync("c:/jarvis-bot/extension/content_fixed.js", "utf8");
const lines = content.split("\n");
// Find the WIDGET_HTML template start and end
for (let i = 450; i < lines.length; i++) {
  if (lines[i].includes("WIDGET_HTML")) {
    console.log(`Found WIDGET_HTML at line ${i + 1}`);
  }
  if (i >= 450 && i < 490) {
    console.log(`Line ${i + 1}: ${JSON.stringify(lines[i])}`);
  }
}
// Find the closing backtick
for (let i = 456; i < lines.length; i++) {
  if (lines[i].trim().endsWith("`")) {
    console.log(`\nFound closing backtick at line ${i + 1}: ${JSON.stringify(lines[i])}`);
    break;
  }
}
