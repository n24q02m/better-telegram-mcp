# AGENTS.md - tools/

**OVERVIEW:** 6 mega-tools with action dispatch. Each tool = 1 FastMCP registration, N actions via match statement.

## WHERE TO LOOK

```
messages.py      send, edit, delete, forward, pin, react, search, history
chats.py         list, info, create, join, leave, members, admin, settings, topics
media.py         send_photo, send_file, send_voice, send_video, download
contacts.py      list, search, add, block
config_tool.py   status, set, cache_clear, setup_status, setup_start, setup_reset, setup_complete
help_tool.py     documentation lookup
```

## CONVENTIONS

### Mega-Tool Pattern

Each tool file exports one `handle_*` function that dispatches to private action handlers:

```python
async def handle_messages(backend: TelegramBackend, action: str, **kwargs) -> str:
    match action:
        case "send": return await _handle_send(backend, args)
        case "edit": return await _handle_edit(backend, args)
        case _: return err(f"Unknown action '{action}'")
```

### Action Handlers

- Private functions: `async def _handle_send(backend, args) -> str`
- Validate required params first, return `err("...")` if missing
- Call backend method, wrap result in `ok(result)`
- Use Pydantic models for complex args (MessagesArgs, ChatOptions)
- Use `**kwargs` for simple tools (config_tool.py)

### Error Returns

- Return error strings, never raise exceptions from tool handlers
- `err("message")` for validation failures
- `safe_error(e)` for caught exceptions (sanitizes credentials)
- `ok(result)` for success (wraps dict/list in JSON string)

### Tool Registration

Tools registered in `server.py` with annotations:

```python
@mcp.tool(
    annotations={
        "readOnlyHint": "false",
        "destructiveHint": "true",
        "idempotentHint": "false",
    }
)
async def message(action: str, ...) -> str:
    return await handle_messages(backend, action, ...)
```

## ANTI-PATTERNS

- Don't raise exceptions from `handle_*` or `_handle_*` functions (return error strings)
- Don't validate in both tool function and handler (validate once in handler)
- Don't use positional args for actions (use `action: str` param + match/dict dispatch)
- Don't duplicate backend calls (one handler = one backend method)
- Don't forget `safe_error()` wrapper in top-level try/except (prevents credential leaks)
