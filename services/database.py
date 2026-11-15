"""SQLite persistence layer (SQLAlchemy) for JARVIS chat history.

Stores one row per chat session and one row per message so the extension can
reload past conversations and the AI can be given short-term memory.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from config.settings import DATABASE_URL


class Base(DeclarativeBase):
    """Declarative base for all JARVIS tables."""


class ChatSession(Base):
    """A single conversation thread, keyed by a client-supplied id."""

    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    messages: Mapped[List["ChatMessage"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.id",
    )


class ChatMessage(Base):
    """A single user or assistant turn inside a session."""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(16))  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    session: Mapped[ChatSession] = relationship(back_populates="messages")


# ---------------------------------------------------------------------------
# Engine / session factory
# ---------------------------------------------------------------------------
# check_same_thread=False lets FastAPI's threadpool reuse connections safely.
# The 30s busy timeout stops a concurrent writer (dashboard + phone + browser
# extension all share jarvis.db) from raising "database is locked".
_IS_SQLITE = DATABASE_URL.startswith("sqlite")
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 30} if _IS_SQLITE else {},
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """Create tables if they do not exist yet and enable durable SQLite mode."""
    Base.metadata.create_all(bind=engine)
    if _IS_SQLITE:
        # WAL lets other clients keep reading while a chat turn is being
        # written, and FULL synchronous guarantees a committed session /
        # message survives a crash or a server restart.
        with engine.begin() as conn:
            conn.exec_driver_sql("PRAGMA journal_mode=WAL")
            conn.exec_driver_sql("PRAGMA synchronous=FULL")


# ---------------------------------------------------------------------------
# Data-access helpers
# ---------------------------------------------------------------------------
def get_history(session_id: str, limit: int = 10) -> List[Dict[str, str]]:
    """Return the last *limit* turns for a session, oldest first."""
    with SessionLocal() as db:
        rows = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.id.desc())
            .limit(limit)
            .all()
        )
    rows.reverse()
    return [{"role": r.role, "content": r.content} for r in rows]


def record_turn(session_id: str, user_message: str, assistant_message: str) -> str:
    """Persist the session (if new) and both turns of an exchange."""
    with SessionLocal() as db:
        session = db.get(ChatSession, session_id)
        if session is None:
            session = ChatSession(id=session_id, title=user_message[:80])
            db.add(session)
        else:
            session.updated_at = datetime.now(timezone.utc)

        db.add(ChatMessage(session_id=session_id, role="user", content=user_message))
        db.add(ChatMessage(session_id=session_id, role="assistant", content=assistant_message))
        db.commit()
    return session_id


def new_session_id() -> str:
    """Generate a fresh session id."""
    return uuid.uuid4().hex


def list_sessions(limit: int = 50) -> List[Dict[str, Any]]:
    """List recent sessions with a message count, newest first."""
    with SessionLocal() as db:
        rows = (
            db.query(ChatSession, func.count(ChatMessage.id).label("message_count"))
            .outerjoin(ChatMessage, ChatMessage.session_id == ChatSession.id)
            .group_by(ChatSession.id)
            .order_by(ChatSession.updated_at.desc())
            .limit(limit)
            .all()
        )
    return [
        {
            "session_id": s.id,
            "title": s.title,
            "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat(),
            "message_count": count,
        }
        for s, count in rows
    ]


def get_messages(session_id: str) -> List[Dict[str, Any]]:
    """Return the full ordered transcript for a session."""
    with SessionLocal() as db:
        rows = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.id.asc())
            .all()
        )
    return [
        {
            "role": r.role,
            "content": r.content,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


def delete_session(session_id: str) -> bool:
    """Delete a session and its messages. Returns True if it existed."""
    with SessionLocal() as db:
        session = db.get(ChatSession, session_id)
        if session is None:
            return False
        db.delete(session)
        db.commit()
    return True
