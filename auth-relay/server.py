"""Remote auth relay server for better-telegram-mcp.

Stateless relay between user's browser and MCP server.
No Telegram credentials stored — only relays OTP codes and results.

Deploy: Docker on OCI VM, Caddy reverse proxy, CF Tunnel.
Domain: better-telegram-mcp.n24q02m.com
"""

from __future__ import annotations

import html
import json
import time
import uuid
from collections import defaultdict

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

SESSION_TTL = 600  # 10 minutes
CLEANUP_INTERVAL = 60
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 30  # requests per window per IP
OTP_ATTEMPT_LIMIT = 5  # max verify attempts per session

# In-memory session store
_sessions: dict[str, dict] = {}
_last_cleanup: float = 0

# Rate limiting
_rate_limits: dict[str, list[float]] = defaultdict(list)


def _get_client_ip(request: Request) -> str:
    """Safely extract client IP, respecting reverse proxies if headers are present."""
    if "cf-connecting-ip" in request.headers:
        return request.headers["cf-connecting-ip"]
    if "x-forwarded-for" in request.headers:
        # X-Forwarded-For can be a comma-separated list of IPs; the first is the client
        return request.headers["x-forwarded-for"].split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_rate_limit(ip: str) -> bool:
    """Return True if request is allowed, False if rate limited."""
    now = time.time()
    window = _rate_limits[ip]
    _rate_limits[ip] = [t for t in window if now - t < RATE_LIMIT_WINDOW]
    if len(_rate_limits[ip]) >= RATE_LIMIT_MAX:
        return False
    _rate_limits[ip].append(now)
    return True


def _cleanup() -> None:
    global _last_cleanup
    now = time.time()
    if now - _last_cleanup < CLEANUP_INTERVAL:
        return
    _last_cleanup = now
    expired = [k for k, v in _sessions.items() if now - v["created_at"] > SESSION_TTL]
    for k in expired:
        del _sessions[k]


def _mask_phone(phone: str) -> str:
    if len(phone) > 7:
        return phone[:4] + "***" + phone[-4:]
    return phone[:2] + "***"


# HTML template
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
  <p class="sub">MCP Server — <span class="phone">PHONE_PLACEHOLDER</span></p>

  <div id="step0" class="step active">
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

  <div id="step-wait" class="step">
    <div class="st info" style="display:block" id="wait-msg">
      Waiting for MCP server to process...
    </div>
  </div>

  <div id="step-expired" class="step">
    <div class="st error" style="display:block">
      Session expired. Restart your MCP server to get a new auth link.
    </div>
  </div>
</div>
<script>
const TOKEN=TOKEN_PLACEHOLDER;
const $=id=>document.getElementById(id);
function show(id){document.querySelectorAll('.step').forEach(s=>s.classList.remove('active'));$(id).classList.add('active')}
function st(el,cls,msg){el.className='st '+cls;el.textContent=msg;el.style.display='block'}
function togglePwd(){const s=$('pwd-section');s.style.display=s.style.display==='none'?'block':'none'}

async function sendCode(){
  const btn=$('step0').querySelector('button'),s=$('s0');
  btn.disabled=true;btn.textContent='Sending...';
  try{
    const r=await fetch(`/auth/${TOKEN}/send-code`,{method:'POST'});const d=await r.json();
    if(d.ok){st(s,'info','Requesting OTP...');show('step-wait');pollStatus('send_code_done')}
    else{st(s,'error',d.error||'Failed');btn.disabled=false;btn.textContent='Retry'}
  }catch(e){st(s,'error','Network error');btn.disabled=false;btn.textContent='Retry'}
}

