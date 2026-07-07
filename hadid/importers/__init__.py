"""Importers turn platform export files into normalized conversation dicts.

Each importer module exposes:

- ``parse_data(data)``: yield conversations from already-parsed JSON data
- ``parse_export(path)``: same, reading a JSON file or an export ZIP

Conversation shape::

    {
      "source": "chatgpt",
      "source_id": "<stable unique id>",
      "title": "...",
      "created_at": "ISO-8601 or None",
      "messages": [{"role": "user|assistant", "content": "...", "created_at": ...}],
    }
"""

from __future__ import annotations

import json
import logging
import zipfile
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

logger = logging.getLogger(__name__)

_KNOWN_FILES = ("conversations.json", "MyActivity.json")


def unix_to_iso(ts: float | int | None) -> str | None:
    """Convert a unix timestamp to an ISO-8601 UTC string."""
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat()
    except (ValueError, OSError, OverflowError):
        return None


def load_json_from_path(path: str) -> Any:
    """Load JSON from a plain file or from inside a platform export ZIP."""
    if str(path).lower().endswith(".zip"):
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                if name.rsplit("/", 1)[-1] in _KNOWN_FILES:
                    logger.info("reading %s from %s", name, path)
                    with z.open(name) as f:
                        return json.loads(f.read().decode("utf-8"))
        raise ValueError(
            "no conversations.json or MyActivity.json found inside the ZIP"
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def first_original_id(*values: Any) -> Any | None:
    """Return the first non-empty platform-provided id value."""
    for value in values:
        if value is not None and str(value).strip():
            return value
    return None


def source_id_for(
    source: str,
    original_id: Any | None,
    *,
    title: str | None,
    created_at: str | None,
    messages: list[dict[str, Any]],
) -> tuple[str, bool]:
    """Return a stable source id and whether it had to be generated.

    Platform ids are preserved exactly. When an export omits the original
    conversation id, build a deterministic id from fields that should stay
    stable across incremental re-imports.
    """
    if original_id is not None and str(original_id).strip():
        return str(original_id), False

    first_message: dict[str, Any] = {}
    for message in messages:
        if str(message.get("content") or "").strip():
            first_message = {
                "role": message.get("role"),
                "content": message.get("content"),
                "created_at": message.get("created_at"),
            }
            break

    identity = {
        "source": source,
        "title": title or "Untitled",
        "created_at": created_at,
        "first_message": first_message,
    }
    raw = json.dumps(identity, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    digest = sha256(raw.encode("utf-8")).hexdigest()
    return f"generated-{source}-{digest}", True


def detect_platform(data: Any) -> str:
    """Best-effort detection of which platform produced an export."""
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            if "mapping" in item:
                return "chatgpt"
            if "chat_messages" in item:
                return "claude"
            if "title" in item and "time" in item:
                return "gemini"
    raise ValueError(
        "could not detect the export format; specify the platform explicitly"
    )
