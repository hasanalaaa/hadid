"""Importer for Gemini activity exported via Google Takeout (MyActivity.json).

Note: Google Takeout includes your prompts and, when available, brief
response snippets in ``subtitles`` — not always the full model responses.
The activity log is archived as a single prompt-history conversation.
"""

from __future__ import annotations

from typing import Any, Iterator

from . import load_json_from_path, source_id_for


def parse_export(path: str) -> Iterator[dict[str, Any]]:
    """Yield normalized conversations from a Takeout export file or ZIP."""
    return parse_data(load_json_from_path(path))


def parse_data(data: Any) -> Iterator[dict[str, Any]]:
    """Yield normalized conversations from parsed Takeout activity data."""
    if not isinstance(data, list):
        raise ValueError("Unexpected Gemini export format: expected a JSON list")

    messages: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        title = item.get("title") or ""
        if not title.startswith("Prompted "):
            continue
        text = title[len("Prompted "):].strip()
        if not text:
            continue
        when = item.get("time")
        messages.append(
            {"role": "user", "content": text, "created_at": when,
             "_sort": (when or "") + "0"}
        )
        subtitles = item.get("subtitles") or []
        answer = "\n".join(
            s.get("name", "") for s in subtitles if isinstance(s, dict)
        ).strip()
        if answer:
            messages.append(
                {"role": "assistant", "content": answer, "created_at": when,
                 "_sort": (when or "") + "1"}
            )
    messages.sort(key=lambda m: m.pop("_sort"))

    title = "Gemini prompt history"
    created_at = messages[0]["created_at"] if messages else None
    source_id, generated = source_id_for(
        "gemini",
        None,
        title=title,
        created_at=created_at,
        messages=messages,
    )
    yield {
        "source": "gemini",
        "source_id": source_id,
        "title": title,
        "created_at": created_at,
        "messages": messages,
        "_source_id_generated": generated,
    }
