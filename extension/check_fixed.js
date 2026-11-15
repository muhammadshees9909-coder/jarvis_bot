const fs = require("fs");
const content = fs.readFileSync("c:/jarvis-bot/extension/content_fixed.js", "utf8");
const lines = content.split("\n");
let apiCount = 0;
for (let i = 0; i < lines.length; i++) {
  if (lines[i].includes("const API_BASE")) {
    apiCount++;
    console.log(`API_BASE at line ${i + 1}: ${lines[i]}`);
  }
  if (lines[i].includes("const CHAT_URL")) {
    console.log(`CHAT_URL at line ${i + 1}: ${lines[i]}`);
  }
}
console.log("API_BASE count:", apiCount);
console.log("Total lines:", lines.length);
