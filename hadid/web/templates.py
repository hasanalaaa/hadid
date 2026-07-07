"""Static web UI assets for Hadid.

The UI remains dependency-free: files are bundled as package data and served
by the stdlib HTTP server.
"""

from __future__ import annotations

from importlib import resources

_STATIC_PACKAGE = "hadid.web.static"
_CONTENT_TYPES = {
    "style.css": "text/css; charset=utf-8",
    "app.js": "application/javascript; charset=utf-8",
}


def _read_bytes(name: str) -> bytes:
    return (resources.files(_STATIC_PACKAGE) / name).read_bytes()


def index_html() -> str:
    """Return the bundled single-page app shell."""
    return _read_bytes("index.html").decode("utf-8")


def static_asset(name: str) -> tuple[str, bytes] | None:
    """Return a whitelisted static asset and content type."""
    content_type = _CONTENT_TYPES.get(name)
    if content_type is None:
        return None
    return content_type, _read_bytes(name)
