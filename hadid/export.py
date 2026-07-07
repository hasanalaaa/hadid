"""Export archived conversations to portable formats."""

from __future__ import annotations

import re
from typing import Any


def safe_filename(title: str | None, max_length: int = 60) -> str:
    """Turn a conversation title into a safe filename fragment."""
    name = re.sub(r"[^\w\s-]", "", title or "untitled").strip()
    name = re.sub(r"\s+", "-", name)
    return (name or "untitled")[:max_length]


def conversation_to_markdown(conv: dict[str, Any]) -> str:
    """Render a full conversation dict as a Markdown document."""
    lines = ["# " + (conv.get("title") or "Untitled"), ""]
    lines.append("- **Source:** " + str(conv.get("source", "unknown")))
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
