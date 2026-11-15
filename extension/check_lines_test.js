try {
  require("fs").readFileSync("c:/jarvis-bot/extension/content.js", "utf8");
  console.log("File read OK");
} catch (e) {
  console.log("Read error:", e.message);
}
