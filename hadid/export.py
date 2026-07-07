"""Export archived conversations to portable formats."""

from __future__ import annotations

import re

from .models import Conversation


def safe_filename(title: str | None, max_length: int = 60) -> str:
    """Turn a conversation title into a safe filename fragment."""
    name = re.sub(r"[^\w\s-]", "", title or "untitled").strip()
    name = re.sub(r"\s+", "-", name)
    return (name or "untitled")[:max_length]


def conversation_to_markdown(conv: Conversation) -> str:
    """Render a full conversation dict as a Markdown document."""
    lines = ["# " + (conv["title"] or "Untitled"), ""]
    lines.append("- **Source:** " + conv["source"])
    created_at = conv["created_at"]
    if created_at:
        lines.append("- **Created:** " + created_at)
    lines.append("")
    for m in conv.get("messages", []):
        who = "You" if m["role"] == "user" else "Assistant"
        lines.append("## " + who)
        message_created_at = m["created_at"]
        if message_created_at:
            lines.append("*" + message_created_at + "*")
        lines.append("")
        lines.append(m["content"])
        lines.append("")
    return "\n".join(lines)
