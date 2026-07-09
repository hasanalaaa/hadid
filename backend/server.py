"""Hadid API — archive and search your AI conversations."""

from __future__ import annotations

import io
import json
import logging
import os
import re
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response, StreamingResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from starlette.middleware.cors import CORSMiddleware

from demo_data import DEMO_CONVERSATIONS
from export_utils import conversation_to_markdown, conversation_to_obsidian, safe_filename
from importers import IMPORTERS, PLATFORMS, detect_platform, load_json_from_bytes, message_hash
from tagger import suggest_tags

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="Hadid API")
api = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hadid")

MAX_UPLOAD_BYTES = 250 * 1024 * 1024


# ---------------------------------------------------------------- models

class TagBody(BaseModel):
    name: str = Field(min_length=1, max_length=50)


def conv_out(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": doc["_id"],
        "source": doc["source"],
        "source_id": doc["source_id"],
        "title": doc.get("title") or "Untitled",
        "created_at": doc.get("created_at"),
        "favorite": bool(doc.get("favorite")),
        "message_count": int(doc.get("message_count", 0)),
        "tags": doc.get("tags", []),
    }


# ---------------------------------------------------------------- storage

async def insert_messages(conv_id: str, source: str,
                          messages: list[dict[str, Any]], start_idx: int) -> None:
    if not messages:
        return
    docs = [
        {
            "_id": uuid4().hex,
            "conversation_id": conv_id,
            "source": source,
            "idx": start_idx + i,
            "role": m["role"],
            "content": m["content"],
            "created_at": m.get("created_at"),
            "content_hash": message_hash(m),
        }
        for i, m in enumerate(messages)
    ]
    await db.messages.insert_many(docs)


async def upsert_conversation(conv: dict[str, Any], auto_tag: bool = True) -> tuple[str, int]:
    """Insert or incrementally update one normalized conversation.

    Returns ("added"|"updated"|"skipped", n_new_messages).
    """
    incoming = conv["messages"]
    incoming_hashes = [message_hash(m) for m in incoming]
    existing = await db.conversations.find_one(
        {"source": conv["source"], "source_id": conv["source_id"]}
    )
    if existing is not None:
        cid = existing["_id"]
        stored = await db.messages.find(
            {"conversation_id": cid}, {"content_hash": 1}
        ).sort("idx", 1).to_list(None)
        stored_hashes = [s.get("content_hash") for s in stored]
        if stored_hashes == incoming_hashes:
            return ("skipped", 0)
        if (len(stored_hashes) < len(incoming_hashes)
                and incoming_hashes[: len(stored_hashes)] == stored_hashes):
            new_messages = incoming[len(stored_hashes):]
            await insert_messages(cid, conv["source"], new_messages, len(stored_hashes))
            await db.conversations.update_one(
                {"_id": cid}, {"$inc": {"message_count": len(new_messages)}}
            )
            return ("updated", len(new_messages))
        await db.messages.delete_many({"conversation_id": cid})
        await insert_messages(cid, conv["source"], incoming, 0)
        await db.conversations.update_one(
            {"_id": cid},
            {"$set": {"message_count": len(incoming), "title": conv.get("title"),
                      "created_at": conv.get("created_at")}},
        )
        return ("updated", max(0, len(incoming) - len(stored_hashes)))

    cid = uuid4().hex
    tags = suggest_tags(conv) if auto_tag else []
    await db.conversations.insert_one({
        "_id": cid,
        "source": conv["source"],
        "source_id": conv["source_id"],
        "title": conv.get("title") or "Untitled",
        "created_at": conv.get("created_at"),
        "favorite": False,
        "message_count": len(incoming),
        "tags": tags,
        "imported_at": datetime.now(timezone.utc).isoformat(),
    })
    await insert_messages(cid, conv["source"], incoming, 0)
    return ("added", len(incoming))


