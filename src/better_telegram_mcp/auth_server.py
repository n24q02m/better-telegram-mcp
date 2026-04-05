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

from loguru import logger
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

from .utils.formatting import mask_phone, sanitize_error

if TYPE_CHECKING:
    from .backends.base import TelegramBackend
    from .config import Settings

_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Telegram Auth</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,-apple-system,sans-serif;background:#0f0f0f;color:#e0e0e0;
  display:flex;justify-content:center;align-items:center;min-height:100vh}
.card{background:#1a1a1a;border:1px solid #333;border-radius:12px;padding:2.5rem;
  max-width:420px;width:100%}
h1{font-size:1.5rem;font-weight:600;margin-bottom:.5rem;color:#fff}
p{color:#999;font-size:.9rem;line-height:1.5;margin-bottom:2rem}
.form-group{margin-bottom:1.5rem}
label{display:block;font-size:.8rem;font-weight:500;margin-bottom:.5rem;color:#bbb;text-transform:uppercase;letter-spacing:.05em}
input{width:100%;background:#262626;border:1px solid #333;border-radius:6px;padding:.75rem;color:#fff;font-size:1rem;transition:border-color .2s}
input:focus{outline:none;border-color:#2481cc}
button{width:100%;background:#2481cc;color:#fff;border:none;border-radius:6px;padding:.75rem;font-size:1rem;font-weight:600;cursor:pointer;transition:background .2s}
button:hover{background:#288fdf}
button:disabled{background:#333;cursor:not-allowed;color:#666}
.status{margin-top:1rem;font-size:.85rem;text-align:center;min-height:1.25rem}
.status.error{color:#ff4d4d}
.status.success{color:#4dff88}
.step{display:none}
.step.active{display:block}
.phone-display{background:#262626;padding:.5rem .75rem;border-radius:6px;font-family:monospace;color:#2481cc;margin-bottom:1.5rem;display:inline-block}
#pwd-group{display:none}
</style>
</head>
<body>
<div class="card">
  <div id="step1" class="step active">
    <h1>Authentication</h1>
    <p>Sign in to Telegram to enable MCP tools. A code will be sent to your Telegram app.</p>
    <div class="phone-display">PHONE</div>
    <button id="btn-send" onclick="sendCode()">Send Code</button>
    <div id="status1" class="status"></div>
  </div>

  <div id="step-verify" class="step">
    <h1>Verify Code</h1>
    <p>Enter the 5-digit code sent to your Telegram app.</p>
    <div class="form-group">
      <label for="otp">OTP Code</label>
      <input type="text" id="otp" placeholder="12345" autocomplete="one-time-code">
    </div>
    <div id="pwd-group" class="form-group">
      <label for="pwd">2FA Password</label>
      <input type="password" id="pwd" placeholder="Enter password">
    </div>
    <button id="btn-verify" onclick="verify()">Verify</button>
    <div id="status-v" class="status"></div>
  </div>

  <div id="step2" class="step">
    <h1 style="color:#4dff88">✓ Authenticated</h1>
    <p>Successfully signed in as <strong id="auth-name" style="color:#fff">User</strong>. You can now close this tab and return to your agent.</p>
    <button onclick="window.close()">Close Tab</button>
  </div>
</div>

<script>
const $=id=>document.getElementById(id);
const _t="TOKEN";
let _needsPwd=false;

function st(e,c,m){e.textContent=m;e.className='status '+c}
function btnLoad(b,t){b.disabled=true;b.textContent=t}
function btnReset(b,t){b.disabled=false;b.textContent=t}
function show(id){
  document.querySelectorAll('.step').forEach(s=>s.classList.remove('active'));
  $(id).classList.add('active');
}
function showPwd(){
  _needsPwd=true;
  $('pwd-group').style.display='block';
}

async function sendCode(){
  const btn=$('btn-send'), s=$('status1');
  btnLoad(btn,'Sending...');
  try{
    const r=await fetch('/send-code',{method:'POST',headers:{'X-Auth-Token':_t}});
    const d=await r.json();
    if(d.ok){show('step-verify')}
    else{st(s,'error',d.error||'Failed to send code');btnReset(btn,'Send Code')}
  }catch(e){st(s,'error','Network error');btnReset(btn,'Send Code')}
}

async function verify(){
  const btn=$('btn-verify'), s=$('status-v'), code=$('otp').value;
  if(!code){st(s,'error','Please enter the code');return}
  const body={code};
  if(_needsPwd)body.password=$('pwd').value;

  btnLoad(btn,'Verifying...');
  try{
    const r=await fetch('/verify',{method:'POST',headers:{'Content-Type':'application/json','X-Auth-Token':_t},body:JSON.stringify(body)});
    const d=await r.json();
    if(d.ok){$('auth-name').textContent=d.name||'User';show('step2')}
    else{
      if(d.needs_password){showPwd();st(s,'error','2FA password is required. Please enter it above.')}
      else{st(s,'error',d.error||'Verification failed')}
      btnReset(btn,'Verify Code');
    }
  }catch(e){st(s,'error','Network error. Check your connection.');btnReset(btn,'Verify Code')}
}

$('otp').addEventListener('keydown',e=>{if(e.key==='Enter')verify()});
document.addEventListener('DOMContentLoaded',()=>{
  const p=$('pwd');if(p)p.addEventListener('keydown',e=>{if(e.key==='Enter')verify()});
});
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
        """Extract client IP, respecting reverse proxy headers."""
        if "cf-connecting-ip" in request.headers:
            return request.headers["cf-connecting-ip"]
        if "x-forwarded-for" in request.headers:
            return request.headers["x-forwarded-for"].split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _check_rate_limit(self, key: str) -> bool:
        """Check if key is within rate limit. Returns True if allowed."""
        now = time.time()
        window_start = now - self._RATE_LIMIT_WINDOW
        self._rate_limits[key] = [t for t in self._rate_limits[key] if t > window_start]
        if len(self._rate_limits[key]) >= self._RATE_LIMIT_MAX:
            return False
        self._rate_limits[key].append(now)
        return True

    async def _handle_index(self, request: Request) -> HTMLResponse:
        """Serve the auth form."""
        if self._auth_complete.is_set():
            page_html = _PAGE.replace("step active", "step").replace(
                'id="step2" class="step"', 'id="step2" class="step active"'
            )
            page_html = page_html.replace("User", html.escape(self._auth_name))
        else:
            phone = self._settings.phone or "Unknown"
            page_html = _PAGE.replace("PHONE", html.escape(mask_phone(phone)))

        page_html = page_html.replace("TOKEN", self._token)
        return HTMLResponse(page_html)

    async def _handle_send_code(self, request: Request) -> JSONResponse:
        """Send OTP code to Telegram app."""
        if request.headers.get("x-auth-token") != self._token:
            return JSONResponse({"ok": False, "error": "Unauthorized"}, status_code=401)

        ip = self._get_client_ip(request)
        if not self._check_rate_limit(f"send_code:{ip}"):
            return JSONResponse(
                {"ok": False, "error": "Too many requests. Please wait."},
                status_code=429,
            )

        phone = self._settings.phone
        if not phone:
            return JSONResponse({"ok": False, "error": "Phone number not configured"})

        try:
            await self._backend.send_code(phone)
            return JSONResponse({"ok": True})
        except Exception as e:
            logger.warning("AuthServer send_code failed: {}", e)
            return JSONResponse({"ok": False, "error": sanitize_error(str(e))})

    async def _handle_verify(self, request: Request) -> JSONResponse:
        """Verify OTP code and optional password."""
        if request.headers.get("x-auth-token") != self._token:
            return JSONResponse({"ok": False, "error": "Unauthorized"}, status_code=401)

        ip = self._get_client_ip(request)
        if not self._check_rate_limit(f"verify:{ip}"):
            return JSONResponse(
                {"ok": False, "error": "Too many requests. Please wait."},
                status_code=429,
            )

        try:
            data = await request.json()
        except Exception:
            return JSONResponse({"ok": False, "error": "Invalid request body"})

        code = data.get("code")
        password = data.get("password")
        phone = self._settings.phone

        if not code or not phone:
            return JSONResponse({"ok": False, "error": "Code and phone required"})

        try:
            result = await self._backend.sign_in(phone, code, password=password)
            self._auth_name = result.get("authenticated_as", "User")
            self._auth_complete.set()
            return JSONResponse({"ok": True, "name": self._auth_name})
        except Exception as e:
            msg = str(e)
            logger.warning("AuthServer verify failed: {}", msg)
            needs_pwd = (
                "password" in msg.lower() or "2fa" in msg.lower() or "srp" in msg.lower()
            )
            return JSONResponse(
                {
                    "ok": False,
                    "error": sanitize_error(msg),
                    "needs_password": needs_pwd,
                }
            )

    async def _handle_status(self, request: Request) -> JSONResponse:
        """Check authentication status."""
        return JSONResponse(
            {
                "authenticated": self._auth_complete.is_set(),
                "name": self._auth_name,
            }
        )

    async def start(self) -> int:
        """Start the web server in the background. Returns the port."""
        self.port = _find_free_port()
        self.url = f"http://127.0.0.1:{self.port}"

        app = Starlette(
            routes=[
                Route("/", self._handle_index, methods=["GET"]),
                Route("/send-code", self._handle_send_code, methods=["POST"]),
                Route("/verify", self._handle_verify, methods=["POST"]),
                Route("/status", self._handle_status, methods=["GET"]),
            ]
        )

        import uvicorn

        config = uvicorn.Config(app, host="127.0.0.1", port=self.port, log_level="error")
        self._uvicorn_server = uvicorn.Server(config)

        # Start uvicorn in background
        asyncio.create_task(self._uvicorn_server.serve())
        logger.info("AuthServer started at {}", self.url)
        return self.port

    async def stop(self) -> None:
        """Stop the web server."""
        if self._uvicorn_server:
            await self._uvicorn_server.shutdown()
            self._uvicorn_server = None

    async def wait_for_auth(self) -> None:
        """Block until authentication is complete."""
        await self._auth_complete.wait()
