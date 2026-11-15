const fs = require("fs");
const content = fs.readFileSync("c:/jarvis-bot/extension/content.js", "utf8");
const lines = content.split("\n");
let count = 0;
for (let i = 0; i < lines.length; i++) {
  if (lines[i].includes("const STATE")) {
    count++;
    console.log(`Line ${i + 1}: ${lines[i]}`);
  }
}
console.log("Total STATE declarations:", count);
