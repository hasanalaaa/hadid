"""SQLite storage with FTS5 full-text search for archived conversations."""

from __future__ import annotations

import logging
import os
import sqlite3
from hashlib import sha256
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
    message_count INTEGER NOT NULL DEFAULT 0,
    UNIQUE(source, source_id)
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT,
    content_hash TEXT
);
CREATE INDEX IF NOT EXISTS idx_messages_conversation
    ON messages(conversation_id);
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    content, content='messages', content_rowid='id'
);
CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
    UPDATE conversations SET message_count = message_count + 1
        WHERE id = new.conversation_id;
END;
CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, content)
    VALUES ('delete', old.id, old.content);
    UPDATE conversations SET message_count = message_count - 1
        WHERE id = old.conversation_id;
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


def _message_hash(m: Message) -> str:
    """Deterministic hash for a single message's content.

    Uses null-byte separators to prevent field-boundary collisions.
    """
    raw = "\0".join([
        m.get("role") or "",
        m.get("content") or "",
        m.get("created_at") or "",
    ])
    return sha256(raw.encode("utf-8")).hexdigest()


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

        try:
            self.conn.execute(
                "ALTER TABLE conversations"
                " ADD COLUMN message_count INTEGER NOT NULL DEFAULT 0"
            )
            # Backfill from existing data
            self.conn.execute(
                "UPDATE conversations SET message_count ="
                " (SELECT COUNT(*) FROM messages"
                "  WHERE messages.conversation_id = conversations.id)"
            )
            self.conn.commit()
            logger.info("migrated archive: added conversations.message_count")
        except sqlite3.OperationalError:
            pass  # column already exists

        try:
            self.conn.execute(
                "ALTER TABLE messages ADD COLUMN content_hash TEXT"
            )
            self.conn.commit()
            logger.info("migrated archive: added messages.content_hash")
        except sqlite3.OperationalError:
            pass  # column already exists

    def close(self) -> None:
        self.conn.close()

    def add_conversation(self, conv: Conversation) -> tuple[str, int] | None:
        """Insert or incrementally update one normalized conversation.

        Returns ``("added", n_messages)`` for a new conversation,
        ``("updated", n_new_messages)`` when new messages were merged into
        an existing one, or ``None`` when nothing changed.

        Uses content hashing to detect changes more accurately than
        count-based comparison alone:
        - Identical hash sets → skip (even if ordering changed)
        - All stored hashes are a prefix of incoming → append only new
        - Otherwise → full re-insert (content diverged)
        """
        incoming = conv["messages"]
        incoming_hashes = [_message_hash(m) for m in incoming]
        cur = self.conn.execute(
            "SELECT id, message_count FROM conversations"
            " WHERE source = ? AND source_id = ?",
            (conv["source"], conv["source_id"]),
        )
        row = cur.fetchone()
        if row is not None:
            conv_id = int(row["id"])
            existing_count = int(row["message_count"])

            # Fetch stored hashes in insertion order
            cur = self.conn.execute(
                "SELECT content_hash FROM messages"
                " WHERE conversation_id = ? ORDER BY id",
                (conv_id,),
            )
            stored_hashes = [r["content_hash"] for r in cur.fetchall()]

            # Fast path: identical hash sequences → nothing changed
            if stored_hashes == incoming_hashes:
                return None

            # Check if stored hashes lack content_hash (pre-migration data)
            # or if stored is a prefix of incoming (append-only case)
            has_hashes = all(h is not None for h in stored_hashes)
            if (
                has_hashes
                and len(stored_hashes) < len(incoming_hashes)
                and incoming_hashes[:len(stored_hashes)] == stored_hashes
            ):
                # Append only the truly new messages
                new_messages = incoming[len(stored_hashes):]
                self._insert_messages(conv_id, new_messages)
                self.conn.commit()
                n_new = len(new_messages)
                logger.info(
                    "appended %d message(s) to conversation %s", n_new, conv_id
                )
                return ("updated", n_new)

            # Fallback: content diverged or legacy data without hashes —
            # delete all and re-insert.  Also covers len(incoming) <= existing
            # when content actually changed.
            if len(incoming) <= existing_count and has_hashes:
                # Fewer or equal messages but different hashes: content changed
                pass  # fall through to delete + re-insert
            elif len(incoming) <= existing_count:
                # Legacy path (no hashes): same count-based skip as before
                return None

            self.conn.execute(
                "DELETE FROM messages WHERE conversation_id = ?", (conv_id,)
            )
            self._insert_messages(conv_id, incoming)
            self.conn.commit()
            logger.info("updated conversation %s with new messages", conv_id)
            return ("updated", len(incoming) - existing_count)
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
            (
                conv_id,
                m["role"],
                m["content"],
                m.get("created_at"),
                _message_hash(m),
            )
            for m in messages
        ]
        self.conn.executemany(
            "INSERT INTO messages"
            " (conversation_id, role, content, created_at, content_hash)"
            " VALUES (?, ?, ?, ?, ?)",
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
        self,
        source: str | None = None,
        favorites_only: bool = False,
        limit: int = 0,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List conversations using the denormalized message_count column.

        Pass ``limit > 0`` for pagination.  ``limit=0`` (default) returns all.
        """
        where: list[str] = []
        params: list[Any] = []
        if source:
            where.append("source = ?")
            params.append(source)
        if favorites_only:
            where.append("favorite = 1")
        sql = (
            "SELECT id, source, title, created_at, favorite, message_count"
            " FROM conversations"
        )
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY created_at DESC"
        if limit > 0:
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
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
