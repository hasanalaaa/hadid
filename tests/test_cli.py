"""End-to-end CLI tests using realistic synthetic platform exports."""

import json
import zipfile

from hadid.cli import main


def _chatgpt_conversations():
    """Two realistic conversations: branched mapping with system/tool
    noise, multimodal parts, and Arabic content."""
    return [
        {
            "id": "c0f5",
            "title": "Debugging a Python script",
            "create_time": 1735689600.25,
            "update_time": 1735689800.0,
            "mapping": {
                "aaa": {"id": "aaa", "message": None, "parent": None,
                        "children": ["bbb"]},
                "bbb": {
                    "id": "bbb",
                    "message": {
                        "author": {"role": "system"},
                        "create_time": None,
                        "content": {"content_type": "text", "parts": [""]},
                    },
                    "parent": "aaa", "children": ["ccc"],
                },
                "ccc": {
                    "id": "ccc",
                    "message": {
                        "author": {"role": "user"},
                        "create_time": 1735689601.0,
                        "content": {
                            "content_type": "text",
                            "parts": ["Why does my script raise KeyError?"],
                        },
                    },
                    "parent": "bbb", "children": ["ddd"],
                },
                "ddd": {
                    "id": "ddd",
                    "message": {
                        "author": {"role": "assistant"},
                        "create_time": 1735689610.0,
                        "content": {
                            "content_type": "text",
                            "parts": ["You read a missing key. Use dict.get."],
                        },
                    },
                    "parent": "ccc", "children": ["eee"],
                },
                "eee": {
                    "id": "eee",
                    "message": {
                        "author": {"role": "tool"},
                        "create_time": 1735689612.0,
                        "content": {"content_type": "text",
                                    "parts": ["tool output"]},
                    },
                    "parent": "ddd", "children": [],
                },
            },
        },
        {
            "id": "9d2a",
            "title": "\u062a\u0639\u0644\u0645 \u0627\u0644\u0628\u0631\u0645\u062c\u0629",
            "create_time": 1736000000.0,
            "mapping": {
                "r": {"id": "r", "message": None, "parent": None,
                      "children": ["m1"]},
                "m1": {
                    "id": "m1",
                    "message": {
                        "author": {"role": "user"},
                        "create_time": 1736000001.0,
                        "content": {
                            "content_type": "text",
                            "parts": [
                                "\u0645\u0627 \u0623\u0641\u0636\u0644 \u0644\u063a\u0629 "
                                "\u0644\u0644\u0645\u0628\u062a\u062f\u0626\u064a\u0646\u061f"
                            ],
                        },
                    },
                    "parent": "r", "children": ["m2"],
                },
                "m2": {
                    "id": "m2",
                    "message": {
                        "author": {"role": "assistant"},
                        "create_time": 1736000010.0,
                        "content": {
                            "content_type": "text",
                            "parts": [
                                "\u0628\u0627\u064a\u062b\u0648\u0646 "
                                "\u062e\u064a\u0627\u0631 \u0645\u0645\u062a\u0627\u0632 "
                                "\u0644\u0644\u0645\u0628\u062a\u062f\u0626\u064a\u0646."
                            ],
                        },
                    },
                    "parent": "m1", "children": ["m3"],
                },
                "m3": {
                    "id": "m3",
                    "message": {
                        "author": {"role": "user"},
                        "create_time": 1736000020.0,
                        "content": {"content_type": "multimodal_text",
                                    "parts": [{"asset_pointer": "file://x"}]},
                    },
                    "parent": "m2", "children": [],
                },
            },
        },
    ]


CLAUDE_EXPORT = [
    {
        "uuid": "6f9a",
        "name": "API design review",
        "created_at": "2025-06-01T10:00:00Z",
        "chat_messages": [
            {"sender": "human", "text": "Review my REST API design",
             "created_at": "2025-06-01T10:00:01Z", "attachments": []},
            {"sender": "assistant", "text": "",
             "content": [
                 {"type": "tool_use", "name": "analyzer"},
                 {"type": "text", "text": "Use plural nouns for endpoints."},
             ],
             "created_at": "2025-06-01T10:00:05Z"},
        ],
    }
]

GEMINI_EXPORT = [
    {
        "header": "Gemini Apps",
        "title": "Prompted Summarize the history of SQLite",
        "time": "2025-05-01T09:00:00.123Z",
        "products": ["Gemini Apps"],
        "subtitles": [{"name": "SQLite began in 2000 as an embedded DB."}],
    },
    {
        "header": "Gemini Apps",
        "title": "Visited some unrelated page",
        "time": "2025-05-01T09:05:00.000Z",
    },
]


def _make_chatgpt_zip(tmp_path):
    """Build a ZIP shaped like a real ChatGPT data export."""
    zpath = tmp_path / "chatgpt-export.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        z.writestr("conversations.json", json.dumps(_chatgpt_conversations()))
        z.writestr("user.json", json.dumps({"id": "user-1"}))
        z.writestr("chat.html", "<html></html>")
    return str(zpath)


