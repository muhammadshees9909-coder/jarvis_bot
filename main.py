"""Main entry point for the JARVIS FastAPI web server.

Run with:  uvicorn main:app --reload
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config.settings import APP_TITLE, APP_DESCRIPTION
from services import ai_service, database, market_data, news_service

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version="1.0.0",
)

# Create the SQLite tables on boot (safe to call repeatedly).
database.init_db()

# ---------------------------------------------------------------------------
# Host / proxy configuration for public tunnels
# ---------------------------------------------------------------------------
# Cloudflare quick tunnels and ngrok hand out a *random* subdomain on every
# launch, so those domains are whitelisted with wildcards. Add your own with
# the ALLOWED_HOSTS env var (comma separated); set ALLOWED_HOSTS=* to switch
# the check off completely (e.g. when using a LAN IP that is unknown upfront).
_DEFAULT_ALLOWED_HOSTS = (
    "localhost,127.0.0.1,[::1],"
    "*.trycloudflare.com,*.ngrok-free.app,*.ngrok-free.dev,*.ngrok.app,"
    "*.ngrok.io,*.loca.lt"
)
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", _DEFAULT_ALLOWED_HOSTS).split(",")
    if host.strip()
]
app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)

# CORS Middleware add kar diya hai taaki extension har website par chal sake
# (tunnel domains bhi allow hote hain taaki phone browser se requests ja sakein).
#
# allow_private_network answers Chrome's Private Network Access preflight: a page
# served from a public site that calls http://127.0.0.1:8000 sends
# `Access-Control-Request-Private-Network: true`, and unless the reply carries
# `Access-Control-Allow-Private-Network: true` the browser blocks the request.
# Without it the extension widget reported "Connection Error" even though this
# server was up and healthy.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Sabhi origins/websites ko allow karega
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_private_network=True,
)
# NOTE: behind a tunnel uvicorn must trust the proxy headers, otherwise the
# secure scheme is lost. run.bat (remote mode) launches uvicorn with
# `--proxy-headers --forwarded-allow-ips *`; cloudflared/ngrok connect from
# 127.0.0.1, which uvicorn already trusts by default.

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------
class PageContext(BaseModel):
    """Active browser tab the question was typed in (sent by the extension)."""
    url: Optional[str] = None
    title: Optional[str] = None


class ChatRequest(BaseModel):
    """JSON body accepted by the /chat endpoint."""
    message: str
    session_id: Optional[str] = None
    page_context: Optional[PageContext] = None


class ChatResponse(BaseModel):
    """JSON payload returned by /chat."""
    response: str
    market_context: Dict[str, Any]
    session_id: Optional[str] = None
    timestamp: str
    error: Optional[str] = None

# ---------------------------------------------------------------------------
# Market context helpers
# ---------------------------------------------------------------------------
def build_market_context() -> Dict[str, Any]:
    """Return a snapshot of live prices used as context and in the response."""
    prices = market_data.get_market_prices()
    return {
        "eurusd": prices["EURUSD"],
        "dxy": prices["DXY"],
        "dxy_change_percent": prices["DXY_change_percent"],
        "us10y": prices["US10Y"],
        "us10y_change_bps": prices["US10Y_change_bps"],
    }


def build_market_context_string(prices: Dict[str, Any]) -> str:
    """Human-readable market context appended to every AI prompt."""
    return (
        f"EURUSD: {prices['EURUSD']}, DXY: {prices['DXY']} "
        f"(Change: {prices['DXY_change_percent']}%), "
        f"US10Y: {prices['US10Y']}%"
    )


def clean_page_context(page_context: Optional[PageContext]) -> Optional[Dict[str, str]]:
    """Trim the incoming tab context so a huge URL cannot flood the prompt.

    Returns ``None`` when the caller sent nothing useful, so the AI prompt stays
    exactly as it was before the widget started attaching tab info.
    """
    if page_context is None:
        return None
    url = (page_context.url or "").strip()[:2048]
    title = (page_context.title or "").strip()[:300]
    if not url and not title:
        return None
    return {"url": url, "title": title}

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    """Serve the dark-mode chat interface."""
    return HTMLResponse(content=_load_ui(), status_code=200)


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    """Generate a JARVIS reply using live market context and prior turns."""
    message = (req.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message must not be empty.")

    # Reuse the caller's session, or open a new one for this browser widget.
    session_id = req.session_id or database.new_session_id()
    history = database.get_history(session_id, limit=10)

    prices = market_data.get_market_prices()
    context_string = build_market_context_string(prices)

    # The extension widget reports the tab it was typed in, so questions about
    # "which platform am I on?" / "kya khula hai screen par?" can be answered.
    page_context = clean_page_context(req.page_context)

    error: Optional[str] = None
    try:
        reply = ai_service.get_jarvis_response(
            message,
            market_context=context_string,
            history=history,
            page_context=page_context,
        )
    except ai_service.AIUnavailableError as exc:
        # Model overloaded / quota / network: the server is fine, the AI is not.
        # Surface a real reason so the dashboard does not claim "server offline".
        print(f"⚠️ AI UNAVAILABLE: {exc}", flush=True)
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    except RuntimeError as exc:
        # Config problems (e.g. missing GEMINI_API_KEY) reach here too.
        print(f"🔥 AI CONFIG ERROR: {exc}", flush=True)
        raise HTTPException(status_code=503, detail=f"AI service not configured: {exc}")
    except Exception as exc:  # noqa: BLE001 - keep the chat UI alive
        print(f"🔥 ACTUAL AI SERVICE ERROR: {exc}", flush=True)
        raise HTTPException(status_code=502, detail=f"AI service error: {exc}")

    # Persist the exchange so history survives reloads and server restarts.
    try:
        database.record_turn(session_id, message, reply)
    except Exception as exc:  # noqa: BLE001 - persistence must not break chat
        logger.warning("Failed to persist chat turn: %s", exc)

    return ChatResponse(
        response=reply,
        market_context=build_market_context(),
        session_id=session_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        error=error,
    )


@app.get("/api/sessions")
async def sessions() -> Dict[str, Any]:
    """List stored chat sessions, newest first."""
    stored = database.list_sessions()
    return {"sessions": stored, "count": len(stored)}


@app.get("/api/sessions/{session_id}/messages")
async def session_messages(session_id: str) -> Dict[str, Any]:
    """Return the full transcript for one session."""
    messages = database.get_messages(session_id)
    if not messages:
        raise HTTPException(status_code=404, detail="Session not found or empty.")
    return {"session_id": session_id, "messages": messages, "count": len(messages)}


@app.delete("/api/sessions/{session_id}")
async def remove_session(session_id: str) -> Dict[str, Any]:
    """Delete a session and all of its messages."""
    if not database.delete_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"deleted": session_id}


@app.get("/api/market")
async def market() -> Dict[str, Any]:
    """Live EUR/USD, DXY and US10Y snapshot for the dashboard ticker."""
    return {
        "market_context": build_market_context(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/health")
async def health() -> Dict[str, Any]:
    """Liveness check for the web server."""
    return {
        "status": "ok",
        "service": "JARVIS",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/news")
async def news() -> Dict[str, Any]:
    """Return today's high-impact USD/EUR economic events with PKT times."""
    events = news_service.get_news_events()
    return {
        "events": events,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# PWA / static assets
# ---------------------------------------------------------------------------
# Icons and the web-app manifest live in `static/` and are served from /static.
if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _static_file(name: str, media_type: str) -> FileResponse:
    """Serve one file from `static/`, or 404 if the deployment is incomplete."""
    path = STATIC_DIR / name
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"{name} not found.")
    return FileResponse(path, media_type=media_type)


@app.get("/manifest.json", include_in_schema=False)
async def pwa_manifest() -> FileResponse:
    """PWA web app manifest so phones can install JARVIS on the home screen."""
    return _static_file("manifest.json", "application/manifest+json")


@app.get("/sw.js", include_in_schema=False)
async def service_worker() -> FileResponse:
    """Service worker - served from the root so it can control the whole app."""
    return _static_file("sw.js", "application/javascript")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> FileResponse:
    """Default browser favicon request."""
    return _static_file("icon.svg", "image/svg+xml")


def _load_ui() -> str:
    """Load the embedded chat UI template."""
    ui_path = BASE_DIR / "templates" / "index.html"
    return ui_path.read_text(encoding="utf-8")