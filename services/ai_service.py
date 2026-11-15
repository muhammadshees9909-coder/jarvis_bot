import os
import sys
import time
import traceback
import logging
from typing import Dict, List, Optional
from dotenv import load_dotenv; load_dotenv()

logger = logging.getLogger(__name__)

_client = None

# ---------------------------------------------------------------------------
# Model configuration + automatic retry / fallback
# ---------------------------------------------------------------------------
# Gemini occasionally answers with "503 UNAVAILABLE - the model is overloaded".
# A short exponential-backoff retry on the primary model, then a switch to the
# next model in the chain, keeps a temporary spike from failing the user's chat.
# The fallbacks are live models verified to answer `generateContent` quickly
# (gemini-2.0-flash and gemini-2.5-flash-lite were retired by Google; the big
# flash models can take 20s+ per reply, so the lite ones come first).
PRIMARY_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
FALLBACK_MODELS = [
    model.strip()
    for model in os.getenv(
        "GEMINI_FALLBACK_MODELS",
        "gemini-3.1-flash-lite,gemini-3.5-flash-lite,gemini-3.5-flash",
    ).split(",")
    if model.strip()
]
MAX_ATTEMPTS = 3            # attempts per model
BACKOFF_BASE_SECONDS = 0.75  # 0.75s, then 1.5s between retries of one model

# "retry" - transient spike on this model, wait a moment and try again.
_RETRYABLE_MARKERS = (
    "503", "unavailable", "overloaded", "high demand", "500", "502", "504",
    "deadline", "timeout", "internal error", "connection reset", "connection aborted",
)
# "next" - this particular model is unusable; another model may still work.
_MODEL_GONE_MARKERS = (
    "404", "429", "not_found", "not found", "no longer available",
    "not supported", "resource_exhausted", "rate limit", "quota",
)
_RETRYABLE_STATUS_CODES = {500, 502, 503, 504}
_MODEL_GONE_STATUS_CODES = {404, 429}


class AIUnavailableError(RuntimeError):
    """Every Gemini attempt failed (model overload / quota / network).

    Carries the HTTP status the API layer should answer with, so the dashboard
    can show a real reason instead of a generic "server offline" message.
    """

    def __init__(self, message: str, *, status_code: int = 503):
        super().__init__(message)
        self.status_code = status_code


def _classify(exc: Exception) -> str:
    """Sort an API failure into 'retry', 'next' (try another model) or 'fatal'."""
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    if isinstance(code, int):
        if code in _RETRYABLE_STATUS_CODES:
            return "retry"
        if code in _MODEL_GONE_STATUS_CODES:
            return "next"
    text = f"{type(exc).__name__}: {exc}".lower()
    if any(marker in text for marker in _RETRYABLE_MARKERS):
        return "retry"
    if any(marker in text for marker in _MODEL_GONE_MARKERS):
        return "next"
    return "fatal"

# ---------------------------------------------------------------------------
# Persona + language rules
# ---------------------------------------------------------------------------
# Prepended to every request so Gemini mirrors whatever language the user
# writes in instead of defaulting to Hindi/Devanagari for Hinglish input.
SYSTEM_INSTRUCTION = """You are JARVIS, a warm and friendly forex assistant for the EUR/USD market, talking with Shees like a helpful friend who happens to know the markets.

LANGUAGE RULES (highest priority):
1. Reply in the SAME language and script the user used in their latest message.
   - English input -> reply in English.
   - Roman Urdu input (e.g. "EURUSD ka outlook kya hai?") -> reply in natural, casual Roman Urdu written in Latin letters, the way friends text each other ("Yaar, abhi EURUSD 1.0850 ke aas paas hai aur DXY thoda strong lag raha hai."). NEVER reply in Devanagari/Hindi script unless the user writes in Devanagari.
   - Urdu script input (اردو) -> reply in Urdu script.
2. Sound like a friend, not a report. Words like "yaar", "dekho", "chalo", "acha", "theek hai", "bilkul" fit naturally when the user speaks Roman Urdu. Warm and relaxed, never stiff, formal or robotic.
3. Mirror casual code-switching: if the user mixes English and Roman Urdu, mix them back the same way.
4. Keep trading terminology in English (EURUSD, DXY, US10Y, bullish, bearish, support, resistance, pip, stop-loss). Never translate instrument names or indicator names.
5. Numbers, prices and percentages always use Western digits.

VOICE RULES (your answer is read out loud by a text-to-speech voice):
- Write plain conversational sentences, the way you would say them out loud.
- Never use markdown or special symbols: no asterisks, no hash headings, no bullet points or numbered lists, no tables, no backticks, no code blocks, no emojis.
- Spell units in words when the voice would stumble: write "0.35 percent" instead of "0.35%", and write prices plainly like "1.0850".
- Keep it short enough to listen to comfortably: 2 to 5 sentences for a normal question.

STYLE RULES:
- Be concise and decisive: lead with the take, then the reasoning.
- Ground every answer in the Live Market Data provided below. If data is missing, say so instead of inventing numbers.
- Never invent economic events, price levels or statistics that are not in the provided context.
- This is market analysis, not financial advice. Do not add a disclaimer paragraph unless the user asks about risk.
"""


def _get_client():
    """Create the Gemini client on first use.

    Building the client at import time made the whole FastAPI app crash on
    startup whenever the key was missing/invalid. Doing it lazily keeps the
    server alive and surfaces the problem as a normal chat error instead.
    """
    global _client
    if _client is None:
        from google import genai
        from google.genai import types

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Please add it to your .env file."
            )
        _client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                # The SDK retries 5x internally with a 1s->60s backoff, which
                # stalls the chat for ~90s before our fallback ever runs. Turn
                # that off so the retry/fallback loop below owns the timing.
                retry_options=types.HttpRetryOptions(attempts=1),
                timeout=60_000,  # 60s hard cap per request (milliseconds)
            ),
        )
    return _client