def test_chatgpt_zip_end_to_end(tmp_path, capsys):
    zpath = _make_chatgpt_zip(tmp_path)
    db = str(tmp_path / "archive.db")

    assert main(["--db", db, "import", "auto", zpath]) == 0
    out = capsys.readouterr().out
    assert "Detected platform: chatgpt" in out
    assert "Added 2" in out

    # system/tool/multimodal noise is excluded: 4 real messages remain
    assert main(["--db", db, "stats"]) == 0
    out = capsys.readouterr().out
    assert "Conversations: 2" in out
    assert "Messages:      4" in out

    # Arabic full-text search works end to end, with highlighting
    assert main(["--db", db, "search", "\u0628\u0627\u064a\u062b\u0648\u0646"]) == 0
    out = capsys.readouterr().out
    assert "\u062a\u0639\u0644\u0645 \u0627\u0644\u0628\u0631\u0645\u062c\u0629" in out
    assert "\u00ab" in out

    assert main(["--db", db, "list"]) == 0
    out = capsys.readouterr().out
    assert "[chatgpt]" in out


def test_reimport_merges_only_new_messages(tmp_path, capsys):
    convs = _chatgpt_conversations()
    p = tmp_path / "conversations.json"
    p.write_text(json.dumps(convs), encoding="utf-8")
    db = str(tmp_path / "a.db")
    assert main(["--db", db, "import", "chatgpt", str(p)]) == 0
    capsys.readouterr()

    # the same export later, with one extra reply in one conversation
    convs[0]["mapping"]["fff"] = {
        "id": "fff",
        "message": {
            "author": {"role": "user"},
            "create_time": 1735689620.0,
            "content": {"content_type": "text",
                        "parts": ["Thanks, that fixed it!"]},
        },
        "parent": "ddd", "children": [],
    }
    p.write_text(json.dumps(convs), encoding="utf-8")
    assert main(["--db", db, "import", "chatgpt", str(p)]) == 0
    out = capsys.readouterr().out
    assert "Added 0, updated 1, skipped 1" in out

    # the merged message is immediately searchable
    assert main(["--db", db, "search", "fixed"]) == 0
    assert "Debugging a Python script" in capsys.readouterr().out


def test_claude_and_favorite_flow(tmp_path, capsys):
    p = tmp_path / "conversations.json"
    p.write_text(json.dumps(CLAUDE_EXPORT), encoding="utf-8")
    db = str(tmp_path / "a.db")
    assert main(["--db", db, "import", "auto", str(p)]) == 0
    out = capsys.readouterr().out
    assert "Detected platform: claude" in out

    assert main(["--db", db, "favorite", "1"]) == 0
    assert "added to favorites" in capsys.readouterr().out

    assert main(["--db", db, "list", "--favorites"]) == 0
    out = capsys.readouterr().out
    assert "\u2605" in out and "[claude]" in out

    # text inside content blocks (after tool_use noise) was captured
    assert main(["--db", db, "search", "plural"]) == 0
    assert "API design review" in capsys.readouterr().out


def test_gemini_and_export_all(tmp_path, capsys):
    p = tmp_path / "MyActivity.json"
    p.write_text(json.dumps(GEMINI_EXPORT), encoding="utf-8")
    db = str(tmp_path / "a.db")
    exports = tmp_path / "out"
    assert main(["--db", db, "import", "gemini", str(p)]) == 0
    capsys.readouterr()

    assert main(["--db", db, "export", "--all", "--dir", str(exports)]) == 0
    files = list(exports.glob("*.md"))
    assert len(files) == 1
    content = files[0].read_text(encoding="utf-8")
    assert content.startswith("# Gemini prompt history")
    assert "## You" in content and "SQLite" in content


def test_export_single_to_file(tmp_path, capsys):
    p = tmp_path / "conversations.json"
    p.write_text(json.dumps(CLAUDE_EXPORT), encoding="utf-8")
    db = str(tmp_path / "a.db")
    out_md = tmp_path / "conv.md"
    assert main(["--db", db, "import", "claude", str(p)]) == 0
    capsys.readouterr()
    assert main(["--db", db, "export", "1", "--out", str(out_md)]) == 0
    text = out_md.read_text(encoding="utf-8")
    assert text.startswith("# API design review")
    assert "## Assistant" in text


def test_error_paths(tmp_path, capsys):
    db = str(tmp_path / "a.db")

    assert main(["--db", db, "import", "chatgpt", "missing.json"]) == 1
    assert "File not found" in capsys.readouterr().err

    bad_zip = tmp_path / "bad.zip"
    bad_zip.write_text("not a zip", encoding="utf-8")
    assert main(["--db", db, "import", "chatgpt", str(bad_zip)]) == 1
    assert "not a valid ZIP" in capsys.readouterr().err

    bad_json = tmp_path / "bad.json"
    bad_json.write_text("{invalid json", encoding="utf-8")
    assert main(["--db", db, "import", "claude", str(bad_json)]) == 1
    assert "JSON file is invalid" in capsys.readouterr().err

    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    assert main(["--db", db, "import", "auto", str(bad)]) == 1
    assert "could not detect" in capsys.readouterr().err

    assert main(["--db", db, "export", "999"]) == 1
    assert "not found" in capsys.readouterr().err

    assert main(["--db", db, "export"]) == 1
    assert "provide a conversation id" in capsys.readouterr().err

    assert main(["--db", db, "favorite", "42"]) == 1
    assert "not found" in capsys.readouterr().err
