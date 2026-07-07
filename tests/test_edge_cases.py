"""Edge-case tests for importers, storage helpers, and the web layer."""

import zipfile

import pytest

from hadid.db import _fts_query
from hadid.importers import (
    chatgpt,
    claude,
    detect_platform,
    gemini,
    load_json_from_path,
)
from hadid.web import host_is_allowed


def test_chatgpt_empty_mapping():
    convs = list(chatgpt.parse_data([{"id": "e1", "title": "Empty",
                                      "mapping": {}}]))
    assert convs[0]["messages"] == []


def test_chatgpt_rejects_non_list():
    with pytest.raises(ValueError):
        list(chatgpt.parse_data({"mapping": {}}))


def test_claude_skips_non_text_blocks():
    data = [{
        "uuid": "u1", "name": "Tools", "created_at": "2025-01-01T00:00:00Z",
        "chat_messages": [
            {"sender": "assistant", "text": "",
             "content": [{"type": "tool_use", "name": "calc"}]},
            {"sender": "human", "text": "hi"},
        ],
    }]
    convs = list(claude.parse_data(data))
    assert [m["content"] for m in convs[0]["messages"]] == ["hi"]


def test_gemini_without_prompts_yields_empty_history():
    data = [{"title": "Visited page", "time": "2025-01-01T00:00:00Z"}]
    convs = list(gemini.parse_data(data))
    assert convs[0]["messages"] == []


def test_detect_platform_failures():
    with pytest.raises(ValueError):
        detect_platform([])
    with pytest.raises(ValueError):
        detect_platform({"not": "a list"})


def test_zip_without_known_files(tmp_path):
    z = tmp_path / "x.zip"
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("readme.txt", "hi")
    with pytest.raises(ValueError):
        load_json_from_path(str(z))


def test_fts_query_quotes_tokens():
    assert _fts_query('hello "world"') == '"hello" """world"""'
    assert _fts_query("   ") == ""


def test_host_validation():
    assert host_is_allowed("127.0.0.1")
    assert host_is_allowed("127.0.0.1:8642")
    assert host_is_allowed("localhost:8642")
    assert host_is_allowed("LOCALHOST")
    assert host_is_allowed("[::1]:8642")
    assert host_is_allowed("[::1]")
    assert not host_is_allowed("evil.example.com")
    assert not host_is_allowed("evil.example.com:8642")
    assert not host_is_allowed(None)
    assert not host_is_allowed("")
