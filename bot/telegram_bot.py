"""Telegram command & message handlers for the JARVIS AI trading assistant."""
from __future__ import annotations

import logging
import random
import time

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.error import NetworkError, TimedOut

from config import settings
from bot import network
from services import ai_service, market_data

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Starts the conversation and greets the trader."""
    welcome_text = (
        "Hey! Systems online. I'm JARVIS, your EUR/USD market intelligence bot.\n"
        "Ask me anything about market sentiment, DXY, yields, or news events!"
    )
    await update.message.reply_text(welcome_text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles natural language queries from the trader."""
    user_message = update.message.text

    # Fetch current market context
    prices = market_data.get_market_prices()
    context_str = (
        f"EURUSD: {prices['EURUSD']}, DXY: {prices['DXY']} "
        f"(Change: {prices['DXY_change_percent']}%), "
        f"US10Y: {prices['US10Y']}%"
    )

    # Generate response using JARVIS AI service
    try:
        reply = ai_service.get_jarvis_response(user_message, market_context=context_str)
    except Exception as exc:  # noqa: BLE001 - keep the conversation alive
        logger.error("AI service error: %s", exc)
        reply = "Sorry sir, I'm having trouble connecting to my neural network right now."
        await update.message.reply_text(reply)
        return

    await update.message.reply_text(reply)


def _build_application() -> Application:
    """Build the application with a hardened network request adapter."""
    custom_request = network.build_httpx_request(
        proxy_url=settings.TELEGRAM_PROXY_URL,
        connect_timeout=settings.TELEGRAM_CONNECT_TIMEOUT,
        read_timeout=settings.TELEGRAM_READ_TIMEOUT,
        write_timeout=settings.TELEGRAM_WRITE_TIMEOUT,
        max_retries=settings.MAX_NETWORK_RETRIES,
        base_delay=settings.RETRY_BASE_DELAY,
        max_delay=settings.RETRY_MAX_DELAY,
    )
    return ApplicationBuilder().token(settings.TELEGRAM_BOT_TOKEN).request(custom_request).build()


def _run_polling_with_retries(
    app: Application,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
) -> None:
    """Run :meth:`Application.run_polling` with resilience against network failures.

    The Telegram Bot API is sometimes blocked or throttled (e.g. restricted ISPs).
    Instead of crashing, we retry the polling loop a few times with exponential
    back-off. Connection-level errors (DNS / connect failures, protocol errors)
    are retried automatically by :class:`bot.network.RetryingTransport`.
    """
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            logger.info(
                "Connecting to Telegram Bot API (attempt %d/%d)...",
                attempt + 1,
                max_retries + 1,
            )
            app.run_polling()
            return
        except (KeyboardInterrupt, SystemExit):
            logger.info("Polling stopped by user.")
            raise
        except Exception as exc:  # noqa: BLE001 - keep the process alive
            last_error = exc
            if attempt == max_retries:
                break
            delay = min(base_delay * (2 ** attempt), max_delay)
            delay *= random.uniform(0.8, 1.2)  # jitter
            logger.warning(
                "Telegram network error (%r). Attempt %d/%d, retrying in %.1fs",
                exc,
                attempt + 1,
                max_retries + 1,
                delay,
            )
            time.sleep(delay)

    logger.critical(
        "Could not connect to Telegram API after %d attempts. Exiting.", max_retries
    )
    raise SystemExit(1)


def run_telegram_bot() -> None:
    """Initialize and run the Telegram bot with resilient networking."""
    logger.info("Building Telegram application with hardened network adapter...")
    try:
        app = _build_application()
    except Exception as exc:
        logger.error("Failed to build Telegram request adapter: %s", exc)
        raise

    logger.info("JARVIS Telegram Bot is starting (network retries enabled)...")
    _run_polling_with_retries(app)
