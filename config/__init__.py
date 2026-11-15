"""JARVIS configuration package."""
from types import SimpleNamespace

from .settings import *  # noqa: F401,F403

# Expose a namespace object (`settings`) alongside the flat module constants so
# both `from config.settings import ...` and `from config import settings` work.
_settings = SimpleNamespace(
    TELEGRAM_BOT_TOKEN=TELEGRAM_BOT_TOKEN,
    GROQ_API_KEY=GROQ_API_KEY,
    TIMEZONE=TIMEZONE,
    TELEGRAM_PROXY_URL=TELEGRAM_PROXY_URL,
    TELEGRAM_CONNECT_TIMEOUT=TELEGRAM_CONNECT_TIMEOUT,
    TELEGRAM_READ_TIMEOUT=TELEGRAM_READ_TIMEOUT,
    TELEGRAM_WRITE_TIMEOUT=TELEGRAM_WRITE_TIMEOUT,
    MAX_NETWORK_RETRIES=MAX_NETWORK_RETRIES,
    RETRY_BASE_DELAY=RETRY_BASE_DELAY,
    RETRY_MAX_DELAY=RETRY_MAX_DELAY,
)

# `config.settings` and `config.settings` module object remain importable as a
# module, while `settings` itself is now a dot-attr namespace object.
settings = _settings

