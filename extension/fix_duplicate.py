data = open(r"c:/jarvis-bot/extension/content.js", "rb").read().decode("utf-8")
lines = data.split("\n")
# Find and remove the duplicate API_BASE and CHAT_URL lines
# Lines 432 and 433 (0-indexed 431 and 432) have duplicates
# We'll remove the second occurrence
i = 0
while i < len(lines):
    if i > 0 and lines[i].startswith('const API_BASE = "http://127.0.0.1:8000";') and lines[i-1].strip() == "":
        # Check if previous non-empty line is STATE
        j = i - 1
        while j > 0 and lines[j].strip() == "":
            j -= 1
        if j > 0 and lines[j].strip().startswith("const STATE"):
            # Found the duplicate block - remove these 2 lines
            del lines[i:i+2]
            i -= 2
            continue
    i += 1

new_content = "\n".join(lines)
open(r"c:/jarvis-bot/extension/content_fixed.js", "w").write(new_content)
print("Fixed. Total lines:", len(lines))
