const fs = require("fs");
const content = fs.readFileSync("c:/jarvis-bot/extension/content_fixed.js", "utf8");
const lines = content.split("\n");
console.log("Line 457:", JSON.stringify(lines[456]));
console.log("Line 457 length:", lines[456].length);
console.log("Line 457 hex:", Array.from(lines[456]).map(c => c.charCodeAt(0).toString(16).padStart(2, "0")).join(" "));
console.log("Char after backtick:", JSON.stringify(lines[456][lines[456].indexOf("`") + 1]));
