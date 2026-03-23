from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..server import MessagesArgs

from ..backends.base import ModeError, TelegramBackend
from ..utils.formatting import err, ok, safe_error


async def _handle_send(backend: TelegramBackend, args: MessagesArgs) -> str:
    if not args.chat_id or not args.text:
        return err(
            "'send' requires chat_id and text. "
            "chat_id: positive int (user), negative int (group), or @username. "
            "Optional parse_mode: HTML, MarkdownV2, or Markdown."
        )
    result = await backend.send_message(
        args.chat_id,
        args.text,
        reply_to=args.reply_to,
        parse_mode=args.parse_mode,
    )
    return ok(result)


async def _handle_edit(backend: TelegramBackend, args: MessagesArgs) -> str:
    if not args.chat_id or args.message_id is None or not args.text:
        return err(
            "'edit' requires chat_id, message_id, and text. "
            "Optional parse_mode: HTML, MarkdownV2, or Markdown."
        )
    result = await backend.edit_message(
        args.chat_id, args.message_id, args.text, parse_mode=args.parse_mode
    )
    return ok(result)


async def _handle_delete(backend: TelegramBackend, args: MessagesArgs) -> str:
    if not args.chat_id or args.message_id is None:
        return err("'delete' requires chat_id and message_id")
    result = await backend.delete_message(args.chat_id, args.message_id)
    return ok({"deleted": result})


async def _handle_forward(backend: TelegramBackend, args: MessagesArgs) -> str:
    if not args.from_chat or not args.to_chat or args.message_id is None:
        return err("'forward' requires from_chat, to_chat, and message_id")
    result = await backend.forward_message(
        args.from_chat, args.to_chat, args.message_id
    )
    return ok(result)


async def _handle_pin(backend: TelegramBackend, args: MessagesArgs) -> str:
    if not args.chat_id or args.message_id is None:
        return err("'pin' requires chat_id and message_id")
    result = await backend.pin_message(args.chat_id, args.message_id)
    return ok({"pinned": result})


async def _handle_react(backend: TelegramBackend, args: MessagesArgs) -> str:
    if not args.chat_id or args.message_id is None or not args.emoji:
        return err("'react' requires chat_id, message_id, and emoji")
    result = await backend.react_to_message(args.chat_id, args.message_id, args.emoji)
    return ok({"reacted": result})


async def _handle_search(backend: TelegramBackend, args: MessagesArgs) -> str:
    if not args.query:
        return err("'search' requires query")
    results = await backend.search_messages(
        args.query, chat_id=args.chat_id, limit=args.limit
    )
    return ok({"messages": results, "count": len(results)})


async def _handle_history(backend: TelegramBackend, args: MessagesArgs) -> str:
    if not args.chat_id:
        return err("'history' requires chat_id")
    results = await backend.get_history(
        args.chat_id, limit=args.limit, offset_id=args.offset_id
    )
    return ok({"messages": results, "count": len(results)})


_ACTION_HANDLERS: dict[
    str, Callable[[TelegramBackend, MessagesArgs], Coroutine[Any, Any, str]]
] = {
    "send": _handle_send,
    "edit": _handle_edit,
    "delete": _handle_delete,
    "forward": _handle_forward,
    "pin": _handle_pin,
    "react": _handle_react,
    "search": _handle_search,
    "history": _handle_history,
}


async def handle_messages(
    backend: TelegramBackend,
    args: MessagesArgs,
) -> str:
    try:
        handler = _ACTION_HANDLERS.get(args.action)
        if handler is None:
            import difflib

            valid = sorted(_ACTION_HANDLERS)
            closest = difflib.get_close_matches(args.action, valid, n=1)
            suggestion = f" Did you mean '{closest[0]}'?" if closest else ""
            return err(
                f"Unknown action '{args.action}'.{suggestion} "
                f"Valid: {'|'.join(valid)}"
            )
        return await handler(backend, args)
    except ModeError as e:
        return err(str(e))
    except Exception as e:
        return safe_error(e)
