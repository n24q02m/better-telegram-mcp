from __future__ import annotations

from typing import Any

from ..backends.base import ModeError, TelegramBackend
from ..utils.formatting import err, ok


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
    try:
        match action:
            case "list":
                results = await backend.list_chats(limit=limit)
                return ok({"chats": results, "count": len(results)})

            case "info":
                if not chat_id:
                    return err("'info' requires chat_id")
                result = await backend.get_chat_info(chat_id)
                return ok(result)

            case "create":
                if not title:
                    return err("'create' requires title")
                result = await backend.create_chat(
                    title, is_channel=is_channel
                )
                return ok(result)

            case "join":
                if not link_or_hash:
                    return err("'join' requires link_or_hash")
                result = await backend.join_chat(link_or_hash)
                return ok({"joined": result})

            case "leave":
                if not chat_id:
                    return err("'leave' requires chat_id")
                result = await backend.leave_chat(chat_id)
                return ok({"left": result})

            case "members":
                if not chat_id:
                    return err("'members' requires chat_id")
                results = await backend.get_members(chat_id, limit=limit)
                return ok({"members": results, "count": len(results)})

            case "admin":
                if not chat_id or user_id is None:
                    return err("'admin' requires chat_id and user_id")
                result = await backend.promote_admin(
                    chat_id, user_id, demote=demote
                )
                action_word = "demoted" if demote else "promoted"
                return ok({action_word: result})

            case "settings":
                if not chat_id:
                    return err("'settings' requires chat_id")
                kwargs: dict[str, Any] = {}
                if title is not None:
                    kwargs["title"] = title
                if description is not None:
                    kwargs["description"] = description
                if not kwargs:
                    return err(
                        "'settings' requires at least one of: title, description"
                    )
                result = await backend.update_chat_settings(chat_id, **kwargs)
                return ok({"updated": result})

            case "topics":
                if not chat_id:
                    return err("'topics' requires chat_id")
                if not topic_action:
                    return err("'topics' requires topic_action")
                kwargs_t: dict[str, Any] = {}
                if topic_id is not None:
                    kwargs_t["topic_id"] = topic_id
                if topic_name is not None:
                    kwargs_t["name"] = topic_name
                result = await backend.manage_topics(
                    chat_id, topic_action, **kwargs_t
                )
                return ok(result)

            case _:
                return err(
                    f"Unknown action '{action}'. "
                    "Valid: list|info|create|join|leave|members|admin|settings|topics"
                )
    except ModeError as e:
        return err(str(e))
    except Exception as e:
        return err(f"{type(e).__name__}: {e}")
