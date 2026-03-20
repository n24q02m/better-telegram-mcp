from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel, Field

from ..backends.base import ModeError, TelegramBackend
from ..utils.formatting import err, ok, safe_error


class ChatOptions(BaseModel):
    chat_id: str | int | None = Field(default=None, description="ID of the chat")
    title: str | None = Field(default=None, description="Title for new/updated chat")
    description: str | None = Field(default=None, description="Description for chat")
    is_channel: bool = Field(default=False, description="Whether to create a channel")
    link_or_hash: str | None = Field(default=None, description="Invite link or hash")
    user_id: int | None = Field(default=None, description="User ID to manage")
    demote: bool = Field(default=False, description="Whether to demote admin")
    limit: int = Field(default=50, description="Max results to return")
    topic_action: str | None = Field(
        default=None, description="Topic action to perform"
    )
    topic_id: int | None = Field(default=None, description="Topic ID to manage")
    topic_name: str | None = Field(default=None, description="Topic name to create")


async def _handle_list(backend: TelegramBackend, options: ChatOptions) -> str:
    results = await backend.list_chats(limit=options.limit)
    return ok({"chats": results, "count": len(results)})


async def _handle_info(backend: TelegramBackend, options: ChatOptions) -> str:
    if not options.chat_id:
        return err("'info' requires chat_id")
    result = await backend.get_chat_info(options.chat_id)
    return ok(result)


async def _handle_create(backend: TelegramBackend, options: ChatOptions) -> str:
    if not options.title:
        return err("'create' requires title")
    result = await backend.create_chat(options.title, is_channel=options.is_channel)
    return ok(result)


async def _handle_join(backend: TelegramBackend, options: ChatOptions) -> str:
    if not options.link_or_hash:
        return err("'join' requires link_or_hash")
    result = await backend.join_chat(options.link_or_hash)
    return ok({"joined": result})


async def _handle_leave(backend: TelegramBackend, options: ChatOptions) -> str:
    if not options.chat_id:
        return err("'leave' requires chat_id")
    result = await backend.leave_chat(options.chat_id)
    return ok({"left": result})


async def _handle_members(backend: TelegramBackend, options: ChatOptions) -> str:
    if not options.chat_id:
        return err("'members' requires chat_id")
    results = await backend.get_members(options.chat_id, limit=options.limit)
    return ok({"members": results, "count": len(results)})


async def _handle_admin(backend: TelegramBackend, options: ChatOptions) -> str:
    if not options.chat_id or options.user_id is None:
        return err("'admin' requires chat_id and user_id")
    result = await backend.promote_admin(
        options.chat_id, options.user_id, demote=options.demote
    )
    action_word = "demoted" if options.demote else "promoted"
    return ok({action_word: result})


async def _handle_settings(backend: TelegramBackend, options: ChatOptions) -> str:
    if not options.chat_id:
        return err("'settings' requires chat_id")
    kwargs: dict[str, Any] = {}
    if options.title is not None:
        kwargs["title"] = options.title
    if options.description is not None:
        kwargs["description"] = options.description
    if not kwargs:
        return err("'settings' requires at least one of: title, description")
    result = await backend.update_chat_settings(options.chat_id, **kwargs)
    return ok({"updated": result})


async def _handle_topics(backend: TelegramBackend, options: ChatOptions) -> str:
    if not options.chat_id:
        return err("'topics' requires chat_id")
    if not options.topic_action:
        return err("'topics' requires topic_action")
    kwargs_t: dict[str, Any] = {}
    if options.topic_id is not None:
        kwargs_t["topic_id"] = options.topic_id
    if options.topic_name is not None:
        kwargs_t["name"] = options.topic_name
    result = await backend.manage_topics(
        options.chat_id, options.topic_action, **kwargs_t
    )
    return ok(result)


_ACTION_HANDLERS: dict[
    str, Callable[[TelegramBackend, ChatOptions], Awaitable[str]]
] = {
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
    options: ChatOptions,
) -> str:
    try:
        handler = _ACTION_HANDLERS.get(action)
        if handler:
            return await handler(backend, options)

        return err(
            f"Unknown action '{action}'. "
            "Valid: list|info|create|join|leave|members|admin|settings|topics"
        )
    except ModeError as e:
        return err(str(e))
    except Exception as e:
        return safe_error(e)
