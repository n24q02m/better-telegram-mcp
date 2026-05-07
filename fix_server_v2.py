import sys

with open('src/better_telegram_mcp/server.py', 'r') as f:
    lines = f.readlines()

# We know chat starts at 277 (1-based, so 276 in 0-based)
chat_start = 276
# We need to find where the corrupted block ends and media's decorator or actual start begins.
# Line 314 currently has: ) -> str: which belongs to media
# Line 337 has @mcp.tool for Contacts.
# Let's find "async def contact" to be sure.
contact_start = -1
for i, line in enumerate(lines):
    if 'async def contact(' in line:
        contact_start = i
        break

if contact_start == -1:
    print("Could not find contact tool")
    sys.exit(1)

# Backtrack from contact_start to find the @mcp.tool for contact
contact_decorator_start = contact_start
while contact_decorator_start > 0 and '@mcp.tool(' not in lines[contact_decorator_start]:
    contact_decorator_start -= 1

# Now we have the block from chat_start to contact_decorator_start that needs fixing.
# This block currently contains corrupted chat and corrupted media.

new_block = [
    "async def chat(args: ChatOptions) -> str:\n",
    "    \"\"\"List, create, join, leave, manage members, settings, and topics.\n",
    "\n",
    "    Actions:\n",
    "    - list (-> limit=50)\n",
    "    - info (chat_id)\n",
    "    - create (title -> is_channel)\n",
    "    - join (link_or_hash)\n",
    "    - leave (chat_id)\n",
    "    - members (chat_id -> limit=50)\n",
    "    - admin (chat_id, user_id -> demote)\n",
    "    - settings (chat_id, title|description)\n",
    "    - topics (chat_id, topic_action -> topic_id, topic_name)\n",
    "    \"\"\"\n",
    "    if _unconfigured or _pending_auth:\n",
    "        return _not_ready_response()\n",
    "\n",
    "    return await handle_chats(get_backend(), args)\n",
    "\n",
    "\n",
    "@mcp.tool(\n",
    "    annotations=ToolAnnotations(\n",
    "        title=\"Telegram Media\",\n",
    "        readOnlyHint=False,\n",
    "        destructiveHint=False,\n",
    "        idempotentHint=False,\n",
    "        openWorldHint=True,\n",
    "    )\n",
    ")\n",
    "async def media(\n",
    "    action: str,\n",
    "    chat_id: str | int | None = None,\n",
    "    file_path_or_url: str | None = None,\n",
    "    message_id: int | None = None,\n",
    "    caption: str | None = None,\n",
    "    output_dir: str | None = None,\n",
    ") -> str:\n",
    "    \"\"\"Send photos, files, voice, video, and download media from messages.\n",
    "\n",
    "    Actions (file_path_or_url: local path or URL):\n",
    "    - send_photo (chat_id, file_path_or_url -> caption)\n",
    "    - send_file (chat_id, file_path_or_url -> caption)\n",
    "    - send_voice (chat_id, file_path_or_url -> caption)\n",
    "    - send_video (chat_id, file_path_or_url -> caption)\n",
    "    - download (chat_id, message_id -> output_dir)\n",
    "    \"\"\"\n",
    "    if _unconfigured or _pending_auth:\n",
    "        return _not_ready_response()\n",
    "\n",
    "    opts = MediaOptions(\n",
    "        chat_id=chat_id,\n",
    "        file_path_or_url=file_path_or_url,\n",
    "        message_id=message_id,\n",
    "        caption=caption,\n",
    "        output_dir=output_dir,\n",
    "    )\n",
    "    return await handle_media(get_backend(), action, opts)\n",
    "\n",
    "\n"
]

final_lines = lines[:chat_start] + new_block + lines[contact_decorator_start:]
with open('src/better_telegram_mcp/server.py', 'w') as f:
    f.writelines(final_lines)
print(f"Successfully fixed server.py from {chat_start} to {contact_decorator_start}")
