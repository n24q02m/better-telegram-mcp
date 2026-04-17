# CHANGELOG

<!-- version list -->

## v4.5.2 (2026-04-17)

### Bug Fixes

- Update lockfile to include mcp-core 1.1.1
  ([`23e1dfc`](https://github.com/n24q02m/better-telegram-mcp/commit/23e1dfc090c1e307f2d4867bad5166365c13961f))


## v4.5.1 (2026-04-17)

### Bug Fixes

- Bump version to rebuild with mcp-core 1.1.1
  ([`0565a92`](https://github.com/n24q02m/better-telegram-mcp/commit/0565a92bac6f3ebccb4b800d097a347a67cd5358))


## v4.5.0 (2026-04-17)

### Bug Fixes

- Add diacritic preservation pre-commit hook
  ([#324](https://github.com/n24q02m/better-telegram-mcp/pull/324),
  [`97351c9`](https://github.com/n24q02m/better-telegram-mcp/commit/97351c97ef3a1737eff97e0f1ec4d51a527802c8))

- Bump authlib to 1.6.11 for CSRF cache bypass (GHSA-jj8c-mmj3-mmgv)
  ([`874aad3`](https://github.com/n24q02m/better-telegram-mcp/commit/874aad31fff05b23089ac49b44d28c8fc1a1c5b6))

- Document live remote URL for HTTP multi-user setup
  ([#323](https://github.com/n24q02m/better-telegram-mcp/pull/323),
  [`15c6c57`](https://github.com/n24q02m/better-telegram-mcp/commit/15c6c57f822eb97c4b234fc947dfc9af898fb362))

- Ignore coverage.xml and htmlcov artifacts
  ([#323](https://github.com/n24q02m/better-telegram-mcp/pull/323),
  [`15c6c57`](https://github.com/n24q02m/better-telegram-mcp/commit/15c6c57f822eb97c4b234fc947dfc9af898fb362))

- Ignore coverage.xml and htmlcov artifacts
  ([`53779fa`](https://github.com/n24q02m/better-telegram-mcp/commit/53779fab745eb62e2d8b9ec4bf3d924578f9ac2c))

- Replace swallowed exceptions with logging in credential_state
  ([`e40cae7`](https://github.com/n24q02m/better-telegram-mcp/commit/e40cae7104834cd3c9df88bce0ddd03fabd865f2))

- **deps**: Bump actions/create-github-app-token digest to 1b10c78
  ([#289](https://github.com/n24q02m/better-telegram-mcp/pull/289),
  [`c79c1d0`](https://github.com/n24q02m/better-telegram-mcp/commit/c79c1d06aadc93dc9c883700ddc0b9347cd0e195))

- **deps**: Bump actions/upload-artifact digest to 043fb46
  ([#278](https://github.com/n24q02m/better-telegram-mcp/pull/278),
  [`ddba3fc`](https://github.com/n24q02m/better-telegram-mcp/commit/ddba3fc7982fb8bf67919059527b93663c816ed2))

- **deps**: Bump docker/build-push-action digest to bcafcac
  ([#290](https://github.com/n24q02m/better-telegram-mcp/pull/290),
  [`5e6fe0e`](https://github.com/n24q02m/better-telegram-mcp/commit/5e6fe0e33798660ee63bba3f4b96a05eb99c2102))

- **deps**: Bump non-major dependencies
  ([#291](https://github.com/n24q02m/better-telegram-mcp/pull/291),
  [`8cdfdc9`](https://github.com/n24q02m/better-telegram-mcp/commit/8cdfdc9a65882508301de13264be69bc9cff13e0))

- **deps**: Lock file maintenance ([#292](https://github.com/n24q02m/better-telegram-mcp/pull/292),
  [`14684e5`](https://github.com/n24q02m/better-telegram-mcp/commit/14684e52b0570031c888eac89c4b50d1159b1540))

### Features

- Add accessible CSS spinners for async loading states in credential form
  ([#295](https://github.com/n24q02m/better-telegram-mcp/pull/295),
  [`84c00b7`](https://github.com/n24q02m/better-telegram-mcp/commit/84c00b74347b9d94a6d3cf20cc9cd690c9c6cbb5))

- Cache trusted_proxy_list using functools.cached_property
  ([`484cbd7`](https://github.com/n24q02m/better-telegram-mcp/commit/484cbd7bfdcf94251f8dc792d3e168b9f6d7944a))

- Optimize OTP cleanup traversal with chronological early-exit
  ([#296](https://github.com/n24q02m/better-telegram-mcp/pull/296),
  [`db23fe3`](https://github.com/n24q02m/better-telegram-mcp/commit/db23fe357027ebebde5c68940637908199eff5dd))

- Use semantic forms for auth UI
  ([`b819ee1`](https://github.com/n24q02m/better-telegram-mcp/commit/b819ee1e9ef2b5ac75a1156a4455f4713db6173f))


## v4.4.2 (2026-04-17)

### Bug Fixes

- Forward PORT env var to run_http in main()
  ([`a34c2c4`](https://github.com/n24q02m/better-telegram-mcp/commit/a34c2c46935dfaa159b13aa7c58017ad8abf7116))


## v4.4.1 (2026-04-17)

### Bug Fixes

- Bump mcp-core pin to 1.1.0 and forward HOST env to run_local_server
  ([`c9e809f`](https://github.com/n24q02m/better-telegram-mcp/commit/c9e809f4cd711919b41d0b6be7fb67f83a4b36cd))

### Chores

- Ignore AI assistant traces
  ([`e94643d`](https://github.com/n24q02m/better-telegram-mcp/commit/e94643dba139edcee9e5e64ae4142f850c2a7ef4))


## v4.4.0 (2026-04-13)

### Bug Fixes

- Add cryptg dependency for Telethon MTProto decryption
  ([`884662c`](https://github.com/n24q02m/better-telegram-mcp/commit/884662cc34c7367ed013faa8d52751a399cc313d))

- Add missing config setup actions to README
  ([`a6c0f65`](https://github.com/n24q02m/better-telegram-mcp/commit/a6c0f6584c05299abbfaef38ab71f468aa583e03))

- Add tests for UserBackend.sign_in chmod path
  ([#270](https://github.com/n24q02m/better-telegram-mcp/pull/270),
  [`fd019fa`](https://github.com/n24q02m/better-telegram-mcp/commit/fd019fadcffd4e596257ae455cab233ab2f2f58c))

- Block sensitive paths on macOS firmlinks
  ([`82ba023`](https://github.com/n24q02m/better-telegram-mcp/commit/82ba023f9eea829320891010e2f5a60ad725032d))

- Bump n24q02m-mcp-core to >=1.0.0 stable
  ([`1ac3c06`](https://github.com/n24q02m/better-telegram-mcp/commit/1ac3c06b1e3d3ed5464d5743a845c0da908fd752))

- Cache static help docs in memory
  ([`04f6954`](https://github.com/n24q02m/better-telegram-mcp/commit/04f695429ee7488df096536c4f06ca41b96024b1))

- Drop local uv.sources override for n24q02m-mcp-core
  ([`eccb4bd`](https://github.com/n24q02m/better-telegram-mcp/commit/eccb4bd8a6e8923281a732d599e7969f05cce386))

- Flatten relay_schema for mcp-core credential form rendering
  ([`33f9821`](https://github.com/n24q02m/better-telegram-mcp/commit/33f98211c9b1cc1ae41fa430145dac3342b6c9a1))

- Improve relay UX when Telethon session already authorized
  ([`0dc0fdb`](https://github.com/n24q02m/better-telegram-mcp/commit/0dc0fdbb5b43738f31faa6c24d441f12b61527eb))

- Lock file maintenance
  ([`91a089d`](https://github.com/n24q02m/better-telegram-mcp/commit/91a089df716dc5bc7b28bc2f559ef017a4510fa7))

- Make credential callbacks async to avoid running-loop error
  ([`bdb5a52`](https://github.com/n24q02m/better-telegram-mcp/commit/bdb5a5242f0a3a394c23c813857ecc7c917f9381))

- Remove dead relay-based OTP flow replaced by /otp endpoint
  ([`85d8204`](https://github.com/n24q02m/better-telegram-mcp/commit/85d8204bb1b526c4da6e40abf27ba42cde0f6a92))

- Remove stale ty ignore directives after type inference improvements
  ([`d290442`](https://github.com/n24q02m/better-telegram-mcp/commit/d2904420c25e8939d9596023fed7da90fd99b02a))

- Unblock CI install by removing editable mcp-relay-core source
  ([`8ace5bf`](https://github.com/n24q02m/better-telegram-mcp/commit/8ace5bfffebbee08852f442c6db6cebd8cf027a5))

- Update non-major dependencies
  ([`93f721b`](https://github.com/n24q02m/better-telegram-mcp/commit/93f721b2173a69f8fe5d54c9e85b2e592df21d1d))

- Update python:3.13-slim-bookworm docker digest to 061b6e5
  ([`9de3fcb`](https://github.com/n24q02m/better-telegram-mcp/commit/9de3fcb449d6c6915daa2429d834a290f9b2ee68))

- Update step-security/harden-runner digest to f808768
  ([`aba2946`](https://github.com/n24q02m/better-telegram-mcp/commit/aba2946a8cb4b79376bf338758b3d76399a935db))

- User mode returns info next_step instead of immediate complete
  ([`b14078d`](https://github.com/n24q02m/better-telegram-mcp/commit/b14078d6d28d613e59afae4861c0e11e32d67e43))

- **deps**: Update non-major dependencies
  ([#250](https://github.com/n24q02m/better-telegram-mcp/pull/250),
  [`a97470e`](https://github.com/n24q02m/better-telegram-mcp/commit/a97470e20314ef233ba824666a96855f91ade079))

### Chores

- **deps**: Bump cryptography in the uv group across 1 directory
  ([#254](https://github.com/n24q02m/better-telegram-mcp/pull/254),
  [`36ec398`](https://github.com/n24q02m/better-telegram-mcp/commit/36ec398f477f09e86a9b13e68e64367305fdd6d6))

- **deps**: Lock file maintenance ([#251](https://github.com/n24q02m/better-telegram-mcp/pull/251),
  [`93cbd5a`](https://github.com/n24q02m/better-telegram-mcp/commit/93cbd5a6af44656ebbda5fbf959852295e70d9f4))

- **deps**: Update dependency cryptography to v46.0.7 [security]
  ([#256](https://github.com/n24q02m/better-telegram-mcp/pull/256),
  [`c7ec0b3`](https://github.com/n24q02m/better-telegram-mcp/commit/c7ec0b324c89647cca86ec0a6819b2ecb0202315))

### Features

- Add cross-OS CI matrix (ubuntu/windows/macos)
  ([`89d5534`](https://github.com/n24q02m/better-telegram-mcp/commit/89d5534f702a169d87d65587d10cceb0d28cfa14))

- Add on_step_submitted for multi-step OTP via /otp endpoint
  ([`79b0041`](https://github.com/n24q02m/better-telegram-mcp/commit/79b0041d1c0911f8eb2422ca570c96a18ad29d81))

- Default to HTTP transport, --stdio for backward compat
  ([`afe5973`](https://github.com/n24q02m/better-telegram-mcp/commit/afe5973eeedda6e9fc29779a6851705d7796bac1))

- Hot-reload backend after relay credentials are configured
  ([`c94314d`](https://github.com/n24q02m/better-telegram-mcp/commit/c94314d1b0eed69daef22fcb1f8efa1d48bea76a))

- Migrate from mcp-relay-core to mcp-core
  ([`a88004a`](https://github.com/n24q02m/better-telegram-mcp/commit/a88004a6d69be5a8018180f0d5e4da4c3706f12a))

- Migrate to mcp-core Self-hosted AS for HTTP default
  ([`cf1d209`](https://github.com/n24q02m/better-telegram-mcp/commit/cf1d209d4a12eeb430d902ce54534e8c8324f410))

- Restore telegram credential form with Bot/User mode tabs
  ([`eaac8a6`](https://github.com/n24q02m/better-telegram-mcp/commit/eaac8a65bff50ba421b4dd211b55052ada3d4f5b))

- Sync local changes and implement OAuth hot-reload
  ([`4861941`](https://github.com/n24q02m/better-telegram-mcp/commit/48619417af5a346c2bc7a91fd28f512314525224))

- **auth**: Add aria-live regions to status messages
  ([#170](https://github.com/n24q02m/better-telegram-mcp/pull/170),
  [`1b150fc`](https://github.com/n24q02m/better-telegram-mcp/commit/1b150fc84534a47bab3a214b80c6a7d2ce2a72e4))


## v4.3.0 (2026-04-07)

### Bug Fixes

- Add credential state tests for relay redesign
  ([`6d72698`](https://github.com/n24q02m/better-telegram-mcp/commit/6d726989ee2f2a809428ff60df016a637b29087a))

- Apply ruff formatting to credential state tests
  ([`ed98dac`](https://github.com/n24q02m/better-telegram-mcp/commit/ed98dacf1d66dedfd7e388e77fca558191222f1b))

- PBKDF2 600k iterations and random salt migration in session store
  ([`48987f3`](https://github.com/n24q02m/better-telegram-mcp/commit/48987f38fe3a5144c90cd67f75bbe251667ff28e))

- Remove BETA markers and promote relay as primary setup method
  ([`c8c05fa`](https://github.com/n24q02m/better-telegram-mcp/commit/c8c05fa79edb42257184671b67a6e06d1447d55e))

- Resolve ruff lint errors in credential state tests
  ([`1a5a374`](https://github.com/n24q02m/better-telegram-mcp/commit/1a5a374d37109ad28102b9397a030006588dccc6))

- Sync uv.lock with current version
  ([`328705f`](https://github.com/n24q02m/better-telegram-mcp/commit/328705fe3abab4ce64c2437f25b032e85bc5c533))

### Features

- Migrate code review from Qodo to CodeRabbit
  ([#211](https://github.com/n24q02m/better-telegram-mcp/pull/211),
  [`065e50d`](https://github.com/n24q02m/better-telegram-mcp/commit/065e50dbd61b956d370f7722dc19b9e4b7ba3d5b))


## v4.3.0-beta.1 (2026-04-07)

### Features

- Add setup actions to config tool for relay trigger
  ([`0bb2979`](https://github.com/n24q02m/better-telegram-mcp/commit/0bb2979b699345da5441975d7e08cc18663aace1))


## v4.2.0 (2026-04-06)

### Bug Fixes

- Mark relay as BETA, promote env vars as primary setup method
  ([`756bf22`](https://github.com/n24q02m/better-telegram-mcp/commit/756bf223c32f6c76a39c27b0555a22723ea6b95a))

### Features

- Non-blocking relay with state machine and lazy trigger
  ([`567f08a`](https://github.com/n24q02m/better-telegram-mcp/commit/567f08ab22f9c5999a2e0f50de863d3c10fd5c9f))


## v4.1.0 (2026-04-04)

### Bug Fixes

- CSRF token protection, auth_server tests, dependency updates, and test improvements
  ([#169](https://github.com/n24q02m/better-telegram-mcp/pull/169),
  [`1f743de`](https://github.com/n24q02m/better-telegram-mcp/commit/1f743de1a8cad73bd835cb8fefeb70c5c9cdc132))

### Features

- Add agent/manual setup guides, simplify README, cleanup root
  ([`1dad3c9`](https://github.com/n24q02m/better-telegram-mcp/commit/1dad3c9ea91b4e5517d4274bc6cd81477ad30b8e))


## v4.0.1 (2026-04-03)

### Bug Fixes

- Consolidated security fixes, dependency updates, and test improvements
  ([#135](https://github.com/n24q02m/better-telegram-mcp/pull/135),
  [`07ad289`](https://github.com/n24q02m/better-telegram-mcp/commit/07ad289ea120d3965139040e34564a108f04685a))

- Scope marketplace sync token to claude-plugins repo
  ([`4e83bdb`](https://github.com/n24q02m/better-telegram-mcp/commit/4e83bdb6dc3a5a30caad2e6a1a5ba75c9f3432d0))


## v4.0.0 (2026-04-03)

### Bug Fixes

- HTTP single-user mode respects env vars before CredentialStore
  ([`4a88149`](https://github.com/n24q02m/better-telegram-mcp/commit/4a881490a186825ceb84d28901d9ab308aad93a5))

### Documentation

- Fix tool names in README to match server.py (singular form)
  ([`f13241a`](https://github.com/n24q02m/better-telegram-mcp/commit/f13241a3eab3648d0e955f428fc0fae7ecc808d8))

### Features

- Implement multi-user HTTP MCP endpoint with per-user backend isolation
  ([`eb76960`](https://github.com/n24q02m/better-telegram-mcp/commit/eb76960c2d372f516bf286aa723122faae9ccf4c))

- Remove deprecated Gemini CLI extension support
  ([`0175c8a`](https://github.com/n24q02m/better-telegram-mcp/commit/0175c8a1526331d686598d8703b5010203dd9c20))

- Split telegram tool into message/chat/media/contact domains
  ([`4dc5022`](https://github.com/n24q02m/better-telegram-mcp/commit/4dc50227fcc89d8a810d8d5d6e0bf324ecfa0d3a))

### Refactoring

- Remove legacy auth flow, auto-open browser in relay setup
  ([`a2e27d1`](https://github.com/n24q02m/better-telegram-mcp/commit/a2e27d13c7ee588455aa9c91c7bfd78ae8d3b57b))

### Testing

- Add consolidated E2E test with relay/env/plugin and bot/user modes
  ([`6fcf715`](https://github.com/n24q02m/better-telegram-mcp/commit/6fcf715a6c99eb2d0dbebcbb41c1cf1dd67d7c4b))

### Breaking Changes

- Auth_server.py and auth_client.py are no longer used for user mode OTP authentication. All auth
  flows go through relay bidirectional messaging (mcp-relay-core).


## v3.5.0 (2026-03-31)

### Bug Fixes

- **cd**: Remove orphan build-auth-relay from sync-marketplace needs
  ([`1b588c4`](https://github.com/n24q02m/better-telegram-mcp/commit/1b588c415f5cf3936ea52a1f931c96e07f9a1f77))

- **deps**: Update non-major dependencies
  ([#92](https://github.com/n24q02m/better-telegram-mcp/pull/92),
  [`2996bb6`](https://github.com/n24q02m/better-telegram-mcp/commit/2996bb6fdb0883dcbf1a31bf1de7a48e57f4370d))

- **test**: Skip Unix-only path traversal tests on Windows
  ([#99](https://github.com/n24q02m/better-telegram-mcp/pull/99),
  [`e5a4c74`](https://github.com/n24q02m/better-telegram-mcp/commit/e5a4c7443001a686f6af1c472e49406f6d5a80b9))

### Chores

- **deps**: Lock file maintenance ([#93](https://github.com/n24q02m/better-telegram-mcp/pull/93),
  [`0a429c1`](https://github.com/n24q02m/better-telegram-mcp/commit/0a429c13ecb183c60fef681ba7c31abf90dbc63d))

### Continuous Integration

- Fix Qodo vertex_ai config, VERTEXAI_LOCATION, and Renovate PSR rule
  ([`72c7447`](https://github.com/n24q02m/better-telegram-mcp/commit/72c7447801634d8246eb84301d9d4b2c0971eaef))

- **cd**: Add plugin marketplace sync on stable release
  ([`4196543`](https://github.com/n24q02m/better-telegram-mcp/commit/4196543f52eb16586cd8ca551acef132a0ede390))

### Refactoring

- Remove orphan auth-relay, hardcode Telegram app credentials
  ([`83dde3b`](https://github.com/n24q02m/better-telegram-mcp/commit/83dde3b0e563e1342a2416b4f48d1cf0c7d9c34a))


## v3.5.0-beta.1 (2026-03-30)

### Bug Fixes

- Pin Docker base image SHA in auth-relay Dockerfile
  ([`1b74b88`](https://github.com/n24q02m/better-telegram-mcp/commit/1b74b88bd39d503239e349bbfb4d4254f3a0de6d))

- Resolve coverage regression and Windows test compatibility
  ([`0894b37`](https://github.com/n24q02m/better-telegram-mcp/commit/0894b37451ec68d4b080ad55e3a6d664057c4051))

### Features

- Add multi-user HTTP mode with per-user credential isolation
  ([#96](https://github.com/n24q02m/better-telegram-mcp/pull/96),
  [`075b5b0`](https://github.com/n24q02m/better-telegram-mcp/commit/075b5b08ade1e833ac514fe20e915b5204289b01))


## v3.4.0 (2026-03-28)

### Bug Fixes

- Bump mcp-relay-core to >=1.0.5
  ([`50c0f66`](https://github.com/n24q02m/better-telegram-mcp/commit/50c0f6663bbfab6c3dbbffb4405a3d696e70c744))

- Check saved session files after relay skip
  ([`6dc591b`](https://github.com/n24q02m/better-telegram-mcp/commit/6dc591b742189e94b27a6302c3c5430618471b3f))

- Credential resolution order -- relay only when no local credentials
  ([`bfc90c6`](https://github.com/n24q02m/better-telegram-mcp/commit/bfc90c6f58b42f8075147f21a6b3b06058d61341))

- Pin Docker base images to SHA digests
  ([`2cbd9ba`](https://github.com/n24q02m/better-telegram-mcp/commit/2cbd9ba4c43039d10022a304fc2a14e6875b861b))

- Pin pre-commit hooks to commit SHA
  ([`b3e2333`](https://github.com/n24q02m/better-telegram-mcp/commit/b3e23339e7417c1ef3455172fe0baa596fffc4be))

- Send complete message to relay page after config saved
  ([`bef96aa`](https://github.com/n24q02m/better-telegram-mcp/commit/bef96aa01ed89dbe5770a831c65da3b17bfb552d))

- Skip auth_client when relay already handled user-mode setup
  ([`d68f2a1`](https://github.com/n24q02m/better-telegram-mcp/commit/d68f2a19c931f2c3ce570dd3bd4c800543a54427))

- **cd**: Remove empty env blocks from OIDC migration
  ([`faaf477`](https://github.com/n24q02m/better-telegram-mcp/commit/faaf477fef0e0c26f42e3bf579a745bea78a97b5))

- **cd**: Replace GH_PAT with GitHub App installation token
  ([`835b7bb`](https://github.com/n24q02m/better-telegram-mcp/commit/835b7bbf7468c301d1ce19a91df3a6acc95ca225))

- **cd**: Use PyPI OIDC trusted publishing instead of PYPI_TOKEN
  ([`8b2af0c`](https://github.com/n24q02m/better-telegram-mcp/commit/8b2af0c19b8765481806135439a0b23be600a821))

- **ci**: Consolidate SMTP_USERNAME and NOTIFY_EMAIL into one secret
  ([`7148b24`](https://github.com/n24q02m/better-telegram-mcp/commit/7148b2442c6d2330d3c8cbcdc9a433abd4b0e0ab))

- **ci**: Consolidate SMTP_USERNAME+PASSWORD into SMTP_CREDENTIAL
  ([`39558b4`](https://github.com/n24q02m/better-telegram-mcp/commit/39558b4dad966a228265099f8ab6cdc76c828332))

- **ci**: Remove CODECOV_TOKEN, use tokenless upload
  ([`3ee4fbc`](https://github.com/n24q02m/better-telegram-mcp/commit/3ee4fbc96bb2dceee8d0ffa1ea2d25da6c72dd2f))

- **ci**: Use Vertex AI WIF instead of GEMINI_API_KEY for code review
  ([`6ad4732`](https://github.com/n24q02m/better-telegram-mcp/commit/6ad473266a2f39cb452f0a00c08a3f5f8d64882a))

- **deps**: Update non-major dependencies
  ([#85](https://github.com/n24q02m/better-telegram-mcp/pull/85),
  [`918bd38`](https://github.com/n24q02m/better-telegram-mcp/commit/918bd385559a91005ea9e8628b78dbc06c6b86e4))

- **deps**: Update non-major dependencies
  ([#82](https://github.com/n24q02m/better-telegram-mcp/pull/82),
  [`ddafab8`](https://github.com/n24q02m/better-telegram-mcp/commit/ddafab81e723519346e34004f532102e5594d833))

### Chores

- **deps**: Lock file maintenance
  ([`931551d`](https://github.com/n24q02m/better-telegram-mcp/commit/931551dddd89b725a0d347723edfc8ebf0f78519))

- **deps**: Update actions/create-github-app-token action to v3
  ([#88](https://github.com/n24q02m/better-telegram-mcp/pull/88),
  [`4a075bd`](https://github.com/n24q02m/better-telegram-mcp/commit/4a075bdf0b0f7bd8afa0857f530304a26337350c))

- **deps**: Update codecov/codecov-action action to v6
  ([#83](https://github.com/n24q02m/better-telegram-mcp/pull/83),
  [`f124484`](https://github.com/n24q02m/better-telegram-mcp/commit/f124484ab811a8d3339a7a9f0e50023a506ab5ca))

- **deps**: Update google-github-actions/auth action to v3
  ([#89](https://github.com/n24q02m/better-telegram-mcp/pull/89),
  [`c8b6191`](https://github.com/n24q02m/better-telegram-mcp/commit/c8b6191c02d1c1e6e97ec0bcad2ebe2e70e863e0))

### Features

- Integrate Telegram OTP/2FA auth into relay messaging
  ([`b75ba48`](https://github.com/n24q02m/better-telegram-mcp/commit/b75ba48f18dcb7cb71dc7dcc48752a2c4dae0cd5))

- Relay-first startup — always show relay URL
  ([`83b56ab`](https://github.com/n24q02m/better-telegram-mcp/commit/83b56abeeb7412cb32435d8a00d310747c19d4dc))

- Unblock async init flow by running webbrowser.open as background task
  ([#66](https://github.com/n24q02m/better-telegram-mcp/pull/66),
  [`6ed2ba7`](https://github.com/n24q02m/better-telegram-mcp/commit/6ed2ba7471a557dcbaba5c73ee75c47cdf2df685))

### Performance Improvements

- Run webbrowser.open in background task to avoid blocking initialization
  ([#66](https://github.com/n24q02m/better-telegram-mcp/pull/66),
  [`6ed2ba7`](https://github.com/n24q02m/better-telegram-mcp/commit/6ed2ba7471a557dcbaba5c73ee75c47cdf2df685))

### Testing

- Fix relay_setup tests and improve coverage
  ([`664d6de`](https://github.com/n24q02m/better-telegram-mcp/commit/664d6de371f28e19b3e581cd631a62e564098b5e))


## v3.3.0 (2026-03-26)

### Chores

- Add server.json to PSR version_variables, sync version
  ([`55f9828`](https://github.com/n24q02m/better-telegram-mcp/commit/55f98281c48df8319a3b3d8b63ac3d47c4a944df))

- Clean up plugin manifest for best practices
  ([`ec970b4`](https://github.com/n24q02m/better-telegram-mcp/commit/ec970b435bf65b56ea6c607c410c26688f6644f1))

### Documentation

- Fix marketplace references, improve Gemini CLI extension config
  ([`c3c6b26`](https://github.com/n24q02m/better-telegram-mcp/commit/c3c6b26a0e701765558a2d12be0f7ad5cdf7641e))

- Standardize README structure
  ([`1c7cdcf`](https://github.com/n24q02m/better-telegram-mcp/commit/1c7cdcf480b0279fb88a470a9048e7ce6972505b))


## v3.3.0-beta.1 (2026-03-25)

### Bug Fixes

- Align gemini-extension.json key with plugin.json
  ([`02c2579`](https://github.com/n24q02m/better-telegram-mcp/commit/02c2579b5c04e26a9bb398839c975828bfe1a414))

- Auto-sync plugin.json version via PSR
  ([`952b6ca`](https://github.com/n24q02m/better-telegram-mcp/commit/952b6ca67e2f4c9d34c124e7eb866529dfebcc80))

- Correct plugin install commands per official docs
  ([`322a9e0`](https://github.com/n24q02m/better-telegram-mcp/commit/322a9e01789b24557bf44668045329b120a69448))

- Handle empty string credentials + remove empty env vars from configs
  ([`fc713ac`](https://github.com/n24q02m/better-telegram-mcp/commit/fc713ace1ccf83be248d5525c0d8b66b3e7cd72a))

- Remove env from README MCP config examples
  ([`112fe1a`](https://github.com/n24q02m/better-telegram-mcp/commit/112fe1a0fec1b4e48c839f6be2942a528649840f))

- Remove env vars from plugin.json to prevent overwriting user config
  ([`47997da`](https://github.com/n24q02m/better-telegram-mcp/commit/47997dafea5cf4ece403e90cfbdebc83a5519b68))

- Remove pr-title-check job from CI
  ([`8c7d0cf`](https://github.com/n24q02m/better-telegram-mcp/commit/8c7d0cff0a6761b19905f1da96172437880ed14a))

- Switch mcp-relay-core from git dep to published PyPI package
  ([#77](https://github.com/n24q02m/better-telegram-mcp/pull/77),
  [`76b207f`](https://github.com/n24q02m/better-telegram-mcp/commit/76b207f0d4daa04db199994c907cd282bf2c834f))

- Sync plugin.json version and add skills/hooks references
  ([`8d54d4f`](https://github.com/n24q02m/better-telegram-mcp/commit/8d54d4fec376db09ff1d4c1cd4d9ba79b6ab3932))

- Unify Plugin install section with marketplace + individual options
  ([`d47409c`](https://github.com/n24q02m/better-telegram-mcp/commit/d47409c6a124a9d209f0a3169ccce89e7a783d48))

- Update ruff pre-commit hook to v0.15.7
  ([`e74a65c`](https://github.com/n24q02m/better-telegram-mcp/commit/e74a65c5406e0d7ed0199a7271657f63fc710501))

- Use version_variables for JSON files in PSR config
  ([`bdfd83e`](https://github.com/n24q02m/better-telegram-mcp/commit/bdfd83e066d5db669f735df53ff08adf19309aa7))

### Chores

- Add docker-compose overlay for HTTP mode deployment
  ([#77](https://github.com/n24q02m/better-telegram-mcp/pull/77),
  [`76b207f`](https://github.com/n24q02m/better-telegram-mcp/commit/76b207f0d4daa04db199994c907cd282bf2c834f))

### Documentation

- Add relay files to CLAUDE.md file structure
  ([`1d557a7`](https://github.com/n24q02m/better-telegram-mcp/commit/1d557a7e8a741d23d7fb325e2eb20aec51f20209))

- Add zero-config relay setup section to README
  ([`fefe28a`](https://github.com/n24q02m/better-telegram-mcp/commit/fefe28a83bf0953507826374f7e3d464e1d0d086))

### Features

- Add complete env vars and pipx mode to plugin config
  ([`20f9dd5`](https://github.com/n24q02m/better-telegram-mcp/commit/20f9dd5b07231316ad7d99817aa14841f0feae90))

- Add Gemini CLI extension config with PSR version sync
  ([`372c34b`](https://github.com/n24q02m/better-telegram-mcp/commit/372c34be9f0da3834807787c29cb390b074e01b0))

- Add HTTP transport mode with encrypted credential store
  ([#77](https://github.com/n24q02m/better-telegram-mcp/pull/77),
  [`76b207f`](https://github.com/n24q02m/better-telegram-mcp/commit/76b207f0d4daa04db199994c907cd282bf2c834f))

- Add zero-env-config relay setup via mcp-relay-core
  ([#77](https://github.com/n24q02m/better-telegram-mcp/pull/77),
  [`76b207f`](https://github.com/n24q02m/better-telegram-mcp/commit/76b207f0d4daa04db199994c907cd282bf2c834f))

- Multi-mode plugin config (stdio + docker + http)
  ([`65677c9`](https://github.com/n24q02m/better-telegram-mcp/commit/65677c9c5143ca49c0d693c2bf65976d34679ede))

- Standardize README with MCP Resources, Security, collapsible clients
  ([`571b230`](https://github.com/n24q02m/better-telegram-mcp/commit/571b23067be1e7a8248260f7cd8829073947828e))

- Zero-env-config relay setup + HTTP transport mode
  ([#77](https://github.com/n24q02m/better-telegram-mcp/pull/77),
  [`76b207f`](https://github.com/n24q02m/better-telegram-mcp/commit/76b207f0d4daa04db199994c907cd282bf2c834f))


## v3.2.0 (2026-03-24)

### Bug Fixes

- Add gitleaks secret detection to pre-commit hooks
  ([`180fbd5`](https://github.com/n24q02m/better-telegram-mcp/commit/180fbd54f219946de45c118b9df8cc372491f27f))

- Apply ruff formatting to pass CI lint check
  ([`437cf10`](https://github.com/n24q02m/better-telegram-mcp/commit/437cf108568b3d02917db1877a9e62ad30a4a56c))

### Testing

- Add full/real bot mode tests via MCP protocol
  ([`77277b2`](https://github.com/n24q02m/better-telegram-mcp/commit/77277b28adca75a7f5ce5ba0aa58eef9b3aecf70))


## v3.2.0-beta.1 (2026-03-23)

### Bug Fixes

- Allow help/config tools without credentials, add actionable setup hints
  ([`125f855`](https://github.com/n24q02m/better-telegram-mcp/commit/125f855de78ea08adf92818e2fe5b24dd737082b))

- Correct plugin packaging paths and marketplace schema
  ([`d9065e0`](https://github.com/n24q02m/better-telegram-mcp/commit/d9065e03c458787637c0787274f8fd8e52d1cf52))

- Correct setup-bot skill to use env var instead of runtime config for bot token
  ([`c97797b`](https://github.com/n24q02m/better-telegram-mcp/commit/c97797bbd4a88043f0d6cc462ee8ee263d7ce83a))

- Improve tool descriptions and corrective errors for LLM call pass rate
  ([`6f79799`](https://github.com/n24q02m/better-telegram-mcp/commit/6f79799f0b47e7b38c9b1b9346a977f3a7912cca))

- Standardize README structure with plugin-first Quick Start
  ([`722fc45`](https://github.com/n24q02m/better-telegram-mcp/commit/722fc45dc516173dfe20835a8550d90dc6056b6f))

- Sync plugin.json and server.json to v3.1.2
  ([`9a365b0`](https://github.com/n24q02m/better-telegram-mcp/commit/9a365b0b3b67e5773e58c7a4f694e9f5171d633c))

### Chores

- **deps**: Lock file maintenance ([#46](https://github.com/n24q02m/better-telegram-mcp/pull/46),
  [`1ae96c6`](https://github.com/n24q02m/better-telegram-mcp/commit/1ae96c6265a268352761acf59ec16d6869032644))

- **deps**: Update non-major dependencies
  ([#45](https://github.com/n24q02m/better-telegram-mcp/pull/45),
  [`f44696f`](https://github.com/n24q02m/better-telegram-mcp/commit/f44696fe27bc463fc564accdf1e706756f1acfa5))

- **deps**: Update qodo-ai/pr-agent digest to 42d55d4
  ([#50](https://github.com/n24q02m/better-telegram-mcp/pull/50),
  [`23d29a2`](https://github.com/n24q02m/better-telegram-mcp/commit/23d29a2f26f6c0f3f69b2e62dfb8816b9d364700))

### Documentation

- Add TELEGRAM_BOT_TOKEN env to plugin.json and setup guide
  ([`6090687`](https://github.com/n24q02m/better-telegram-mcp/commit/6090687b946789dc844eb5133d993b31421a4eca))

- Standardize README sections and sync Also by table
  ([`5ccee24`](https://github.com/n24q02m/better-telegram-mcp/commit/5ccee242737dc2b0c1f0ca90c20432551d8fb2fa))

### Features

- Add plugin packaging with skills, hooks, and marketplace metadata
  ([`26c7d1e`](https://github.com/n24q02m/better-telegram-mcp/commit/26c7d1e0818fae8712aced32e5717a8d24f58e2b))

- Async help tool I/O ([#52](https://github.com/n24q02m/better-telegram-mcp/pull/52),
  [`f26cd4b`](https://github.com/n24q02m/better-telegram-mcp/commit/f26cd4bbc7602fea23283bf37b50440da84f6585))

- Improve tool descriptions and error messages for better LLM pass rate
  ([`9b9909e`](https://github.com/n24q02m/better-telegram-mcp/commit/9b9909e74467cdd25238a72b39f0dd4aa231b3c6))

### Refactoring

- Redesign skills/hooks per approved spec
  ([`e933160`](https://github.com/n24q02m/better-telegram-mcp/commit/e93316006ff2e9b001f55179f8419b01197190d5))

### Testing

- Add pytest-based live MCP protocol tests
  ([`2013653`](https://github.com/n24q02m/better-telegram-mcp/commit/201365372f12ec0befb5bb4975d8bcf0e026eead))


## v3.1.2 (2026-03-20)

### Bug Fixes

- Improve auth web form UX
  ([`4f2db45`](https://github.com/n24q02m/better-telegram-mcp/commit/4f2db458f0af3382693d8c342f823dd775a86760))

- Rewrite README for accuracy and completeness
  ([`d3262e9`](https://github.com/n24q02m/better-telegram-mcp/commit/d3262e9a3880121ba9d9096fc991e6cc2da23af2))


## v3.1.1 (2026-03-20)

### Bug Fixes

- Add IPv4-mapped IPv6 to SSRF blocklist
  ([#44](https://github.com/n24q02m/better-telegram-mcp/pull/44),
  [`59aee2c`](https://github.com/n24q02m/better-telegram-mcp/commit/59aee2ce996925e312d351fa6c5270fedf511c54))

- Use Path.is_relative_to for path containment checks and expand tool reference docs
  ([`3445da7`](https://github.com/n24q02m/better-telegram-mcp/commit/3445da78345efb13269fda6e7d7a239c01af84ca))

- **ci**: Remove job-level continue-on-error from dependency-review
  ([`86aeea1`](https://github.com/n24q02m/better-telegram-mcp/commit/86aeea1016de4f84d88e3f99fbe35dc0f29807e8))

### Chores

- **deps**: Lock file maintenance ([#23](https://github.com/n24q02m/better-telegram-mcp/pull/23),
  [`1def987`](https://github.com/n24q02m/better-telegram-mcp/commit/1def9878cba893747f9fa23470031d332763d609))

- **deps**: Update codecov/codecov-action digest to 1af5884
  ([#27](https://github.com/n24q02m/better-telegram-mcp/pull/27),
  [`c094a15`](https://github.com/n24q02m/better-telegram-mcp/commit/c094a15bcb1750aff96090dd5498d792877ca678))

- **deps**: Update dawidd6/action-send-mail action to v16
  ([#26](https://github.com/n24q02m/better-telegram-mcp/pull/26),
  [`cc137f4`](https://github.com/n24q02m/better-telegram-mcp/commit/cc137f4cda77b031fb5d9753f4a1b8cc12658986))

### Documentation

- Add PRIVACY.md for data handling transparency
  ([`43cdd94`](https://github.com/n24q02m/better-telegram-mcp/commit/43cdd945cd649f82179795746760dd4552e5b6e4))

- Standardize README, SECURITY, CONTRIBUTING per cross-repo audit
  ([`ba851c7`](https://github.com/n24q02m/better-telegram-mcp/commit/ba851c7ae4646dd149f67a50a20f839a4c2db4c9))

### Performance Improvements

- Replace get_messages/get_dialogs with iter_messages/iter_dialogs
  ([#28](https://github.com/n24q02m/better-telegram-mcp/pull/28),
  [`bbcd88a`](https://github.com/n24q02m/better-telegram-mcp/commit/bbcd88a7b2531ec68918e7d4b6d776756eeee022))


## v3.1.0 (2026-03-18)

### Bug Fixes

- Remove auth secret, use token-based auth for public relay
  ([`df7d544`](https://github.com/n24q02m/better-telegram-mcp/commit/df7d54425691c9bf65fb0608a5e79bd5d1bbb9c2))

### Features

- Add auth-relay Docker build to CD pipeline
  ([`bc097f0`](https://github.com/n24q02m/better-telegram-mcp/commit/bc097f0e5d133eb805e8b74c979561f5f95f5d05))


## v3.0.0 (2026-03-18)

### Features

- Dual-mode auth (local + remote relay) with security hardening
  ([`5a7cece`](https://github.com/n24q02m/better-telegram-mcp/commit/5a7cecee89ca83f6c2723fba90c6097b7366d015))

### Breaking Changes

- Config tool `auth` and `send_code` actions removed. Authentication is now handled exclusively via
  web UI (local or remote).


## v2.0.0 (2026-03-17)

### Bug Fixes

- Remove terminal popup auth, simplify to CLI-first auth flow
  ([`dc9d5c6`](https://github.com/n24q02m/better-telegram-mcp/commit/dc9d5c6b261ba853e938c00edc58b1cd34e9dd5f))

### Features

- Add web-based OTP auth flow for MCP server
  ([`670ba67`](https://github.com/n24q02m/better-telegram-mcp/commit/670ba67d1d4fedd5b447193934a48a6397bfa2fd))

- Remove CLI auth, web UI is the only auth method
  ([`c0d02cf`](https://github.com/n24q02m/better-telegram-mcp/commit/c0d02cf63303ed53980dc20bde1a14057af9ba6a))

- Remove TELEGRAM_PASSWORD env var, 2FA via web UI only
  ([`caa3195`](https://github.com/n24q02m/better-telegram-mcp/commit/caa3195327a72aed7c4ada93c9d9e4a8491629aa))

### Breaking Changes

- `TELEGRAM_PASSWORD` env var no longer supported. 2FA passwords are now entered exclusively through
  the web auth UI or via curl POST /verify with {"code":"...", "password":"..."}.


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
