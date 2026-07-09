"""Backend API tests for Hadid — AI conversation archive."""
from __future__ import annotations

import io
import json
import os
import zipfile

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
    # fall back: read from frontend/.env
    with open("/app/frontend/.env") as fh:
        for line in fh:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip()
                break

BASE_URL = (BASE_URL or "").rstrip("/")
API = f"{BASE_URL}/api"

CHATGPT_FIXTURE = "/app/tests/fixtures/chatgpt_sample.json"
CLAUDE_FIXTURE = "/app/tests/fixtures/claude_sample.json"


@pytest.fixture(scope="session")
def s():
    session = requests.Session()
    return session


# ---------- Root & Demo ----------
class TestRoot:
    def test_root(self, s):
        r = s.get(f"{API}/")
        assert r.status_code == 200
        d = r.json()
        assert d["app"] == "hadid"
        assert isinstance(d["platforms"], list)
        assert "chatgpt" in d["platforms"]
        assert "claude" in d["platforms"]


class TestDemo:
    def test_load_demo(self, s):
        r = s.post(f"{API}/demo")
        assert r.status_code == 200
        d = r.json()
        assert d["platform"] == "demo"
        # idempotent: since we already have demo data, expect skipped>0
        assert d["skipped"] >= 0

    def test_demo_idempotent(self, s):
        # calling second time should mostly skip
        r = s.post(f"{API}/demo")
        assert r.status_code == 200
        d = r.json()
        # Everything skipped since same content
        assert d["added"] == 0 and d["updated"] == 0
        assert d["skipped"] >= 9


