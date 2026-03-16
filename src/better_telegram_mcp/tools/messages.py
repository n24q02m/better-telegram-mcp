from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..server import MessagesArgs

from ..backends.base import ModeError, TelegramBackend
from ..utils.formatting import err, ok


async def handle_messages(
    backend: TelegramBackend,
    args: MessagesArgs,
) -> str:
    try:
        match args.action:
            case "send":
                if not args.chat_id or not args.text:
                    return err("'send' requires chat_id and text")
                result = await backend.send_message(
                    args.chat_id,
                    args.text,
                    reply_to=args.reply_to,
                    parse_mode=args.parse_mode,
                )
                return ok(result)

            case "edit":
                if not args.chat_id or args.message_id is None or not args.text:
                    return err("'edit' requires chat_id, message_id, and text")
                result = await backend.edit_message(
                    args.chat_id, args.message_id, args.text, parse_mode=args.parse_mode
                )
                return ok(result)

            case "delete":
                if not args.chat_id or args.message_id is None:
                    return err("'delete' requires chat_id and message_id")
                result = await backend.delete_message(args.chat_id, args.message_id)
                return ok({"deleted": result})

            case "forward":
                if not args.from_chat or not args.to_chat or args.message_id is None:
                    return err("'forward' requires from_chat, to_chat, and message_id")
                result = await backend.forward_message(
                    args.from_chat, args.to_chat, args.message_id
                )
                return ok(result)

            case "pin":
                if not args.chat_id or args.message_id is None:
                    return err("'pin' requires chat_id and message_id")
                result = await backend.pin_message(args.chat_id, args.message_id)
                return ok({"pinned": result})

            case "react":
                if not args.chat_id or args.message_id is None or not args.emoji:
                    return err("'react' requires chat_id, message_id, and emoji")
                result = await backend.react_to_message(
                    args.chat_id, args.message_id, args.emoji
                )
                return ok({"reacted": result})

            case "search":
                if not args.query:
                    return err("'search' requires query")
                results = await backend.search_messages(
                    args.query, chat_id=args.chat_id, limit=args.limit
                )
                return ok({"messages": results, "count": len(results)})

            case "history":
                if not args.chat_id:
                    return err("'history' requires chat_id")
                results = await backend.get_history(
                    args.chat_id, limit=args.limit, offset_id=args.offset_id
                )
                return ok({"messages": results, "count": len(results)})

            case _:
                return err(
                    f"Unknown action '{args.action}'. "
                    "Valid: send|edit|delete|forward|pin|react|search|history"
                )
    except ModeError as e:
        return err(str(e))
    except Exception as e:
        return err(f"{type(e).__name__}: {e}")
