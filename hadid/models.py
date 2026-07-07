"""Shared normalized data shapes used between importers and storage."""

from __future__ import annotations

from typing import TypedDict


class Message(TypedDict):
    """One normalized chat message."""

    role: str
    content: str
    created_at: str | None


class SortableMessage(Message, total=False):
    """Importer-only message shape while ordering platform export nodes."""

    _sort: float | int | str


class Conversation(TypedDict):
    """One normalized conversation ready to persist."""

    source: str
    source_id: str
    title: str
    created_at: str | None
    messages: list[Message]


class ImportedConversation(Conversation, total=False):
    """Conversation emitted by an importer before CLI warnings are handled."""

    _source_id_generated: bool


class StoredConversation(Conversation, total=False):
    """Conversation loaded from the archive, including database metadata."""

    id: int
    favorite: int
