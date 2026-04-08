"""Local web server for Telegram OTP authentication.

Used when TELEGRAM_AUTH_URL=local. Serves auth form on localhost.
Runs for the MCP server lifetime. Shows auth form when unauthorized,
status page when authenticated.
"""

from __future__ import annotations

import asyncio
import html
import secrets
import socket
import time
from collections import defaultdict
from typing import TYPE_CHECKING

from starlette.applications import Starlette
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

from .utils.formatting import mask_phone, sanitize_error
# Internal helpers for backward compatibility in tests
_mask_phone = mask_phone
_sanitize_error = sanitize_error

if TYPE_CHECKING:
    from starlette.requests import Request

    from .backends.base import TelegramBackend
    from .config import Settings

_PAGE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Telegram Authentication</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #f4f7f9; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; color: #333; }
    .card { background: #fff; padding: 32px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); width: 100%; max-width: 360px; text-align: center; }
    h2 { margin-top: 0; color: #0088cc; }
    p { font-size: 14px; line-height: 1.5; color: #666; margin-bottom: 24px; }
    .phone { font-weight: 600; color: #333; }
    input { width: 100%; padding: 12px; margin-bottom: 16px; border: 1px solid #ddd; border-radius: 8px; font-size: 16px; box-sizing: border-box; outline: none; transition: border-color 0.2s; }
    input:focus { border-color: #0088cc; }
    button { width: 100%; padding: 12px; background: #0088cc; color: #fff; border: none; border-radius: 8px; font-size: 16px; font-weight: 600; cursor: pointer; transition: background 0.2s; }
    button:hover { background: #0077b5; }
    button:disabled { background: #ccc; cursor: not-allowed; }
    .status { margin-top: 16px; font-size: 13px; min-height: 1.5em; }
    .status.error { color: #d32f2f; }
    .status.success { color: #388e3c; }
    .hidden { display: none; }
    .pwd-hint { font-size: 12px; color: #999; margin-top: -8px; margin-bottom: 16px; text-align: left; }
  </style>
</head>
<body>
  <div class="card">
    <h2>Telegram Auth</h2>
    <div id="step1">
      <p>Authentication required for <span class="phone">PHONE</span></p>
      <button id="btn-send" onclick="sendCode()">Send Code</button>
      <div id="otp-area" class="hidden">
        <input type="text" id="otp" placeholder="Enter OTP Code" maxlength="10">
        <div id="pwd-area" class="hidden">
          <p class="pwd-hint">Your account has two-factor authentication enabled.</p>
          <input type="password" id="pwd" placeholder="2FA Password">
        </div>
        <button id="btn-verify" onclick="verify()">Verify Code</button>
      </div>
    </div>
    <div id="step2" class="hidden">
      <p class="success" role="status" aria-live="polite">
        <strong>Authorized!</strong><br>
        Authenticated as <strong id="auth-name"></strong>.<br>
        You can now close this tab.
      </p>
    </div>
    <div id="status" class="status" role="status" aria-live="polite"></div>
  </div>

<script>
let _t = new URLSearchParams(window.location.search).get('token');
const $ = (id) => document.getElementById(id);
const st = (el, cls, txt) => { el.textContent = txt; el.className = 'status ' + cls; };

async function checkStatus() {
  if(!_t) return;
  try {
    const r = await fetch('/status', { headers: { 'X-Auth-Token': _t } });
    if(r.status === 403) { st($('status'), 'error', 'Invalid or missing token. Please use the link from your MCP server logs.'); $('btn-send').disabled = true; return; }
    const d = await r.json();
    if(d.authenticated){ $('auth-name').textContent = d.name || 'User'; show('step2') }
  } catch(e) {}
}

function show(id) {
  ['step1','step2','otp-area'].forEach(k => $(k).classList.add('hidden'));
  $(id).classList.remove('hidden');
  if(id==='otp-area') $('step1').classList.remove('hidden');
}

function btnLoading(btn, txt) { btn.disabled = true; btn.textContent = txt; }
function btnReset(btn, txt) { btn.disabled = false; btn.textContent = txt; }

async function sendCode() {
  const btn = $('btn-send');
  const s = $('status');
  st(s, '', 'Sending code...');
  btnLoading(btn, 'Sending...');
  try {
    const r = await fetch('/send-code', { method: 'POST', headers: { 'X-Auth-Token': _t } });
    const d = await r.json();
    if(d.ok) { st(s, 'success', 'Code sent to your Telegram app!'); show('otp-area'); btn.classList.add('hidden'); }
    else { st(s, 'error', d.error || 'Failed to send code'); btnReset(btn, 'Send Code'); }
  } catch(e) { st(s, 'error', 'Network error. Check your connection.'); btnReset(btn, 'Send Code'); }
}

function showPwd() { $('pwd-area').classList.remove('hidden'); $('pwd').focus(); }

async function verify() {
  const code = $('otp').value.trim();
  const btn = $('btn-verify');
  const s = $('status');
  if(!code) { st(s, 'error', 'Please enter the code sent.'); return; }
  btnLoading(btn, 'Verifying...');
  try {
    const body = { code };
    const pwd = $('pwd').value.trim();
    if(pwd) body.password = pwd;
    const r = await fetch('/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Auth-Token': _t },
      body: JSON.stringify(body)
    });
    const d = await r.json();
    if(d.ok) { $('auth-name').textContent = d.name || 'User'; show('step2'); st(s, '', ''); }
    else {
      if(d.needs_password) { showPwd(); st(s, 'error', '2FA password is required. Please enter it above.'); }
      else { st(s, 'error', d.error || 'Verification failed'); }
      btnReset(btn, 'Verify Code');
    }
  } catch(e) { st(s, 'error', 'Network error. Check your connection.'); btnReset(btn, 'Verify Code'); }
}

$('otp').addEventListener('keydown', e => { if(e.key === 'Enter') verify(); });
document.addEventListener('DOMContentLoaded', () => {
  const p = $('pwd'); if(p) p.addEventListener('keydown', e => { if(e.key === 'Enter') verify(); });
});
checkStatus();
</script>
</body>
</html>"""


def _find_free_port() -> int:
    """Find an available port on 127.0.0.1."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]
    except OSError as e:
        raise RuntimeError(f"Could not find a free port: {e}") from e


class AuthServer:
    """Local web server for OTP authentication (TELEGRAM_AUTH_URL=local)."""

    _RATE_LIMIT_WINDOW = 60  # seconds
    _RATE_LIMIT_MAX = 5  # requests per window per IP per endpoint

    def __init__(self, backend: TelegramBackend, settings: Settings):
        self._backend = backend
        self._settings = settings
        self._auth_complete = asyncio.Event()
        self._auth_name: str = ""
        self._uvicorn_server: object | None = None
        self._rate_limits: dict[str, list[float]] = defaultdict(list)
        self._token = secrets.token_urlsafe(32)
        self.port: int = 0
        self.url: str = ""

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP strictly from request.client.host.

        🛡️ Sentinel: Parsing HTTP headers like X-Forwarded-For introduces IP spoofing
        vulnerabilities on locally bound servers.
        """
        return request.client.host if request.client else "unknown"

    def _check_rate_limit(self, key: str) -> bool:
        """Check if key is within rate limit. Returns True if allowed."""
        now = time.time()
        window_start = now - self._RATE_LIMIT_WINDOW
        timestamps = self._rate_limits[key]
        self._rate_limits[key] = [t for t in timestamps if t > window_start]
        if len(self._rate_limits[key]) >= self._RATE_LIMIT_MAX:
            return False
        self._rate_limits[key].append(now)
        return True

    def _make_app(self) -> Starlette:
        async def index(request: Request) -> HTMLResponse:
            phone = self._settings.phone or "unknown"
            # 🛡️ Sentinel: Prevent XSS by escaping dynamic data before insertion
            page_html = _PAGE.replace("PHONE", html.escape(mask_phone(phone)))
            return HTMLResponse(
                page_html,
                headers={
                    "Content-Security-Policy": (
                        "default-src 'self'; "
                        "style-src 'unsafe-inline'; "
                        "script-src 'unsafe-inline'"
                    ),
                    "X-Frame-Options": "DENY",
                    "X-Content-Type-Options": "nosniff",
                },
            )

        async def status_endpoint(request: Request) -> JSONResponse:
            if request.headers.get("X-Auth-Token") != self._token:
                return JSONResponse({"error": "Forbidden"}, status_code=403)
            try:
                authorized = await self._backend.is_authorized()
            except Exception:
                authorized = False
            data: dict = {"authenticated": authorized}
            if authorized and self._auth_name:
                data["name"] = self._auth_name
            return JSONResponse(data)

        async def send_code(request: Request) -> JSONResponse:
            if request.headers.get("X-Auth-Token") != self._token:
                return JSONResponse({"error": "Forbidden"}, status_code=403)
            ip = self._get_client_ip(request)
            if not self._check_rate_limit(f"send_code:{ip}"):
                return JSONResponse(
                    {
                        "ok": False,
                        "error": "Too many attempts. Please try again later.",
                    },
                    status_code=429,
                )
            phone = self._settings.phone
            if not phone:
                return JSONResponse(
                    {"ok": False, "error": "TELEGRAM_PHONE not configured"}
                )
            try:
                await self._backend.send_code(phone)
                return JSONResponse({"ok": True})
            except Exception as e:
                return JSONResponse({"ok": False, "error": sanitize_error(str(e))})

        async def verify(request: Request) -> JSONResponse:
            if request.headers.get("X-Auth-Token") != self._token:
                return JSONResponse({"error": "Forbidden"}, status_code=403)
            ip = self._get_client_ip(request)
            if not self._check_rate_limit(f"verify:{ip}"):
                return JSONResponse(
                    {
                        "ok": False,
                        "error": "Too many attempts. Please try again later.",
                    },
                    status_code=429,
                )
            try:
                body = await request.json()
            except Exception:
                return JSONResponse({"ok": False, "error": "Invalid request"})
            code = body.get("code", "").strip()
            if not code:
                return JSONResponse({"ok": False, "error": "Code is required"})
            phone = self._settings.phone
            if not phone:
                return JSONResponse(
                    {"ok": False, "error": "TELEGRAM_PHONE not configured"}
                )
            password = body.get("password") or None
            try:
                result = await self._backend.sign_in(phone, code, password=password)
                self._auth_name = result.get("authenticated_as", "User")
                self._auth_complete.set()
                return JSONResponse({"ok": True, "name": self._auth_name})
            except Exception as e:
                error_msg = str(e)
                needs_password = any(
                    kw in error_msg.lower()
                    for kw in ("password", "2fa", "two-factor", "srp")
                )
                clean_msg = sanitize_error(error_msg)
                resp: dict = {"ok": False, "error": clean_msg}
                if needs_password:
                    resp["needs_password"] = True
                return JSONResponse(resp)

        app = Starlette(
            routes=[
                Route("/", index),
                Route("/status", status_endpoint),
                Route("/send-code", send_code, methods=["POST"]),
                Route("/verify", verify, methods=["POST"]),
            ]
        )
        # 🛡️ Sentinel: Restrict Host header to local addresses only
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["127.0.0.1", "localhost", "testserver"],
        )
        return app

    async def start(self) -> str:
        """Start the auth server. Returns the URL."""
        import uvicorn

        self.port = _find_free_port()
        self.url = f"http://127.0.0.1:{self.port}?token={self._token}"

        app = self._make_app()
        config = uvicorn.Config(
            app, host="127.0.0.1", port=self.port, log_level="warning"
        )
        server = uvicorn.Server(config)
        task = asyncio.create_task(server.serve())
        self._uvicorn_server = server

        # Wait briefly to see if it fails (e.g. port already bound)
        await asyncio.sleep(0.3)
        if task.done():
            try:
                task.result()  # Raise exception if task failed
            except OSError as e:
                raise RuntimeError(
                    f"Could not start server on port {self.port}: {e}"
                ) from e
        from loguru import logger

        logger.info("Auth server started at {}", self.url)
        return self.url

    async def wait_for_auth(self) -> None:
        """Block until authentication is complete."""
        await self._auth_complete.wait()

    async def stop(self) -> None:
        """Stop the auth server."""
        if self._uvicorn_server is not None:
            from uvicorn import Server

            server = self._uvicorn_server
            if hasattr(server, "should_exit"):
                server.should_exit = True
            await asyncio.sleep(0.5)
            self._uvicorn_server = None
            from loguru import logger

            logger.info("Auth server stopped")