async def run_import(conversations: Any, auto_tag: bool) -> dict[str, Any]:
    added = updated = skipped = messages = 0
    for conv in conversations:
        if not conv["messages"]:
            skipped += 1
            continue
        result, n = await upsert_conversation(conv, auto_tag=auto_tag)
        if result == "added":
            added += 1
            messages += n
        elif result == "updated":
            updated += 1
            messages += n
        else:
            skipped += 1
    return {"added": added, "updated": updated, "skipped": skipped, "messages": messages}


# ---------------------------------------------------------------- import

@api.get("/")
async def root() -> dict[str, Any]:
    return {"app": "hadid", "version": "2.0.0", "platforms": PLATFORMS}


@api.post("/import")
async def import_export(
    file: UploadFile = File(...),
    platform: str = Form("auto"),
    auto_tag: str = Form("1"),
) -> dict[str, Any]:
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "file too large (max 250MB)")
    if not content:
        raise HTTPException(400, "empty file")
    try:
        data = load_json_from_bytes(file.filename or "export.json", content)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(400, "invalid JSON file")
    except (zipfile.BadZipFile, ValueError) as e:
        raise HTTPException(400, str(e))
    if platform == "auto":
        try:
            platform = detect_platform(data)
        except ValueError as e:
            raise HTTPException(400, str(e))
    if platform not in IMPORTERS:
        raise HTTPException(400, f"unknown platform: {platform}")
    try:
        result = await run_import(IMPORTERS[platform](data), auto_tag == "1")
    except ValueError as e:
        raise HTTPException(400, str(e))
    result["platform"] = platform
    return result


@api.post("/demo")
async def load_demo() -> dict[str, Any]:
    result = await run_import(iter(DEMO_CONVERSATIONS), True)
    result["platform"] = "demo"
    return result


# ---------------------------------------------------------------- conversations

