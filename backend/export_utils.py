"""Export conversations to portable formats."""

from __future__ import annotations

import re
from typing import Any


def safe_filename(title: str | None, max_length: int = 60) -> str:
    name = re.sub(r"[^\w\s-]", "", title or "untitled", flags=re.UNICODE).strip()
    name = re.sub(r"\s+", "-", name)
    return (name or "untitled")[:max_length]


def conversation_to_markdown(conv: dict[str, Any]) -> str:
    lines = ["# " + (conv.get("title") or "Untitled"), ""]
    lines.append("- **Source:** " + conv["source"])
    if conv.get("created_at"):
        lines.append("- **Created:** " + conv["created_at"])
    lines.append("")
    for m in conv.get("messages", []):
        who = "You" if m["role"] == "user" else "Assistant"
        lines.append("## " + who)
        if m.get("created_at"):
            lines.append("*" + m["created_at"] + "*")
        lines.append("")
        lines.append(m["content"])
        lines.append("")
    return "\n".join(lines)


def conversation_to_obsidian(conv: dict[str, Any]) -> str:
    title = conv.get("title") or "Untitled"
    lines = ["---", f'title: "{title}"', f"source: {conv['source']}",
             f"tags: {['archive', conv['source']] + list(conv.get('tags', []))}"]
    if conv.get("created_at"):
        lines.append(f"created: {conv['created_at']}")
    lines.append(f"favorite: {bool(conv.get('favorite'))}")
    lines.extend(["---", "", f"# {title}", ""])
    for m in conv.get("messages", []):
        who = "You" if m["role"] == "user" else "Assistant"
        ts = m.get("created_at")
        lines.append(f"## {who}{f' *({ts})*' if ts else ''}")
        lines.append("")
        lines.append(m["content"])
        lines.append("")
    return "\n".join(lines)
