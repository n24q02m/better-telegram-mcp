# Telegram Contacts

Manage contacts: list, search, add, and block/unblock users. All actions require user mode.

## Actions

### list
List all contacts.
No parameters required.

### search
Search contacts by name or username.
- **query** (required): Search query

### add
Add a new contact.
- **phone** (required): Phone number (international format, e.g. "+1234567890")
- **first_name** (required): First name
- **last_name**: Last name (optional)

### block
Block or unblock a user.
- **user_id** (required): User ID to block/unblock
- **unblock**: Set true to unblock (default: false)