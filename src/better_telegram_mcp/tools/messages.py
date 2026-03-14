from __future__ import annotations

from ..backends.base import ModeError, TelegramBackend
from ..utils.formatting import err, ok


async def handle_messages(
    backend: TelegramBackend,
    action: str,
    *,
    chat_id: str | int | None = None,
    text: str | None = None,
    message_id: int | None = None,
    reply_to: int | None = None,
    parse_mode: str | None = None,
    from_chat: str | int | None = None,
    to_chat: str | int | None = None,
    emoji: str | None = None,
    query: str | None = None,
    limit: int = 20,
    offset_id: int | None = None,
) -> str:
    try:
        match action:
            case "send":
                if not chat_id or not text:
                    return err("'send' requires chat_id and text")
                result = await backend.send_message(
                    chat_id, text, reply_to=reply_to, parse_mode=parse_mode
                )
                return ok(result)

            case "edit":
                if not chat_id or message_id is None or not text:
                    return err("'edit' requires chat_id, message_id, and text")
                result = await backend.edit_message(
                    chat_id, message_id, text, parse_mode=parse_mode
                )
                return ok(result)

            case "delete":
                if not chat_id or message_id is None:
                    return err("'delete' requires chat_id and message_id")
                result = await backend.delete_message(chat_id, message_id)
                return ok({"deleted": result})

            case "forward":
                if not from_chat or not to_chat or message_id is None:
                    return err(
                        "'forward' requires from_chat, to_chat, and message_id"
                    )
                result = await backend.forward_message(
                    from_chat, to_chat, message_id
                )
                return ok(result)

            case "pin":
                if not chat_id or message_id is None:
                    return err("'pin' requires chat_id and message_id")
                result = await backend.pin_message(chat_id, message_id)
                return ok({"pinned": result})

            case "react":
                if not chat_id or message_id is None or not emoji:
                    return err("'react' requires chat_id, message_id, and emoji")
                result = await backend.react_to_message(
                    chat_id, message_id, emoji
                )
                return ok({"reacted": result})

            case "search":
                if not query:
                    return err("'search' requires query")
                results = await backend.search_messages(
                    query, chat_id=chat_id, limit=limit
                )
                return ok({"messages": results, "count": len(results)})

            case "history":
                if not chat_id:
                    return err("'history' requires chat_id")
                results = await backend.get_history(
                    chat_id, limit=limit, offset_id=offset_id
                )
                return ok({"messages": results, "count": len(results)})

            case _:
                return err(
                    f"Unknown action '{action}'. "
                    "Valid: send|edit|delete|forward|pin|react|search|history"
                )
    except ModeError as e:
        return err(str(e))
    except Exception as e:
        return err(f"{type(e).__name__}: {e}")
