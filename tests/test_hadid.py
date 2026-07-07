"""Tests for importers, storage, search, favorites, merge, and export."""

import json
import zipfile

from hadid.cli import main
from hadid.db import Archive
from hadid.export import conversation_to_markdown, safe_filename
from hadid.importers import (
    chatgpt,
    claude,
    detect_platform,
    gemini,
    load_json_from_path,
)

CHATGPT_SAMPLE = [
    {
        "id": "conv-1",
        "title": "Vector databases",
        "create_time": 1735689600,
        "mapping": {
            "root": {"message": None, "parent": None, "children": ["n1"]},
            "n1": {
                "message": {
                    "author": {"role": "user"},
                    "create_time": 1735689601,
                    "content": {"content_type": "text",
                                "parts": ["What is a vector database?"]},
                },
                "parent": "root",
                "children": ["n2"],
            },
            "n2": {
                "message": {
                    "author": {"role": "assistant"},
                    "create_time": 1735689610,
                    "content": {"content_type": "text",
                                "parts": ["A vector database stores embeddings."]},
                },
                "parent": "n1",
                "children": [],
            },
        },
    }
]

CLAUDE_SAMPLE = [
    {
        "uuid": "abc-123",
        "name": "Trip planning",
        "created_at": "2025-06-01T10:00:00Z",
        "chat_messages": [
            {"sender": "human", "text": "Plan a trip to Japan",
             "created_at": "2025-06-01T10:00:01Z"},
            {"sender": "assistant", "text": "",
             "content": [{"type": "text", "text": "Start with Tokyo and Kyoto."}],
             "created_at": "2025-06-01T10:00:05Z"},
        ],
    }
]

GEMINI_SAMPLE = [
    {
        "title": "Prompted How do black holes form?",
        "time": "2025-05-01T09:00:00Z",
        "subtitles": [{"name": "Black holes form when massive stars collapse."}],
    },
    {"title": "Visited some page", "time": "2025-05-01T09:05:00Z"},
]


def _write(tmp_path, name, data):
    p = tmp_path / name
    p.write_text(json.dumps(data), encoding="utf-8")
    return str(p)


def _conv(source, sid, title, text):
    return {
        "source": source,
        "source_id": sid,
        "title": title,
        "created_at": "2025-01-01T00:00:00Z",
        "messages": [
            {"role": "user", "content": text,
             "created_at": "2025-01-01T00:00:00Z"},
        ],
    }


def _chatgpt_missing_id(title, text, ts=1735689600):
    return {
        "title": title,
        "create_time": ts,
        "mapping": {
            "root": {"message": None, "parent": None, "children": ["n1"]},
            "n1": {
                "message": {
                    "author": {"role": "user"},
                    "create_time": ts + 1,
                    "content": {"content_type": "text", "parts": [text]},
                },
                "parent": "root",
                "children": [],
            },
        },
    }


def test_chatgpt_importer(tmp_path):
    convs = list(chatgpt.parse_export(_write(tmp_path, "c.json", CHATGPT_SAMPLE)))
    assert len(convs) == 1
    conv = convs[0]
    assert conv["source"] == "chatgpt"
    assert conv["source_id"] == "conv-1"
    assert not conv["_source_id_generated"]
    assert [m["role"] for m in conv["messages"]] == ["user", "assistant"]
    assert "embeddings" in conv["messages"][1]["content"]


def test_claude_importer(tmp_path):
    convs = list(claude.parse_export(_write(tmp_path, "c.json", CLAUDE_SAMPLE)))
    assert len(convs) == 1
    conv = convs[0]
    assert conv["source"] == "claude"
    assert conv["source_id"] == "abc-123"
    assert not conv["_source_id_generated"]
    assert conv["messages"][0]["role"] == "user"
    assert conv["messages"][1]["content"] == "Start with Tokyo and Kyoto."


def test_gemini_importer(tmp_path):
    convs = list(gemini.parse_export(_write(tmp_path, "g.json", GEMINI_SAMPLE)))
    assert len(convs) == 1
    conv = convs[0]
    assert conv["source"] == "gemini"
    assert conv["source_id"].startswith("generated-gemini-")
    assert conv["_source_id_generated"]
    assert [m["role"] for m in conv["messages"]] == ["user", "assistant"]
    assert "black holes" in conv["messages"][0]["content"]


def test_missing_original_ids_do_not_collide():
    data = [
        _chatgpt_missing_id("Missing one", "first distinct prompt"),
        _chatgpt_missing_id("Missing two", "second distinct prompt"),
    ]
    convs = list(chatgpt.parse_data(data))
    assert convs[0]["source_id"].startswith("generated-chatgpt-")
    assert convs[1]["source_id"].startswith("generated-chatgpt-")
    assert convs[0]["source_id"] != convs[1]["source_id"]
    assert convs[0]["_source_id_generated"]
    assert convs[1]["_source_id_generated"]

    with Archive(":memory:") as archive:
        for conv in convs:
            archive.add_conversation(conv)
        assert archive.stats()["conversations"] == 2


def test_claude_missing_original_id_gets_generated_source_id():
    data = [
        {
            "name": "Missing Claude uuid",
            "created_at": "2025-06-01T10:00:00Z",
            "chat_messages": [
                {
                    "sender": "human",
                    "text": "This export omitted the conversation uuid",
                    "created_at": "2025-06-01T10:00:01Z",
                },
            ],
        }
    ]
    conv = list(claude.parse_data(data))[0]
    assert conv["source_id"].startswith("generated-claude-")
    assert conv["_source_id_generated"]


