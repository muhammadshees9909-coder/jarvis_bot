const fs = require("fs");
const content = fs.readFileSync("c:/jarvis-bot/extension/content_fixed.js", "utf8");
const lines = content.split("\n");
// Check the WIDGET_HTML template area
for (let i = 454; i < 470; i++) {
  console.log(`Line ${i + 1}: ${JSON.stringify(lines[i])}`);
}
