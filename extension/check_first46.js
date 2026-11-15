const fs = require("fs");
const original = fs.readFileSync("c:/jarvis-bot/extension/content.js", "utf8");
const clean = fs.readFileSync("c:/jarvis-bot/extension/content_clean.js", "utf8");

const origLines = original.split("\n");
const cleanLines = clean.split("\n");

console.log("Comparing first 46 lines...");
for (let i = 0; i < 46; i++) {
  const o = origLines[i] || "<missing>";
  const c = cleanLines[i] || "<missing>";
  if (o !== c) {
    console.log(`Line ${i + 1}:`);
    console.log(`  ORIG: ${JSON.stringify(o)}`);
    console.log(`  CLEAN: ${JSON.stringify(c)}`);
  }
}
