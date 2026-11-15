const fs = require("fs");
const content = fs.readFileSync("c:/jarvis-bot/extension/content.js", "utf8");
const lines = content.split("\n");
// Check line 46 (index 45)
const line46 = lines[45];
console.log("Line 46:", JSON.stringify(line46));
console.log("Line 46 length:", line46.length);
console.log("Line 46 hex:", Array.from(line46).map(c => c.charCodeAt(0).toString(16).padStart(2, "0")).join(" "));
// Check lines 1-46
for (let i = 0; i < Math.min(46, lines.length); i++) {
  console.log(`Line ${i + 1}: ${lines[i].length} chars`);
}
// Check if there's a backslash-r in line 46
const backtickIdx = line46.indexOf("`");
console.log("Backtick at index:", backtickIdx);
if (backtickIdx >= 0) {
  const charAfterBacktick = line46[backtickIdx + 1];
  console.log("Char after backtick:", JSON.stringify(charAfterBacktick));
  console.log("Char code:", charAfterBacktick.charCodeAt(0).toString(16));
}
