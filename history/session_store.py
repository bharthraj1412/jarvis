# history/session_store.py
"""
SQLite-backed persistent session and turn storage for JARVIS MK37.

Storage location: ~/.jarvis/history/sessions.db

Schema:
  sessions — one row per interactive session
  turns    — every user/assistant exchange and tool call
  tags     — free-form session tags for filtering

Thread-safe: all writes go through a threading.Lock().
Auto-creates the DB and tables on first use.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any


_DB_DIR = Path.home() / ".jarvis" / "history"
_DB_PATH = _DB_DIR / "sessions.db"

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    start_ts    INTEGER NOT NULL,
    end_ts      INTEGER,
    mode        TEXT NOT NULL DEFAULT 'general',
    backend     TEXT NOT NULL DEFAULT 'gemini',
    turn_count  INTEGER NOT NULL DEFAULT 0,
    summary     TEXT
);

CREATE TABLE IF NOT EXISTS turns (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL REFERENCES sessions(id),
    ts          INTEGER NOT NULL,
    role        TEXT NOT NULL,
    content     TEXT NOT NULL DEFAULT '',
    tool_name   TEXT,
    tool_args   TEXT,
    tool_result TEXT,
    backend     TEXT,
    latency_ms  INTEGER
);

CREATE TABLE IF NOT EXISTS tags (
    session_id  TEXT NOT NULL REFERENCES sessions(id),
    tag         TEXT NOT NULL,
    PRIMARY KEY (session_id, tag)
);

CREATE INDEX IF NOT EXISTS idx_turns_session ON turns(session_id);
CREATE INDEX IF NOT EXISTS idx_turns_ts ON turns(ts);
CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag);
"""

# Full-text search virtual table (created separately so it can fail gracefully)
_FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS turns_fts USING fts5(
    content,
    tool_name,
    tool_result,
    content='turns',
    content_rowid='id'
);
"""

_FTS_TRIGGER_SQL = """
CREATE TRIGGER IF NOT EXISTS turns_ai AFTER INSERT ON turns BEGIN
    INSERT INTO turns_fts(rowid, content, tool_name, tool_result)
    VALUES (new.id, new.content, new.tool_name, new.tool_result);
