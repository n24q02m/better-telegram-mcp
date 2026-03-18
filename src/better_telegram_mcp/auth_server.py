"""Local web server for Telegram OTP authentication.

Used when TELEGRAM_AUTH_URL=local. Serves auth form on localhost.
Runs for the MCP server lifetime. Shows auth form when unauthorized,
status page when authenticated.
"""

from __future__ import annotations

import asyncio
import socket
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
  max-width:400px;width:100%}
h1{font-size:1.5rem;margin-bottom:.5rem;color:#fff}
.sub{color:#888;font-size:.875rem;margin-bottom:1.5rem}
.step{display:none}.step.active{display:block}
label{display:block;font-size:.875rem;color:#aaa;margin-bottom:.5rem}
input{width:100%;padding:.75rem 1rem;background:#111;border:1px solid #444;
  border-radius:8px;color:#fff;font-size:1rem;outline:none;margin-bottom:1rem;
  font-family:monospace;letter-spacing:.15em;text-align:center}
input:focus{border-color:#3b82f6}
button{width:100%;padding:.75rem;background:#3b82f6;color:#fff;border:none;
  border-radius:8px;font-size:1rem;cursor:pointer;font-weight:500}
button:hover{background:#2563eb}
button:disabled{background:#333;color:#666;cursor:not-allowed}
.st{margin-top:1rem;padding:.75rem;border-radius:8px;font-size:.875rem;display:none}
.st.error{display:block;background:#2d1111;border:1px solid #dc2626;color:#f87171}
.st.success{display:block;background:#0d2818;border:1px solid #16a34a;color:#4ade80}
.st.info{display:block;background:#1a1a2e;border:1px solid #3b82f6;color:#93c5fd}
.phone{font-family:monospace;color:#3b82f6}
.pwd-toggle{font-size:.8rem;color:#666;cursor:pointer;margin-bottom:1rem;display:inline-block}
.pwd-toggle:hover{color:#aaa}
#pwd-section{display:none}
</style>
</head>
<body>
<div class="card">
  <h1>Telegram Authentication</h1>
  <p class="sub">MCP Server — <span class="phone">PHONE</span></p>

  <div id="step0" class="step">
    <p style="margin-bottom:1rem">Send OTP code to your Telegram app</p>
    <button onclick="sendCode()">Send OTP Code</button>
    <div id="s0" class="st"></div>
  </div>

  <div id="step1" class="step">
    <label for="otp">Enter OTP from Telegram app</label>
    <input id="otp" type="text" maxlength="6" placeholder="12345" autofocus
           inputmode="numeric" pattern="[0-9]*">
    <span class="pwd-toggle" onclick="togglePwd()">+ 2FA password</span>
    <div id="pwd-section">
      <label for="pwd">2FA Password</label>
      <input id="pwd" type="password" placeholder="Required if 2FA enabled">
    </div>
    <button onclick="verify()">Verify</button>
    <div id="s1" class="st"></div>
  </div>

  <div id="step2" class="step">
    <div class="st success" style="display:block">
      Authenticated as <strong id="auth-name"></strong>.<br>
      MCP server is now active. You can close this tab.
    </div>
  </div>

  <div id="loading" class="step active">
    <p style="color:#666">Checking session...</p>
  </div>
</div>
<script>
const $=id=>document.getElementById(id);
function show(id){document.querySelectorAll('.step').forEach(s=>s.classList.remove('active'));$(id).classList.add('active')}
function st(el,cls,msg){el.className='st '+cls;el.textContent=msg;el.style.display='block'}
function togglePwd(){const s=$('pwd-section');s.style.display=s.style.display==='none'?'block':'none'}

async function checkStatus(){
  try{const r=await fetch('/status');const d=await r.json();
    if(d.authenticated){$('auth-name').textContent=d.name||'User';show('step2')}
    else{show('step0')}
  }catch(e){show('step0')}
}

async function sendCode(){
  const btn=$('step0').querySelector('button'),s=$('s0');
  btn.disabled=true;btn.textContent='Sending...';
  try{const r=await fetch('/send-code',{method:'POST'});const d=await r.json();
    if(d.ok){st(s,'info','OTP sent! Check your Telegram app.');setTimeout(()=>{show('step1');$('otp').focus()},800)}
    else{st(s,'error',d.error||'Failed');btn.disabled=false;btn.textContent='Retry'}
  }catch(e){st(s,'error','Network error');btn.disabled=false;btn.textContent='Retry'}
}

async function verify(){
  const btn=$('step1').querySelector('button'),s=$('s1');
  const code=$('otp').value.trim();
  if(!code){st(s,'error','Enter the OTP code');return}
  btn.disabled=true;btn.textContent='Verifying...';
  try{const body={code};const pwd=$('pwd').value.trim();if(pwd)body.password=pwd;
    const r=await fetch('/verify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    const d=await r.json();
    if(d.ok){$('auth-name').textContent=d.name||'User';show('step2')}
    else{st(s,'error',d.error||'Failed');btn.disabled=false;btn.textContent='Verify'}
  }catch(e){st(s,'error','Network error');btn.disabled=false;btn.textContent='Verify'}
}

$('otp').addEventListener('keydown',e=>{if(e.key==='Enter')verify()});
checkStatus();
</script>
</body>
</html>"""


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _mask_phone(phone: str) -> str:
    if len(phone) > 7:
        return phone[:4] + "***" + phone[-4:]
    return phone[:2] + "***"


class AuthServer:
    """Local web server for OTP authentication (TELEGRAM_AUTH_URL=local)."""

    def __init__(self, backend: TelegramBackend, settings: Settings):
        self._backend = backend
        self._settings = settings
        self._auth_complete = asyncio.Event()
        self._auth_name: str = ""
        self._uvicorn_server: object | None = None
        self.port: int = 0
        self.url: str = ""

    def _make_app(self) -> Starlette:
        async def index(request: Request) -> HTMLResponse:
            phone = self._settings.phone or "unknown"
            html = _PAGE.replace("PHONE", _mask_phone(phone))
            return HTMLResponse(html)

        async def status_endpoint(request: Request) -> JSONResponse:
            try:
                authorized = await self._backend.is_authorized()
            except Exception:
                authorized = False
            data: dict = {"authenticated": authorized}
            if authorized and self._auth_name:
                data["name"] = self._auth_name
            return JSONResponse(data)

        async def send_code(request: Request) -> JSONResponse:
            phone = self._settings.phone
            if not phone:
                return JSONResponse(
                    {"ok": False, "error": "TELEGRAM_PHONE not configured"}
                )
            try:
                await self._backend.send_code(phone)
                return JSONResponse({"ok": True})
            except Exception as e:
                return JSONResponse({"ok": False, "error": str(e)})

        async def verify(request: Request) -> JSONResponse:
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
                return JSONResponse({"ok": False, "error": str(e)})

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
        self.url = f"http://127.0.0.1:{self.port}"

        app = self._make_app()
        config = uvicorn.Config(
            app, host="127.0.0.1", port=self.port, log_level="warning"
        )
        server = uvicorn.Server(config)
        asyncio.create_task(server.serve())
        self._uvicorn_server = server
        await asyncio.sleep(0.3)
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
