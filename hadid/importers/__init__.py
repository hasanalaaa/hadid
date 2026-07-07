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
