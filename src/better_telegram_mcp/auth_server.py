"""Local web server for Telegram OTP authentication.

Used when TELEGRAM_AUTH_URL=local. Serves auth form on localhost.
Runs for the MCP server lifetime. Shows auth form when unauthorized,
status page when authenticated.
"""

from __future__ import annotations

import asyncio
import bisect
import html
import re
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
input:focus-visible,button:focus-visible{outline:2px solid #3b82f6;outline-offset:2px}
input[aria-invalid="true"]{border-color:#ef4444}
input[aria-invalid="true"]:focus,input[aria-invalid="true"]:focus-visible{border-color:#ef4444;outline:2px solid #ef4444}
button{width:100%;padding:.75rem;background:#3b82f6;color:#fff;border:none;
  border-radius:8px;font-size:1rem;cursor:pointer;font-weight:500}
button:hover{background:#2563eb}
button:disabled{background:#333;color:#666;cursor:not-allowed}
button[aria-busy="true"]{color:transparent!important;position:relative;pointer-events:none;opacity:1!important;background:#3b82f6!important}
button[aria-busy="true"]::after{content:"";position:absolute;left:50%;top:50%;width:1.25rem;height:1.25rem;margin:-0.625rem 0 0 -0.625rem;border:2px solid rgba(255,255,255,0.3);border-top-color:#fff;border-radius:50%;animation:spin 0.8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.st{margin-top:1rem;padding:.75rem;border-radius:8px;font-size:.875rem;display:none}
.st.error{display:block;background:#2d1111;border:1px solid #dc2626;color:#f87171}
.st.success{display:block;background:#0d2818;border:1px solid #16a34a;color:#4ade80}
.st.info{display:block;background:#1a1a2e;border:1px solid #3b82f6;color:#93c5fd}
.phone{font-family:monospace;color:#3b82f6}
#pwd-section{display:none;margin-top:.5rem}
.pwd-hint{font-size:.8rem;color:#888;margin-bottom:.5rem}
.divider{border:0;border-top:1px solid #333;margin:1.25rem 0}
.req{color:#ef4444;margin-left:.25rem}
</style>
</head>
<body>
<div class="card">
  <h1>Telegram Authentication</h1>
  <p class="sub">MCP Server -- <span class="phone">PHONE</span></p>

  <div id="step0" class="step">
    <form onsubmit="event.preventDefault(); sendCode();">
      <fieldset id="fs0" style="border:none;padding:0;margin:0">
        <p style="margin-bottom:1rem;color:#aaa">
          Step 1: Send a login code to your Telegram app.
        </p>
        <button id="btn-send" type="submit">Send OTP Code</button>
        <div id="s0" class="st" role="status" aria-live="polite"></div>
      </fieldset>
    </form>

    <hr class="divider">

    <form onsubmit="event.preventDefault(); verify();">
      <fieldset id="fs1" style="border:none;padding:0;margin:0">
        <p style="margin-bottom:.75rem;color:#aaa">
          Step 2: Enter the code you received.
        </p>
        <label for="otp">OTP Code <span aria-hidden="true" class="req">*</span></label>
        <input id="otp" type="text" placeholder="Enter code" autofocus
               inputmode="numeric" pattern="[0-9]*"
               autocomplete="one-time-code" aria-describedby="s1" required>
        <div id="pwd-section">
          <label for="pwd">2FA Password <span aria-hidden="true" class="req">*</span></label>
          <input id="pwd" type="password" placeholder="Enter your 2FA password"
                 autocomplete="current-password" aria-describedby="pwd-hint s1">
          <p id="pwd-hint" class="pwd-hint">Your account has two-factor authentication enabled.</p>
        </div>
        <button id="btn-verify" type="submit">Verify Code</button>
        <div id="s1" class="st" role="status" aria-live="polite"></div>
      </fieldset>
    </form>
  </div>

  <div id="step2" class="step">
    <div class="st success" style="display:block" role="status" aria-live="polite">
      Authenticated as <strong id="auth-name"></strong>.<br>
      MCP server is now active. You can close this tab.
    </div>
  </div>

  <div id="loading" class="step active">
    <p style="color:#666">Checking session...</p>
  </div>
</div>
<script>
const $=id=>document.getElementById(id),_t=new URLSearchParams(window.location.search).get("token");
function show(id){
  document.querySelectorAll('.step').forEach(s=>s.classList.remove('active'));
  $(id).classList.add('active');
}
function st(el,cls,msg){el.className='st '+cls;el.textContent=msg;el.style.display='block'}
function clearSt(el){el.className='st';el.textContent='';el.style.display='none'}
function btnLoading(fs,btn,text){fs.disabled=true;btn.textContent=text;btn.setAttribute('aria-busy','true')}
function btnReset(fs,btn,text){fs.disabled=false;btn.textContent=text;btn.removeAttribute('aria-busy')}
function showPwd(){$('pwd-section').style.display='block';$('pwd').required=true;$('pwd').focus()}
function setInvalid(id){$(id).setAttribute('aria-invalid','true')}
function clearInvalid(id){$(id).removeAttribute('aria-invalid')}

async function checkStatus(){
  try{const r=await fetch('/status',{headers:{'X-Auth-Token':_t}});const d=await r.json();
    if(d.authenticated){$('auth-name').textContent=d.name||'User';show('step2')}
    else{show('step0');$('otp').focus()}
  }catch(e){show('step0')}
}

async function sendCode(){
  const btn=$('btn-send'),s=$('s0'),fs=$('fs0');
  btnLoading(fs,btn,'Sending...');clearSt($('s1'));
  try{const r=await fetch('/send-code',{method:'POST',headers:{'X-Auth-Token':_t}});const d=await r.json();
    if(d.ok){st(s,'info','Code sent! Check your Telegram app.');btnReset(fs,btn,'Resend Code');$('otp').focus()}
    else{st(s,'error',d.error||'Failed to send code');btnReset(fs,btn,'Retry')}
  }catch(e){st(s,'error','Network error. Check your connection.');btnReset(fs,btn,'Retry')}
}

async function verify(){
  const btn=$('btn-verify'),s=$('s1'),fs=$('fs1');
  clearInvalid('otp');clearInvalid('pwd');
  const code=$('otp').value.trim();
  if(!code){st(s,'error','Please enter the OTP code first.');setInvalid('otp');return}
  btnLoading(fs,btn,'Verifying...');
  try{const body={code};const pwd=$('pwd').value.trim();if(pwd)body.password=pwd;
    const r=await fetch('/verify',{method:'POST',headers:{'Content-Type':'application/json','X-Auth-Token':_t},body:JSON.stringify(body)});
    const d=await r.json();
    if(d.ok){$('auth-name').textContent=d.name||'User';show('step2')}
    else{
      btnReset(fs,btn,'Verify Code');
      if(d.needs_password){showPwd();st(s,'error','2FA password is required. Please enter it above.');setInvalid('pwd')}
      else{st(s,'error',d.error||'Verification failed');setInvalid('otp');if($('pwd-section').style.display==='block')setInvalid('pwd')}
    }
  }catch(e){st(s,'error','Network error. Check your connection.');setInvalid('otp');if($('pwd-section').style.display==='block')setInvalid('pwd');btnReset(fs,btn,'Verify Code')}
}
checkStatus();
</script>
</body>
</html>"""


_CAUSED_BY_RE = re.compile(r"\s*\(caused by \w+\)\s*$", re.IGNORECASE)

_ERROR_SIMPLIFICATIONS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r".*password.*required.*", re.IGNORECASE),
        "Two-factor authentication password is required.",
    ),
    (
        re.compile(r".*password.*invalid.*|.*invalid.*password.*", re.IGNORECASE),
        "Incorrect 2FA password. Please try again.",
    ),
    (
        re.compile(r".*phone.*code.*invalid.*|.*invalid.*code.*", re.IGNORECASE),
        "Invalid OTP code. Please check and try again.",
    ),
    (
        re.compile(r".*phone.*code.*expired.*|.*code.*expired.*", re.IGNORECASE),
        "OTP code has expired. Please request a new one.",
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
    """Find an available port on 127.0.0.1."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]
    except OSError as e:
        raise RuntimeError(f"Could not find a free port: {e}") from e


def _mask_phone(phone: str) -> str:
    if len(phone) > 7:
        return phone[:4] + "***" + phone[-4:]
    return phone[:2] + "***"


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
        """Extract actual client socket IP to prevent spoofing and rate limit bypass."""
        client_ip = request.client.host if request.client else "unknown"
        # 🛡️ Sentinel: Never trust x-forwarded-for or cf-connecting-ip headers for rate
        # limiting unless explicitly behind a configured trusted proxy, as they can be easily spoofed.
        if client_ip in self._settings.trusted_proxy_list:
            if "cf-connecting-ip" in request.headers:
                return request.headers["cf-connecting-ip"]
            if "x-forwarded-for" in request.headers:
                return request.headers["x-forwarded-for"].split(",")[0].strip()
        return client_ip

    def _check_rate_limit(self, key: str) -> bool:
        """Check if key is within rate limit. Returns True if allowed."""
        now = time.time()
        window_start = now - self._RATE_LIMIT_WINDOW
        timestamps = self._rate_limits[key]

        # ⚡ Bolt: Use bisect.bisect_right for O(log N) sliding window pruning
        # and del for in-place modification to avoid O(N) list rebuilding.
        idx = bisect.bisect_right(timestamps, window_start)
        if idx > 0:
            del timestamps[:idx]

        if len(timestamps) >= self._RATE_LIMIT_MAX:
            return False
        timestamps.append(now)
        return True

    def _make_app(self) -> Starlette:
        async def index(request: Request) -> HTMLResponse:
            phone = self._settings.phone or "unknown"
            # 🛡️ Sentinel: Prevent XSS by escaping dynamic data before insertion
            page_html = _PAGE.replace("PHONE", html.escape(_mask_phone(phone)))
            return HTMLResponse(
                page_html,
                headers={
                    "Content-Security-Policy": "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'",
                    "X-Frame-Options": "DENY",
                    "X-Content-Type-Options": "nosniff",
                },
            )

        async def status_endpoint(request: Request) -> JSONResponse:
            if not secrets.compare_digest(
                request.headers.get("X-Auth-Token", ""), self._token
            ):
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
            if not secrets.compare_digest(
                request.headers.get("X-Auth-Token", ""), self._token
            ):
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
                return JSONResponse({"ok": False, "error": _sanitize_error(str(e))})

        async def verify(request: Request) -> JSONResponse:
            if not secrets.compare_digest(
                request.headers.get("X-Auth-Token", ""), self._token
            ):
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
                clean_msg = _sanitize_error(error_msg)
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
        logger.info("Auth server started on port {}", self.port)
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
