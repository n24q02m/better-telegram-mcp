from __future__ import annotations

import os
from typing import Any

from loguru import logger
from telethon.tl.types import Channel, Chat, User

from ..config import Settings


def prepare_session_file(settings: Settings) -> None:
    """Prepare session directory and file with secure permissions."""
    settings.data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

    # Pre-create session file with secure permissions to avoid TOCTOU
    # where Telethon creates it with default (insecure) permissions
    session_path = settings.data_dir / settings.session_name
    actual_session_path = session_path.with_suffix(".session")
    try:
        fd = os.open(str(actual_session_path), os.O_CREAT | os.O_WRONLY, 0o600)
        os.close(fd)
    except OSError as e:
        # Windows may not support this or file already exists
        logger.debug("Could not pre-create session file: {e}", e=e)


def secure_session_file(settings: Settings) -> None:
    """Ensure existing session files are secured with 0o600 permissions."""
    session_file = (settings.data_dir / settings.session_name).with_suffix(".session")
    if session_file.exists():
        try:
            os.chmod(session_file, 0o600)
        except OSError as e:
            logger.debug("Could not set session file permissions: {e}", e=e)


def serialize_message(msg: Any) -> dict[str, Any]:
    """Serialize a Telethon message object to a dictionary."""
    sender_id = None
    if hasattr(msg, "sender_id") and msg.sender_id is not None:
        sender_id = msg.sender_id
    return {
        "message_id": getattr(msg, "id", None),
        "text": getattr(msg, "text", "") or "",
        "date": str(msg.date) if getattr(msg, "date", None) else None,
        "sender_id": sender_id,
    }


def serialize_dialog(d: Any) -> dict[str, Any]:
    """Serialize a Telethon dialog object to a dictionary."""
    title = getattr(d, "title", None) or getattr(d, "name", None) or ""
    return {
        "id": getattr(d, "id", None),
        "title": title,
        "unread_count": getattr(d, "unread_count", 0),
    }


def serialize_user(u: Any) -> dict[str, Any]:
    """Serialize a Telethon user object to a dictionary."""
    return {
        "id": getattr(u, "id", None),
        "first_name": getattr(u, "first_name", None) or "",
        "last_name": getattr(u, "last_name", None) or "",
        "username": getattr(u, "username", None),
        "phone": getattr(u, "phone", None),
    }


def serialize_entity(entity: Any) -> dict[str, Any]:
    """Serialize a Telethon entity (User, Chat, or Channel) to a dictionary."""
    info: dict[str, Any] = {"id": entity.id}
    if isinstance(entity, (Channel, Chat)):
        info["title"] = getattr(entity, "title", "")
        info["participants_count"] = getattr(entity, "participants_count", None)
    elif isinstance(entity, User):
        info["first_name"] = getattr(entity, "first_name", "")
        info["last_name"] = getattr(entity, "last_name", "")
        info["username"] = getattr(entity, "username", None)
    return info
