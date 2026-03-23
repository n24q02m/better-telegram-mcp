from __future__ import annotations

from pydantic import BaseModel, Field

from ..backends.base import ModeError, TelegramBackend
from ..utils.formatting import err, ok, safe_error


class ContactsOptions(BaseModel):
    query: str | None = Field(default=None, description="Query to search for")
    phone: str | None = Field(default=None, description="Phone number to add")
    first_name: str | None = Field(
        default=None, description="First name of the contact"
    )
    last_name: str | None = Field(default=None, description="Last name of the contact")
    user_id: int | None = Field(default=None, description="User ID to block/unblock")
    unblock: bool = Field(default=False, description="Whether to unblock the user")


async def handle_contacts(
    backend: TelegramBackend,
    action: str,
    options: ContactsOptions | None = None,
) -> str:
    if options is None:
        options = ContactsOptions()
    try:
        match action:
            case "list":
                results = await backend.list_contacts()
                return ok({"contacts": results, "count": len(results)})

            case "search":
                if not options.query:
                    return err("'search' requires query")
                results = await backend.search_contacts(options.query)
                return ok({"contacts": results, "count": len(results)})

            case "add":
                if not options.phone or not options.first_name:
                    return err("'add' requires phone and first_name")
                result = await backend.add_contact(
                    options.phone, options.first_name, last_name=options.last_name
                )
                return ok({"added": result})

            case "block":
                if options.user_id is None:
                    return err("'block' requires user_id")
                result = await backend.block_user(
                    options.user_id, unblock=options.unblock
                )
                action_word = "unblocked" if options.unblock else "blocked"
                return ok({action_word: result})

            case _:
                import difflib

                valid = ["add", "block", "list", "search"]
                closest = difflib.get_close_matches(action, valid, n=1)
                suggestion = f" Did you mean '{closest[0]}'?" if closest else ""
                return err(
                    f"Unknown action '{action}'.{suggestion} Valid: {'|'.join(valid)}"
                )
    except ModeError as e:
        return err(str(e))
    except Exception as e:
        return safe_error(e)
