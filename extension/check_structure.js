const fs = require("fs");
const content = fs.readFileSync("c:/jarvis-bot/extension/content.js", "utf8");
const lines = content.split("\n");
let stateCount = 0;
let apiCount = 0;
for (let i = 0; i < lines.length; i++) {
  if (lines[i].includes("const STATE")) {
    stateCount++;
    console.log(`STATE at line ${i + 1}: ${lines[i]}`);
  }
  if (lines[i].includes("const API_BASE")) {
    apiCount++;
    console.log(`API_BASE at line ${i + 1}: ${lines[i]}`);
  }
  if (lines[i].includes("const CHAT_URL")) {
    console.log(`CHAT_URL at line ${i + 1}: ${lines[i]}`);
  }
}
console.log("STATE count:", stateCount);
console.log("API_BASE count:", apiCount);
