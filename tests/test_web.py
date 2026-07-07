"""HTTP-level tests for the local web app."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Iterator

import pytest

from hadid.db import Archive
from hadid.web.server import _Handler


@pytest.fixture
def web_server(tmp_path: Path) -> Iterator[str]:
    db = str(tmp_path / "archive.db")
    with Archive(db) as archive:
        archive.add_conversation(
            {
                "source": "chatgpt",
                "source_id": "web-1",
                "title": "Web smoke",
                "created_at": "2025-01-01T00:00:00Z",
                "messages": [
                    {
                        "role": "user",
                        "content": "searchable web token",
                        "created_at": "2025-01-01T00:00:01Z",
                    }
                ],
            }
        )

    _Handler.archive = Archive(db, allow_threads=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        if _Handler.archive is not None:
            _Handler.archive.close()
            _Handler.archive = None
        thread.join(timeout=1)


def _request(
    base_url: str, path: str, *, method: str = "GET", host: str = "127.0.0.1"
) -> tuple[int, dict[str, str], bytes]:
    req = urllib.request.Request(
        base_url + path,
        method=method,
        headers={"Host": host},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()


def test_web_shell_static_assets_and_csp(web_server: str):
    status, headers, body = _request(web_server, "/")
    csp = headers["Content-Security-Policy"]
    assert status == 200
    assert "unsafe-inline" not in csp
    assert "style-src 'self'" in csp
    assert "script-src 'self'" in csp
    assert b'href="/static/style.css"' in body
    assert b'src="/static/app.js"' in body

    status, headers, body = _request(web_server, "/static/style.css")
    assert status == 200
    assert headers["Content-Type"].startswith("text/css")
    assert b":root" in body

    status, headers, body = _request(web_server, "/static/app.js")
    assert status == 200
    assert headers["Content-Type"].startswith("application/javascript")
    assert b"function init()" in body


def test_web_api_routes_still_work(web_server: str):
    status, _, body = _request(web_server, "/api/conversations")
    assert status == 200
    conversations = json.loads(body)
    assert conversations[0]["title"] == "Web smoke"

    status, _, body = _request(web_server, "/api/search?q=token")
    assert status == 200
    assert json.loads(body)[0]["title"] == "Web smoke"

    status, _, body = _request(web_server, "/api/conversation/1/favorite", method="POST")
    assert status == 200
    assert json.loads(body) == {"favorite": 1}

    status, _, body = _request(web_server, "/api/conversation/1")
    assert status == 200
    assert json.loads(body)["favorite"] == 1


def test_web_rejects_unknown_static_assets_and_bad_hosts(web_server: str):
    status, _, body = _request(web_server, "/static/missing.js")
    assert status == 404
    assert body == b"Not found"

    status, _, body = _request(web_server, "/api/stats", host="evil.example.com")
    assert status == 403
    assert body == b"Forbidden"


def test_web_api_edge_cases(web_server: str):
    # Bad limit and offset (ValueError fallback to 0)
    status, _, body = _request(web_server, "/api/conversations?limit=abc&offset=xyz")
    assert status == 200
    assert len(json.loads(body)) == 1

    # Empty search query
    status, _, body = _request(web_server, "/api/search?q=")
    assert status == 200
    assert json.loads(body) == []

    # Invalid and non-existent IDs for GET
    status, _, body = _request(web_server, "/api/conversation/abc")
    assert status == 400
    status, _, body = _request(web_server, "/api/conversation/999")
    assert status == 404

    # Invalid and non-existent IDs for POST favorite
    status, _, body = _request(web_server, "/api/conversation/abc/favorite", method="POST")
    assert status == 400
    status, _, body = _request(web_server, "/api/conversation/999/favorite", method="POST")
    assert status == 404

    # 404 routes
    status, _, body = _request(web_server, "/api/unknown")
    assert status == 404
    status, _, body = _request(web_server, "/api/stats", method="POST")
    assert status == 404

    # Forbidden POST (host header invalid)
    status, _, body = _request(
        web_server, "/api/conversation/1/favorite", method="POST", host="evil.example.com"
    )
    assert status == 403


def test_web_api_stats_and_activity(web_server: str):
    status, _, body = _request(web_server, "/api/stats")
    assert status == 200
    stats = json.loads(body)
    assert stats["conversations"] == 1
    assert stats["messages"] == 1

    status, _, body = _request(web_server, "/api/activity")
    assert status == 200
    activity = json.loads(body)
    assert len(activity) == 1
    assert activity[0]["month"] == "2025-01"
    assert activity[0]["n"] == 1
