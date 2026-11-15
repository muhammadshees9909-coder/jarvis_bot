const fs = require("fs");
let s = fs.readFileSync("c:/jarvis-bot/extension/content.js", "utf8");
// Replace template literal with string concatenation
s = s.replace(
  /const CHAT_URL = `.*\/chat`;/,
  "const CHAT_URL = API_BASE + '/chat';"
);
fs.writeFileSync("c:/jarvis-bot/extension/content_test2.js", s);
console.log("Written");
