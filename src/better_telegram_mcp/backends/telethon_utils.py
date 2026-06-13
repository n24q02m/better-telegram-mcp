"""Telethon-specific serialization and utility functions."""

from __future__ import annotations

from typing import Any


def serialize_message(msg: Any) -> dict[str, Any]:
    """Serialize a Telethon Message object to a dictionary."""
    sender_id = getattr(msg, "sender_id", None)
    return {
        "message_id": msg.id,
        "text": msg.text or "",
        "date": str(msg.date) if msg.date else None,
        "sender_id": sender_id,
    }


def serialize_dialog(d: Any) -> dict[str, Any]:
    """Serialize a Telethon Dialog object to a dictionary."""
    title = getattr(d, "title", None) or getattr(d, "name", None) or ""
    return {
        "id": d.id,
        "title": title,
        "unread_count": getattr(d, "unread_count", 0),
    }


def serialize_user(u: Any) -> dict[str, Any]:
    """Serialize a Telethon User object to a dictionary."""
    return {
        "id": u.id,
        "first_name": getattr(u, "first_name", None) or "",
        "last_name": getattr(u, "last_name", None) or "",
        "username": getattr(u, "username", None),
        "phone": getattr(u, "phone", None),
    }
