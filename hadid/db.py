"""SQLite storage with FTS5 full-text search for archived conversations."""

from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path
from types import TracebackType
from typing import Any

from .models import Conversation, Message, StoredConversation

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = str(Path.home() / ".hadid" / "hadid.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,
    source_id TEXT NOT NULL,
    title TEXT,
    created_at TEXT,
    favorite INTEGER NOT NULL DEFAULT 0,
    UNIQUE(source, source_id)
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_messages_conversation
    ON messages(conversation_id);
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    content, content='messages', content_rowid='id'
);
CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
END;
CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, content)
    VALUES ('delete', old.id, old.content);
END;
"""

# Applied on every connection. foreign_keys is OFF by default in SQLite,
# which silently disables ON DELETE CASCADE; WAL improves concurrency
# and crash safety for a local, single-writer workload.
_PRAGMAS = (
    "PRAGMA foreign_keys = ON",
    "PRAGMA journal_mode = WAL",
    "PRAGMA synchronous = NORMAL",
)


def _fts_query(query: str) -> str:
    """Quote each token so user input can never break FTS5 syntax."""
    tokens = [t for t in query.split() if t]
    return " ".join('"' + t.replace('"', '""') + '"' for t in tokens)


class Archive:
    """A local archive of AI conversations backed by SQLite.

    Prefer using it as a context manager::

        with Archive(path) as archive:
            archive.search("...")

    Set ``allow_threads=True`` when the instance is shared across threads;
    callers are then responsible for serializing access (e.g. with a lock).
    """

    def __init__(
        self, db_path: str = DEFAULT_DB_PATH, *, allow_threads: bool = False
    ) -> None:
        if db_path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=not allow_threads)
        self.conn.row_factory = sqlite3.Row
        for pragma in _PRAGMAS:
            try:
                self.conn.execute(pragma)
            except sqlite3.OperationalError:  # pragma: no cover - FS dependent
                logger.debug("pragma not applied: %s", pragma)
        self.conn.executescript(_SCHEMA)
        self._migrate()

    def __enter__(self) -> Archive:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def _migrate(self) -> None:
        """Upgrade archives created by older Hadid versions."""
        try:
            self.conn.execute(
                "ALTER TABLE conversations"
                " ADD COLUMN favorite INTEGER NOT NULL DEFAULT 0"
            )
            self.conn.commit()
            logger.info("migrated archive: added conversations.favorite")
        except sqlite3.OperationalError:
            pass  # column already exists

    def close(self) -> None:
        self.conn.close()

    def add_conversation(self, conv: Conversation) -> tuple[str, int] | None:
        """Insert or incrementally update one normalized conversation.

        Returns ``("added", n_messages)`` for a new conversation,
        ``("updated", n_new_messages)`` when new messages were merged into
        an existing one, or ``None`` when nothing changed.
        """
        incoming = conv["messages"]
        cur = self.conn.execute(
            "SELECT id FROM conversations WHERE source = ? AND source_id = ?",
            (conv["source"], conv["source_id"]),
        )
        row = cur.fetchone()
        if row is not None:
            conv_id = int(row["id"])
            cur = self.conn.execute(
                "SELECT COUNT(*) AS n FROM messages WHERE conversation_id = ?",
                (conv_id,),
            )
            existing = int(cur.fetchone()["n"])
            if len(incoming) <= existing:
                return None
            self.conn.execute(
                "DELETE FROM messages WHERE conversation_id = ?", (conv_id,)
            )
            self._insert_messages(conv_id, incoming)
            self.conn.commit()
            logger.info("updated conversation %s with new messages", conv_id)
            return ("updated", len(incoming) - existing)
        cur = self.conn.execute(
            "INSERT INTO conversations (source, source_id, title, created_at)"
            " VALUES (?, ?, ?, ?)",
            (
                conv["source"],
                conv["source_id"],
                conv.get("title"),
                conv.get("created_at"),
            ),
        )
        conv_id = int(cur.lastrowid or 0)
        self._insert_messages(conv_id, incoming)
        self.conn.commit()
        return ("added", len(incoming))

    def _insert_messages(
        self, conv_id: int, messages: list[Message]
    ) -> None:
        rows = [
            (conv_id, m["role"], m["content"], m.get("created_at"))
            for m in messages
        ]
        self.conn.executemany(
            "INSERT INTO messages (conversation_id, role, content, created_at)"
            " VALUES (?, ?, ?, ?)",
            rows,
        )

    def search(
        self, query: str, source: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Full-text search across all messages, best matches first."""
        fts = _fts_query(query)
        if not fts:
            return []
        sql = (
            "SELECT m.id AS message_id, m.conversation_id, c.title, c.source,"
            " m.role,"
            " snippet(messages_fts, 0, '\u00ab', '\u00bb', ' \u2026 ', 18) AS snippet"
            " FROM messages_fts"
            " JOIN messages m ON m.id = messages_fts.rowid"
            " JOIN conversations c ON c.id = m.conversation_id"
            " WHERE messages_fts MATCH ?"
        )
        params: list[Any] = [fts]
        if source:
            sql += " AND c.source = ?"
            params.append(source)
        sql += " ORDER BY rank LIMIT ?"
        params.append(limit)
        cur = self.conn.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]

    def list_conversations(
        self, source: str | None = None, favorites_only: bool = False
    ) -> list[dict[str, Any]]:
        where: list[str] = []
        params: list[Any] = []
        if source:
            where.append("c.source = ?")
            params.append(source)
        if favorites_only:
            where.append("c.favorite = 1")
        sql = (
            "SELECT c.id, c.source, c.title, c.created_at, c.favorite,"
            " COUNT(m.id) AS message_count"
            " FROM conversations c"
            " LEFT JOIN messages m ON m.conversation_id = c.id"
        )
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " GROUP BY c.id ORDER BY c.created_at DESC"
        cur = self.conn.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]

    def get_conversation(self, conv_id: int) -> StoredConversation | None:
        cur = self.conn.execute(
            "SELECT id, source, source_id, title, created_at, favorite"
            " FROM conversations WHERE id = ?",
            (conv_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        cur = self.conn.execute(
            "SELECT role, content, created_at FROM messages"
            " WHERE conversation_id = ? ORDER BY id",
            (conv_id,),
        )
        messages: list[Message] = [
            {
                "role": str(r["role"]),
                "content": str(r["content"]),
                "created_at": r["created_at"],
            }
            for r in cur.fetchall()
        ]
        return {
            "id": int(row["id"]),
            "source": str(row["source"]),
            "source_id": str(row["source_id"]),
            "title": str(row["title"] or "Untitled"),
            "created_at": row["created_at"],
            "favorite": int(row["favorite"]),
            "messages": messages,
        }

    def toggle_favorite(self, conv_id: int) -> int | None:
        """Toggle a conversation's favorite flag. Returns the new value
        (0 or 1), or None if the conversation does not exist."""
        cur = self.conn.execute(
            "SELECT favorite FROM conversations WHERE id = ?", (conv_id,)
        )
        row = cur.fetchone()
        if row is None:
            return None
        new_value = 0 if row["favorite"] else 1
        self.conn.execute(
            "UPDATE conversations SET favorite = ? WHERE id = ?",
            (new_value, conv_id),
        )
        self.conn.commit()
        return new_value

    def stats(self) -> dict[str, Any]:
        cur = self.conn.execute(
            "SELECT"
            " (SELECT COUNT(*) FROM conversations) AS conversations,"
            " (SELECT COUNT(*) FROM messages) AS messages,"
            " (SELECT COUNT(*) FROM conversations WHERE favorite = 1) AS favorites"
        )
        totals = dict(cur.fetchone())
        cur = self.conn.execute(
            "SELECT source, COUNT(*) AS n FROM conversations GROUP BY source"
        )
        totals["by_source"] = {r["source"]: r["n"] for r in cur.fetchall()}
        return totals

    def activity(self) -> list[dict[str, Any]]:
        """Message counts grouped by month, for the dashboard chart."""
        cur = self.conn.execute(
            "SELECT substr(created_at, 1, 7) AS month, COUNT(*) AS n"
            " FROM messages WHERE created_at IS NOT NULL"
            " GROUP BY month ORDER BY month"
        )
        return [dict(r) for r in cur.fetchall()]
