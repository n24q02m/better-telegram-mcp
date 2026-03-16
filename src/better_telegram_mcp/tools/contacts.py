from __future__ import annotations

from dataclasses import dataclass

from ..backends.base import ModeError, TelegramBackend
from ..utils.formatting import err, ok


@dataclass
class ContactsArgs:
    query: str | None = None
    phone: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    user_id: int | None = None
    unblock: bool = False


async def handle_contacts(
    backend: TelegramBackend,
    action: str,
    args: ContactsArgs | None = None,
) -> str:
    if args is None:
        args = ContactsArgs()
    try:
        match action:
            case "list":
                results = await backend.list_contacts()
                return ok({"contacts": results, "count": len(results)})

            case "search":
                if not args.query:
                    return err("'search' requires query")
                results = await backend.search_contacts(args.query)
                return ok({"contacts": results, "count": len(results)})

            case "add":
                if not args.phone or not args.first_name:
                    return err("'add' requires phone and first_name")
                result = await backend.add_contact(
                    args.phone, args.first_name, last_name=args.last_name
                )
                return ok({"added": result})

            case "block":
                if args.user_id is None:
                    return err("'block' requires user_id")
                result = await backend.block_user(args.user_id, unblock=args.unblock)
                action_word = "unblocked" if args.unblock else "blocked"
                return ok({action_word: result})

            case _:
                return err(f"Unknown action '{action}'. Valid: list|search|add|block")
    except ModeError as e:
        return err(str(e))
    except Exception as e:
        return err(f"{type(e).__name__}: {e}")