def test_gemini_generated_source_id_is_stable_when_export_grows():
    original = list(gemini.parse_data(GEMINI_SAMPLE))[0]
    larger = [
        *GEMINI_SAMPLE,
        {
            "title": "Prompted What changed later?",
            "time": "2025-05-02T09:00:00Z",
            "subtitles": [{"name": "A later prompt was added."}],
        },
    ]
    updated = list(gemini.parse_data(larger))[0]
    assert original["source_id"] == updated["source_id"]
    assert updated["_source_id_generated"]


def test_missing_original_id_reimport_is_stable_and_warns(tmp_path, capsys):
    data = [_chatgpt_missing_id("No platform id", "stable first prompt")]
    path = tmp_path / "conversations.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    db = str(tmp_path / "archive.db")

    assert main(["--db", db, "import", "chatgpt", str(path)]) == 0
    first = capsys.readouterr()
    assert "Added 1" in first.out
    assert "has no original id" in first.err
    assert "generated deterministic source_id generated-chatgpt-" in first.err

    data[0]["mapping"]["n2"] = {
        "message": {
            "author": {"role": "assistant"},
            "create_time": 1735689603,
            "content": {"content_type": "text", "parts": ["second answer"]},
        },
        "parent": "n1",
        "children": [],
    }
    path.write_text(json.dumps(data), encoding="utf-8")

    assert main(["--db", db, "import", "chatgpt", str(path)]) == 0
    second = capsys.readouterr()
    assert "Added 0, updated 1, skipped 0" in second.out
    assert "has no original id" in second.err

    assert main(["--db", db, "stats"]) == 0
    stats = capsys.readouterr().out
    assert "Conversations: 1" in stats
    assert "Messages:      2" in stats


def test_archive_roundtrip_and_search(tmp_path):
    with Archive(":memory:") as archive:
        conv = next(chatgpt.parse_export(_write(tmp_path, "c.json", CHATGPT_SAMPLE)))
        assert archive.add_conversation(conv) == ("added", 2)
        assert archive.add_conversation(conv) is None  # unchanged: skipped

        results = archive.search("embeddings")
        assert len(results) == 1
        assert results[0]["title"] == "Vector databases"

        convs = archive.list_conversations()
        assert convs[0]["message_count"] == 2
        full = archive.get_conversation(convs[0]["id"])
        assert full is not None and len(full["messages"]) == 2


def test_incremental_update():
    with Archive(":memory:") as archive:
        conv = _conv("chatgpt", "x", "Growing", "first message")
        assert archive.add_conversation(conv) == ("added", 1)
        conv["messages"].append(
            {"role": "assistant", "content": "second", "created_at": None}
        )
        assert archive.add_conversation(conv) == ("updated", 1)
        convs = archive.list_conversations()
        assert convs[0]["message_count"] == 2
        # merged content is searchable (FTS stays in sync)
        assert len(archive.search("second")) == 1


def test_favorites_and_filters():
    with Archive(":memory:") as archive:
        archive.add_conversation(_conv("chatgpt", "a", "Alpha", "hello world"))
        archive.add_conversation(_conv("claude", "b", "Beta", "hello moon"))

        convs = archive.list_conversations(source="claude")
        assert len(convs) == 1 and convs[0]["title"] == "Beta"

        beta_id = convs[0]["id"]
        assert archive.toggle_favorite(beta_id) == 1
        favs = archive.list_conversations(favorites_only=True)
        assert [c["title"] for c in favs] == ["Beta"]
        assert archive.toggle_favorite(beta_id) == 0
        assert archive.toggle_favorite(9999) is None

        results = archive.search("hello", source="chatgpt")
        assert len(results) == 1 and results[0]["source"] == "chatgpt"

        stats = archive.stats()
        assert stats["conversations"] == 2
        assert stats["by_source"] == {"chatgpt": 1, "claude": 1}


def test_activity():
    with Archive(":memory:") as archive:
        archive.add_conversation(_conv("chatgpt", "a", "Alpha", "hello"))
        act = archive.activity()
        assert act == [{"month": "2025-01", "n": 1}]


def test_zip_loading_and_detection(tmp_path):
    zpath = tmp_path / "export.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        z.writestr("data/conversations.json", json.dumps(CHATGPT_SAMPLE))
    data = load_json_from_path(str(zpath))
    assert detect_platform(data) == "chatgpt"
    assert detect_platform(CLAUDE_SAMPLE) == "claude"
    assert detect_platform(GEMINI_SAMPLE) == "gemini"


def test_export_markdown():
    conv = {
        "title": "My Chat",
        "source": "chatgpt",
        "created_at": "2025-01-01T00:00:00Z",
        "messages": [
            {"role": "user", "content": "Hi", "created_at": None},
            {"role": "assistant", "content": "Hello!", "created_at": None},
        ],
    }
    md = conversation_to_markdown(conv)
    assert md.startswith("# My Chat")
    assert "## You" in md and "## Assistant" in md
    assert "Hello!" in md


def test_safe_filename():
    assert safe_filename("Hello / World: test?") == "Hello-World-test"
    assert safe_filename("") == "untitled"


def test_search_handles_special_characters():
    with Archive(":memory:") as archive:
        assert archive.search('"broken OR (syntax') == []  # must not raise
