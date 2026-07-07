"""Local web UI server for browsing and searching the archive.

Security model: the server is intended for loopback use only. It validates
the Host header (mitigating DNS-rebinding), sends a strict Content-Security-
Policy, and never writes anything to disk besides the archive itself.
"""

from __future__ import annotations

import json
import logging
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from ..db import DEFAULT_DB_PATH, Archive
from .templates import index_html, static_asset

logger = logging.getLogger(__name__)

_ALLOWED_HOSTS = {"127.0.0.1", "localhost", "::1"}


def host_is_allowed(host_header: str | None) -> bool:
    """Return True when the Host header refers to this machine (loopback).

    Handles bracketed IPv6 literals ([::1], [::1]:8642) as well as
    host:port forms. Anything else is rejected (anti DNS-rebinding).
    """
    host = (host_header or "").strip().lower()
    if host.startswith("["):
        host = host.split("]", 1)[0].lstrip("[")
    else:
        host = host.split(":", 1)[0]
    return host in _ALLOWED_HOSTS


_SECURITY_HEADERS = (
    ("X-Content-Type-Options", "nosniff"),
    ("Referrer-Policy", "no-referrer"),
    (
        "Content-Security-Policy",
        "default-src 'none'; style-src 'self'; "
        "script-src 'self'; connect-src 'self'; img-src 'self' data:",
    ),
)


class _Handler(BaseHTTPRequestHandler):
    """Request handler. The archive is shared and guarded by a lock."""

    server_version = "Hadid"
    archive: Archive | None = None
    lock = threading.Lock()

    # -- helpers ---------------------------------------------------------

    def _host_allowed(self) -> bool:
        return host_is_allowed(self.headers.get("Host"))

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for name, value in _SECURITY_HEADERS:
            self.send_header(name, value)
        if content_type.startswith("application/json"):
            self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj: Any, status: int = 200) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8")

    # -- routes ----------------------------------------------------------

    def do_GET(self) -> None:
        if not self._host_allowed():
            self._send(403, b"Forbidden", "text/plain")
            return
        if self.archive is None:  # pragma: no cover - misconfiguration guard
            self._json({"error": "server not ready"}, status=500)
            return
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)
        if path == "/":
            self._send(200, index_html().encode("utf-8"), "text/html; charset=utf-8")
        elif path.startswith("/static/"):
            asset = static_asset(path.removeprefix("/static/"))
            if asset is None:
                self._send(404, b"Not found", "text/plain")
                return
            content_type, body = asset
            self._send(200, body, content_type)
        elif path == "/api/conversations":
            source = qs.get("source", [None])[0]
            favorites = qs.get("favorites", ["0"])[0] in ("1", "true")
            try:
                limit = int(qs.get("limit", ["0"])[0])
            except ValueError:
                limit = 0
            try:
                offset = int(qs.get("offset", ["0"])[0])
            except ValueError:
                offset = 0
            with self.lock:
                conversations = self.archive.list_conversations(
                    source=source, favorites_only=favorites,
                    limit=limit, offset=offset,
                )
            self._json(conversations)
        elif path == "/api/search":
            query = qs.get("q", [""])[0]
            source = qs.get("source", [None])[0]
            if not query.strip():
                self._json([])
                return
            with self.lock:
                results = self.archive.search(query, source=source)
            self._json(results)
        elif path == "/api/stats":
            with self.lock:
                stats = self.archive.stats()
            self._json(stats)
        elif path == "/api/activity":
            with self.lock:
                activity = self.archive.activity()
            self._json(activity)
        elif path.startswith("/api/conversation/"):
            try:
                conv_id = int(path.rsplit("/", 1)[1])
            except ValueError:
                self._json({"error": "invalid id"}, status=400)
                return
            with self.lock:
                conv = self.archive.get_conversation(conv_id)
            if conv is None:
                self._json({"error": "not found"}, status=404)
            else:
                self._json(conv)
        else:
            self._send(404, b"Not found", "text/plain")

    def do_POST(self) -> None:
        if not self._host_allowed():
            self._send(403, b"Forbidden", "text/plain")
            return
        if self.archive is None:  # pragma: no cover - misconfiguration guard
            self._json({"error": "server not ready"}, status=500)
            return
        parsed = urllib.parse.urlparse(self.path)
        parts = [p for p in parsed.path.split("/") if p]
        if (
            len(parts) == 4
            and parts[0] == "api"
            and parts[1] == "conversation"
            and parts[3] == "favorite"
        ):
            try:
                conv_id = int(parts[2])
            except ValueError:
                self._json({"error": "invalid id"}, status=400)
                return
            with self.lock:
                value = self.archive.toggle_favorite(conv_id)
            if value is None:
                self._json({"error": "not found"}, status=404)
            else:
                self._json({"favorite": value})
        else:
            self._send(404, b"Not found", "text/plain")

    def log_message(self, fmt: str, *args: Any) -> None:
        logger.debug("%s - %s", self.address_string(), fmt % args)


def serve(
    db_path: str = DEFAULT_DB_PATH, host: str = "127.0.0.1", port: int = 8642
) -> None:  # pragma: no cover
    """Start the local web app (loopback use only)."""
    if host not in _ALLOWED_HOSTS:
        logger.warning(
            "binding to %s exposes your archive beyond this machine", host
        )
    _Handler.archive = Archive(db_path, allow_threads=True)
    server = ThreadingHTTPServer((host, port), _Handler)
    print(f"Hadid is running at http://{host}:{port}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
        _Handler.archive.close()
