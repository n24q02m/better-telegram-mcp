from __future__ import annotations

from typing import Any

from ..backends.base import ModeError, TelegramBackend
from ..utils.formatting import err, ok


async def _handle_list(backend: TelegramBackend, kwargs: dict[str, Any]) -> str:
    limit = kwargs.get("limit", 50)
    results = await backend.list_chats(limit=limit)
    return ok({"chats": results, "count": len(results)})


async def _handle_info(backend: TelegramBackend, kwargs: dict[str, Any]) -> str:
    chat_id = kwargs.get("chat_id")
    if not chat_id:
        return err("'info' requires chat_id")
    result = await backend.get_chat_info(chat_id)
    return ok(result)


async def _handle_create(backend: TelegramBackend, kwargs: dict[str, Any]) -> str:
    title = kwargs.get("title")
    is_channel = kwargs.get("is_channel", False)
    if not title:
        return err("'create' requires title")
    result = await backend.create_chat(title, is_channel=is_channel)
    return ok(result)


async def _handle_join(backend: TelegramBackend, kwargs: dict[str, Any]) -> str:
    link_or_hash = kwargs.get("link_or_hash")
    if not link_or_hash:
        return err("'join' requires link_or_hash")
    result = await backend.join_chat(link_or_hash)
    return ok({"joined": result})


async def _handle_leave(backend: TelegramBackend, kwargs: dict[str, Any]) -> str:
    chat_id = kwargs.get("chat_id")
    if not chat_id:
        return err("'leave' requires chat_id")
    result = await backend.leave_chat(chat_id)
    return ok({"left": result})


async def _handle_members(backend: TelegramBackend, kwargs: dict[str, Any]) -> str:
    chat_id = kwargs.get("chat_id")
    limit = kwargs.get("limit", 50)
    if not chat_id:
        return err("'members' requires chat_id")
    results = await backend.get_members(chat_id, limit=limit)
    return ok({"members": results, "count": len(results)})


async def _handle_admin(backend: TelegramBackend, kwargs: dict[str, Any]) -> str:
    chat_id = kwargs.get("chat_id")
    user_id = kwargs.get("user_id")
    demote = kwargs.get("demote", False)
    if not chat_id or user_id is None:
        return err("'admin' requires chat_id and user_id")
    result = await backend.promote_admin(chat_id, user_id, demote=demote)
    action_word = "demoted" if demote else "promoted"
    return ok({action_word: result})


async def _handle_settings(backend: TelegramBackend, kwargs: dict[str, Any]) -> str:
    chat_id = kwargs.get("chat_id")
    title = kwargs.get("title")
    description = kwargs.get("description")
    if not chat_id:
        return err("'settings' requires chat_id")
    settings_kwargs: dict[str, Any] = {}
    if title is not None:
        settings_kwargs["title"] = title
    if description is not None:
        settings_kwargs["description"] = description
    if not settings_kwargs:
        return err("'settings' requires at least one of: title, description")
    result = await backend.update_chat_settings(chat_id, **settings_kwargs)
    return ok({"updated": result})


async def _handle_topics(backend: TelegramBackend, kwargs: dict[str, Any]) -> str:
    chat_id = kwargs.get("chat_id")
    topic_action = kwargs.get("topic_action")
    topic_id = kwargs.get("topic_id")
    topic_name = kwargs.get("topic_name")

    if not chat_id:
        return err("'topics' requires chat_id")
    if not topic_action:
        return err("'topics' requires topic_action")
    topic_kwargs: dict[str, Any] = {}
    if topic_id is not None:
        topic_kwargs["topic_id"] = topic_id
    if topic_name is not None:
        topic_kwargs["name"] = topic_name
    result = await backend.manage_topics(chat_id, topic_action, **topic_kwargs)
    return ok(result)


_ACTION_HANDLERS = {
    "list": _handle_list,
    "info": _handle_info,
    "create": _handle_create,
    "join": _handle_join,
    "leave": _handle_leave,
    "members": _handle_members,
    "admin": _handle_admin,
    "settings": _handle_settings,
    "topics": _handle_topics,
}


async def handle_chats(
    backend: TelegramBackend,
    action: str,
    *,
    chat_id: str | int | None = None,
    title: str | None = None,
    description: str | None = None,
    is_channel: bool = False,
    link_or_hash: str | None = None,
    user_id: int | None = None,
    demote: bool = False,
    limit: int = 50,
    topic_action: str | None = None,
    topic_id: int | None = None,
    topic_name: str | None = None,
) -> str:
    kwargs = {
        "chat_id": chat_id,
        "title": title,
        "description": description,
        "is_channel": is_channel,
        "link_or_hash": link_or_hash,
        "user_id": user_id,
        "demote": demote,
        "limit": limit,
        "topic_action": topic_action,
        "topic_id": topic_id,
        "topic_name": topic_name,
    }

    try:
        handler = _ACTION_HANDLERS.get(action)
        if handler:
            return await handler(backend, kwargs)

        return err(
            f"Unknown action '{action}'. "
            "Valid: list|info|create|join|leave|members|admin|settings|topics"
        )
    except ModeError as e:
        return err(str(e))
    except Exception as e:
        return err(f"{type(e).__name__}: {e}")