def _build_page_context_block(page_context: Optional[Dict[str, str]]) -> str:
    """Describe the browser tab the question came from.

    The extension widget sends ``{url, title}`` of the active tab with every
    ``/chat`` call, so questions like "Main kis platform par hoon?" ("Which
    platform am I on?") or "ye page kya hai?" can be answered from the actual
    site instead of being guessed.
    """
    if not page_context:
        return ""
    url = str(page_context.get("url") or "").strip()
    title = str(page_context.get("title") or "").strip()
    if not url and not title:
        return ""

    lines = ["User's current browser tab (where this question was typed):"]
    if title:
        lines.append(f"- Page title: {title}")
    if url:
        lines.append(f"- URL: {url}")
    lines.append(
        "If the user asks which platform/site they are on, or refers to what is "
        "open on their screen, answer from this tab: name the website (e.g. the "
        "site in the URL) and say what such a page is typically used for. Never "
        "guess a platform that is not listed here, and if no tab context is "
        "given, ask the user which site they mean."
    )
    return "\n".join(lines)


def _build_prompt(
    user_prompt: str,
    market_context: str = "",
    history: Optional[List[dict]] = None,
    page_context: Optional[Dict[str, str]] = None,
) -> str:
    """Compose the final prompt: persona + prior turns + live data + open tab + query."""
    parts: List[str] = [SYSTEM_INSTRUCTION]

    if history:
        lines = []
        for turn in history:
            role = "User" if turn.get("role") == "user" else "JARVIS"
            lines.append(f"{role}: {turn.get('content', '')}")
        if lines:
            parts.append("Conversation so far:\n" + "\n".join(lines))

    if market_context:
        parts.append(f"Live Market Data: {market_context}")

    page_block = _build_page_context_block(page_context)
    if page_block:
        parts.append(page_block)

    parts.append(f"User Query ({_detect_language(user_prompt)}): {user_prompt}")
    return "\n\n".join(parts)


def _detect_language(text: str) -> str:
    """Cheap script sniff so the model gets an explicit language hint."""
    if any("\u0600" <= ch <= "\u06FF" for ch in text):
        return "Urdu script"
    if any("\u0900" <= ch <= "\u097F" for ch in text):
        return "Devanagari"
    roman_urdu_markers = (
        "kya", "kaise", "kaisay", "hai", "hain", "ka", "ki", "ke", "mein", "nahi",
        "batao", "bataen", "karo", "krdo", "achha", "acha", "theek", "aap", "tum",
        "abhi", "ajj", "aaj", "ya", "aur", "par", "se", "ko", "hoga", "karna", "h",
    )
    words = set(text.lower().replace("?", " ").replace(",", " ").split())
    if len(words & set(roman_urdu_markers)) >= 2:
        return "Roman Urdu - reply in Roman Urdu/Latin script"
    return "English unless the user clearly used another language"


def _report_failure(exc: Optional[Exception]) -> None:
    """Log the last underlying error so the console keeps the real cause."""
    print(f"🔥 GEMINI API EXCEPTION CAUGHT: {exc}", flush=True)
    if exc is not None:
        traceback.print_exception(type(exc), exc, exc.__traceback__, file=sys.stderr)


def get_jarvis_response(
    user_prompt: str,
    market_context: str = "",
    history: Optional[List[dict]] = None,
    page_context: Optional[Dict[str, str]] = None,
):
    """Generate a reply, retrying with backoff and falling back across models.

    ``page_context`` is the active browser tab ({url, title}) supplied by the
    Chrome extension widget; when present it is injected into the prompt.

    Raises ``AIUnavailableError`` (with a user-friendly message + HTTP status)
    only once every model and attempt has failed, so the API layer can return a
    meaningful error instead of a bare 500.
    """
    full_prompt = _build_prompt(user_prompt, market_context, history, page_context)
    client = _get_client()

    models = [PRIMARY_MODEL] + [m for m in FALLBACK_MODELS if m != PRIMARY_MODEL]
    last_error: Optional[Exception] = None

    for model in models:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=full_prompt,
                )
                text = getattr(response, "text", None)
                if not text:
                    raise RuntimeError("Gemini returned an empty response.")
                if model != PRIMARY_MODEL:
                    logger.warning("Gemini recovered using fallback model %s", model)
                return text
            except Exception as exc:  # noqa: BLE001 - decide retry vs give up
                last_error = exc
                verdict = _classify(exc)
                logger.warning(
                    "Gemini %s attempt %d/%d failed (%s): %s",
                    model, attempt, MAX_ATTEMPTS, verdict, exc,
                )
                if verdict == "fatal":
                    # Bad API key / invalid request - retrying or swapping the
                    # model cannot help, so stop immediately.
                    _report_failure(exc)
                    raise AIUnavailableError(
                        f"JARVIS AI configuration error: {exc}", status_code=502
                    ) from exc
                if verdict == "next":
                    break  # model retired / out of quota -> try the next one now
                if attempt < MAX_ATTEMPTS:
                    time.sleep(BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)))

    _report_failure(last_error)
    raise AIUnavailableError(
        "JARVIS AI is temporarily unavailable — Gemini is overloaded or unreachable. "
        "Thodi der baad dobara koshish karein."
    ) from last_error
