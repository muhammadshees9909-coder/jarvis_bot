"""Environment variable loader for the JARVIS EUR/USD Market Intelligence System.

Loads settings from ``.env`` (if present) and exposes validated constants used by
the AI service, market data fetcher, and the FastAPI web server.
"""

from pathlib import Path
from dotenv import load_dotenv
import os
import warnings

# ---------------------------------------------------------------------------
# Load environment variables from a .env file (if present)
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# ---------------------------------------------------------------------------
# Helpers for resolving (and validating) environment variables
# ---------------------------------------------------------------------------
def _env_str(name: str, default: str = "") -> str:
    """Return an environment variable as *str*, falling back to *default*."""
    value = os.getenv(name)
    return value if value is not None else default


def _env_float(name: str, default: float) -> float:
    """Return an environment variable as *float*, falling back to *default*."""
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    """Return an environment variable as *int*, falling back to *default*."""
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


# ---------------------------------------------------------------------------
# Required credentials
# ---------------------------------------------------------------------------
# GROQ is only used by the optional Telegram bridge. The FastAPI web server does
# not need it, so a missing key must never take the whole server down at import.
GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    warnings.warn(
        "GROQ_API_KEY is not set. The optional Telegram bridge will be disabled.",
        stacklevel=2,
    )

# TELEGRAM_BOT_TOKEN is no longer required for the FastAPI web UI. It remains
# available (optional) for the optional Telegram bridge in `bot/`.
TELEGRAM_BOT_TOKEN: str | None = os.getenv("TELEGRAM_BOT_TOKEN")

# ---------------------------------------------------------------------------
# Timezone
# ---------------------------------------------------------------------------
TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Karachi")

# ---------------------------------------------------------------------------
# FastAPI web server settings
# ---------------------------------------------------------------------------
WEB_HOST: str = os.getenv("WEB_HOST", "127.0.0.1")
WEB_PORT: int = _env_int("WEB_PORT", 8000)
DEBUG: bool = _env_int("DEBUG", 0) == 1

APP_TITLE: str = "JARVIS - Forex Market Intelligence"
APP_DESCRIPTION: str = (
    "Personalised EUR/USD trading assistant with live market context "
    "and AI-powered market analysis."
)

# ---------------------------------------------------------------------------
# Persistence (SQLite via SQLAlchemy)
# ---------------------------------------------------------------------------
BASE_DIR_STR: str = str(BASE_DIR)
DATABASE_URL: str = os.getenv(
    "DATABASE_URL", f"sqlite:///{(BASE_DIR / 'jarvis.db').as_posix()}"
)

# ---------------------------------------------------------------------------
# Optional network / retry tuning (kept for the optional Telegram bridge)
# ---------------------------------------------------------------------------
TELEGRAM_PROXY_URL: str = _env_str("TELEGRAM_PROXY_URL", "")
TELEGRAM_CONNECT_TIMEOUT: float = _env_float("TELEGRAM_CONNECT_TIMEOUT", 30.0)
TELEGRAM_READ_TIMEOUT: float = _env_float("TELEGRAM_READ_TIMEOUT", 30.0)
TELEGRAM_WRITE_TIMEOUT: float = _env_float("TELEGRAM_WRITE_TIMEOUT", 30.0)
MAX_NETWORK_RETRIES: int = _env_int("MAX_NETWORK_RETRIES", 3)
RETRY_BASE_DELAY: float = _env_float("RETRY_BASE_DELAY", 1.0)
RETRY_MAX_DELAY: float = _env_float("RETRY_MAX_DELAY", 30.0)
