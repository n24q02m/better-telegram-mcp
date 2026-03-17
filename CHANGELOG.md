# CHANGELOG

<!-- version list -->

## v1.3.0 (2026-03-17)

### Bug Fixes

- Add security hardening for path traversal, SSRF, and info disclosure
  ([`2f2e200`](https://github.com/n24q02m/better-telegram-mcp/commit/2f2e2009f64a93baf1bb1c4713f641a6f9cdefcf))

- Fix 'Too many arguments in chats' code health issue
  ([#5](https://github.com/n24q02m/better-telegram-mcp/pull/5),
  [`a872546`](https://github.com/n24q02m/better-telegram-mcp/commit/a87254680a7f4076de76ae4af98155b6bc1a3b89))

- Prevent command injection in terminal execution
  ([#12](https://github.com/n24q02m/better-telegram-mcp/pull/12),
  [`9655bb9`](https://github.com/n24q02m/better-telegram-mcp/commit/9655bb93d01dbfe84f07f841a3791c8e27810ab3))

- Resolve ty type checker CI failure and align README with portfolio standard
  ([`8906b49`](https://github.com/n24q02m/better-telegram-mcp/commit/8906b49de61af1f90be760aedfd85bd1a42cd9d1))

- **ci**: Use pull_request_target for jobs requiring secrets
  ([`16d9204`](https://github.com/n24q02m/better-telegram-mcp/commit/16d92044b7c5b96437822e1964ade8c381c0d95e))

- **deps**: Update non-major dependencies
  ([#18](https://github.com/n24q02m/better-telegram-mcp/pull/18),
  [`060b5ce`](https://github.com/n24q02m/better-telegram-mcp/commit/060b5ce218ae202ee723f4532265555d1bf3e3ce))

### Chores

- Standardize repo files across MCP server portfolio
  ([`5756415`](https://github.com/n24q02m/better-telegram-mcp/commit/57564158767a72ba10dffe04f66ba13a514098a0))

- Trigger Glama repo resync after history rewrite
  ([`3c69363`](https://github.com/n24q02m/better-telegram-mcp/commit/3c693632bb792177ab69e5ba27b29ed211964e72))

- **config**: Migrate config renovate.json
  ([#21](https://github.com/n24q02m/better-telegram-mcp/pull/21),
  [`35a12ab`](https://github.com/n24q02m/better-telegram-mcp/commit/35a12ab44a6b6da849858a867a7de86d5dcf6033))

- **deps**: Lock file maintenance ([#20](https://github.com/n24q02m/better-telegram-mcp/pull/20),
  [`09aaed9`](https://github.com/n24q02m/better-telegram-mcp/commit/09aaed91057a03689a86c23ec489c84339f8466d))

- **deps**: Update actions/download-artifact digest to 3e5f45b
  ([#15](https://github.com/n24q02m/better-telegram-mcp/pull/15),
  [`8d4cb4e`](https://github.com/n24q02m/better-telegram-mcp/commit/8d4cb4ed20238e23b27d69343cda0ead1ff03b1f))

- **deps**: Update astral-sh/setup-uv digest to 37802ad
  ([#16](https://github.com/n24q02m/better-telegram-mcp/pull/16),
  [`76c8e27`](https://github.com/n24q02m/better-telegram-mcp/commit/76c8e273cd74ab3c38056579202d4cf347afd9bb))

- **deps**: Update dawidd6/action-send-mail action to v15
  ([#19](https://github.com/n24q02m/better-telegram-mcp/pull/19),
  [`3acb374`](https://github.com/n24q02m/better-telegram-mcp/commit/3acb374ffc76720b83f56b1938c12114d0b10eea))

- **deps**: Update step-security/harden-runner digest to fa2e9d6
  ([#17](https://github.com/n24q02m/better-telegram-mcp/pull/17),
  [`3e7819a`](https://github.com/n24q02m/better-telegram-mcp/commit/3e7819a96cecd4645f3b4d34f41bd84bac5ab40c))

### Code Style

- Format test_user_backend.py with ruff
  ([#6](https://github.com/n24q02m/better-telegram-mcp/pull/6),
  [`2d10e35`](https://github.com/n24q02m/better-telegram-mcp/commit/2d10e3522af07ca8a6cf76bab2a3c0d91048abe2))

### Features

- Add test for clear_cache exception handling
  ([#6](https://github.com/n24q02m/better-telegram-mcp/pull/6),
  [`2d10e35`](https://github.com/n24q02m/better-telegram-mcp/commit/2d10e3522af07ca8a6cf76bab2a3c0d91048abe2))

- Refactor `messages` tool to use `MessagesArgs` struct model
  ([#10](https://github.com/n24q02m/better-telegram-mcp/pull/10),
  [`9fecb96`](https://github.com/n24q02m/better-telegram-mcp/commit/9fecb96b68235be04488249d7fafe13718ab5061))

- Refactor config tool to extract match cases into separate functions
  ([#7](https://github.com/n24q02m/better-telegram-mcp/pull/7),
  [`92f06c1`](https://github.com/n24q02m/better-telegram-mcp/commit/92f06c13038ab1fbc8b5ca562d87beda66be7cca))

- Test: cover send_code exception in user mode lifespan
  ([#4](https://github.com/n24q02m/better-telegram-mcp/pull/4),
  [`e7986b6`](https://github.com/n24q02m/better-telegram-mcp/commit/e7986b66839e0644d5d14a0e1a7e2355a028bce3))

### Testing

- Add clear_cache exception test ([#6](https://github.com/n24q02m/better-telegram-mcp/pull/6),
  [`2d10e35`](https://github.com/n24q02m/better-telegram-mcp/commit/2d10e3522af07ca8a6cf76bab2a3c0d91048abe2))

- Cover `send_code` exception in user mode lifespan
  ([#4](https://github.com/n24q02m/better-telegram-mcp/pull/4),
  [`e7986b6`](https://github.com/n24q02m/better-telegram-mcp/commit/e7986b66839e0644d5d14a0e1a7e2355a028bce3))

- Cover `send_code` exception in user mode lifespan and fix formatting
  ([#4](https://github.com/n24q02m/better-telegram-mcp/pull/4),
  [`e7986b6`](https://github.com/n24q02m/better-telegram-mcp/commit/e7986b66839e0644d5d14a0e1a7e2355a028bce3))


## v1.2.0 (2026-03-15)

### Bug Fixes

- Remove real phone number and API ID from README examples
  ([`bf55ea4`](https://github.com/n24q02m/better-telegram-mcp/commit/bf55ea40a5827e6e3147043a11c523b10c273af0))

### Chores

- Align repo structure, CI/CD, and config with reference MCP servers
  ([`30413ea`](https://github.com/n24q02m/better-telegram-mcp/commit/30413eafa864d8db02fbb1bfa33cf47e1375df9b))

### Documentation

- Rewrite README with runtime auth flow, fix user mode UX documentation
  ([`b80761d`](https://github.com/n24q02m/better-telegram-mcp/commit/b80761d6370b909f064c6f2820cc19fbccfa3558))

### Features

- Open terminal for direct OTP input, fallback to config tool for headless
  ([`56e7f08`](https://github.com/n24q02m/better-telegram-mcp/commit/56e7f08298f3babdf90bec213db8504b3957d8c1))


## v1.1.2 (2026-03-15)

### Bug Fixes

- List_contacts uses GetContactsRequest (get_contacts not in Telethon)
  ([`658e9a7`](https://github.com/n24q02m/better-telegram-mcp/commit/658e9a7e59030284ee1e29d22347b208b4997534))

### Testing

- Add user mode integration tests with live MTProto API
  ([`658e9a7`](https://github.com/n24q02m/better-telegram-mcp/commit/658e9a7e59030284ee1e29d22347b208b4997534))


## v1.1.1 (2026-03-15)

### Bug Fixes

- Catch send_code errors in lifespan to prevent server crash
  ([`79ac576`](https://github.com/n24q02m/better-telegram-mcp/commit/79ac5765c68a8b9fbd06074e2d9552aabf44667c))


## v1.1.0 (2026-03-15)

### Features

- Automatic runtime auth via config tool, remove mandatory auth CLI
  ([`f896f27`](https://github.com/n24q02m/better-telegram-mcp/commit/f896f27c1b54423da9477e7ef0124b64e9b92dc6))

### Testing

- Add bot mode integration tests with live Telegram API
  ([`eb6316b`](https://github.com/n24q02m/better-telegram-mcp/commit/eb6316b112d952af45c9d9b6717ea987aac902bb))


## v1.0.8 (2026-03-15)

### Bug Fixes

- Add email notify CI job, sync all GitHub secrets, fix minor issues
  ([`a6eca53`](https://github.com/n24q02m/better-telegram-mcp/commit/a6eca5306dbcee78c555b899024904cc8e432289))


## v1.0.7 (2026-03-15)

### Bug Fixes

- Add mcp-name to README for MCP Registry ownership verification
  ([`9b277d9`](https://github.com/n24q02m/better-telegram-mcp/commit/9b277d9d6da9503c28d30185e8941bbd4df6b2fa))


## v1.0.6 (2026-03-15)

### Bug Fixes

- Shorten server.json description to <= 100 chars for MCP Registry
  ([`fa1a39d`](https://github.com/n24q02m/better-telegram-mcp/commit/fa1a39dcba9062382782a29498b3e8440e1706ec))


## v1.0.5 (2026-03-15)

### Bug Fixes

- Add description and repository to server.json for MCP Registry
  ([`a921541`](https://github.com/n24q02m/better-telegram-mcp/commit/a921541aac8edf1fa292f125b2a27db835a38cd7))


## v1.0.4 (2026-03-15)

### Bug Fixes

- Remove LICENSE from .dockerignore, improve README with auth docs and troubleshooting
  ([`1d588c7`](https://github.com/n24q02m/better-telegram-mcp/commit/1d588c75c11d0e3bd3e2f528552deed53eecf506))


## v1.0.3 (2026-03-15)

### Bug Fixes

- Add ty rule ignores for Telethon dynamic types
  ([`925bffc`](https://github.com/n24q02m/better-telegram-mcp/commit/925bffc3233861355f6f58a58e9f65760c61749e))


## v1.0.2 (2026-03-15)

### Bug Fixes

- Implement config.set/cache_clear, topics.list, add missing repo files
  ([`bd385cb`](https://github.com/n24q02m/better-telegram-mcp/commit/bd385cb75c8a2ecb35d76fe3f71fae9e9dc95d76))


## v1.0.1 (2026-03-15)

### Bug Fixes

- Copy README.md and LICENSE in Dockerfile for uv build
  ([`2a907b4`](https://github.com/n24q02m/better-telegram-mcp/commit/2a907b4747bd9137a48a9afcaf069cda8799d012))


## v1.0.0 (2026-03-15)

- Initial Release
