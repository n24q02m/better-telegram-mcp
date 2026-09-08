# Better Telegram MCP Handover

## Current product

Better Telegram MCP exposes Telegram messaging, chat, media, and contact operations through MCP. It supports Bot API and MTProto user-account modes, local stdio operation, and HTTP relay setup for self-hosted multi-user deployments.

The public contract is defined by the repository README, `server.json`, package metadata, and the documented MCP tools. The credential form is rendered through the shared MCP core renderer; Telegram adds its Bot/User tabs and accessibility enhancements without maintaining a second form renderer.

## Build and verify

- Python: 3.13
- Install: `uv sync --group dev --no-sources`

- Lint: `uv run --no-sync ruff check .`
- Format: `uv run --no-sync ruff format --check .`
- Types: `uv run --no-sync ty check`
- Tests: `uv run --no-sync pytest tests/`
- Worker tests: `npm ci`, then `npm run test:worker`
- Worker types: `npm run type-check`

Integration, live, full, and end-to-end tests require Telegram credentials and an approved test account. A representative protocol check must call a domain operation such as listing chats or updates; configuration status alone is only a handshake.

## Runtime and data boundaries

Bot mode uses `TELEGRAM_BOT_TOKEN`. User mode uses the documented phone/OTP flow and stores the Telethon session in the configured data directory. HTTP deployments require the documented transport, public URL, and OAuth/relay settings. Remote credential state must remain isolated per authenticated subject.

Pending OTP metadata is indexed by subject and bearer. The index supports an O(1) empty-state check; cleanup still applies the five-minute expiry policy and removes stale entries without scanning when the index is empty.

Do not put credentials, OTPs, session files, or raw protocol transcripts in the repository. Do not use external infrastructure as a source of truth for local development or verification.

## Transport-contract reconciliation

The executable currently defaults to local stdio; HTTP is explicit through
`--http`, `MCP_TRANSPORT=http`, or `TRANSPORT_MODE=http`. The canonical stack
mode matrix names `http remote relay` as Telegram's deployed default. This is
an explicit source-versus-canonical contract discrepancy, not a documentation
claim of equivalence. Main must decide whether to migrate the executable
default, update the canonical matrix, or retain separate local and deployed
defaults before closing the global docs item.

## Recent source decisions

- Added the `color-scheme: light dark` form metadata so native browser controls follow the page's supported themes.
- Added indexed pending-OTP existence checks and an early return in auth cleanup for the empty state.
- Upgraded the Worker test dependency to Vitest 5 while retaining the repository's npm lockfile workflow.
- Consolidated duplicate palette proposals into the single form metadata implementation. The view-transition proposal was not adopted because it added a second lockfile and animation behavior without a product acceptance requirement.

## In-flight and release notes

Source changes require repository-native checks and CI readback before merge. BETA/package publication and live protocol evidence are separate from source merge. Stable promotion is a separate release decision and is not implied by this handover.

Rollback is the normal reviewed revert of the source commit and package dependency update. Preserve the prior lockfile and source revision in version control; do not delete local credential or session data as part of a code rollback.

## Week-one operator checklist

1. Confirm the intended transport and credential mode.
2. Install with the documented `uv` and `npm` commands.
3. Run lint, type, Python tests, Worker tests, and Worker type checks.
4. Exercise one representative read-only Telegram domain operation with approved credentials.
5. Confirm per-subject credential isolation and pending-OTP expiry behavior.
6. Review the exact CI run and artifact identity before using a BETA package.

## Triage

- Form theme mismatch: inspect the rendered `<head>` and the shared renderer version.
- OTP cleanup regression: inspect the shared pending-OTP index and run the auth-store tests with an in-memory backend.
- Worker dependency mismatch: remove `node_modules`, run `npm ci`, and rerun the Worker tests; never edit the lockfile manually.
- Authentication failures: distinguish missing credentials, malformed documented credential input, and provider rejection before rotating anything.
