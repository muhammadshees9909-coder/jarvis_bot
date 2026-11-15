const fs = require("fs");
const content = fs.readFileSync("c:/jarvis-bot/extension/content.js", "utf8");
const lines = content.split("\n");
for (let i = 428; i < 445; i++) {
  console.log(`Line ${i + 1}: ${JSON.stringify(lines[i])}`);
}
