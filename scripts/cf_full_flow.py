"""CF better-telegram-mcp live OAuth full-flow self-test harness.

Drives the deployed better-telegram-mcp Cloudflare Worker (Worker + per-sub
Container + KV) end-to-end against a public endpoint. better-telegram is a
LOCAL-FORM server (like wet/mnemo/imagine/email, NOT delegated like notion): the
/authorize gate is just the relay password, so the whole flow is fully autonomous
-- no third-party consent.

Flow (authorization_code + PKCE, DCR public client; ported verbatim from the
email/imagine CF harnesses):
  1. DCR register   -- POST /register (RFC 7591) -> client_id
  2. password-grant -- GET /authorize -> POST /login (Gate A relay password) -> form
  3. save creds     -- POST /authorize?nonce=... {TELEGRAM_BOT_TOKEN} (retry-on-500
                       for the E.1 outbound-interception race). Bot mode REQUIRES a
                       real bot token; the server resolves the per-sub Bot API backend.
  4. token          -- POST /token (code + verifier) -> bearer JWT
  5. tool call      -- config(status) + chat(info, @telegram); assert the bot backend
                       resolves and a representative read-only chat-domain operation
                       succeeds.

Recreate gate (SUCCESS CRITERION 4 -- the whole point of the migration):
  --save-only  : save the bot token for one sub, dump the EXACT JWT (relay-login
                 mints a random sub per /authorize, so verify MUST replay this token).
  --auth-only  : replay the dumped JWT WITHOUT re-saving; chat(info) must still
                 resolve the bot -> the token survived container delete+recreate in KV.

Secrets from env (skret): TELEGRAM_BOT_TOKEN from /better-telegram-mcp/prod; relay
gate password MCP_RELAY_PASSWORD (or RELAY_PW) from /oci-vm-prod/prod (infra-shared)
-- compose both namespaces.

Examples:
  skret run -e prod --path=/oci-vm-prod/prod -- \
    skret run -e prod --path=/better-telegram-mcp/prod -- \
      python scripts/cf_full_flow.py
  ... -- python scripts/cf_full_flow.py --save-only
  ... -- python scripts/cf_full_flow.py --auth-only
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json as _json
import os
import re
import secrets
import sys
import time
import urllib.parse
from pathlib import Path

# No hardcoded host: set CF_ENDPOINT or pass --endpoint https://<your-worker-domain>.
# This self-tests YOUR deployed CF server; creds come from env (MCP_RELAY_PASSWORD +
# provider keys) -- the maintainer injects them via skret, but any export works.
DEFAULT_ENDPOINT = os.environ.get("CF_ENDPOINT", "")


def _password() -> str:
    pw = os.environ.get("RELAY_PW") or os.environ.get("MCP_RELAY_PASSWORD")
    if not pw:
        raise SystemExit(
            "MCP_RELAY_PASSWORD (or RELAY_PW) is required for the password-grant "
            "login gate. It lives in skret /oci-vm-prod/prod (infra-shared), NOT "
            "/better-telegram-mcp/prod -- compose both namespaces."
        )
    return pw


def _bot_creds() -> dict[str, str]:
    """Bot mode credential: TELEGRAM_BOT_TOKEN from the skret e2e identity. The
    server validates/resolves the Bot API backend on save."""
    tok = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not tok:
        raise SystemExit(
            "TELEGRAM_BOT_TOKEN required (skret /better-telegram-mcp/prod) to save a "
            "credential -- bot mode cannot operate without a token."
        )
    return {"TELEGRAM_BOT_TOKEN": tok}


class _SaveRetry(Exception):
    pass


def get_token(endpoint: str, creds: dict[str, str], *, save_retries: int = 8) -> str:
    """Full OAuth flow, retrying on a transient 500 at the credential save step (CF
    Containers outbound-interception race on cold instances; E.1). Each retry restarts
    from DCR so the nonce is fresh."""
    import httpx  # lazy: keep --help importable without httpx

    last: Exception | None = None
    for attempt in range(save_retries):
        try:
            return _get_token_once(httpx, endpoint, creds)
        except _SaveRetry as e:
            last = e
            print(
                f"get_token: save 500 (interception race), retry {attempt + 1}/{save_retries}"
            )
            time.sleep(3)
    raise RuntimeError(f"get_token failed after {save_retries} retries: {last}")


def _get_token_once(httpx, endpoint: str, creds: dict[str, str]) -> str:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    ru = "http://localhost:9999/cb"
    pw = _password()
    with httpx.Client(timeout=120, follow_redirects=False) as c:
        cid = c.post(
            f"{endpoint}/register",
            json={
                "client_name": "cf-verify",
                "redirect_uris": [ru],
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
                "token_endpoint_auth_method": "none",
                "scope": "offline_access",
            },
        ).json()["client_id"]
        az = c.get(
            f"{endpoint}/authorize",
            params={
                "response_type": "code",
                "client_id": cid,
                "redirect_uri": ru,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "state": "st",
                "scope": "offline_access",
            },
        )
        nxt = urllib.parse.parse_qs(
            urllib.parse.urlparse(az.headers["location"]).query
        )["next"][0]
        lg = c.post(f"{endpoint}/login", data={"next": nxt, "password": pw})
        url = lg.headers["location"]
        url = url if url.startswith("http") else endpoint + url
        form_html = c.get(url).text
        m = re.search(r"/authorize\?nonce=([A-Za-z0-9_\-]+)", form_html)
        assert m, "nonce not found in form"
        nonce = m.group(1)
        sub = c.post(
            f"{endpoint}/authorize", params={"nonce": nonce}, json=creds, timeout=120
        )
        if sub.status_code == 500 and "save credentials" in sub.text:
            raise _SaveRetry(sub.text[:120])
        assert sub.status_code == 200, (sub.status_code, sub.text[:400])
        data = sub.json()
        assert data.get("ok"), data
        code = urllib.parse.parse_qs(urllib.parse.urlparse(data["redirect_url"]).query)[
            "code"
        ][0]
        tok = c.post(
            f"{endpoint}/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": ru,
                "client_id": cid,
                "code_verifier": verifier,
            },
        )
        assert tok.status_code == 200, (tok.status_code, tok.text[:300])
        return tok.json()["access_token"]


def _sub_of(token: str) -> str:
    payload = _json.loads(base64.urlsafe_b64decode(token.split(".")[1] + "=="))
    return payload.get("sub", "?")


# Substrings (case-insensitive) meaning "credentials not resolved yet" -- the bot
# token is still propagating through KV, or was never saved. _call retries on ANY of
# these (E.2 cross-colo window); the assertion FAILS HARD on them (not-ready != PASS).
_NOT_READY_MARKERS = (
    "awaiting_setup",
    "not configured",
    "credentials are required",
    "no credentials",
    "to set up",
    # telegram surfaces "not yet set up" as the per-sub backend lazily
    # initializing from the KV-saved token (E.2 cross-colo propagation window).
    "backend not initialized",
    "server lifespan not started",
    "not authenticated",
)


def _not_ready(txt: str | None) -> bool:
    if not txt:
        return True
    low = txt.lower()
    return any(m in low for m in _NOT_READY_MARKERS)


async def _call(s, label, tool, args, *, retries=20, delay=8):
    for i in range(retries):
        try:
            res = await s.call_tool(tool, args)
            txt = "".join(getattr(b, "text", "") for b in res.content)
            if _not_ready(txt):
                print(f"{label}: not ready (KV propagating) try {i + 1}/{retries}")
                await asyncio.sleep(delay)
                continue
            print(f"{label} OK:", txt[:320].replace("\n", " "))
            return txt
        except Exception as e:
            print(f"{label} ERR:", repr(e)[:300])
            return None
    print(f"{label}: gave up after {retries} tries (still not ready)")
    return None


def _assert_bot_connected(txt: str | None) -> None:
    """config(action="status") for a resolved bot backend returns
    {"mode": "bot", "connected": true, "authorized": true, ...}. `authorized: true`
    means the per-sub backend made a real getMe round-trip to the Telegram Bot API
    with the KV-resolved token -- the strongest bot-mode proof. (chat(action="list")
    is USER-mode only: a bot has no dialog list, so config(status) is the bot health
    check, not a chat listing.)"""
    assert txt is not None, (
        "config(status) returned no payload (gave up while not ready)"
    )
    assert not _not_ready(txt), (
        f"bot backend NOT resolved (token never propagated): {txt[:300]}"
    )
    low = txt.lower()
    assert '"connected": true' in low or '"connected":true' in low, (
        f"bot not connected to Telegram: {txt[:300]}"
    )
    assert '"authorized": true' in low or '"authorized":true' in low, (
        f"bot token not authorized by Telegram (getMe failed): {txt[:300]}"
    )
    print("ASSERT OK: bot backend connected + authorized (real getMe round-trip).")


def _assert_chat_info(txt: str | None) -> None:
    """Assert that chat(info) returned a real Telegram chat object."""
    assert txt is not None, "chat(info) returned no payload"
    assert not _not_ready(txt), f"chat(info) backend was not ready: {txt[:300]}"
    low = txt.lower()
    assert '"id"' in low or '"id":' in low, (
        f"chat(info) did not return a chat id: {txt[:300]}"
    )
    assert '"type"' in low or '"type":' in low, (
        f"chat(info) did not return a chat type: {txt[:300]}"
    )
    print("ASSERT OK: chat(info, @telegram) returned a real chat object.")


async def _session(endpoint: str, token: str):
    from mcp import ClientSession  # lazy
    from mcp.client.streamable_http import streamablehttp_client

    return streamablehttp_client(
        f"{endpoint}/mcp", headers={"Authorization": f"Bearer {token}"}
    ), ClientSession


def _token_file() -> Path:
    return Path(__file__).with_name(".telegram_cf_token")


async def run_full(endpoint: str) -> None:
    token = get_token(endpoint, _bot_creds())
    print("TOKEN OK len=", len(token), "sub=", _sub_of(token))
    transport, ClientSession = await _session(endpoint, token)
    async with transport as (r, w, _), ClientSession(r, w) as s:
        await s.initialize()
        tools = await s.list_tools()
        print("TOOLS:", [t.name for t in tools.tools])
        txt = await _call(s, "CONFIG_STATUS", "config", {"action": "status"})
        _assert_bot_connected(txt)
        chat_txt = await _call(
            s,
            "CHAT_INFO",
            "chat",
            {"action": "info", "chat_id": "@telegram"},
        )
        _assert_chat_info(chat_txt)
    print("FULL FLOW PASS.")


async def run_save_only(endpoint: str) -> None:
    token = get_token(endpoint, _bot_creds())
    _token_file().write_text(token)
    print("SAVE-ONLY OK: bot token saved for sub=", _sub_of(token), "(token dumped)")


async def run_auth_only(endpoint: str) -> None:
    tok_path = _token_file()
    if not tok_path.exists():
        raise SystemExit("No dumped token -- run --save-only first.")
    token = tok_path.read_text().strip()
    print("AUTH-ONLY: replaying saved token for sub=", _sub_of(token), "(no re-save)")
    transport, ClientSession = await _session(endpoint, token)
    async with transport as (r, w, _), ClientSession(r, w) as s:
        await s.initialize()
        txt = await _call(s, "CONFIG_STATUS", "config", {"action": "status"})
        _assert_bot_connected(txt)
        chat_txt = await _call(
            s,
            "CHAT_INFO",
            "chat",
            {"action": "info", "chat_id": "@telegram"},
        )
        _assert_chat_info(chat_txt)
    print("AUTH-ONLY PASS: bot token survived recreate (KV resolved, no re-save).")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="CF better-telegram-mcp live OAuth full-flow self-test harness.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--endpoint",
        default=DEFAULT_ENDPOINT,
        required=not DEFAULT_ENDPOINT,
        help=f"Deployed telegram endpoint (default: {DEFAULT_ENDPOINT})",
    )
    mode = p.add_mutually_exclusive_group()
    mode.add_argument(
        "--save-only",
        action="store_true",
        help="Save the bot token for one sub + dump the token (recreate-gate setup).",
    )
    mode.add_argument(
        "--auth-only",
        action="store_true",
        help="Replay dumped token, no re-save (recreate-gate verify).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.save_only:
        asyncio.run(run_save_only(args.endpoint))
    elif args.auth_only:
        asyncio.run(run_auth_only(args.endpoint))
    else:
        asyncio.run(run_full(args.endpoint))
    return 0


if __name__ == "__main__":
    sys.exit(main())