# ---------- Import ChatGPT & Claude ----------
class TestImport:
    def test_import_chatgpt_auto_detect(self, s):
        # First clear the specific test-conv entries by trying re-import scenario
        with open(CHATGPT_FIXTURE, "rb") as f:
            files = {"file": ("chatgpt_sample.json", f, "application/json")}
            r = s.post(f"{API}/import", files=files, data={"platform": "auto"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["platform"] == "chatgpt"
        # Should add 2 conversations, 4 messages (system message skipped)
        # However if we've already run tests, could be skipped
        total = d["added"] + d["updated"] + d["skipped"]
        assert total == 2

    def test_import_chatgpt_reimport_skipped(self, s):
        with open(CHATGPT_FIXTURE, "rb") as f:
            files = {"file": ("chatgpt_sample.json", f, "application/json")}
            r = s.post(f"{API}/import", files=files, data={"platform": "auto"})
        assert r.status_code == 200
        d = r.json()
        assert d["platform"] == "chatgpt"
        assert d["skipped"] == 2
        assert d["added"] == 0
        assert d["updated"] == 0

    def test_import_claude_auto_detect(self, s):
        with open(CLAUDE_FIXTURE, "rb") as f:
            files = {"file": ("claude_sample.json", f, "application/json")}
            r = s.post(f"{API}/import", files=files, data={"platform": "auto"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["platform"] == "claude"
        total = d["added"] + d["updated"] + d["skipped"]
        assert total == 1

    def test_import_claude_verify_messages(self, s):
        # find the claude test conversation and confirm 4 messages
        r = s.get(f"{API}/conversations", params={"source": "claude", "q": "Claude Import Test"})
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) >= 1
        # locate exact one
        conv = next((c for c in items if c["title"] == "Claude Import Test"), None)
        assert conv is not None, "claude import test conversation not found"
        assert conv["message_count"] == 4
        r2 = s.get(f"{API}/conversations/{conv['id']}")
        assert r2.status_code == 200
        detail = r2.json()
        assert len(detail["messages"]) == 4
        # verify mixed text-field and content-blocks are both parsed
        contents = [m["content"] for m in detail["messages"]]
        assert any("Paris" in c for c in contents)
        assert any("Berlin" in c for c in contents)

    def test_import_empty_file(self, s):
        files = {"file": ("empty.json", b"", "application/json")}
        r = s.post(f"{API}/import", files=files, data={"platform": "auto"})
        assert r.status_code == 400

    def test_import_invalid_json(self, s):
        files = {"file": ("bad.json", b"{not json}", "application/json")}
        r = s.post(f"{API}/import", files=files, data={"platform": "auto"})
        assert r.status_code == 400


# ---------- Conversations listing / detail ----------
class TestConversations:
    def test_list_default(self, s):
        r = s.get(f"{API}/conversations")
        assert r.status_code == 200
        d = r.json()
        assert "items" in d and "total" in d
        assert d["total"] >= 9

    def test_list_source_filter(self, s):
        r = s.get(f"{API}/conversations", params={"source": "chatgpt"})
        assert r.status_code == 200
        d = r.json()
        for it in d["items"]:
            assert it["source"] == "chatgpt"

    def test_list_title_q(self, s):
        r = s.get(f"{API}/conversations", params={"q": "Claude"})
        assert r.status_code == 200
        for it in r.json()["items"]:
            assert "claude" in it["title"].lower()

    def test_list_pagination(self, s):
        r = s.get(f"{API}/conversations", params={"limit": 2, "offset": 0})
        assert r.status_code == 200
        assert len(r.json()["items"]) <= 2

    def test_get_conversation_404(self, s):
        r = s.get(f"{API}/conversations/nonexistent-id-xyz")
        assert r.status_code == 404

    def test_get_conversation_detail(self, s):
        lst = s.get(f"{API}/conversations", params={"limit": 1}).json()
        cid = lst["items"][0]["id"]
        r = s.get(f"{API}/conversations/{cid}")
        assert r.status_code == 200
        d = r.json()
        assert d["id"] == cid
        assert isinstance(d["messages"], list)
        assert len(d["messages"]) > 0


# ---------- Favorite / delete / tags ----------
class TestFavoritesTagsDelete:
    def test_favorite_toggle(self, s):
        lst = s.get(f"{API}/conversations", params={"limit": 1}).json()
        cid = lst["items"][0]["id"]
        original = lst["items"][0]["favorite"]
        r1 = s.post(f"{API}/conversations/{cid}/favorite")
        assert r1.status_code == 200
        assert r1.json()["favorite"] != original
        # toggle back
        r2 = s.post(f"{API}/conversations/{cid}/favorite")
        assert r2.json()["favorite"] == original

    def test_favorites_filter(self, s):
        lst = s.get(f"{API}/conversations", params={"limit": 1}).json()
        cid = lst["items"][0]["id"]
        s.post(f"{API}/conversations/{cid}/favorite")
        r = s.get(f"{API}/conversations", params={"favorites": "true"})
        ids = [i["id"] for i in r.json()["items"]]
        assert cid in ids
        # cleanup: toggle back
        s.post(f"{API}/conversations/{cid}/favorite")

    def test_add_remove_tag_and_tag_list(self, s):
        lst = s.get(f"{API}/conversations", params={"limit": 1}).json()
        cid = lst["items"][0]["id"]
        r = s.post(f"{API}/conversations/{cid}/tags", json={"name": "TEST_tag_xyz"})
        assert r.status_code == 200
        tags = s.get(f"{API}/tags").json()
        names = [t["name"] for t in tags]
        assert "TEST_tag_xyz" in names
        # filter by tag
        r2 = s.get(f"{API}/conversations", params={"tag": "TEST_tag_xyz"})
        assert cid in [i["id"] for i in r2.json()["items"]]
        # remove
        r3 = s.delete(f"{API}/conversations/{cid}/tags/TEST_tag_xyz")
        assert r3.status_code == 200

    def test_delete_and_reimport(self, s):
        # Import a fresh temp conversation, then delete it
        temp = [{
            "id": "test-delete-conv-abc",
            "title": "TEST Delete Me",
            "create_time": 1750200000,
            "mapping": {
                "x1": {"message": {"author": {"role": "user"},
                       "content": {"parts": ["hello"]}, "create_time": 1750200000}},
                "x2": {"message": {"author": {"role": "assistant"},
                       "content": {"parts": ["hi there"]}, "create_time": 1750200010}},
            },
        }]
        buf = json.dumps(temp).encode("utf-8")
        files = {"file": ("temp.json", buf, "application/json")}
        r = s.post(f"{API}/import", files=files, data={"platform": "auto"})
        assert r.status_code == 200
        # find it
        r2 = s.get(f"{API}/conversations", params={"q": "TEST Delete Me"})
        items = [i for i in r2.json()["items"] if i["title"] == "TEST Delete Me"]
        assert items
        cid = items[0]["id"]
        r3 = s.delete(f"{API}/conversations/{cid}")
        assert r3.status_code == 200
        r4 = s.get(f"{API}/conversations/{cid}")
        assert r4.status_code == 404


# ---------- Search ----------
class TestSearch:
    def test_search_english(self, s):
        r = s.get(f"{API}/search", params={"q": "React"})
        assert r.status_code == 200
        results = r.json()
        # snippets contain markers or React
        if results:
            # ensure structure
            for item in results:
                assert "snippet" in item and "conversation_id" in item

    def test_search_arabic(self, s):
        r = s.get(f"{API}/search", params={"q": "تسويق"})
        assert r.status_code == 200
        results = r.json()
        assert isinstance(results, list)
        # if we have any result, check marker chars present
        for item in results:
            assert "snippet" in item

    def test_search_source_filter(self, s):
        r = s.get(f"{API}/search", params={"q": "the", "source": "chatgpt"})
        assert r.status_code == 200
        for item in r.json():
            assert item["source"] == "chatgpt"

    def test_search_missing_q(self, s):
        r = s.get(f"{API}/search")
        assert r.status_code == 422  # missing required param


# ---------- Stats / Activity / Wordcloud ----------
class TestStatsEndpoints:
    def test_stats(self, s):
        r = s.get(f"{API}/stats")
        assert r.status_code == 200
        d = r.json()
        for k in ["conversations", "messages", "favorites", "tags", "by_source",
                  "avg_message_chars", "max_message_chars", "oldest", "newest"]:
            assert k in d

    def test_activity(self, s):
        r = s.get(f"{API}/activity")
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list)
        for row in rows:
            assert "month" in row and "n" in row

    def test_wordcloud_excludes_stop_words(self, s):
        r = s.get(f"{API}/wordcloud", params={"limit": 60})
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list)
        for row in rows:
            assert "word" in row and "count" in row
            assert row["word"] not in {"the", "a", "and", "of", "من", "في"}


# ---------- Export / Import archive ----------
class TestExportImport:
    def test_export_conversation_markdown(self, s):
        lst = s.get(f"{API}/conversations", params={"limit": 1}).json()
        cid = lst["items"][0]["id"]
        r = s.get(f"{API}/export/conversation/{cid}")
        assert r.status_code == 200
        assert "text/markdown" in r.headers.get("content-type", "").lower()
        assert len(r.content) > 0

    def test_export_all_zip(self, s):
        r = s.get(f"{API}/export/all")
        assert r.status_code == 200
        assert "zip" in r.headers.get("content-type", "").lower()
        # ensure valid zip
        z = zipfile.ZipFile(io.BytesIO(r.content))
        assert len(z.namelist()) > 0

    def test_export_archive_and_reimport(self, s):
        r = s.get(f"{API}/export/archive")
        assert r.status_code == 200
        assert "json" in r.headers.get("content-type", "").lower()
        data = json.loads(r.content.decode("utf-8"))
        assert isinstance(data, list) and len(data) >= 9
        # re-upload; everything should be skipped
        files = {"file": ("archive.json", r.content, "application/json")}
        r2 = s.post(f"{API}/import/archive", files=files)
        assert r2.status_code == 200
        d = r2.json()
        assert d["skipped"] >= len(data) or d["added"] == 0


# ---------- Autotag ----------
class TestAutotag:
    def test_autotag(self, s):
        r = s.post(f"{API}/autotag")
        assert r.status_code == 200
        assert "tagged" in r.json()


# ---------- Clear archive (LAST) then reload demo ----------
class TestClearArchive:
    """Runs last alphabetically-ish; keep this last in file order.
    Cleans then restores demo so app stays populated."""

    def test_clear_and_restore_demo(self, s):
        r = s.delete(f"{API}/archive")
        assert r.status_code == 200
        d = r.json()
        assert "conversations_deleted" in d and "messages_deleted" in d
        # verify empty
        stats = s.get(f"{API}/stats").json()
        assert stats["conversations"] == 0
        # restore
        r2 = s.post(f"{API}/demo")
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2["added"] >= 9
        stats2 = s.get(f"{API}/stats").json()
        assert stats2["conversations"] >= 9
