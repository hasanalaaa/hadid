"""Importer for Claude data exports (conversations.json)."""

from __future__ import annotations

from typing import Any, Iterator

from ..models import ImportedConversation, Message
from . import load_json_from_path, source_id_for


def _message_text(m: dict[str, Any]) -> str:
    text = (m.get("text") or "").strip()
    if text:
        return text
    blocks = m.get("content") or []
    parts = [
        b.get("text", "")
        for b in blocks
        if isinstance(b, dict) and b.get("type") == "text"
    ]
    return "\n".join(p for p in parts if p).strip()


def parse_export(path: str) -> Iterator[ImportedConversation]:
    """Yield normalized conversations from a Claude export file or ZIP."""
    return parse_data(load_json_from_path(path))


def parse_data(data: Any) -> Iterator[ImportedConversation]:
    """Yield normalized conversations from parsed Claude export data."""
    if not isinstance(data, list):
        raise ValueError("Unexpected Claude export format: expected a JSON list")

    for conv in data:
        messages: list[Message] = []
        for m in conv.get("chat_messages") or []:
            text = _message_text(m)
            if not text:
                continue
            role = "user" if m.get("sender") == "human" else "assistant"
            messages.append(
                {"role": role, "content": text, "created_at": m.get("created_at")}
            )
        title = conv.get("name") or "Untitled"
        created_at = conv.get("created_at")
        source_id, generated = source_id_for(
            "claude",
            conv.get("uuid"),
            title=title,
            created_at=created_at,
            messages=messages,
        )
        yield {
            "source": "claude",
            "source_id": source_id,
            "title": title,
            "created_at": created_at,
            "messages": messages,
            "_source_id_generated": generated,
        }