async function verify(){
  const btn=$('step1').querySelector('button'),s=$('s1');
  const code=$('otp').value.trim();
  if(!code){st(s,'error','Enter the OTP code');return}
  btn.disabled=true;btn.textContent='Verifying...';
  try{
    const body={code};const pwd=$('pwd').value.trim();if(pwd)body.password=pwd;
    const r=await fetch(`/auth/${TOKEN}/verify`,{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    const d=await r.json();
    if(d.ok){st(s,'info','Verifying...');show('step-wait');pollStatus('completed')}
    else{st(s,'error',d.error||'Failed');btn.disabled=false;btn.textContent='Verify'}
  }catch(e){st(s,'error','Network error');btn.disabled=false;btn.textContent='Verify'}
}

async function pollStatus(waitFor){
  for(let i=0;i<150;i++){
    await new Promise(r=>setTimeout(r,2000));
    try{
      const r=await fetch(`/auth/${TOKEN}/status`);const d=await r.json();
      if(d.status==='expired'){show('step-expired');return}
      if(d.status==='error'){$('wait-msg').textContent=d.error||'Error';
        if(waitFor==='completed'){show('step1');st($('s1'),'error',d.error||'Failed');
          $('step1').querySelector('button').disabled=false;$('step1').querySelector('button').textContent='Verify'}
        else{show('step0');st($('s0'),'error',d.error||'Failed');
          $('step0').querySelector('button').disabled=false;$('step0').querySelector('button').textContent='Retry'}
        return}
      if(waitFor==='send_code_done'&&(d.status==='send_code_done'||d.status==='idle')){
        show('step1');$('otp').focus();return}
      if(waitFor==='completed'&&d.status==='completed'){
        $('auth-name').textContent=d.name||'User';show('step2');return}
    }catch(e){}
  }
}

$('otp').addEventListener('keydown',e=>{if(e.key==='Enter')verify()});
</script>
</body>
</html>"""


# ============================================================
# API endpoints (called by MCP server local)
# ============================================================


async def api_create_session(request: Request) -> JSONResponse:
    """MCP local creates a new auth session."""
    ip = _get_client_ip(request)
    if not _check_rate_limit(ip):
        return JSONResponse({"error": "Rate limited"}, status_code=429)
    _cleanup()
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid request"}, status_code=400)

    token = uuid.uuid4().hex
    _sessions[token] = {
        "phone_masked": body.get("phone_masked", "***"),
        "status": "idle",
        "command": None,
        "result": None,
        "created_at": time.time(),
    }
    base = str(request.base_url).rstrip("/")
    return JSONResponse({"token": token, "url": f"{base}/auth/{token}"})


async def api_poll_session(request: Request) -> JSONResponse:
    """MCP local polls for pending commands."""
    token = request.path_params["token"]
    session = _sessions.get(token)
    if not session:
        return JSONResponse({"status": "expired"})

    if time.time() - session["created_at"] > SESSION_TTL:
        del _sessions[token]
        return JSONResponse({"status": "expired"})

    if session["command"]:
        cmd = session["command"]
        session["command"] = None  # consumed
        return JSONResponse({"status": "command", **cmd})

    return JSONResponse({"status": session["status"]})


async def api_push_result(request: Request) -> JSONResponse:
    """MCP local pushes command execution result."""
    token = request.path_params["token"]
    session = _sessions.get(token)
    if not session:
        return JSONResponse({"error": "expired"}, status_code=404)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid"}, status_code=400)

    action = body.get("action")
    if action == "send_code":
        if body.get("ok"):
            session["status"] = "send_code_done"
        else:
            session["status"] = "error"
            session["result"] = {"error": body.get("error", "Failed to send code")}
    elif action == "verify":
        if body.get("ok"):
            session["status"] = "completed"
            session["result"] = {"name": body.get("name", "User")}
        else:
            session["status"] = "error"
            session["result"] = {"error": body.get("error", "Verification failed")}

    return JSONResponse({"ok": True})


# ============================================================
# Browser endpoints (called by user)
# ============================================================


async def auth_page(request: Request) -> HTMLResponse:
    """Serve auth HTML page."""
    token = request.path_params["token"]
    session = _sessions.get(token)
    if not session:
        return HTMLResponse("<h1>Session expired</h1>", status_code=404)

    # 🛡️ Sentinel: Prevent XSS by escaping dynamic data before insertion
    # Use json.dumps for TOKEN_PLACEHOLDER to safely inject into JavaScript context
    page_html = _PAGE.replace("TOKEN_PLACEHOLDER", json.dumps(token))
    page_html = page_html.replace(
        "PHONE_PLACEHOLDER", html.escape(session["phone_masked"])
    )
    return HTMLResponse(page_html)


async def auth_send_code(request: Request) -> JSONResponse:
    """User requests OTP send."""
    ip = _get_client_ip(request)
    if not _check_rate_limit(ip):
        return JSONResponse({"ok": False, "error": "Rate limited. Try again later."})
    token = request.path_params["token"]
    session = _sessions.get(token)
    if not session:
        return JSONResponse({"ok": False, "error": "Session expired"})

    session["command"] = {"action": "send_code"}
    session["status"] = "send_code_requested"
    return JSONResponse({"ok": True})


async def auth_verify(request: Request) -> JSONResponse:
    """User submits OTP code."""
    ip = _get_client_ip(request)
    if not _check_rate_limit(ip):
        return JSONResponse({"ok": False, "error": "Rate limited. Try again later."})
    token = request.path_params["token"]
    session = _sessions.get(token)
    if not session:
        return JSONResponse({"ok": False, "error": "Session expired"})

    # OTP attempt limit
    attempts = session.get("verify_attempts", 0)
    if attempts >= OTP_ATTEMPT_LIMIT:
        return JSONResponse(
            {"ok": False, "error": "Too many attempts. Request a new session."}
        )
    session["verify_attempts"] = attempts + 1

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "Invalid request"})

    code = body.get("code", "").strip()
    if not code:
        return JSONResponse({"ok": False, "error": "Code required"})

    session["command"] = {
        "action": "verify",
        "code": code,
        "password": body.get("password") or None,
    }
    session["status"] = "verify_requested"
    return JSONResponse({"ok": True})


async def auth_status(request: Request) -> JSONResponse:
    """Browser polls for auth status."""
    token = request.path_params["token"]
    session = _sessions.get(token)
    if not session:
        return JSONResponse({"status": "expired"})

    if time.time() - session["created_at"] > SESSION_TTL:
        del _sessions[token]
        return JSONResponse({"status": "expired"})

    data: dict = {"status": session["status"]}
    if session["status"] == "completed" and session.get("result"):
        data["name"] = session["result"].get("name", "User")
    elif session["status"] == "error" and session.get("result"):
        data["error"] = session["result"].get("error", "Unknown error")
        session["status"] = "idle"  # reset for retry
        session["result"] = None
    return JSONResponse(data)


# ============================================================
# Health check
# ============================================================


async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "sessions": len(_sessions)})


# ============================================================
# App
# ============================================================

app = Starlette(
    routes=[
        # API (MCP local)
        Route("/api/sessions", api_create_session, methods=["POST"]),
        Route("/api/sessions/{token}", api_poll_session),
        Route("/api/sessions/{token}/result", api_push_result, methods=["POST"]),
        # Browser (user)
        Route("/auth/{token}", auth_page),
        Route("/auth/{token}/send-code", auth_send_code, methods=["POST"]),
        Route("/auth/{token}/verify", auth_verify, methods=["POST"]),
        Route("/auth/{token}/status", auth_status),
        # Health
        Route("/health", health),
    ],
    # No CORS middleware — browser requests are same-origin only
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)  # noqa: S104
