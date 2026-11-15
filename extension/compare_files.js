const fs = require("fs");
const original = fs.readFileSync("c:/jarvis-bot/extension/content.js", "utf8");
const clean = fs.readFileSync("c:/jarvis-bot/extension/content_clean.js", "utf8");

const origLines = original.split("\n");
const cleanLines = clean.split("\n");

console.log("Original line count:", origLines.length);
console.log("Clean line count:", cleanLines.length);

// Compare first 50 lines
const maxLines = Math.max(origLines.length, cleanLines.length);
for (let i = 0; i < maxLines; i++) {
  const o = origLines[i] || "<missing>";
  const c = cleanLines[i] || "<missing>";
  if (o !== c) {
    console.log(`Line ${i + 1}:`);
    console.log(`  ORIG: ${JSON.stringify(o)}`);
    console.log(`  CLEAN: ${JSON.stringify(c)}`);
  }
}
