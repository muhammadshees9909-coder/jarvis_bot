const fs = require("fs");
let content = fs.readFileSync("c:/jarvis-bot/extension/content.js", "utf8");
// Find the template literal and replace it with a regular string
const startIdx = content.indexOf("const WIDGET_HTML = `");
const endIdx = content.indexOf("`;\n\n// ---------------------------------------------------------------------------\n// Widget injection", startIdx);
if (startIdx >= 0 && endIdx >= 0) {
  // Get the template literal content (including the backticks)
  const templateLiteral = content.substring(startIdx, endIdx + 1);
  // Replace with a multi-line regular string using array join
  const lines = templateLiteral.split("\n");
  // Find the start and end of the template literal (the backticks)
  const startBacktick = lines[0].indexOf("`");
  const endBacktick = lines[lines.length - 1].lastIndexOf("`");
  // Build a regular string
  const stringLines = lines.map(l => l.substring(startBacktick + 1, l.length - (l.length - l.lastIndexOf("`") - 1)));
  const stringContent = stringLines.join("\\n");
  const replacement = `const WIDGET_HTML = "${stringContent}";`;
  content = content.substring(0, startIdx) + replacement + content.substring(endIdx + 1);
  fs.writeFileSync("c:/jarvis-bot/extension/content_fixed.js", content);
  console.log("Fixed and written to content_fixed.js");
} else {
  console.log("Could not find template literal boundaries");
  console.log("startIdx:", startIdx, "endIdx:", endIdx);
}
