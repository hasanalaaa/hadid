"""Importer for ChatGPT data exports (conversations.json)."""

from __future__ import annotations

from typing import Any, Iterator

from ..models import ImportedConversation, Message, SortableMessage
from . import first_original_id, load_json_from_path, source_id_for, unix_to_iso


def parse_export(path: str) -> Iterator[ImportedConversation]:
    """Yield normalized conversations from a ChatGPT export file or ZIP."""
    return parse_data(load_json_from_path(path))


def parse_data(data: Any) -> Iterator[ImportedConversation]:
    """Yield normalized conversations from parsed ChatGPT export data."""
    if not isinstance(data, list):
        raise ValueError("Unexpected ChatGPT export format: expected a JSON list")

    for conv in data:
        mapping = conv.get("mapping") or {}
        messages: list[SortableMessage] = []
        for node in mapping.values():
            msg = (node or {}).get("message")
            if not msg:
                continue
            role = ((msg.get("author") or {}).get("role")) or ""
            if role not in ("user", "assistant"):
                continue
            content = msg.get("content") or {}
            parts = content.get("parts") or []
            text = "\n".join(p for p in parts if isinstance(p, str)).strip()
            if not text:
                continue
            messages.append(
                {
                    "role": role,
                    "content": text,
                    "created_at": unix_to_iso(msg.get("create_time")),
                    "_sort": msg.get("create_time") or 0,
                }
            )
        messages.sort(key=lambda m: m["_sort"])
        normalized_messages: list[Message] = [
            {
                "role": m["role"],
                "content": m["content"],
                "created_at": m["created_at"],
            }
            for m in messages
        ]
        title = conv.get("title") or "Untitled"
        created_at = unix_to_iso(conv.get("create_time"))
        source_id, generated = source_id_for(
            "chatgpt",
            first_original_id(conv.get("id"), conv.get("conversation_id")),
            title=title,
            created_at=created_at,
            messages=normalized_messages,
        )
        yield {
            "source": "chatgpt",
            "source_id": source_id,
            "title": title,
            "created_at": created_at,
            "messages": normalized_messages,
            "_source_id_generated": generated,
        }
