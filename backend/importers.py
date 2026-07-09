"""Importers: turn platform export files into normalized conversation dicts."""

from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Iterator

_KNOWN_FILES = ("conversations.json", "MyActivity.json")


def unix_to_iso(ts: Any) -> str | None:
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat()
    except (ValueError, OSError, OverflowError, TypeError):
        return None


def load_json_from_bytes(filename: str, content: bytes) -> Any:
    """Load JSON from raw bytes: plain JSON file or a platform export ZIP."""
    if filename.lower().endswith(".zip") or content[:4] == b"PK\x03\x04":
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            for name in z.namelist():
                if name.rsplit("/", 1)[-1] in _KNOWN_FILES:
                    with z.open(name) as f:
                        return json.loads(f.read().decode("utf-8"))
            for name in z.namelist():
                if name.lower().endswith(".json"):
                    with z.open(name) as f:
                        return json.loads(f.read().decode("utf-8"))
        raise ValueError("no JSON export found inside the ZIP")
    return json.loads(content.decode("utf-8"))


def message_hash(m: dict[str, Any]) -> str:
    raw = "\0".join([
        m.get("role") or "",
        m.get("content") or "",
        m.get("created_at") or "",
    ])
    return sha256(raw.encode("utf-8")).hexdigest()


def _first_id(*values: Any) -> Any | None:
    for value in values:
        if value is not None and str(value).strip():
            return value
    return None


