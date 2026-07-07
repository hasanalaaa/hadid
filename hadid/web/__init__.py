"""Hadid local web application."""

from __future__ import annotations

from .server import host_is_allowed, serve

__all__ = ["host_is_allowed", "serve"]
