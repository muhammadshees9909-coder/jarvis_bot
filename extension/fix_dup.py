lines = open(r"c:/jarvis-bot/extension/content.js", "r", encoding="utf-8").read().split("\n")
# Find the first occurrence of a block starting with STATE and containing duplicate API_BASE
# Remove all lines from the SECOND API_BASE occurrence to the function that follows
# Find all occurrences of "const API_BASE"
positions = [i for i, l in enumerate(lines) if "const API_BASE" in l]
print("API_BASE positions:", [p+1 for p in positions])

# The first occurrence is at line 16 (index 15)
# The second occurrence is the duplicate we want to remove
# Remove the second occurrence and the following line (CHAT_URL)
if len(positions) >= 2:
    dup_idx = positions[1]  # index of second API_BASE
    del lines[dup_idx:dup_idx+2]
    print("Removed duplicate API_BASE and CHAT_URL at line", dup_idx+1)

open(r"c:/jarvis-bot\extension\content_fixed.js", "w", encoding="utf-8").write("\n".join(lines))
print("Done. Total lines:", len(lines))
