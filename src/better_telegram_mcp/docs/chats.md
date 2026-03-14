# Telegram Chats

Manage chats: list, get info, create, join, leave, members, admin, settings, and topics.

## Actions

### list
List your chats (user mode only).
- **limit**: Max chats to return (default: 50)

### info
Get detailed chat information.
- **chat_id** (required): Chat ID or username

### create
Create a new group or channel (user mode only).
- **title** (required): Chat title
- **is_channel**: Create a channel instead of group (default: false)

### join
Join a chat by invite link (user mode only).
- **link_or_hash** (required): Invite link or hash

### leave
Leave a chat.
- **chat_id** (required): Chat ID or username

### members
Get chat members/administrators.
- **chat_id** (required): Chat ID or username
- **limit**: Max members (default: 50)

### admin
Promote or demote a chat admin.
- **chat_id** (required): Chat ID or username
- **user_id** (required): User to promote/demote
- **demote**: Set true to demote (default: false)

### settings
Update chat settings (title, description).
- **chat_id** (required): Chat ID or username
- **title**: New title
- **description**: New description

### topics
Manage forum topics.
- **chat_id** (required): Chat ID or username
- **topic_action** (required): "list", "create", or "close"
- **topic_id**: Topic ID (for close)
- **topic_name**: Topic name (for create)