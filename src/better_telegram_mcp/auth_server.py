"""Local web server for Telegram OTP authentication.

Used when TELEGRAM_AUTH_URL=local. Serves auth form on localhost.
Runs for the MCP server lifetime. Shows auth form when unauthorized,
status page when authenticated.
"""

from __future__ import annotations

import asyncio
import html
import re
import socket
import time
from typing import TYPE_CHECKING

from loguru import logger
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

from .utils.formatting import _mask_phone

if TYPE_CHECKING:
    from .backends.base import TelegramBackend
    from .config import Settings


_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Telegram Auth</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; background: #f0f2f5; }
        .card { background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 100%; max-width: 400px; text-align: center; }
        h1 { margin-top: 0; color: #1c1e21; font-size: 24px; }
        p { color: #65676b; margin-bottom: 1.5rem; }
        input { width: 100%; padding: 12px; margin-bottom: 1rem; border: 1px solid #ddd; border-radius: 6px; box-sizing: border-box; font-size: 16px; }
        button { width: 100%; padding: 12px; background: #0088cc; color: white; border: none; border-radius: 6px; font-size: 16px; cursor: pointer; transition: background 0.2s; }
        button:hover { background: #0077b5; }
        button:disabled { background: #ccc; cursor: not-allowed; }
        #error { color: #d93025; margin-top: 1rem; display: none; }
        #status { color: #1a7f37; margin-top: 1rem; display: none; }
        .hidden { display: none !important; }
    </style>
</head>
<body>
    <div class="card" id="auth-card">
        <h1>Telegram Login</h1>
        <p>Enter the code sent to <b>PHONE</b></p>
        <div id="step-send">
            <button onclick="sendCode()" id="btn-send">Send Code</button>
        </div>
        <div id="step-verify" class="hidden">
            <input type="text" id="otp-code" placeholder="OTP Code" maxlength="10">
            <input type="password" id="otp-password" placeholder="2FA Password (if enabled)">
            <button onclick="verify()" id="btn-verify">Sign In</button>
        </div>
        <p id="error"></p>
        <p id="status"></p>
    </div>
    <div class="card hidden" id="success-card">
        <h1>Success!</h1>
        <p>You are now authenticated. You can close this window.</p>
    </div>

    <script>
        const error = document.getElementById('error');
        const status = document.getElementById('status');
        const stepSend = document.getElementById('step-send');
        const stepVerify = document.getElementById('step-verify');
        const btnSend = document.getElementById('btn-send');
        const btnVerify = document.getElementById('btn-verify');

        function showError(msg) {
            error.innerText = msg;
            error.style.display = 'block';
            status.style.display = 'none';
        }

        function showStatus(msg) {
            status.innerText = msg;
            status.style.display = 'block';
            error.style.display = 'none';
        }

        async function fetch_api(endpoint, body = {}) {
            const resp = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            const data = await resp.json();
            if (!data.ok) throw new Error(data.error || 'Request failed');
            return data;
        }

        async function sendCode() {
            try {
                btnSend.disabled = true;
                showStatus('Sending code...');
                await fetch_api('/api/send-code');
                stepSend.classList.add('hidden');
                stepVerify.classList.remove('hidden');
                showStatus('Code sent! Check your Telegram app.');
            } catch (e) {
                showError(e.message);
                btnSend.disabled = false;
            }
        }

        async function verify() {
            const code = document.getElementById('otp-code').value;
            const password = document.getElementById('otp-password').value;
            if (!code) return showError('Please enter the OTP code');

            try {
                btnVerify.disabled = true;
                showStatus('Verifying...');
                await fetch_api('/api/verify', { code, password });
                document.getElementById('auth-card').classList.add('hidden');
                document.getElementById('success-card').classList.remove('hidden');
            } catch (e) {
                showError(e.message);
                btnVerify.disabled = false;
            }
        }

        // Auto-check status
        setInterval(async () => {
            try {
                const resp = await fetch('/api/status');
                const data = await resp.json();
                if (data.authorized) {
                    document.getElementById('auth-card').classList.add('hidden');
                    document.getElementById('success-card').classList.remove('hidden');
                }
            } catch (e) {}
        }, 5000);
    </script>
</body>
</html>
"""

_CAUSED_BY_RE = re.compile(r"\(caused by .*\)", re.IGNORECASE)

_ERROR_SIMPLIFICATIONS = [
    (
        re.compile(r".*PHONE_NUMBER_INVALID.*", re.IGNORECASE),
        "Invalid phone number. Please check your TELEGRAM_PHONE.",
    ),
    (
        re.compile(r".*password.*required.*|.*2fa.*required.*", re.IGNORECASE),
        "Two-factor authentication (2FA) is required. Please enter your password.",
    ),
    (
        re.compile(r".*password.*invalid.*", re.IGNORECASE),
        "Invalid 2FA password. Please try again.",
    ),
    (
        re.compile(r".*code.*invalid.*|.*code.*expired.*", re.IGNORECASE),
        "Invalid or expired OTP code. Please request a new one.",
    ),
    (
        re.compile(r".*flood.*wait.*|.*too many.*", re.IGNORECASE),
        "Too many attempts. Please wait a moment and try again.",
    ),
]


def _sanitize_error(msg: str) -> str:
    """Simplify internal error messages to user-friendly text."""
    cleaned = _CAUSED_BY_RE.sub("", msg).strip()
    for pattern, friendly in _ERROR_SIMPLIFICATIONS:
        if pattern.match(cleaned):
            return friendly
    return cleaned


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class AuthServer:
    """Local web server for OTP authentication (TELEGRAM_AUTH_URL=local)."""

    _RATE_LIMIT_WINDOW = 60  # seconds
    _MAX_SEND_CODE_ATTEMPTS = 5
    _MAX_VERIFY_ATTEMPTS = 5

    def __init__(self, backend: TelegramBackend, settings: Settings):
        self._backend = backend
        self._settings = settings
        self._port = _find_free_port()
        self._server: asyncio.Task | None = None
        self._url = f"http://127.0.0.1:{self._port}"

        # Rate limiting state
        self._send_code_attempts: list[float] = []
        self._verify_attempts: list[float] = []

    @property
    def url(self) -> str:
        return self._url

    def _make_app(self) -> Starlette:
        async def index(request: Request) -> HTMLResponse:
            phone = self._settings.phone or "unknown"
            # 🛡️ Sentinel: Prevent XSS by escaping dynamic data before insertion
            page_html = _PAGE.replace("PHONE", html.escape(_mask_phone(phone)))
            return HTMLResponse(page_html)

        async def status_endpoint(request: Request) -> JSONResponse:
            try:
                authorized = await self._backend.is_authorized()
                return JSONResponse({"authorized": authorized})
            except Exception:
                return JSONResponse({"authorized": False})

        async def send_code_endpoint(request: Request) -> JSONResponse:
            now = time.time()
            self._send_code_attempts = [
                t for t in self._send_code_attempts if now - t < self._RATE_LIMIT_WINDOW
            ]

            if len(self._send_code_attempts) >= self._MAX_SEND_CODE_ATTEMPTS:
                return JSONResponse(
                    {
                        "ok": False,
                        "error": "Too many code requests. Please wait a minute.",
                    },
                    status_code=429,
                )

            try:
                self._send_code_attempts.append(now)
                phone = self._settings.phone or ""
                await self._backend.send_code(phone)
                return JSONResponse({"ok": True})
            except Exception as e:
                logger.warning(f"Failed to send code: {e}")
                return JSONResponse({"ok": False, "error": _sanitize_error(str(e))})

        async def verify_endpoint(request: Request) -> JSONResponse:
            now = time.time()
            self._verify_attempts = [
                t for t in self._verify_attempts if now - t < self._RATE_LIMIT_WINDOW
            ]

            if len(self._verify_attempts) >= self._MAX_VERIFY_ATTEMPTS:
                return JSONResponse(
                    {"ok": False, "error": "Too many verify attempts. Please wait."},
                    status_code=429,
                )

            try:
                data = await request.json()
                code = data.get("code")
                password = data.get("password")

                if not code:
                    return JSONResponse({"ok": False, "error": "Code is required"})

                self._verify_attempts.append(now)
                phone = self._settings.phone or ""
                await self._backend.sign_in(phone, code, password=password)
                # Success - clear rate limiting
                self._verify_attempts = []
                return JSONResponse({"ok": True})
            except Exception as e:
                logger.warning(f"Failed to verify: {e}")
                return JSONResponse({"ok": False, "error": _sanitize_error(str(e))})

        return Starlette(
            routes=[
                Route("/", index),
                Route("/api/status", status_endpoint),
                Route("/api/send-code", send_code_endpoint, methods=["POST"]),
                Route("/api/verify", verify_endpoint, methods=["POST"]),
            ]
        )

    async def start(self) -> None:
        """Start the server in a background task."""
        import uvicorn

        app = self._make_app()
        config = uvicorn.Config(app, host="127.0.0.1", port=self._port, log_level="warning")
        server = uvicorn.Server(config)

        # 🛡️ Sentinel: Bind explicitly to 127.0.0.1 for local security
        self._server = asyncio.create_task(server.serve())
        logger.info(f"Auth server started at {self._url}")

    async def stop(self) -> None:
        """Stop the background server task."""
        if self._server:
            self._server.cancel()
            try:
                await self._server
            except asyncio.CancelledError:
                pass
