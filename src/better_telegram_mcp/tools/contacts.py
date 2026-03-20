from __future__ import annotations

from pydantic import BaseModel, Field

from ..backends.base import ModeError, TelegramBackend
from ..utils.formatting import err, ok, safe_error


class ContactsArgs(BaseModel):
    query: str | None = Field(default=None, description="Search query for contacts")
    phone: str | None = Field(
        default=None, description="Phone number for adding a contact"
    )
    first_name: str | None = Field(
        default=None, description="First name for adding a contact"
    )
    last_name: str | None = Field(
        default=None, description="Last name for adding a contact"
    )
    user_id: int | None = Field(default=None, description="User ID to block/unblock")
    unblock: bool = Field(default=False, description="Whether to unblock the user")


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
        return safe_error(e)