def _source_id_for(source: str, original_id: Any, *, title: str | None,
                   created_at: str | None, messages: list) -> str:
    if original_id is not None and str(original_id).strip():
        return str(original_id)
    first_message: dict[str, Any] = {}
    for message in messages:
        if str(message.get("content") or "").strip():
            first_message = {
                "role": message.get("role"),
                "content": message.get("content"),
                "created_at": message.get("created_at"),
            }
            break
    identity = {"source": source, "title": title or "Untitled",
                "created_at": created_at, "first_message": first_message}
    raw = json.dumps(identity, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return f"generated-{source}-{sha256(raw.encode('utf-8')).hexdigest()}"


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
            if "thread" in item or item.get("query"):
                return "perplexity"
            if "messages" in item and "create_time" in item:
                return "deepseek"
            if item.get("role") in ("human", "assistant"):
                return "grok"
    if isinstance(data, dict):
        if "conversations" in data:
            inner = data["conversations"]
            if isinstance(inner, list) and inner:
                first = inner[0]
                if "thread" in first or first.get("query"):
                    return "perplexity"
                return "grok"
    raise ValueError("could not detect the export format; specify the platform explicitly")


def parse_chatgpt(data: Any) -> Iterator[dict[str, Any]]:
    if not isinstance(data, list):
        raise ValueError("Unexpected ChatGPT export format: expected a JSON list")
    for conv in data:
        mapping = conv.get("mapping") or {}
        messages: list[dict[str, Any]] = []
        for node in mapping.values():
            msg = (node or {}).get("message")
            if not msg:
                continue
            role = ((msg.get("author") or {}).get("role")) or ""
            if role not in ("user", "assistant"):
                continue
            parts = (msg.get("content") or {}).get("parts") or []
            text = "\n".join(p for p in parts if isinstance(p, str)).strip()
            if not text:
                continue
            messages.append({"role": role, "content": text,
                             "created_at": unix_to_iso(msg.get("create_time")),
                             "_sort": msg.get("create_time") or 0})
        messages.sort(key=lambda m: m["_sort"])
        normalized = [{"role": m["role"], "content": m["content"],
                       "created_at": m["created_at"]} for m in messages]
        title = conv.get("title") or "Untitled"
        created_at = unix_to_iso(conv.get("create_time"))
        yield {
            "source": "chatgpt",
            "source_id": _source_id_for("chatgpt",
                                        _first_id(conv.get("id"), conv.get("conversation_id")),
                                        title=title, created_at=created_at, messages=normalized),
            "title": title, "created_at": created_at, "messages": normalized,
        }


def _claude_text(m: dict[str, Any]) -> str:
    text = (m.get("text") or "").strip()
    if text:
        return text
    blocks = m.get("content") or []
    parts = [b.get("text", "") for b in blocks
             if isinstance(b, dict) and b.get("type") == "text"]
    return "\n".join(p for p in parts if p).strip()


def parse_claude(data: Any) -> Iterator[dict[str, Any]]:
    if not isinstance(data, list):
        raise ValueError("Unexpected Claude export format: expected a JSON list")
    for conv in data:
        messages = []
        for m in conv.get("chat_messages") or []:
            text = _claude_text(m)
            if not text:
                continue
            role = "user" if m.get("sender") == "human" else "assistant"
            messages.append({"role": role, "content": text, "created_at": m.get("created_at")})
        title = conv.get("name") or "Untitled"
        created_at = conv.get("created_at")
        yield {
            "source": "claude",
            "source_id": _source_id_for("claude", conv.get("uuid"), title=title,
                                        created_at=created_at, messages=messages),
            "title": title, "created_at": created_at, "messages": messages,
        }


def parse_gemini(data: Any) -> Iterator[dict[str, Any]]:
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
        messages.append({"role": "user", "content": text, "created_at": when,
                         "_sort": (when or "") + "0"})
        subtitles = item.get("subtitles") or []
        answer = "\n".join(s.get("name", "") for s in subtitles if isinstance(s, dict)).strip()
        if answer:
            messages.append({"role": "assistant", "content": answer, "created_at": when,
                             "_sort": (when or "") + "1"})
    messages.sort(key=lambda m: m["_sort"])
    normalized = [{"role": m["role"], "content": m["content"],
                   "created_at": m["created_at"]} for m in messages]
    title = "Gemini prompt history"
    created_at = normalized[0]["created_at"] if normalized else None
    yield {
        "source": "gemini",
        "source_id": _source_id_for("gemini", None, title=title,
                                    created_at=created_at, messages=normalized),
        "title": title, "created_at": created_at, "messages": normalized,
    }


def parse_deepseek(data: Any) -> Iterator[dict[str, Any]]:
    if not isinstance(data, list):
        raise ValueError("Unexpected DeepSeek export format: expected a JSON list")
    for conv in data:
        messages: list[dict[str, Any]] = []
        for msg in conv.get("messages") or []:
            role = (msg.get("role") or "").lower()
            if role not in ("user", "assistant"):
                continue
            content = msg.get("content") or ""
            if isinstance(content, list):
                text = "\n".join(
                    p.get("text", str(p)) if isinstance(p, dict) else str(p)
                    for p in content).strip()
            else:
                text = str(content).strip()
            if not text:
                continue
            ts = msg.get("created_at") or msg.get("create_time")
            messages.append({"role": role, "content": text,
                             "created_at": unix_to_iso(ts), "_sort": ts or 0})
        messages.sort(key=lambda m: m["_sort"])
        normalized = [{"role": m["role"], "content": m["content"],
                       "created_at": m["created_at"]} for m in messages]
        title = conv.get("title") or "Untitled"
        created_at = unix_to_iso(conv.get("create_time") or conv.get("created_at"))
        yield {
            "source": "deepseek",
            "source_id": _source_id_for("deepseek",
                                        _first_id(conv.get("id"), conv.get("conversation_id")),
                                        title=title, created_at=created_at, messages=normalized),
            "title": title, "created_at": created_at, "messages": normalized,
        }


def parse_grok(data: Any) -> Iterator[dict[str, Any]]:
    if isinstance(data, dict):
        convs = data.get("conversations", data.get("chats", []))
    elif isinstance(data, list):
        convs = data
    else:
        raise ValueError("Unexpected Grok export format: expected a JSON list or object")
    for conv in convs:
        messages = []
        raw_messages = []
        if isinstance(conv, dict):
            raw_messages = conv.get("messages") or conv.get("chat_messages") or []
        for msg in raw_messages:
            role_raw = (msg.get("role") or "").lower()
            role = "user" if role_raw in ("human", "user") else "assistant"
            text = (msg.get("content") or "").strip()
            if not text:
                continue
            messages.append({"role": role, "content": text,
                             "created_at": msg.get("created_at") or msg.get("timestamp")})
        title = conv.get("title") or conv.get("name") or "Untitled"
        created_at = conv.get("created_at") or conv.get("create_time")
        yield {
            "source": "grok",
            "source_id": _source_id_for("grok", conv.get("id"), title=title,
                                        created_at=created_at, messages=messages),
            "title": title, "created_at": created_at, "messages": messages,
        }


def parse_perplexity(data: Any) -> Iterator[dict[str, Any]]:
    convs = data if isinstance(data, list) else data.get("conversations", [])
    for conv in convs:
        thread = conv.get("thread") or conv.get("messages") or []
        messages = []
        for msg in thread:
            role = (msg.get("role") or "").lower()
            if role not in ("user", "assistant"):
                continue
            text = (msg.get("content") or "").strip()
            if not text:
                continue
            messages.append({"role": role, "content": text,
                             "created_at": msg.get("date_updated") or msg.get("timestamp")})
        title = conv.get("title") or conv.get("query", "") or "Untitled"
        created_at = conv.get("date_updated") or conv.get("created_at")
        yield {
            "source": "perplexity",
            "source_id": _source_id_for("perplexity", conv.get("id"), title=title,
                                        created_at=created_at, messages=messages),
            "title": title, "created_at": created_at, "messages": messages,
        }


IMPORTERS = {
    "chatgpt": parse_chatgpt,
    "claude": parse_claude,
    "gemini": parse_gemini,
    "deepseek": parse_deepseek,
    "grok": parse_grok,
    "perplexity": parse_perplexity,
}

PLATFORMS = sorted(IMPORTERS)
