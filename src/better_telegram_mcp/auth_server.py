"""Temporary local web server for Telegram OTP authentication."""

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

_AUTH_PAGE = """<!DOCTYPE html>
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
.status{margin-top:1rem;padding:.75rem;border-radius:8px;font-size:.875rem;display:none}
.status.error{display:block;background:#2d1111;border:1px solid #dc2626;color:#f87171}
.status.success{display:block;background:#0d2818;border:1px solid #16a34a;color:#4ade80}
.status.info{display:block;background:#1a1a2e;border:1px solid #3b82f6;color:#93c5fd}
.phone{font-family:monospace;color:#3b82f6}
.pwd-toggle{font-size:.8rem;color:#666;cursor:pointer;margin-bottom:1rem;display:inline-block}
.pwd-toggle:hover{color:#aaa}
#pwd-section{display:none}
</style>
</head>
<body>
<div class="card">
  <h1>Telegram Authentication</h1>
  <p class="sub">MCP Server needs your Telegram account access</p>

  <div id="step1" class="step active">
    <p style="margin-bottom:1rem">Send OTP code to <span class="phone">PHONE</span></p>
    <button onclick="sendCode()">Send OTP Code</button>
    <div id="s1-status" class="status"></div>
  </div>

  <div id="step2" class="step">
    <label for="otp">Enter OTP from Telegram app</label>
    <input id="otp" type="text" maxlength="6" placeholder="12345" autofocus
           inputmode="numeric" pattern="[0-9]*">
    <span class="pwd-toggle" onclick="togglePwd()">+ 2FA password</span>
    <div id="pwd-section">
      <label for="pwd">2FA Password</label>
      <input id="pwd" type="password" placeholder="Optional">
    </div>
    <button onclick="verify()">Verify</button>
    <div id="s2-status" class="status"></div>
  </div>

  <div id="step3" class="step">
    <div class="status success" style="display:block">
      Authenticated as <strong id="auth-name"></strong>.
      <br>You can close this tab. MCP server is now active.
    </div>
  </div>
</div>
<script>
function show(id){document.querySelectorAll('.step').forEach(s=>s.classList.remove('active'));
  document.getElementById(id).classList.add('active')}
function status(el,cls,msg){el.className='status '+cls;el.textContent=msg;el.style.display='block'}
function togglePwd(){const s=document.getElementById('pwd-section');
  s.style.display=s.style.display==='none'?'block':'none'}

async function sendCode(){
  const btn=document.querySelector('#step1 button');
  const st=document.getElementById('s1-status');
  btn.disabled=true;btn.textContent='Sending...';
  try{
    const r=await fetch('/send-code',{method:'POST'});
    const d=await r.json();
    if(d.ok){status(st,'info','OTP sent! Check your Telegram app.');
      setTimeout(()=>show('step2'),800)}
    else{status(st,'error',d.error||'Failed to send code');btn.disabled=false;btn.textContent='Retry'}
  }catch(e){status(st,'error','Network error');btn.disabled=false;btn.textContent='Retry'}
}

async function verify(){
  const btn=document.querySelector('#step2 button');
  const st=document.getElementById('s2-status');
  const code=document.getElementById('otp').value.trim();
  if(!code){status(st,'error','Enter the OTP code');return}
  btn.disabled=true;btn.textContent='Verifying...';
  try{
    const body={code};
    const pwd=document.getElementById('pwd').value.trim();
    if(pwd)body.password=pwd;
    const r=await fetch('/verify',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify(body)});
    const d=await r.json();
    if(d.ok){document.getElementById('auth-name').textContent=d.name||'User';show('step3')}
    else{status(st,'error',d.error||'Verification failed');btn.disabled=false;btn.textContent='Verify'}
  }catch(e){status(st,'error','Network error');btn.disabled=false;btn.textContent='Verify'}
}

document.getElementById('otp').addEventListener('keydown',e=>{if(e.key==='Enter')verify()});
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
    """Temporary localhost web server for OTP authentication."""

    def __init__(self, backend: TelegramBackend, settings: Settings):
        self._backend = backend
        self._settings = settings
        self._auth_complete = asyncio.Event()
        self._auth_name: str = ""
        self._server: asyncio.Server | None = None
        self.port: int = 0
        self.url: str = ""

    def _make_app(self) -> Starlette:
        async def index(request: Request) -> HTMLResponse:
            phone = self._settings.phone or "unknown"
            html = _AUTH_PAGE.replace("PHONE", _mask_phone(phone))
            return HTMLResponse(html)

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
        # Run in background task
        asyncio.create_task(server.serve())
        self._server = server
        # Wait briefly for server to start
        await asyncio.sleep(0.3)
        logger.info("Auth server started at {}", self.url)
        return self.url

    async def wait_for_auth(self) -> str:
        """Block until authentication is complete. Returns authenticated name."""
        await self._auth_complete.wait()
        return self._auth_name

    async def stop(self) -> None:
        """Stop the auth server."""
        if self._server is not None:
            self._server.should_exit = True
            await asyncio.sleep(0.5)
            self._server = None
            logger.info("Auth server stopped")
