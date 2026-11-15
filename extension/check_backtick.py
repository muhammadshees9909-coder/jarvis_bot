data = open(r"c:/jarvis-bot/extension/content.js", "rb").read()
lines = data.decode("utf-8").split("\n")
for i, l in enumerate(lines):
    if "CHAT_URL" in l or "API_BASE" in l or "WIDGET_HTML" in l:
        print(f"Line {i+1}: {l!r}")
        print(f"  hex: {l.encode().hex()}")
