const fs = require("fs");
const content = fs.readFileSync("c:/jarvis-bot/extension/content.js", "utf8");
// Check first 50 bytes
console.log("First 100 chars:", JSON.stringify(content.substring(0, 100)));
console.log("First 60 bytes hex:", content.substring(0, 60).split("").map(c => c.charCodeAt(0).toString(16)).join(" "));
// Count lines
const lines = content.split("\n");
console.log("Total lines:", lines.length);
// Check line 1
console.log("Line 1:", JSON.stringify(lines[0]));
console.log("Line 1 hex:", lines[0].split("").map(c => c.charCodeAt(0).toString(16)).join(" "));
// Find the actual line numbers
for (let i = 0; i < lines.length; i++) {
  if (i >= 23 && i <= 26) {
    console.log(`Line ${i + 1}: ${JSON.stringify(lines[i])}`);
  }
}
// Find where WIDGET_HTML is
for (let i = 0; i < lines.length; i++) {
  if (lines[i].includes("WIDGET_HTML")) {
    console.log(`Found WIDGET_HTML at line ${i + 1}: ${JSON.stringify(lines[i])}`);
  }
}
