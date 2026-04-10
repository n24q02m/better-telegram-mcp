# AGENTS.md - tests/

**OVERVIEW:** Unit, integration, and E2E tests. Pytest with asyncio, markers, fixtures.

## WHERE TO LOOK

```text
tests/
  conftest.py              # MockBackend, shared fixtures, --backend CLI option
  conftest_e2e.py          # E2E fixtures: --setup (relay|env|plugin), --browser, StderrCapture, parse_result()
  test_*.py                # Unit test modules
  test_backends/           # Backend tests: bot, user, security, base ABC
  test_tools/              # Tool tests: messages, chats, media, contacts, config, help
  test_utils/              # Utility tests (if present)
  integration/             # Live API tests (requires credentials)
    test_bot_live.py       # Bot API integration (@pytest.mark.integration)
    test_user_live.py      # MTProto integration (@pytest.mark.integration)
  test_e2e.py              # Full MCP protocol E2E (3 setup modes x 2 backends)
  test_full_live.py        # Full live test (@pytest.mark.full, @pytest.mark.live)
  test_relay_setup.py      # Relay auth flow coverage
  test_server.py           # Server lifespan and tool registration coverage
  test_credential_state.py # Credential state machine coverage
```

## CONVENTIONS

### Markers
- `@pytest.mark.integration` -- Live API tests (skipped by default, requires credentials)
- `@pytest.mark.e2e` -- Full MCP protocol tests (3 setup modes: relay, env, plugin)
- `@pytest.mark.live` -- Requires live Telegram connection
- `@pytest.mark.full` -- Full integration test (all features)
- `@pytest.mark.asyncio(loop_scope="module")` -- Module-scoped event loop for E2E

### Fixtures (conftest.py)
- `MockBackend` -- Concrete TelegramBackend ABC implementation for unit tests
- `mock_backend` -- AsyncMock backend fixture
- `--backend` CLI option -- Choose bot or user mode (default: bot)

### Fixtures (conftest_e2e.py)
- `--setup` CLI option -- relay (manual browser auth), env (env vars), plugin (published package)
- `--browser` CLI option -- chrome, brave, edge (for relay mode)
- `StderrCapture` -- Tee stderr to buffer + real stderr, extract relay URL
- `parse_result(r)` -- Extract text from MCP result, raise on error
- `parse_result_allow_error(r)` -- Extract text, allow errors
- `open_browser(url, browser)` -- Open URL in specified browser

### Test Patterns
- **Unit tests:** Mock backend, test tool logic in isolation
- **Integration tests:** Live API, skip if credentials missing (`pytestmark = [pytest.mark.integration, pytest.mark.skipif(...)]`)
- **E2E tests:** Full MCP protocol via stdio, 3 setup modes, 2 backend modes (6 combinations)
- **Async tests:** No `@pytest.mark.asyncio` needed (asyncio_mode = "auto")
- **Timeouts:** 30s default, 180s for E2E (`@pytest.mark.timeout(180)`)

### Assertions
- `assert len(tools) == 6` -- Tool count
- `assert set(tools.keys()) == {"message", "chat", "media", "contact", "config", "help"}` -- Tool names
- `with pytest.raises(RuntimeError, match="...")` -- Exception matching
- `parse_result(r)` -- MCP result extraction (raises on error)

## ANTI-PATTERNS

- **DON'T** skip integration tests without reason (use `pytestmark` with `skipif`)
- **DON'T** hardcode credentials (use env vars, skip if missing)
- **DON'T** use `@pytest.mark.asyncio` (asyncio_mode = "auto" handles it)
- **DON'T** forget timeout for long-running tests (E2E, live API)
- **DON'T** test live API in unit tests (mock backend instead)
- **DON'T** duplicate E2E setup logic (use conftest_e2e.py fixtures)
