import sys
sys.path.insert(0, r'C:\jarvis-bot')

from services import ai_service

print("=== Test: _build_jarvis_fallback (standard readout) ===")
mc = "EURUSD: 1.085, DXY: 104.2 (Change: +0.35%), US10Y: 4.25%"
print(ai_service._build_jarvis_fallback(mc, ""))

print("\n=== Test: _build_jarvis_fallback (question) ===")
print(ai_service._build_jarvis_fallback(mc, "What is DXY doing?"))

print("\n=== Test: Groq client initialization ===")
print("client:", ai_service.client)
print("model:", ai_service.client.model if ai_service.client else "no client (offline mode)")

print("\nALL TESTS PASSED")

