const fs = require("fs");
const content = fs.readFileSync("c:/jarvis-bot/extension/content.js", "utf8");
const lines = content.split("\n");
for (let i = 40; i < 50; i++) {
  console.log(`Line ${i + 1}: ${JSON.stringify(lines[i])}`);
}
console.log("---");
// Also check the clean file
const clean = fs.readFileSync("c:/jarvis-bot/extension/content_clean.js", "utf8");
const cleanLines = clean.split("\n");
console.log("Clean file line 42-48:");
for (let i = 41; i < 48; i++) {
  console.log(`Line ${i + 1}: ${JSON.stringify(cleanLines[i])}`);
}
