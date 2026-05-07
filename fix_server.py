import sys

with open('src/better_telegram_mcp/server.py', 'r') as f:
    lines = f.readlines()

# Search for the chat function and media function to identify the block
start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if 'async def chat(' in line:
        start_idx = i
    if 'async def media(' in line:
        end_idx = i
        break

if start_idx != -1 and end_idx != -1:
    # Find the line where media starts - we need to keep the @mcp.tool decorator for media
    media_decorator_idx = end_idx
    while media_decorator_idx > 0 and '@mcp.tool(' not in lines[media_decorator_idx]:
        media_decorator_idx -= 1

    new_chat_lines = [
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
        "\n"
    ]

    final_lines = lines[:start_idx] + new_chat_lines + lines[media_decorator_idx:]
    with open('src/better_telegram_mcp/server.py', 'w') as f:
        f.writelines(final_lines)
    print(f"Successfully refactored chat tool between lines {start_idx} and {media_decorator_idx}")
else:
    print(f"Failed to find indices: start={start_idx}, end={end_idx}")
    sys.exit(1)
