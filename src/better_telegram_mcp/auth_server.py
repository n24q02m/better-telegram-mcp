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
h1{font-size:1.5rem;margin-bottom:.5rem;color:#fff}
.sub{color:#888;font-size:.875rem;margin-bottom:1.5rem}
.step{display:none}.step.active{display:block}
label{display:block;font-size:.875rem;color:#aaa;margin-bottom:.5rem}
input{width:100%;padding:.75rem 1rem;background:#111;border:1px solid #444;
  border-radius:8px;color:#fff;font-size:1rem;outline:none;margin-bottom:1rem;
  font-family:monospace;letter-spacing:.15em;text-align:center}
input[type="password"]{letter-spacing:normal;text-align:left}
input:focus{border-color:#3b82f6}
button{width:100%;padding:.75rem;background:#3b82f6;color:#fff;border:none;
  border-radius:8px;font-size:1rem;font-weight:600;cursor:pointer;transition:background .2s}
button:hover{background:#2563eb}
button:disabled{background:#444;cursor:not-allowed}
.error{background:rgba(239,68,68,.1);border:1px solid #ef4444;color:#f87171;
  padding:.75rem;border-radius:8px;font-size:.875rem;margin-bottom:1rem;display:none}
.success-icon{color:#10b981;font-size:3rem;margin-bottom:1rem}
#step2 h1{color:#10b981}
.loader{display:inline-block;width:1.2rem;height:1.2rem;border:3px solid rgba(255,255,255,.3);
  border-radius:50%;border-top-color:#fff;animation:spin 1s ease-in-out infinite;margin-right:.5rem;vertical-align:middle}
@keyframes spin{to{transform:rotate(360deg)}}
</style>
</head>
<body>
<div class="card">
  <div id="step1" class="step active">
    <h1>Telegram Login</h1>
    <p class="sub">Authenticating for <strong>PHONE</strong></p>
    <div id="status" class="error" role="status" aria-live="polite"></div>
    <div id="auth-form">
      <label for="otp">Enter OTP Code</label>
      <input type="text" id="otp" placeholder="12345" autocomplete="one-time-code">
      <div id="pwd-wrap" style="display:none">
        <label for="pwd">Two-Factor Password</label>
        <input type="password" id="pwd" placeholder="Required for 2FA accounts">
      </div>
      <button id="btn-verify" onclick="verify()">Verify Code</button>
    </div>
  </div>
  <div id="step2" class="step" style="text-align:center">
    <div class="success-icon">✓</div>
    <h1>Success!</h1>
    <p class="sub">Authenticated as <strong id="auth-name">User</strong></p>
    <p>You can close this tab and return to your client.</p>
  </div>
</div>
<script>
const $=id=>document.getElementById(id);const _t=new URLSearchParams(window.location.search).get('token');
const st=(el,cls,msg)=>{el.className=cls;el.textContent=msg;el.style.display=msg?'block':'none'};
const btnLoading=(btn,txt)=>{btn.disabled=true;btn.innerHTML='<span class="loader"></span>'+txt};
const btnReset=(btn,txt)=>{btn.disabled=false;btn.innerHTML=txt};
const showPwd=()=>$('pwd-wrap').style.display='block';const show=id=>{document.querySelectorAll('.step').forEach(s=>s.classList.remove('active'));$(id).classList.add('active')};
async function checkStatus(){
  if(!_t)return;
  try{const r=await fetch('/status',{headers:{'X-Auth-Token':_t}});const d=await r.json();
    if(d.authenticated){$('auth-name').textContent=d.name||'User';show('step2')}}catch(e){}
}
async function verify(){
  const code=$('otp').value.trim();const s=$('status');const btn=$('btn-verify');st(s,'error','');
  if(!code){st(s,'error','Please enter the OTP code sent to your Telegram app.');return}
  btnLoading(btn,'Verifying...');
  try{const body={code};const pwd=$('pwd').value.trim();if(pwd)body.password=pwd;
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
                    "Content-Security-Policy": "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'",
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

        return Starlette(
            routes=[
                Route("/", index),
                Route("/status", status_endpoint),
                Route("/send-code", send_code, methods=["POST"]),
                Route("/verify", verify, methods=["POST"]),
            ]
        )

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
        logger.info("Auth server started at {}", self.url)
        return self.url

    async def wait_for_auth(self) -> None:
        """Block until authentication is complete."""
        await self._auth_complete.wait()

    async def stop(self) -> None:
        """Stop the auth server."""
        if self._uvicorn_server is not None:
            self._uvicorn_server.should_exit = True
            await asyncio.sleep(0.5)
            self._uvicorn_server = None
            logger.info("Auth server stopped")
