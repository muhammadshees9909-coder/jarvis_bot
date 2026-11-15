const fs = require("fs");
const path = require("path");
const content = fs.readFileSync("c:/jarvis-bot/extension/content.js", "utf8");
console.log("File size:", content.length, "bytes");
console.log("Line 25:", JSON.stringify(content.split("\n")[24]));
console.log("Line 46:", JSON.stringify(content.split("\n")[45]));
// Write the first 46 lines to a temp file and check with a new approach
const lines = content.split("\n");
const first46 = lines.slice(0, 46).join("\n") + "\n";
fs.writeFileSync("c:/jarvis-bot/extension/content_first46.txt", first46);
console.log("Wrote first46.txt");
// Also write with \r\n line endings
const first46CrLf = lines.slice(0, 46).join("\r\n") + "\r\n";
fs.writeFileSync("c:/jarvis-bot/extension/content_first46_crlf.txt", first46CrLf);
console.log("Wrote first46_crlf.txt");