END;
"""


class SessionStore:
    """Thread-safe SQLite session store."""

    def __init__(self, db_path: str | Path | None = None):
        self._db_path = Path(db_path) if db_path else _DB_PATH
        self._lock = threading.Lock()
        self._conn: sqlite3.Connection | None = None
        self._ensure_db()

    # ── Connection management ─────────────────────────────────────────────

    def _ensure_db(self) -> None:
        """Create the database and tables if they don't exist."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = self._get_conn()
        conn.executescript(_SCHEMA_SQL)
        try:
            conn.executescript(_FTS_SQL)
            conn.executescript(_FTS_TRIGGER_SQL)
        except sqlite3.OperationalError:
            pass  # FTS5 not available — fall back to LIKE search
        conn.commit()

    def _get_conn(self) -> sqlite3.Connection:
        """Return a thread-local connection (reuses if already open)."""
        if self._conn is None:
            self._conn = sqlite3.connect(
                str(self._db_path),
                check_same_thread=False,
                timeout=10,
            )
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    # ── Session lifecycle ─────────────────────────────────────────────────

    def new_session(self, mode: str = "general", backend: str = "gemini") -> str:
        """Create a new session and return its ID."""
        session_id = uuid.uuid4().hex[:16]
        now = int(time.time())
        with self._lock:
            conn = self._get_conn()
            conn.execute(
                "INSERT INTO sessions (id, start_ts, mode, backend) VALUES (?, ?, ?, ?)",
                (session_id, now, mode, backend),
            )
            conn.commit()
        return session_id

    def add_turn(
        self,
        session_id: str,
        role: str,
        content: str,
        tool_name: str | None = None,
        tool_args: dict | str | None = None,
        tool_result: str | None = None,
        backend: str | None = None,
        latency_ms: int | None = None,
    ) -> int:
        """Record a single turn (user message, assistant response, or tool call).

        Returns the turn row ID.
        """
        now = int(time.time())
        args_str: str | None = None
        if tool_args is not None:
            if isinstance(tool_args, dict):
                try:
                    args_str = json.dumps(tool_args, default=str)[:2000]
                except (TypeError, ValueError):
                    args_str = str(tool_args)[:2000]
            else:
                args_str = str(tool_args)[:2000]

        result_str = str(tool_result)[:5000] if tool_result is not None else None

        with self._lock:
            conn = self._get_conn()
            cur = conn.execute(
                """INSERT INTO turns
                   (session_id, ts, role, content, tool_name, tool_args, tool_result, backend, latency_ms)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (session_id, now, role, content[:10000], tool_name, args_str, result_str, backend, latency_ms),
            )
            conn.execute(
                "UPDATE sessions SET turn_count = turn_count + 1 WHERE id = ?",
                (session_id,),
            )
            conn.commit()
            return cur.lastrowid  # type: ignore[return-value]

    def close_session(self, session_id: str, summary: str | None = None) -> None:
        """Mark a session as ended, optionally with an AI-generated summary."""
        now = int(time.time())
        with self._lock:
            conn = self._get_conn()
            conn.execute(
                "UPDATE sessions SET end_ts = ?, summary = ? WHERE id = ?",
                (now, summary, session_id),
            )
            conn.commit()

    def tag_session(self, session_id: str, tag: str) -> None:
        """Add a tag to a session."""
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO tags (session_id, tag) VALUES (?, ?)",
                    (session_id, tag.lower().strip()),
                )
                conn.commit()
            except sqlite3.IntegrityError:
                pass

    # ── Queries ───────────────────────────────────────────────────────────

    def get_session(self, session_id: str) -> dict | None:
        """Return a full session dict with all its turns."""
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if row is None:
            return None

        session = dict(row)

        turns = conn.execute(
            "SELECT * FROM turns WHERE session_id = ? ORDER BY ts ASC",
            (session_id,),
        ).fetchall()
        session["turns"] = [dict(t) for t in turns]

        tags = conn.execute(
            "SELECT tag FROM tags WHERE session_id = ?",
            (session_id,),
        ).fetchall()
        session["tags"] = [t["tag"] for t in tags]

        return session

    def recent(self, n: int = 10) -> list[dict]:
        """Return the N most recent session summaries (no turns)."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM sessions ORDER BY start_ts DESC LIMIT ?",
            (n,),
        ).fetchall()
        return [dict(r) for r in rows]

    def search(self, query: str, limit: int = 20) -> list[dict]:
        """Full-text search across turn content. Falls back to LIKE if FTS5 unavailable."""
        conn = self._get_conn()

        # Try FTS5 first
        try:
            rows = conn.execute(
                """SELECT t.*, s.mode, s.backend AS session_backend, s.start_ts AS session_start
                   FROM turns_fts fts
                   JOIN turns t ON t.id = fts.rowid
                   JOIN sessions s ON s.id = t.session_id
                   WHERE turns_fts MATCH ?
                   ORDER BY fts.rank
                   LIMIT ?""",
                (query, limit),
            ).fetchall()
            return [dict(r) for r in rows]
        except sqlite3.OperationalError:
            pass

        # Fallback: LIKE search
        like_q = f"%{query}%"
        rows = conn.execute(
            """SELECT t.*, s.mode, s.backend AS session_backend, s.start_ts AS session_start
               FROM turns t
               JOIN sessions s ON s.id = t.session_id
               WHERE t.content LIKE ? OR t.tool_name LIKE ? OR t.tool_result LIKE ?
               ORDER BY t.ts DESC
               LIMIT ?""",
            (like_q, like_q, like_q, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def stats(self) -> dict[str, Any]:
        """Return aggregate statistics about the history database."""
        conn = self._get_conn()
        total_sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        total_turns = conn.execute("SELECT COUNT(*) FROM turns").fetchone()[0]
        tool_calls = conn.execute("SELECT COUNT(*) FROM turns WHERE tool_name IS NOT NULL").fetchone()[0]

        avg_row = conn.execute(
            "SELECT AVG(turn_count) FROM sessions WHERE turn_count > 0"
        ).fetchone()
        avg_turns = round(avg_row[0], 1) if avg_row[0] else 0

        backends_row = conn.execute(
            "SELECT backend, COUNT(*) as cnt FROM sessions GROUP BY backend ORDER BY cnt DESC"
        ).fetchall()
        backend_dist = {r["backend"]: r["cnt"] for r in backends_row}

        first_row = conn.execute("SELECT MIN(start_ts) FROM sessions").fetchone()
        last_row = conn.execute("SELECT MAX(start_ts) FROM sessions").fetchone()

        return {
            "total_sessions": total_sessions,
            "total_turns": total_turns,
            "tool_calls": tool_calls,
            "avg_turns_per_session": avg_turns,
            "backend_distribution": backend_dist,
            "first_session_ts": first_row[0],
            "last_session_ts": last_row[0],
            "db_path": str(self._db_path),
            "db_size_kb": round(self._db_path.stat().st_size / 1024, 1) if self._db_path.exists() else 0,
        }
