"""Resilient network layer for the JARVIS Telegram bot.

This module exists because some ISPs / firewalls silently block Telegram's Bot
API. A single :class:`httpcore.ConnectTimeout` would otherwise bring the whole
bot down at startup. We add:

* :class:`RetryingTransport` - a transport wrapper that re-sends failed
  *connection* requests with exponential back-off and jitter.
* :func:`build_httpx_request` - a factory for hardened :class:`HTTPXRequest`
  objects (timeouts, proxy support and the retry transport).
* :func:`is_retryable_error` - a predicate to distinguish transient network
  failures from real, non-retryable errors.

Only connection-level failures are retried. Read / write timeouts that occur
*after* the request has already been sent are deliberately *not* retried,
because those requests may already have been processed by Telegram and a retry
could produce a duplicate action.
"""
from __future__ import annotations

import asyncio
import logging
import os
import random

import httpx

from telegram.request import HTTPXRequest

__all__ = [
    "HTTPXRequest",
    "RetryingTransport",
    "build_httpx_request",
    "is_retryable_error",
]

logger = logging.getLogger(__name__)

#: Exception types that represent a *connection* failure and are safe to retry.
#: httpx maps the lower-level httpcore errors into these classes, so we only need
#: to match against the httpx exception classes here.
RETRYABLE_ERRORS = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.RemoteProtocolError,
)


def is_retryable_error(exc: BaseException) -> bool:
    """Return ``True`` if *exc* looks like a transient network failure."""
    return isinstance(exc, RETRYABLE_ERRORS)


class RetryingTransport(httpx.AsyncHTTPTransport):
    """An ``httpx`` transport that retries connection failures with backoff + jitter."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._max_delay = max_delay
        super().__init__()

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                return await super().handle_async_request(request)
            except Exception as exc:  # noqa: BLE001 - intentional retry loop
                if not is_retryable_error(exc):
                    raise
                last_error = exc
                if attempt == self._max_retries:
                    break
                delay = min(self._base_delay * (2 ** attempt), self._max_delay)
                delay *= random.uniform(0.8, 1.2)  # jitter
                logger.warning(
                    "Network failure (%r). Attempt %d/%d, retrying in %.1fs",
                    exc,
                    attempt + 1,
                    self._max_retries + 1,
                    delay,
                )
                await asyncio.sleep(delay)

        raise last_error or RuntimeError("retry loop ended without success")


def build_httpx_request(
    *,
    proxy_url: str = "",
    connect_timeout: float = 30.0,
    read_timeout: float = 30.0,
    write_timeout: float = 30.0,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
) -> HTTPXRequest:
    """Build a hardened :class:`telegram.request.HTTPXRequest`.

    Parameters
    ----------
    proxy_url:
        Explicit proxy URL (HTTP/S or SOCKS5). Pass an empty string to disable
        a proxy and instead honour the standard ``HTTPS_PROXY`` / ``ALL_PROXY``
        environment variables.
    connect_timeout, read_timeout, write_timeout:
        HTTP timeouts in seconds applied to every Bot API request.
    max_retries, base_delay, max_delay:
        Retry configuration forwarded to :class:`RetryingTransport`.
    """
    proxy = (
        proxy_url
        or os.getenv("HTTPS_PROXY")
        or os.getenv("ALL_PROXY")
        or None
    )

    # Wrap the plain transport in the retrying wrapper and hand it to httpx
    # through ``httpx_kwargs``. It is the *only* key that overrides the ones
    # python-telegram-bot sets, so timeouts, proxy and limits are preserved.
    retrying_transport = RetryingTransport(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
    )

    return HTTPXRequest(
        connect_timeout=connect_timeout,
        read_timeout=read_timeout,
        write_timeout=write_timeout,
        proxy=proxy,
        httpx_kwargs={"transport": retrying_transport},
    )
