# CHANGELOG

<!-- version list -->

## v4.10.0 (2026-05-06)


## v4.10.0-beta.1 (2026-05-06)

### Bug Fixes

- Consolidate setup docs body to 3 methods (drop legacy Method 4/5)
  ([#455](https://github.com/n24q02m/better-telegram-mcp/pull/455),
  [`6c26daf`](https://github.com/n24q02m/better-telegram-mcp/commit/6c26dafbaf6778ceadc7d727a6d70e2377f52270))

- Remove TELEGRAM_PHONE from userConfig (stdio = bot mode only per spec V9)
  ([#460](https://github.com/n24q02m/better-telegram-mcp/pull/460),
  [`a9168e8`](https://github.com/n24q02m/better-telegram-mcp/commit/a9168e8fc4f5a9e2ebd393f89ef8caf3cc32c7ec))

- Revert pydantic to <2.13 to match mcp-core cap
  ([`f7a7485`](https://github.com/n24q02m/better-telegram-mcp/commit/f7a74857bf3becaaa9a5e56c59dd0d287731e971))

- Sync uv.lock version after v4.9.0 release commit
  ([`17ac5f2`](https://github.com/n24q02m/better-telegram-mcp/commit/17ac5f2659d93303538f3997791e1956f694c289))

- **deps**: Update dependency cryptography to v48
  ([#464](https://github.com/n24q02m/better-telegram-mcp/pull/464),
  [`d9b9c99`](https://github.com/n24q02m/better-telegram-mcp/commit/d9b9c99405181b2987fdb843adddb2423e744bee))

- **deps**: Update non-major dependencies
  ([#437](https://github.com/n24q02m/better-telegram-mcp/pull/437),
  [`82c925a`](https://github.com/n24q02m/better-telegram-mcp/commit/82c925a2e56e092e169f4d3b96b0156d1d51e959))

### Chores

- **deps**: Update step-security/harden-runner digest to a5ad31d
  ([#436](https://github.com/n24q02m/better-telegram-mcp/pull/436),
  [`1fe3621`](https://github.com/n24q02m/better-telegram-mcp/commit/1fe362153f810870095e7fe3c37def31d4a5e1f9))

### Features

- Add explicit Method overview section to setup docs
  ([#454](https://github.com/n24q02m/better-telegram-mcp/pull/454),
  [`dd31227`](https://github.com/n24q02m/better-telegram-mcp/commit/dd312275dce2b2ff7385974d520f34ba338ef6fe))

- Align userConfig with relay_schema fields
  ([#459](https://github.com/n24q02m/better-telegram-mcp/pull/459),
  [`544f0af`](https://github.com/n24q02m/better-telegram-mcp/commit/544f0af63fe2bdc65545ad68acaec7dd9ad5f009))

- Clarify Method 1/2/3 mutually exclusive (CC scope-by-endpoint)
  ([#463](https://github.com/n24q02m/better-telegram-mcp/pull/463),
  [`4af35f3`](https://github.com/n24q02m/better-telegram-mcp/commit/4af35f34178547dabfa99c01ccd1be1f6c2dac36))

- Declare userConfig schema and document install prompt
  ([#456](https://github.com/n24q02m/better-telegram-mcp/pull/456),
  [`a92cab1`](https://github.com/n24q02m/better-telegram-mcp/commit/a92cab153f2e048c9d11b775d7d607b0128d8a6f))

- Document userConfig credential prompts per plugin
  ([#461](https://github.com/n24q02m/better-telegram-mcp/pull/461),
  [`ce8d10e`](https://github.com/n24q02m/better-telegram-mcp/commit/ce8d10e8866db1fc52efc1999a93f85358d7d133))


## v4.9.0 (2026-05-04)

### Bug Fixes

- Bump mcp-core to 1.13.0 (STABLE) ([#453](https://github.com/n24q02m/better-telegram-mcp/pull/453),
  [`de541ca`](https://github.com/n24q02m/better-telegram-mcp/commit/de541cae72a67f72de3a1f0de89553b6f3b5ea5e))


## v4.9.0-beta.14 (2026-05-04)

### Bug Fixes

- Re-lock uv.lock without path source so Docker --frozen succeeds
  ([#451](https://github.com/n24q02m/better-telegram-mcp/pull/451),
  [`f8ef48e`](https://github.com/n24q02m/better-telegram-mcp/commit/f8ef48ee186907baad2e7dade6128a70190d06ea))

- Wire create_http_mcp_server() + auth_scope diagnostic log
  ([#451](https://github.com/n24q02m/better-telegram-mcp/pull/451),
  [`f8ef48e`](https://github.com/n24q02m/better-telegram-mcp/commit/f8ef48ee186907baad2e7dade6128a70190d06ea))

- Wire create_http_mcp_server() + diagnostic log + test fixture reset _multi_user_mode
  ([#451](https://github.com/n24q02m/better-telegram-mcp/pull/451),
  [`f8ef48e`](https://github.com/n24q02m/better-telegram-mcp/commit/f8ef48ee186907baad2e7dade6128a70190d06ea))


## v4.9.0-beta.13 (2026-05-04)

### Bug Fixes

- Re-lock uv.lock without path source so Docker --frozen succeeds
  ([#450](https://github.com/n24q02m/better-telegram-mcp/pull/450),
  [`79961c5`](https://github.com/n24q02m/better-telegram-mcp/commit/79961c5117af9028dc541aef8e2886c8bba6b713))


## v4.9.0-beta.12 (2026-05-04)

### Bug Fixes

- Re-lock uv.lock without path source so Docker --frozen succeeds
  ([#449](https://github.com/n24q02m/better-telegram-mcp/pull/449),
  [`53630c1`](https://github.com/n24q02m/better-telegram-mcp/commit/53630c16f0598eb6261185a180b9afbc5caeeb9c))


## v4.9.0-beta.11 (2026-05-04)

### Bug Fixes

- Re-lock uv.lock without path source so Docker --frozen succeeds
  ([#448](https://github.com/n24q02m/better-telegram-mcp/pull/448),
  [`8c0ed64`](https://github.com/n24q02m/better-telegram-mcp/commit/8c0ed644521d0c8e4f4b1cefeb7c865df9861924))


## v4.9.0-beta.10 (2026-05-04)

### Bug Fixes

- Cover multi-user save_credentials and on_step_submitted branches
  ([#447](https://github.com/n24q02m/better-telegram-mcp/pull/447),
  [`765e203`](https://github.com/n24q02m/better-telegram-mcp/commit/765e203b699d5dcf17f029d388a8cc834c806f43))

- Refactor multi-user HTTP to mcp-core run_http_server (drop relay-core)
  ([#447](https://github.com/n24q02m/better-telegram-mcp/pull/447),
  [`765e203`](https://github.com/n24q02m/better-telegram-mcp/commit/765e203b699d5dcf17f029d388a8cc834c806f43))


## v4.9.0-beta.9 (2026-05-03)

### Bug Fixes

- Bump mcp-core to 1.13.0-beta.9 for /login form shell refactor
  ([#444](https://github.com/n24q02m/better-telegram-mcp/pull/444),
  [`2e47dbb`](https://github.com/n24q02m/better-telegram-mcp/commit/2e47dbbc5b66b946d65b9240f30fd9bc067993e9))


## v4.9.0-beta.8 (2026-05-03)

### Features

- Wire /login relay-password gate into multi-user oauth_server
  ([#443](https://github.com/n24q02m/better-telegram-mcp/pull/443),
  [`0ee389a`](https://github.com/n24q02m/better-telegram-mcp/commit/0ee389a0684592a7b43e115d7ac663357afd8104))


## v4.9.0-beta.7 (2026-05-03)

### Features

- Bump mcp-core to 1.13.0-beta.7 ([#442](https://github.com/n24q02m/better-telegram-mcp/pull/442),
  [`7b71df5`](https://github.com/n24q02m/better-telegram-mcp/commit/7b71df53789481aa22dfa166512568e7951a8dfa))

- Document MCP_RELAY_PASSWORD edge auth gate
  ([#441](https://github.com/n24q02m/better-telegram-mcp/pull/441),
  [`0e0c8ba`](https://github.com/n24q02m/better-telegram-mcp/commit/0e0c8ba706979fd7971b2eb917afe32b239efcd9))

- Pass MCP_RELAY_PASSWORD env to HTTP container
  ([#440](https://github.com/n24q02m/better-telegram-mcp/pull/440),
  [`06024d8`](https://github.com/n24q02m/better-telegram-mcp/commit/06024d8b5d0ee550ab7d1b60c0fb3dcb2a368921))


## v4.9.0-beta.6 (2026-05-02)

### Bug Fixes

- Regenerate uv.lock UV_NO_SOURCES=1 (Docker build trap)
  ([#435](https://github.com/n24q02m/better-telegram-mcp/pull/435),
  [`eb90157`](https://github.com/n24q02m/better-telegram-mcp/commit/eb90157cd6a2c35631b51a8a9f45d0c319bcb634))


## v4.9.0-beta.5 (2026-05-02)

### Bug Fixes

- Setup docs + README reflect stdio-pure architecture
  ([#434](https://github.com/n24q02m/better-telegram-mcp/pull/434),
  [`1fe4d2a`](https://github.com/n24q02m/better-telegram-mcp/commit/1fe4d2acccc6693f8078f7b2ce647416169600f2))

### Chores

- **deps**: Update dawidd6/action-send-mail action to v17
  ([#422](https://github.com/n24q02m/better-telegram-mcp/pull/422),
  [`6e214b9`](https://github.com/n24q02m/better-telegram-mcp/commit/6e214b9d0475fde4a36f463b13532d91699dc02f))

### Features

- Stdio-pure + http-multi-user (drop daemon-bridge)
  ([#433](https://github.com/n24q02m/better-telegram-mcp/pull/433),
  [`1e6588b`](https://github.com/n24q02m/better-telegram-mcp/commit/1e6588b60d6e182d7e58120667631d63537b68e6))


## v4.9.0-beta.4 (2026-04-30)

### Bug Fixes

- Regenerate uv.lock with UV_NO_SOURCES=1 to remove local path references
  ([#428](https://github.com/n24q02m/better-telegram-mcp/pull/428),
  [`bccf15b`](https://github.com/n24q02m/better-telegram-mcp/commit/bccf15bf1c5962811e2bd95d18c8ebcadf3f3433))

### Features

- **auth**: Migrate to in-memory session store (TC-NearZK)
  ([#429](https://github.com/n24q02m/better-telegram-mcp/pull/429),
  [`7cf5304`](https://github.com/n24q02m/better-telegram-mcp/commit/7cf5304255615b5b3b820e2c8b79221656178b2c))

- **docs**: Add trust model section to README
  ([#428](https://github.com/n24q02m/better-telegram-mcp/pull/428),
  [`bccf15b`](https://github.com/n24q02m/better-telegram-mcp/commit/bccf15bf1c5962811e2bd95d18c8ebcadf3f3433))


## v4.9.0-beta.3 (2026-04-30)

### Bug Fixes

- Regenerate uv.lock with UV_NO_SOURCES=1 to remove local path references
  ([#426](https://github.com/n24q02m/better-telegram-mcp/pull/426),
  [`f950492`](https://github.com/n24q02m/better-telegram-mcp/commit/f9504921a29eddaa7fd056dc1acd8f57f55dacc0))


## v4.9.0-beta.2 (2026-04-30)

### Bug Fixes

- Strip [tool.uv.sources] in Dockerfile to fix uv sync --frozen Docker build
  ([#425](https://github.com/n24q02m/better-telegram-mcp/pull/425),
  [`72b2da9`](https://github.com/n24q02m/better-telegram-mcp/commit/72b2da933d98fa72e574e459413f9f76d097bdee))


## v4.9.0-beta.1 (2026-04-30)

### Features

- Route stdio mode to FastMCP direct + multi-target Dockerfile
  ([#424](https://github.com/n24q02m/better-telegram-mcp/pull/424),
  [`e174f90`](https://github.com/n24q02m/better-telegram-mcp/commit/e174f90afd281b7a2a897c9c633677287b111d96))


## v4.8.5 (2026-04-29)

### Bug Fixes

- Bump n24q02m-mcp-core to 1.11.3 for D17 tools cache refresh
  ([#418](https://github.com/n24q02m/better-telegram-mcp/pull/418),
  [`1c0fb63`](https://github.com/n24q02m/better-telegram-mcp/commit/1c0fb63437745b1a056e01af5f13efa2d4941447))

- Pin @latest in plugin.json to bypass uvx cache stale versions
  ([#416](https://github.com/n24q02m/better-telegram-mcp/pull/416),
  [`0caf1a6`](https://github.com/n24q02m/better-telegram-mcp/commit/0caf1a6d76870fa7bd78ec34523902d86ca4a7a2))

- Rebuild uv.lock without local path source
  ([#416](https://github.com/n24q02m/better-telegram-mcp/pull/416),
  [`0caf1a6`](https://github.com/n24q02m/better-telegram-mcp/commit/0caf1a6d76870fa7bd78ec34523902d86ca4a7a2))


## v4.8.4 (2026-04-29)

### Bug Fixes

- Rebuild uv.lock without local path source
  ([#414](https://github.com/n24q02m/better-telegram-mcp/pull/414),
  [`ab5433a`](https://github.com/n24q02m/better-telegram-mcp/commit/ab5433ac7dbb391ec562e095deb19ad4cae14625))


## v4.8.3 (2026-04-29)

### Bug Fixes

- Improve credential form accessibility with ARIA refinements
  ([#409](https://github.com/n24q02m/better-telegram-mcp/pull/409),
  [`f3e21ac`](https://github.com/n24q02m/better-telegram-mcp/commit/f3e21ac8cd3a76979e61da2600e14487d43b83d2))

- Register config__open_relay tool (Transparent Bridge Wave 3)
  ([#412](https://github.com/n24q02m/better-telegram-mcp/pull/412),
  [`cd865ea`](https://github.com/n24q02m/better-telegram-mcp/commit/cd865ead4aa79157a09e253050b3a4127464d821))

- Switch plugin.json to stdio proxy for local relay testing
  ([#410](https://github.com/n24q02m/better-telegram-mcp/pull/410),
  [`b7d93d0`](https://github.com/n24q02m/better-telegram-mcp/commit/b7d93d00c2f79006b5775f9833aa59401f4b865c))

- **deps**: Bump n24q02m-mcp-core to 1.10.0 — Transparent Bridge waves 1-3
  ([#410](https://github.com/n24q02m/better-telegram-mcp/pull/410),
  [`b7d93d0`](https://github.com/n24q02m/better-telegram-mcp/commit/b7d93d00c2f79006b5775f9833aa59401f4b865c))


## v4.8.2 (2026-04-28)

### Bug Fixes

- Migrate plugin.json to deployed HTTP remote + add /health route
  ([#406](https://github.com/n24q02m/better-telegram-mcp/pull/406),
  [`96be424`](https://github.com/n24q02m/better-telegram-mcp/commit/96be424a98f11501dffed9da9b1fa80019e1fb8d))

- Replace stale OAuth 2.1 wording with DCR + relay form in setup-manual
  ([#405](https://github.com/n24q02m/better-telegram-mcp/pull/405),
  [`fd717a6`](https://github.com/n24q02m/better-telegram-mcp/commit/fd717a66ff2831b7387f6e76a0af45254567e0b1))

- **deps**: Bump n24q02m-mcp-core to 1.10.0 — Transparent Bridge waves 1-3
  ([#408](https://github.com/n24q02m/better-telegram-mcp/pull/408),
  [`044b56f`](https://github.com/n24q02m/better-telegram-mcp/commit/044b56fe10033ab7a82a24b8fbf19949e7bc08b7))


## v4.8.1 (2026-04-28)

### Bug Fixes

- Bump n24q02m-mcp-core to 1.9.0 ([#404](https://github.com/n24q02m/better-telegram-mcp/pull/404),
  [`1a7db20`](https://github.com/n24q02m/better-telegram-mcp/commit/1a7db200b41e9737906b8878eb02dc97ea823fbe))

- **deps**: Update non-major dependencies
  ([#401](https://github.com/n24q02m/better-telegram-mcp/pull/401),
  [`c7ac9af`](https://github.com/n24q02m/better-telegram-mcp/commit/c7ac9afe8221210aad1b880bfa0067734e35d63f))


## v4.8.0 (2026-04-27)

### Bug Fixes

- Bump n24q02m-mcp-core to 1.8.0 + widen pydantic to <2.14
  ([#399](https://github.com/n24q02m/better-telegram-mcp/pull/399),
  [`291c7c2`](https://github.com/n24q02m/better-telegram-mcp/commit/291c7c2cb5e434ae11a6e954cc1ddcdd911ba4ad))

- Clear resolved 2026-04-18 known bugs from CLAUDE.md
  ([#397](https://github.com/n24q02m/better-telegram-mcp/pull/397),
  [`5b5aeee`](https://github.com/n24q02m/better-telegram-mcp/commit/5b5aeeee3c536e726c0ab3e60cd4e0c0d20af93d))

- Clear resolved 2026-04-18 known bugs from CLAUDE.md
  ([#396](https://github.com/n24q02m/better-telegram-mcp/pull/396),
  [`389b0b0`](https://github.com/n24q02m/better-telegram-mcp/commit/389b0b096d46605522ee56ea2c687ffe54caa308))

### Features

- Add ## E2E section to CLAUDE.md per Task 21 docs rollout
  ([#395](https://github.com/n24q02m/better-telegram-mcp/pull/395),
  [`da53a65`](https://github.com/n24q02m/better-telegram-mcp/commit/da53a65dbab24fc731869fb560c1c518882ec5ab))

- Render bot token + phone with prefilled value attrs
  ([#397](https://github.com/n24q02m/better-telegram-mcp/pull/397),
  [`5b5aeee`](https://github.com/n24q02m/better-telegram-mcp/commit/5b5aeeee3c536e726c0ab3e60cd4e0c0d20af93d))


## v4.7.2-beta.1 (2026-04-27)

### Bug Fixes

- Sweep doppler/infisical refs to skret SSM
  ([`1d3a948`](https://github.com/n24q02m/better-telegram-mcp/commit/1d3a9489a5db389b3c15a532652842a410f04cdc))


## v4.7.1 (2026-04-24)

### Bug Fixes

- Regenerate uv.lock without [tool.uv.sources] for Docker build
  ([#388](https://github.com/n24q02m/better-telegram-mcp/pull/388),
  [`f7e7ca4`](https://github.com/n24q02m/better-telegram-mcp/commit/f7e7ca47911c729089043639b7109f9a0f6f23a5))


## v4.7.0 (2026-04-24)

### Bug Fixes

- Bump n24q02m-mcp-core to 1.7.5 + loosen pydantic for cohere compat
  ([#385](https://github.com/n24q02m/better-telegram-mcp/pull/385),
  [`e09b1f6`](https://github.com/n24q02m/better-telegram-mcp/commit/e09b1f6cb3730555620f985cb57bf9e1369d0c16))

- Bump n24q02m-mcp-core to 1.7.6 ([#387](https://github.com/n24q02m/better-telegram-mcp/pull/387),
  [`f555bf1`](https://github.com/n24q02m/better-telegram-mcp/commit/f555bf192c85fb3872474a2c08ebb3484d49de5a))

- Bump n24q02m-mcp-core to >=1.7.0 ([#379](https://github.com/n24q02m/better-telegram-mcp/pull/379),
  [`1a1ae4e`](https://github.com/n24q02m/better-telegram-mcp/commit/1a1ae4e6a8139882859e7ea19ce6ff9f60eb2239))

- Optimize trusted proxy list lookup to O(1) (PR 374 split)
  ([`407539f`](https://github.com/n24q02m/better-telegram-mcp/commit/407539fd79c46a1fa9b0cf233703c368244644d2))

- **deps**: Update dependency uvicorn to >=0.46.0
  ([#375](https://github.com/n24q02m/better-telegram-mcp/pull/375),
  [`0e17be6`](https://github.com/n24q02m/better-telegram-mcp/commit/0e17be6d8414287a0f87870e323206c9e1deb9a8))

### Chores

- **deps**: Update python:3.13-slim-bookworm docker digest to bb73517
  ([#372](https://github.com/n24q02m/better-telegram-mcp/pull/372),
  [`2fe0dcc`](https://github.com/n24q02m/better-telegram-mcp/commit/2fe0dcc713ba13ce4786bc5715e65ac2dd57f931))

### Features

- Enforce Smart Daemon Manager (1-Daemon) for stdio transport
  ([`8d68f2e`](https://github.com/n24q02m/better-telegram-mcp/commit/8d68f2e19ef239ac769b0baf7306fc9182e0c252))


## v4.6.12-beta.1 (2026-04-22)

### Bug Fixes

- Add RFC 7591 dynamic client registration endpoint
  ([`ee5d1aa`](https://github.com/n24q02m/better-telegram-mcp/commit/ee5d1aad8e838a9c95bfbe22cdc24eb9aa790a1d))


## v4.6.11 (2026-04-22)

### Bug Fixes

- Return 401 + WWW-Authenticate for bearer auth failures
  ([#370](https://github.com/n24q02m/better-telegram-mcp/pull/370),
  [`a23ea71`](https://github.com/n24q02m/better-telegram-mcp/commit/a23ea71b093f67f50de51ffe49403fb1189271e0))


## v4.6.10 (2026-04-22)

### Bug Fixes

- Follow redirect_url after async OTP/password completion
  ([#369](https://github.com/n24q02m/better-telegram-mcp/pull/369),
  [`0560529`](https://github.com/n24q02m/better-telegram-mcp/commit/0560529f5700849f46438e8e74c35638ef657d30))


## v4.6.9 (2026-04-22)

### Bug Fixes

- Bump n24q02m-mcp-core to 1.6.3 (relay form follow redirect_url)
  ([#368](https://github.com/n24q02m/better-telegram-mcp/pull/368),
  [`e61e041`](https://github.com/n24q02m/better-telegram-mcp/commit/e61e0418b707b0bd3f0b68be85f97e5af8d2cfba))


## v4.6.8 (2026-04-22)

### Bug Fixes

- Bump mcp-core to 1.6.2 ([#366](https://github.com/n24q02m/better-telegram-mcp/pull/366),
  [`09d2fab`](https://github.com/n24q02m/better-telegram-mcp/commit/09d2fabb3cf07cab1f1b2a91eb22051f03f1bced))


## v4.6.7 (2026-04-22)

### Bug Fixes

- Bump n24q02m-mcp-core to 1.5.1
  ([`863260d`](https://github.com/n24q02m/better-telegram-mcp/commit/863260d3b811c4ae7318262b49280eca07ab5050))

- Bump n24q02m-mcp-core to 1.6.1 ([#364](https://github.com/n24q02m/better-telegram-mcp/pull/364),
  [`4630fa8`](https://github.com/n24q02m/better-telegram-mcp/commit/4630fa890a406cc2c79c464468c92af3c0a0fcbe))

- **deps**: Update non-major dependencies
  ([#358](https://github.com/n24q02m/better-telegram-mcp/pull/358),
  [`6d53224`](https://github.com/n24q02m/better-telegram-mcp/commit/6d5322438b3bb8c2e80547ce9a232f7f0487c5a9))

### Chores

- **deps**: Lock file maintenance ([#360](https://github.com/n24q02m/better-telegram-mcp/pull/360),
  [`65d9888`](https://github.com/n24q02m/better-telegram-mcp/commit/65d9888dd78220e004abb18f0e2afe043f3a82fb))

- **deps**: Update astral-sh/setup-uv action to v8
  ([#359](https://github.com/n24q02m/better-telegram-mcp/pull/359),
  [`3ff3cb7`](https://github.com/n24q02m/better-telegram-mcp/commit/3ff3cb759bef04ec263e13093b554d2df38f030b))


## v4.6.6 (2026-04-21)

### Bug Fixes

- Add aria-busy spinner to credential form submit button
  ([`43f6eed`](https://github.com/n24q02m/better-telegram-mcp/commit/43f6eed7495546a5962dd2d9b7e55126632bc4c7))

- Bump non-major Python deps (lock file maintenance)
  ([`a405714`](https://github.com/n24q02m/better-telegram-mcp/commit/a405714ed0625c4f8a4c73edc27b6a515bbafffa))

- Bump non-major Python deps incl mcp-core to 1.5.0
  ([`a4ea367`](https://github.com/n24q02m/better-telegram-mcp/commit/a4ea367ecc157c90bd4287bcacaae3a8626dacfa))

- Bump step-security/harden-runner digest to 8d3c67d
  ([`95b1036`](https://github.com/n24q02m/better-telegram-mcp/commit/95b10364cee8ee3cf02029abc889cf48d61ab068))


## v4.6.5 (2026-04-21)

### Bug Fixes

- Route HTTP entry through transports.http so multi-user OAuth actually runs
  ([`9821675`](https://github.com/n24q02m/better-telegram-mcp/commit/982167513eea5e4c408cbad4fdc0230bb68ede95))


## v4.6.4 (2026-04-21)

### Bug Fixes

- Accept Settings api_id/api_hash defaults for multi-user mode detection
  ([`6d32d4e`](https://github.com/n24q02m/better-telegram-mcp/commit/6d32d4e8997e413928573a620af81897c59ee814))


## v4.6.3 (2026-04-21)

### Bug Fixes

- Case-insensitive Bearer token parsing per RFC 7235 (with tests)
  ([`411ae2d`](https://github.com/n24q02m/better-telegram-mcp/commit/411ae2daced4a010b468db87028a99136f57beac))

- Improve OTP and 2FA password form accessibility
  ([`0ceacf3`](https://github.com/n24q02m/better-telegram-mcp/commit/0ceacf39ee6598ef5c38f6202a6c500526e39b01))

- Memoize trusted proxy parsing in hot path
  ([`4065522`](https://github.com/n24q02m/better-telegram-mcp/commit/40655220289f90ce1bbd0b99010277f8ca967bfe))

- Refuse public-URL single-user fallback + propagate SubjectContext
  ([`4fb18e3`](https://github.com/n24q02m/better-telegram-mcp/commit/4fb18e30798c218fe9b8c263c778e4f66f35fddc))

- Stdio fallback renders custom telegram credential form
  ([`1142286`](https://github.com/n24q02m/better-telegram-mcp/commit/114228637e3e03cd21dda2dbbda60c8029494fd8))

- Stdio fallback spawns local credential form, not remote relay
  ([`48f338b`](https://github.com/n24q02m/better-telegram-mcp/commit/48f338bd252a8c9716d5440697b8aa42f239c62f))

- **deps**: Lock file maintenance (filelock 3.28.0->3.29.0)
  ([`d0f1865`](https://github.com/n24q02m/better-telegram-mcp/commit/d0f18658f332546dc9e921fd6805406b970d2ae4))


## v4.6.2 (2026-04-20)

### Bug Fixes

- Bump n24q02m-mcp-core to >=1.4.3 (aria-busy step reset parity)
  ([#350](https://github.com/n24q02m/better-telegram-mcp/pull/350),
  [`df06f1a`](https://github.com/n24q02m/better-telegram-mcp/commit/df06f1adc364ec52ec4ab1d7dcb0ef93c7bc19e5))

- Clear aria-busy on step-input reset to unblock 2FA submit
  ([#348](https://github.com/n24q02m/better-telegram-mcp/pull/348),
  [`eb1993f`](https://github.com/n24q02m/better-telegram-mcp/commit/eb1993fd8cccf34bbe9ef837274f7640f44ef69b))


## v4.6.1 (2026-04-20)

### Bug Fixes

- Bump n24q02m-mcp-core to >=1.4.2 ([#347](https://github.com/n24q02m/better-telegram-mcp/pull/347),
  [`82bdc1d`](https://github.com/n24q02m/better-telegram-mcp/commit/82bdc1d8c80b26e3d9d9479cea650aa54478d575))


## v4.6.0 (2026-04-19)

### Bug Fixes

- Bump mcp-core to 1.3.0 ([#335](https://github.com/n24q02m/better-telegram-mcp/pull/335),
  [`51eeaed`](https://github.com/n24q02m/better-telegram-mcp/commit/51eeaeda5c2092a2d09982ee65a0dea6318a323e))

- Bump n24q02m-mcp-core to 1.4.0 ([#340](https://github.com/n24q02m/better-telegram-mcp/pull/340),
  [`5de8bdc`](https://github.com/n24q02m/better-telegram-mcp/commit/5de8bdcb059a6b22916fa55726e20b9eaeb72557))

- **deps**: Update dependency pydantic to >=2.13.2
  ([#329](https://github.com/n24q02m/better-telegram-mcp/pull/329),
  [`ab699f4`](https://github.com/n24q02m/better-telegram-mcp/commit/ab699f404ee316f529cf23a2409c386244d9c8ba))

### Chores

- Log non-critical exceptions in UserBackend
  ([#315](https://github.com/n24q02m/better-telegram-mcp/pull/315),
  [`696dddf`](https://github.com/n24q02m/better-telegram-mcp/commit/696dddfe7e94d215653b35ffdf5b57e77b8da789))

- **deps**: Lock file maintenance ([#330](https://github.com/n24q02m/better-telegram-mcp/pull/330),
  [`cd86b41`](https://github.com/n24q02m/better-telegram-mcp/commit/cd86b410dfbe1ad61e5885e7f9542838b6c088e5))

- **deps**: Update step-security/harden-runner digest to 6c3c2f2
  ([#328](https://github.com/n24q02m/better-telegram-mcp/pull/328),
  [`8bda093`](https://github.com/n24q02m/better-telegram-mcp/commit/8bda0936c55d612aa3dbe115db43f3244a537694))

### Performance Improvements

- **user-backend**: Move blocking file I/O to background threads
  ([#320](https://github.com/n24q02m/better-telegram-mcp/pull/320),
  [`4f4f9d4`](https://github.com/n24q02m/better-telegram-mcp/commit/4f4f9d45b26e86fc686021960d1d3aa27fab16db))

### Testing

- Add unit tests for AuthClient and enable coverage reporting
  ([#271](https://github.com/n24q02m/better-telegram-mcp/pull/271),
  [`457f4ee`](https://github.com/n24q02m/better-telegram-mcp/commit/457f4ee68bca2b9a0b29643ed0a06adf1b0eb436))

- **transports**: Add coverage for http_multi_user.py
  ([#318](https://github.com/n24q02m/better-telegram-mcp/pull/318),
  [`61dc43a`](https://github.com/n24q02m/better-telegram-mcp/commit/61dc43a5d1f58dc31a5620c8b47ffd85fa167b09))


## v4.6.0-beta.1 (2026-04-18)

### Bug Fixes

- Add tests for user-mode OTP/2FA relay branches + fix Python 3.13 variable shadowing bug
  ([#334](https://github.com/n24q02m/better-telegram-mcp/pull/334),
  [`a0b5ba5`](https://github.com/n24q02m/better-telegram-mcp/commit/a0b5ba50ec489a6781a903f00b5c1ece2e942829))

- Apply ruff format to auth + test files for CI parity
  ([#334](https://github.com/n24q02m/better-telegram-mcp/pull/334),
  [`a0b5ba5`](https://github.com/n24q02m/better-telegram-mcp/commit/a0b5ba50ec489a6781a903f00b5c1ece2e942829))

- Mask sensitive token in auth server start log
  ([#313](https://github.com/n24q02m/better-telegram-mcp/pull/313),
  [`2c2571c`](https://github.com/n24q02m/better-telegram-mcp/commit/2c2571c741b5b16016ce638c0409f16b0bd113f8))

- Remove hardcoded default dev secret and centralize secret management
  ([#312](https://github.com/n24q02m/better-telegram-mcp/pull/312),
  [`b335f7d`](https://github.com/n24q02m/better-telegram-mcp/commit/b335f7db8535a3fcf5e84eeb94f9e4a7282e8e5b))

- Remove sensitive auth session URL from logs
  ([#307](https://github.com/n24q02m/better-telegram-mcp/pull/307),
  [`137e743`](https://github.com/n24q02m/better-telegram-mcp/commit/137e743749c5d14f634f79997fb7dab1f28e5f69))

- **auth**: Log swallowed exception in pending OTP disconnect
  ([#317](https://github.com/n24q02m/better-telegram-mcp/pull/317),
  [`9374e4c`](https://github.com/n24q02m/better-telegram-mcp/commit/9374e4cb2c21c5b1bd01cbf372faec962264b5f4))

### Features

- Fix user-mode OTP flow over remote relay and patch bot token leak
  ([#334](https://github.com/n24q02m/better-telegram-mcp/pull/334),
  [`a0b5ba5`](https://github.com/n24q02m/better-telegram-mcp/commit/a0b5ba50ec489a6781a903f00b5c1ece2e942829))

### Performance Improvements

- **auth**: Optimize stale OTP cleanup
  ([#306](https://github.com/n24q02m/better-telegram-mcp/pull/306),
  [`e37683d`](https://github.com/n24q02m/better-telegram-mcp/commit/e37683d2eb4b1ae4c4a6e1b03b003159dd4a0977))

### Testing

- Add relay_schema.py tests and fix ty check failures
  ([#266](https://github.com/n24q02m/better-telegram-mcp/pull/266),
  [`b94dd81`](https://github.com/n24q02m/better-telegram-mcp/commit/b94dd81c64176e829cc6603bcd0bb768d520fa5b))

- Add unit tests for auth_client.py and remove from coverage omit
  ([#300](https://github.com/n24q02m/better-telegram-mcp/pull/300),
  [`b286b83`](https://github.com/n24q02m/better-telegram-mcp/commit/b286b836a17387d0b884de2c2e123925f49301b2))

- Add unit tests for http transport and enable coverage
  ([#304](https://github.com/n24q02m/better-telegram-mcp/pull/304),
  [`f6e5868`](https://github.com/n24q02m/better-telegram-mcp/commit/f6e58683bfa22017e20b6ff7f9cfb920335d0165))

- Add unit tests for oauth_server transport
  ([#303](https://github.com/n24q02m/better-telegram-mcp/pull/303),
  [`f48fd99`](https://github.com/n24q02m/better-telegram-mcp/commit/f48fd99d94fcfd132e82897e1b6c8be274e863fd))


## v4.5.3 (2026-04-17)

### Bug Fixes

- Bump n24q02m-mcp-core to 1.2.0 (authlib CVE patch)
  ([`ff8cbd4`](https://github.com/n24q02m/better-telegram-mcp/commit/ff8cbd41eea8de1d38eea633c581fecaa4bf1765))

- Upgrade authlib to 1.6.11 (CVE-2024-cross-site-request-forging)
  ([`591a986`](https://github.com/n24q02m/better-telegram-mcp/commit/591a9862365524dd261a826c91d882f1056d98b7))


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
