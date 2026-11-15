const fs = require("fs");
const content = fs.readFileSync("c:/jarvis-bot/extension/content.js", "utf8");
const lines = content.split("\n");
// Check line 46 (index 45)
console.log("Line 46:", JSON.stringify(lines[45]));
console.log("Hex:", lines[45].split("").map(c => c.charCodeAt(0).toString(16)).join(" "));
// Also check line 25 (CHAT_URL) 
console.log("Line 25:", JSON.stringify(lines[24]));
console.log("Hex:", lines[24].split("").map(c => c.charCodeAt(0).toString(16)).join(" "));
// Check the backtick in line 46
const idx46 = lines[45].indexOf("`");
if (idx46 >= 0) {
  console.log("Char before backtick in line 46:", JSON.stringify(lines[45][idx46 - 1]));
  console.log("Char after backtick in line 46:", JSON.stringify(lines[45][idx46 + 1]));
}