@api.get("/conversations")
async def list_conversations(
    source: str | None = None,
    favorites: bool = False,
    tag: str | None = None,
    q: str | None = None,
    limit: int = Query(30, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    query: dict[str, Any] = {}
    if source:
        query["source"] = source
    if favorites:
        query["favorite"] = True
    if tag:
        query["tags"] = tag
    if q and q.strip():
        query["title"] = {"$regex": re.escape(q.strip()), "$options": "i"}
    total = await db.conversations.count_documents(query)
    docs = await db.conversations.find(query).sort(
        [("created_at", -1)]
    ).skip(offset).limit(limit).to_list(limit)
    return {"items": [conv_out(d) for d in docs], "total": total}


@api.get("/conversations/{cid}")
async def get_conversation(cid: str) -> dict[str, Any]:
    doc = await db.conversations.find_one({"_id": cid})
    if doc is None:
        raise HTTPException(404, "conversation not found")
    msgs = await db.messages.find(
        {"conversation_id": cid}, {"role": 1, "content": 1, "created_at": 1}
    ).sort("idx", 1).to_list(None)
    out = conv_out(doc)
    out["messages"] = [
        {"role": m["role"], "content": m["content"], "created_at": m.get("created_at")}
        for m in msgs
    ]
    return out


@api.post("/conversations/{cid}/favorite")
async def toggle_favorite(cid: str) -> dict[str, Any]:
    doc = await db.conversations.find_one({"_id": cid}, {"favorite": 1})
    if doc is None:
        raise HTTPException(404, "conversation not found")
    new_value = not bool(doc.get("favorite"))
    await db.conversations.update_one({"_id": cid}, {"$set": {"favorite": new_value}})
    return {"favorite": new_value}


@api.delete("/conversations/{cid}")
async def delete_conversation(cid: str) -> dict[str, Any]:
    result = await db.conversations.delete_one({"_id": cid})
    if result.deleted_count == 0:
        raise HTTPException(404, "conversation not found")
    await db.messages.delete_many({"conversation_id": cid})
    return {"ok": True}


@api.post("/conversations/{cid}/tags")
async def add_tag(cid: str, body: TagBody) -> dict[str, Any]:
    result = await db.conversations.update_one(
        {"_id": cid}, {"$addToSet": {"tags": body.name.strip()}}
    )
    if result.matched_count == 0:
        raise HTTPException(404, "conversation not found")
    return {"ok": True}


@api.delete("/conversations/{cid}/tags/{tag_name}")
async def remove_tag(cid: str, tag_name: str) -> dict[str, Any]:
    result = await db.conversations.update_one(
        {"_id": cid}, {"$pull": {"tags": tag_name}}
    )
    if result.matched_count == 0:
        raise HTTPException(404, "conversation not found")
    return {"ok": True}


@api.get("/tags")
async def list_tags() -> list[dict[str, Any]]:
    pipeline = [
        {"$unwind": "$tags"},
        {"$group": {"_id": "$tags", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    rows = await db.conversations.aggregate(pipeline).to_list(None)
    return [{"name": r["_id"], "count": r["count"]} for r in rows]


@api.post("/autotag")
async def autotag_all() -> dict[str, Any]:
    tagged = 0
    async for conv in db.conversations.find({}, {"_id": 1}):
        cid = conv["_id"]
        msgs = await db.messages.find(
            {"conversation_id": cid}, {"content": 1}
        ).to_list(None)
        tags = suggest_tags({"messages": [{"content": m.get("content", "")} for m in msgs]})
        if tags:
            await db.conversations.update_one(
                {"_id": cid}, {"$addToSet": {"tags": {"$each": tags}}}
            )
            tagged += 1
    return {"tagged": tagged}


# ---------------------------------------------------------------- search

def make_snippet(content: str, tokens: list[str], width: int = 200) -> str:
    low = content.lower()
    pos = -1
    for t in tokens:
        p = low.find(t.lower())
        if p != -1 and (pos == -1 or p < pos):
            pos = p
    if pos == -1:
        pos = 0
    start = max(0, pos - 60)
    end = min(len(content), start + width)
    snippet = content[start:end]
    for t in sorted(set(tokens), key=len, reverse=True):
        if not t:
            continue
        snippet = re.sub(
            re.escape(t), lambda m: f"\u00ab{m.group(0)}\u00bb", snippet, flags=re.IGNORECASE
        )
    prefix = "\u2026 " if start > 0 else ""
    suffix = " \u2026" if end < len(content) else ""
    return prefix + snippet.replace("\n", " ") + suffix


@api.get("/search")
async def search(
    q: str = Query(..., min_length=1),
    source: str | None = None,
    tag: str | None = None,
    limit: int = Query(30, ge=1, le=100),
) -> list[dict[str, Any]]:
    tokens = [t for t in q.strip().split() if t]
    if not tokens:
        return []
    base: dict[str, Any] = {}
    if source:
        base["source"] = source
    if tag:
        tagged = await db.conversations.find({"tags": tag}, {"_id": 1}).to_list(None)
        base["conversation_id"] = {"$in": [d["_id"] for d in tagged]}

    text_query = " ".join(f'"{t}"' for t in tokens)
    docs = await db.messages.find(
        {"$text": {"$search": text_query}, **base},
        {"score": {"$meta": "textScore"}, "conversation_id": 1, "role": 1, "content": 1},
    ).sort([("score", {"$meta": "textScore"})]).limit(limit).to_list(limit)

    if not docs:
        pattern = re.escape(q.strip())
        docs = await db.messages.find(
            {"content": {"$regex": pattern, "$options": "i"}, **base},
            {"conversation_id": 1, "role": 1, "content": 1},
        ).limit(limit).to_list(limit)

    conv_ids = list({d["conversation_id"] for d in docs})
    convs = await db.conversations.find(
        {"_id": {"$in": conv_ids}}, {"title": 1, "source": 1, "favorite": 1}
    ).to_list(None)
    conv_map = {c["_id"]: c for c in convs}
    results = []
    for d in docs:
        c = conv_map.get(d["conversation_id"])
        if c is None:
            continue
        results.append({
            "message_id": d["_id"],
            "conversation_id": d["conversation_id"],
            "title": c.get("title") or "Untitled",
            "source": c["source"],
            "role": d["role"],
            "snippet": make_snippet(d["content"], tokens),
        })
    return results


# ---------------------------------------------------------------- stats

@api.get("/stats")
async def stats() -> dict[str, Any]:
    conversations = await db.conversations.count_documents({})
    messages = await db.messages.count_documents({})
    favorites = await db.conversations.count_documents({"favorite": True})
    tag_rows = await db.conversations.aggregate([
        {"$unwind": "$tags"}, {"$group": {"_id": "$tags"}}, {"$count": "n"}
    ]).to_list(1)
    by_source_rows = await db.conversations.aggregate([
        {"$group": {"_id": "$source", "n": {"$sum": 1}}}
    ]).to_list(None)
    msg_stats_rows = await db.messages.aggregate([
        {"$project": {"len": {"$strLenCP": "$content"}}},
        {"$group": {"_id": None, "avg": {"$avg": "$len"}, "max": {"$max": "$len"}}},
    ]).to_list(1)
    date_rows = await db.conversations.aggregate([
        {"$match": {"created_at": {"$ne": None}}},
        {"$group": {"_id": None, "oldest": {"$min": "$created_at"},
                    "newest": {"$max": "$created_at"}}},
    ]).to_list(1)
    msg_stats = msg_stats_rows[0] if msg_stats_rows else {}
    dates = date_rows[0] if date_rows else {}
    return {
        "conversations": conversations,
        "messages": messages,
        "favorites": favorites,
        "tags": tag_rows[0]["n"] if tag_rows else 0,
        "by_source": {r["_id"]: r["n"] for r in by_source_rows},
        "avg_message_chars": int(msg_stats.get("avg") or 0),
        "max_message_chars": int(msg_stats.get("max") or 0),
        "oldest": dates.get("oldest"),
        "newest": dates.get("newest"),
    }


@api.get("/activity")
async def activity() -> list[dict[str, Any]]:
    rows = await db.messages.aggregate([
        {"$match": {"created_at": {"$type": "string"}}},
        {"$group": {"_id": {"$substrCP": ["$created_at", 0, 7]}, "n": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]).to_list(None)
    return [{"month": r["_id"], "n": r["n"]} for r in rows]


_STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "have",
    "has", "had", "do", "does", "did", "will", "would", "could", "should", "may",
    "might", "can", "shall", "to", "of", "in", "for", "on", "with", "at", "by",
    "from", "as", "into", "through", "during", "before", "after", "above", "below",
    "between", "out", "off", "over", "under", "again", "further", "then", "once",
    "here", "there", "when", "where", "why", "how", "all", "each", "every", "both",
    "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only",
    "own", "same", "so", "than", "too", "very", "just", "because", "about", "up",
    "it", "its", "this", "that", "these", "those", "i", "me", "my", "we", "our",
    "you", "your", "he", "him", "his", "she", "her", "they", "them", "their",
    "what", "which", "who", "but", "and", "or", "if", "while", "also", "well",
    "use", "using", "like", "one", "two", "new", "get", "make",
    "على", "من", "في", "إلى", "الى", "عن", "مع", "هذا", "هذه", "ذلك", "التي",
    "الذي", "أن", "ان", "لا", "ما", "هو", "هي", "كان", "كانت", "يكون", "لكن",
    "ثم", "قد", "كل", "بعد", "قبل", "عند", "حتى", "إذا", "اذا", "أو", "او",
    "بين", "منها", "منه", "فيها", "فيه", "لها", "له", "وهي", "وهو", "شنو",
    "شلون", "يعني", "مثل", "أكثر", "اكثر", "بعض", "غير", "أفضل", "افضل",
}


@api.get("/wordcloud")
async def wordcloud(limit: int = Query(60, ge=1, le=300)) -> list[dict[str, Any]]:
    counter: Counter = Counter()
    cursor = db.messages.find({}, {"content": 1}).limit(20000)
    async for row in cursor:
        words = re.findall(r"[a-zA-Z\u0600-\u06FF]{3,}", (row.get("content") or "").lower())
        for w in words:
            if w not in _STOP_WORDS:
                counter[w] += 1
    return [{"word": w, "count": c} for w, c in counter.most_common(limit)]


# ---------------------------------------------------------------- export

@api.get("/export/conversation/{cid}")
async def export_conversation(cid: str, format: str = "markdown") -> Response:
    conv = await get_conversation(cid)
    renderer = conversation_to_obsidian if format == "obsidian" else conversation_to_markdown
    rendered = renderer(conv)
    filename = f"{safe_filename(conv['title'])}.md"
    return Response(
        content=rendered.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@api.get("/export/all")
async def export_all() -> StreamingResponse:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        docs = await db.conversations.find({}).sort([("created_at", -1)]).to_list(None)
        for i, doc in enumerate(docs):
            msgs = await db.messages.find(
                {"conversation_id": doc["_id"]},
                {"role": 1, "content": 1, "created_at": 1},
            ).sort("idx", 1).to_list(None)
            conv = conv_out(doc)
            conv["messages"] = msgs
            name = f"{i + 1:04d}-{safe_filename(conv['title'])}.md"
            z.writestr(name, conversation_to_markdown(conv))
    buf.seek(0)
    return StreamingResponse(
        buf, media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="hadid-export.zip"'},
    )


@api.get("/export/archive")
async def export_archive() -> Response:
    docs = await db.conversations.find({}).sort([("created_at", -1)]).to_list(None)
    result = []
    for doc in docs:
        msgs = await db.messages.find(
            {"conversation_id": doc["_id"]},
            {"role": 1, "content": 1, "created_at": 1},
        ).sort("idx", 1).to_list(None)
        result.append({
            "source": doc["source"],
            "source_id": doc["source_id"],
            "title": doc.get("title"),
            "created_at": doc.get("created_at"),
            "favorite": bool(doc.get("favorite")),
            "tags": doc.get("tags", []),
            "messages": [
                {"role": m["role"], "content": m["content"], "created_at": m.get("created_at")}
                for m in msgs
            ],
        })
    body = json.dumps(result, ensure_ascii=False, indent=2)
    return Response(
        content=body.encode("utf-8"),
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="hadid-archive.json"'},
    )


@api.post("/import/archive")
async def import_archive(file: UploadFile = File(...)) -> dict[str, Any]:
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "file too large (max 250MB)")
    try:
        data = json.loads(content.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(400, "invalid JSON file")
    if not isinstance(data, list):
        raise HTTPException(400, "expected a JSON list of conversations")
    added = skipped = 0
    for item in data:
        if not isinstance(item, dict) or not item.get("messages"):
            skipped += 1
            continue
        conv = {
            "source": item.get("source", "unknown"),
            "source_id": item.get("source_id") or uuid4().hex,
            "title": item.get("title") or "Untitled",
            "created_at": item.get("created_at"),
            "messages": [
                {"role": m.get("role", "user"), "content": m.get("content", ""),
                 "created_at": m.get("created_at")}
                for m in item["messages"] if m.get("content")
            ],
        }
        result, _ = await upsert_conversation(conv, auto_tag=False)
        if result == "skipped":
            skipped += 1
            continue
        added += 1
        updates: dict[str, Any] = {}
        if item.get("favorite"):
            updates["favorite"] = True
        if item.get("tags"):
            updates["tags"] = list(item["tags"])
        if updates:
            await db.conversations.update_one(
                {"source": conv["source"], "source_id": conv["source_id"]},
                {"$set": updates},
            )
    return {"added": added, "skipped": skipped}


@api.delete("/archive")
async def clear_archive() -> dict[str, Any]:
    r1 = await db.conversations.delete_many({})
    r2 = await db.messages.delete_many({})
    return {"conversations_deleted": r1.deleted_count, "messages_deleted": r2.deleted_count}


# ---------------------------------------------------------------- app setup

app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def ensure_indexes() -> None:
    await db.conversations.create_index([("source", 1), ("source_id", 1)], unique=True)
    await db.conversations.create_index([("created_at", -1)])
    await db.conversations.create_index([("tags", 1)])
    await db.messages.create_index([("conversation_id", 1), ("idx", 1)])
    await db.messages.create_index([("content", "text")], default_language="none")


@app.on_event("shutdown")
async def shutdown_db_client() -> None:
    client.close()
