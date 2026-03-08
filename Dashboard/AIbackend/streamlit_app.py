import json, re, time, random, string
import requests
import streamlit as st

# ── CONFIG ────────────────────────────────────────────────────────────────────
API_BASE    = "http://localhost:8000"
CHAT_BASE   = f"{API_BASE}/chat"
AUTH_BASE   = "http://localhost:3000"
MAX_THREADS = 10
THEME       = "light"   # change to "dark" for dark mode
DARK        = THEME == "dark"

st.set_page_config(
    page_title="Multi Utility Chatbot", page_icon="🤖",
    layout="wide", initial_sidebar_state="collapsed",
)

# ── THEME TOKENS ──────────────────────────────────────────────────────────────
if DARK:
    PAGE_BG = "linear-gradient(135deg,#0f172a 0%,#111827 60%,#1e1b4b 100%)"
    SB_BG = "rgba(15,23,42,.97)"; SB_BDR = "#1e293b"; HDR_BG = "rgba(15,23,42,.7)"
    IN_BG = "#1e293b"; IN_BDR = "#334155"
    BOT_BG = "#1e293b"; BOT_COLOR = "#e2e8f0"
    USR_BG = "linear-gradient(135deg,#1d4ed8,#1e40af)"
    TP = "#f1f5f9"; TS = "#94a3b8"; TM = "#64748b"
    T_HOVER = "#1e293b"
    T_ACT_BG = "linear-gradient(135deg,rgba(37,99,235,.25),rgba(109,40,217,.25))"
    T_ACT_BDR = "#3b82f6"; T_ACT_C = "#ffffff"
    Y_BG = "rgba(113,63,18,.25)"; Y_BDR = "#92400e"
    BL_BG = "rgba(30,58,138,.25)"; BL_BDR = "#1e40af"
    THINK_BG = "#1e293b"; SCR = "#334155"; BADGE_BG = "#334155"; TOG_BG = "#1e293b"
    LINK_C = "#60a5fa"; EXP_HEAD = "#1e293b"; AUTH_CARD_BG = "#1e293b"
else:
    PAGE_BG = "linear-gradient(135deg,#f8fafc 0%,#eff6ff 50%,#f8fafc 100%)"
    SB_BG = "rgba(255,255,255,.97)"; SB_BDR = "#e2e8f0"; HDR_BG = "rgba(255,255,255,.7)"
    IN_BG = "#ffffff"; IN_BDR = "#e2e8f0"
    BOT_BG = "#ffffff"; BOT_COLOR = "#0f172a"
    USR_BG = "linear-gradient(135deg,#3b82f6,#2563eb)"
    TP = "#0f172a"; TS = "#64748b"; TM = "#94a3b8"
    T_HOVER = "#f1f5f9"
    T_ACT_BG = "linear-gradient(135deg,rgba(59,130,246,.12),rgba(37,99,235,.12))"
    T_ACT_BDR = "#93c5fd"; T_ACT_C = "#1d4ed8"
    Y_BG = "#fefce8"; Y_BDR = "#fde68a"
    BL_BG = "#eff6ff"; BL_BDR = "#bfdbfe"
    THINK_BG = "#ffffff"; SCR = "#cbd5e1"; BADGE_BG = "#f1f5f9"; TOG_BG = "#f1f5f9"
    LINK_C = "#2563eb"; EXP_HEAD = "#f8fafc"; AUTH_CARD_BG = "#ffffff"

PRIMARY = "linear-gradient(135deg,#3b82f6,#6366f1)"

# ── GLOBAL CSS ────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
html,body{{margin:0!important;padding:0!important;overflow:hidden!important;height:100%!important;width:100%!important;}}
#root,.stApp{{margin:0!important;padding:0!important;background:transparent!important;}}
header[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stDecoration"],
[data-testid="stStatusWidget"],footer,[data-testid="stBottom"],
[data-testid="stSidebar"],[data-testid="collapsedControl"]{{display:none!important;height:0!important;width:0!important;}}
[data-testid="stAppViewContainer"]{{padding:0!important;margin:0!important;background:{PAGE_BG}!important;min-height:100vh!important;}}
section[data-testid="stMain"]{{padding:0!important;margin:0!important;width:100vw!important;background:transparent!important;}}
.main .block-container,
[data-testid="stAppViewContainer"]>.main>.block-container,
section[data-testid="stMain"]>.block-container{{
  padding:0!important;margin:0!important;max-width:100vw!important;width:100vw!important;
}}
[data-testid="stMarkdownContainer"]{{margin:0!important;padding:0!important;line-height:inherit!important;}}
[data-testid="stHorizontalBlock"]{{gap:0!important;align-items:stretch!important;}}
[data-testid="column"]{{padding:0!important;}}

/* sidebar */
.sb-wrap{{background:{SB_BG};border-right:1px solid {SB_BDR};min-height:100vh;padding:16px 12px;backdrop-filter:blur(20px);}}
.sb-logo{{width:44px;height:44px;border-radius:12px;background:{PRIMARY};display:flex;align-items:center;justify-content:center;font-size:20px;box-shadow:0 4px 14px rgba(99,102,241,.4);}}
.sb-label{{display:flex;align-items:center;justify-content:space-between;padding:8px 2px 6px;font-size:11px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;color:{TM};}}
.sb-badge{{font-size:11px;padding:2px 8px;border-radius:20px;background:{BADGE_BG};color:{TS};}}

/* topbar */
.topbar{{border-bottom:1px solid {SB_BDR};padding:13px 18px;display:flex;align-items:center;gap:12px;background:{HDR_BG};backdrop-filter:blur(16px);margin-bottom:0;}}
.topbar-ic{{width:36px;height:36px;border-radius:10px;background:{'linear-gradient(135deg,rgba(99,102,241,.2),rgba(236,72,153,.2))' if DARK else 'linear-gradient(135deg,#ede9fe,#fce7f3)'};display:flex;align-items:center;justify-content:center;font-size:18px;}}
.topbar-ttl{{font-size:18px;font-weight:700;color:{TP};font-family:'Segoe UI',system-ui,sans-serif;}}

/* messages */
.cb-msgs{{overflow-y:auto;padding:18px 18px 8px;height:calc(100vh - 146px);background:transparent;}}
.cb-msgs-inner{{max-width:760px;margin:0 auto;display:flex;flex-direction:column;gap:14px;}}
.cb-empty{{display:flex;flex-direction:column;align-items:center;justify-content:center;padding:80px 0;text-align:center;}}
.cb-empty-ic{{width:80px;height:80px;border-radius:20px;background:{'linear-gradient(135deg,rgba(99,102,241,.2),rgba(139,92,246,.2))' if DARK else 'linear-gradient(135deg,#dbeafe,#ede9fe)'};display:flex;align-items:center;justify-content:center;font-size:36px;margin-bottom:14px;}}
.cb-empty h3{{font-size:22px;font-weight:700;margin:0 0 6px;color:{TP};font-family:'Segoe UI',system-ui,sans-serif;}}
.cb-empty p{{font-size:13px;color:{TS};margin:0;}}

/* bubbles */
.cb-row{{display:flex;gap:10px;align-items:flex-end;}}
.cb-row.user{{flex-direction:row-reverse;}}
.cb-av{{width:32px;height:32px;border-radius:10px;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:15px;}}
.cb-av.bot{{background:{PRIMARY};}}
.cb-av.user{{background:linear-gradient(135deg,#10b981,#0d9488);}}
.cb-bub{{max-width:620px;border-radius:18px;padding:11px 17px;font-size:13px;line-height:1.7;white-space:pre-wrap;word-break:break-word;font-family:'Segoe UI',system-ui,sans-serif;}}
.cb-bub.bot{{background:{BOT_BG};color:{BOT_COLOR};border-bottom-left-radius:4px;box-shadow:0 2px 10px rgba(0,0,0,.07);}}
.cb-bub.user{{background:{USR_BG};color:#fff;border-bottom-right-radius:4px;}}
.cb-bub a{{color:{LINK_C};text-decoration:underline;}}

/* thinking */
.cb-think{{display:flex;gap:10px;align-items:center;padding:2px 0 6px;}}
.cb-tbub{{background:{THINK_BG};border-radius:18px;border-bottom-left-radius:4px;padding:11px 17px;display:flex;align-items:center;gap:10px;font-size:13px;color:{TS};box-shadow:0 2px 10px rgba(0,0,0,.07);}}
.cb-dots{{display:flex;gap:4px;}}
.cb-dot{{width:7px;height:7px;border-radius:50%;background:#6366f1;animation:cbB 1.2s ease-in-out infinite;}}
.cb-dot:nth-child(2){{animation-delay:.2s;}} .cb-dot:nth-child(3){{animation-delay:.4s;}}
@keyframes cbB{{0%,80%,100%{{transform:translateY(0);opacity:.35;}}40%{{transform:translateY(-6px);opacity:1;}}}}

/* interrupts */
.cb-int{{border-radius:14px;padding:15px 17px;max-width:660px;margin:0 0 6px 42px;}}
.cb-int.yellow{{background:{Y_BG};border:1px solid {Y_BDR};}}
.cb-int.blue{{background:{BL_BG};border:1px solid {BL_BDR};}}
.cb-int-ttl{{font-weight:700;font-size:14px;margin-bottom:7px;color:{TP};font-family:'Segoe UI',system-ui,sans-serif;}}
.cb-int-body{{font-size:13px;color:{TS};margin:0 0 10px;line-height:1.6;}}
.cb-int-pre{{background:{IN_BG};border:1px solid {IN_BDR};border-radius:10px;padding:11px;font-size:12px;line-height:1.7;white-space:pre-wrap;word-break:break-word;margin:0 0 10px;color:{TP};}}
.cb-auth-link{{display:inline-block;padding:9px 18px;border-radius:10px;background:#2563eb;color:#fff;text-decoration:none;font-size:13px;font-weight:700;}}

/* st widget overrides */
[data-testid="stTextInput"]>div>div>input{{
  background:{IN_BG}!important;color:{TP}!important;
  border:2px solid {IN_BDR}!important;border-radius:14px!important;
  padding:12px 17px!important;font-size:14px!important;
  font-family:'Segoe UI',system-ui,sans-serif!important;
}}
[data-testid="stTextInput"]>div>div>input:focus{{border-color:#6366f1!important;box-shadow:none!important;}}
[data-testid="stTextInput"] label{{display:none!important;}}
[data-testid="stTextInput"]>div{{margin:0!important;padding:0!important;}}
button[kind="primary"],button[data-testid="baseButton-primary"]{{
  background:{PRIMARY}!important;border:none!important;border-radius:12px!important;
  font-weight:700!important;color:#fff!important;box-shadow:0 4px 12px rgba(99,102,241,.35)!important;
}}
button[kind="secondary"],button[data-testid="baseButton-secondary"]{{
  border-radius:11px!important;font-weight:600!important;
  background:{TOG_BG}!important;border:1px solid {IN_BDR}!important;color:{TP}!important;
}}
button[kind="secondary"]:hover{{background:{T_HOVER}!important;}}
[data-testid="stTextArea"] textarea{{
  background:{IN_BG}!important;color:{TP}!important;
  border:1px solid {IN_BDR}!important;border-radius:12px!important;font-size:13px!important;
}}
[data-testid="stExpander"]{{border:1px solid {IN_BDR}!important;border-radius:12px!important;background:{IN_BG}!important;}}
.cb-msgs::-webkit-scrollbar{{width:4px;}}
.cb-msgs::-webkit-scrollbar-thumb{{background:{SCR};border-radius:4px;}}
.cb-center{{display:flex;align-items:center;justify-content:center;height:100vh;background:{PAGE_BG};}}
.cb-auth-card{{background:{AUTH_CARD_BG};border-radius:24px;padding:48px;text-align:center;max-width:400px;width:90%;box-shadow:0 20px 60px rgba(0,0,0,.18);}}
.cb-auth-ic{{width:64px;height:64px;border-radius:50%;background:#dc2626;display:flex;align-items:center;justify-content:center;font-size:28px;margin:0 auto 16px;}}
.cb-auth-card h2{{font-size:22px;font-weight:700;margin:0 0 8px;color:{TP};font-family:'Segoe UI',system-ui,sans-serif;}}
.cb-auth-card p{{font-size:14px;color:{TS};margin:0 0 28px;}}
.cb-goto-login{{display:inline-block;padding:12px 28px;border-radius:12px;background:#2563eb;color:#fff;text-decoration:none;font-weight:700;font-size:14px;}}
</style>
""", unsafe_allow_html=True)

# ── SESSION STATE ─────────────────────────────────────────────────────────────
def _init():
    defs = dict(
        threads=[], current_thread=None, messages={}, thread_names={},
        sidebar_open=True, interrupt_data=None, interrupt_type=None,
        is_processing=False, user_email=None, user_org=None,
        auth_checked=False, pending_resume=None,
    )
    for k, v in defs.items():
        if k not in st.session_state:
            st.session_state[k] = v
_init()
ss = st.session_state

# ── HELPERS ───────────────────────────────────────────────────────────────────
def gen_id():
    s = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"thread-{int(time.time()*1000)}-{s}"

def make_name(msg):
    if not msg: return "New Conversation"
    w = " ".join(msg.split()[:5])
    return (w[:40] + "...") if len(w) > 40 else w

def cur_msgs():
    return ss.messages.get(ss.current_thread, [])

def add_msg(role, content, tid=None):
    t = tid or ss.current_thread
    ss.messages.setdefault(t, []).append({"role": role, "content": content})

def linkify(text):
    return re.sub(
        r'(https?://\S+)',
        r'<a href="\1" target="_blank" rel="noopener noreferrer">\1</a>',
        text or ""
    )

def create_thread():
    if len(ss.threads) >= MAX_THREADS:
        ss.threads.pop()
    tid = gen_id()
    ss.threads.insert(0, tid)
    ss.current_thread = tid
    ss.messages[tid] = []
    ss.thread_names[tid] = "New Conversation"
    ss.interrupt_data = None
    ss.interrupt_type = None
    ss.is_processing = False

def load_thread(tid):
    ss.current_thread = tid
    ss.interrupt_data = None
    ss.interrupt_type = None
    ss.is_processing = False
    try:
        r = requests.get(f"{CHAT_BASE}/threads/{tid}", timeout=8)
        msgs = r.json().get("messages", [])
        ss.messages[tid] = msgs
        if not ss.thread_names.get(tid) or ss.thread_names[tid] == "New Conversation":
            first = next((m["content"] for m in msgs if m["role"] == "user"), "")
            if first:
                ss.thread_names[tid] = make_name(first)
    except Exception:
        ss.messages[tid] = []

# ── AUTH ──────────────────────────────────────────────────────────────────────
def fetch_user():
    if ss.auth_checked: return
    ss.auth_checked = True
    params = st.query_params
    if "email" in params and "org" in params:
        ss.user_email = params["email"]
        ss.user_org = params["org"]
        return
    try:
        r = requests.get(f"{AUTH_BASE}/whoAmI", timeout=5)
        if r.ok:
            d = r.json()
            ss.user_email = d.get("email")
            ss.user_org = d.get("org")
    except Exception:
        pass

def handle_oauth():
    p = st.query_params
    code = p.get("code")
    state = p.get("state")
    if not code or not state: return
    try:
        r = requests.get(f"{CHAT_BASE}/gmail/auth/callback",
                         params={"code": code, "state": state}, timeout=15)
        d = r.json()
        if d.get("gmail_access_token"):
            if state not in ss.threads:
                ss.threads.insert(0, state)
                ss.messages[state] = []
                ss.thread_names[state] = "Gmail Auth"
            ss.current_thread = state
            ss.interrupt_data = None
            ss.interrupt_type = None
            ss.is_processing = True
            ss.pending_resume = {"state_update": {
                "gmail_access_token": d["gmail_access_token"],
                "gmail_token_expiry": d.get("gmail_token_expiry"),
            }}
            # Preserve email/org params, only remove OAuth code/state
            existing = dict(st.query_params)
            existing.pop("code", None)
            existing.pop("state", None)
            st.query_params.update(existing)
            st.rerun()
    except Exception as e:
        st.error(f"OAuth error: {e}")

# ── BACKEND ───────────────────────────────────────────────────────────────────
def api_send(text):
    try:
        r = requests.post(f"{CHAT_BASE}/message", json={
            "thread_id": ss.current_thread, "message": text,
            "user_email": ss.user_email, "org": ss.user_org,
        }, timeout=15)
        r.raise_for_status()
        return True
    except Exception as e:
        add_msg("assistant", f"Send error: {e}")
        return False

def api_resume(payload):
    body = {"thread_id": ss.current_thread}
    if "state_update" in payload:
        body["state_update"] = payload["state_update"]
    else:
        body["user_input"] = payload.get("user_input", "")
    try:
        requests.post(f"{CHAT_BASE}/resume", json=body, timeout=15)
        return True
    except Exception as e:
        add_msg("assistant", f"Resume error: {e}")
        return False

# ── STREAMING ─────────────────────────────────────────────────────────────────
def stream_chat(msg_ph, status_ph):
    """
    Consume SSE from /chat/stream, render each message chunk live.
    Handles 'message', 'interrupt', and 'end' SSE events.
    Resumes the LangGraph from where it left off if interrupted.
    """
    tid = ss.current_thread
    url = f"{CHAT_BASE}/stream?thread_id={tid}"
    seen = set()
    try:
        with requests.get(url, stream=True, timeout=180) as resp:
            resp.raise_for_status()
            ev = "message"
            dl = []
            for raw in resp.iter_lines(decode_unicode=True):
                if raw.startswith("event:"):
                    ev = raw[6:].strip()
                    dl = []
                elif raw.startswith("data:"):
                    dl.append(raw[5:].strip())
                elif raw == "":
                    ps = "\n".join(dl)
                    dl = []
                    if not ps:
                        ev = "message"
                        continue
                    try:
                        payload = json.loads(ps)
                    except Exception:
                        ev = "message"
                        continue

                    if ev == "message":
                        role = payload.get("role", "assistant")
                        chunk = payload.get("content", "")
                        if role and chunk:
                            msgs = ss.messages.get(tid, [])
                            if msgs and msgs[-1]["role"] == "assistant" and role == "assistant":
                                # Append token to existing assistant bubble (streaming)
                                ss.messages[tid][-1]["content"] += chunk
                            else:
                                # First chunk — create new assistant bubble
                                add_msg(role, chunk, tid)
                            status_ph.empty()
                            msg_ph.markdown(build_msgs(), unsafe_allow_html=True)

                    elif ev == "interrupt":
                        ss.interrupt_data = payload
                        ss.interrupt_type = payload.get("type")
                        ss.is_processing = False
                        status_ph.empty()
                        return

                    elif ev == "end":
                        ss.is_processing = False
                        status_ph.empty()
                        return

                    ev = "message"

    except Exception as e:
        add_msg("assistant", f"Stream error: {e}", tid)
        ss.is_processing = False
        status_ph.empty()

# ── HTML BUILDERS ─────────────────────────────────────────────────────────────
def build_msgs():
    msgs = cur_msgs()
    inner = ""
    if not msgs:
        inner = (
            '<div class="cb-empty">'
            '<div class="cb-empty-ic">&#10024;</div>'
            '<h3>Start a conversation</h3>'
            '<p>Search &middot; Email &middot; Calendar &middot; Documents</p>'
            '</div>'
        )
    else:
        for m in msgs:
            role = m.get("role", "assistant")
            content = linkify(m.get("content", ""))
            av = "&#129302;" if role == "assistant" else "&#128100;"
            avc = "bot" if role == "assistant" else "user"
            rc = "user" if role == "user" else ""
            inner += (
                f'<div class="cb-row {rc}">'
                f'<div class="cb-av {avc}">{av}</div>'
                f'<div class="cb-bub {avc}">{content}</div>'
                f'</div>'
            )
        if ss.is_processing and not ss.interrupt_type:
            inner += (
                '<div class="cb-think">'
                '<div class="cb-av bot">&#129302;</div>'
                '<div class="cb-tbub">'
                '<div class="cb-dots">'
                '<div class="cb-dot"></div>'
                '<div class="cb-dot"></div>'
                '<div class="cb-dot"></div>'
                '</div>'
                '<span>Thinking&hellip;</span>'
                '</div></div>'
            )
    scroll_js = (
        '<script>'
        '(function(){var e=document.getElementById("cbS");'
        'if(e)e.scrollTop=e.scrollHeight;})();'
        '</script>'
    )
    return (
        f'<div class="cb-msgs" id="cbS">'
        f'<div class="cb-msgs-inner">{inner}</div>'
        f'</div>'
        f'{scroll_js}'
    )

# ── MAIN ──────────────────────────────────────────────────────────────────────
fetch_user()
handle_oauth()

if not ss.threads:
    create_thread()
if not ss.current_thread:
    ss.current_thread = ss.threads[0]

# Not-authenticated gate
if not ss.user_email or not ss.user_org:
    st.markdown(
        '<div class="cb-center">'
        '<div class="cb-auth-card">'
        '<div class="cb-auth-ic">&#128274;</div>'
        '<h2>Not Authenticated</h2>'
        '<p>Please log in to access the chatbot</p>'
        '<a href="/login" class="cb-goto-login">Go to Login</a>'
        '</div></div>',
        unsafe_allow_html=True
    )
    st.stop()

# ── LAYOUT ────────────────────────────────────────────────────────────────────
if ss.sidebar_open:
    sb_col, main_col = st.columns([1, 3.6])
else:
    sb_col, main_col = st.columns([0.001, 1])

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with sb_col:
    if ss.sidebar_open:
        st.markdown('<div class="sb-wrap">', unsafe_allow_html=True)

        h1, h2 = st.columns([1, 1])
        with h1:
            st.markdown('<div class="sb-logo">&#10024;</div>', unsafe_allow_html=True)
        with h2:
            if st.button("‹", key="sb_close", help="Close sidebar"):
                ss.sidebar_open = False
                st.rerun()

        if st.button("＋  New Chat", key="new_chat", use_container_width=True, type="primary"):
            create_thread()
            st.rerun()

        st.markdown(
            f'<div class="sb-label">'
            f'<span>Recent Chats</span>'
            f'<span class="sb-badge">{len(ss.threads)}/{MAX_THREADS}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

        for tid in ss.threads:
            name = ss.thread_names.get(tid, "New Conversation")
            active = tid == ss.current_thread
            icon = "▶ " if active else ""
            if st.button(
                f"{icon}💬  {name}", key=f"t_{tid}",
                use_container_width=True,
                type="primary" if active else "secondary"
            ):
                load_thread(tid)
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

# ── MAIN AREA ─────────────────────────────────────────────────────────────────
with main_col:

    # Top bar
    top1, top2 = st.columns([0.07, 1])
    with top1:
        if not ss.sidebar_open:
            if st.button("›", key="sb_open", help="Open sidebar"):
                ss.sidebar_open = True
                st.rerun()
    with top2:
        st.markdown(
            '<div class="topbar">'
            '<div class="topbar-ic">&#129302;</div>'
            '<span class="topbar-ttl">Multi Utility Chatbot</span>'
            '</div>',
            unsafe_allow_html=True
        )

    # Messages area
    msg_ph = st.empty()
    msg_ph.markdown(build_msgs(), unsafe_allow_html=True)

    # ── Interrupt UI ──────────────────────────────────────────────────────────
    if ss.interrupt_data:
        itype = ss.interrupt_type
        idata = ss.interrupt_data
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

        if itype == "GMAIL_AUTH_REQUIRED":
            ep = idata.get("auth_start_endpoint", "")
            auth_url = f"{API_BASE}{ep}?thread_id={ss.current_thread}"
            msg = idata.get("message", "Click below to authorize Gmail access.")
            st.markdown(
                f'<div class="cb-int yellow">'
                f'<div class="cb-int-ttl">&#9888;&#65039; Gmail Authorization Required</div>'
                f'<p class="cb-int-body">{msg}</p>'
                f'<a href="{auth_url}" target="_blank" class="cb-auth-link">&#128272; Authorize Gmail</a>'
                f'</div>',
                unsafe_allow_html=True
            )
            with st.expander("Already authorized? Paste token here"):
                tok = st.text_input("Access token", key="g_tok")
                exp = st.text_input("Expiry (ISO format)", key="g_exp")
                if st.button("Submit token", key="g_sub"):
                    ss.interrupt_data = None
                    ss.interrupt_type = None
                    ss.is_processing = True
                    ss.pending_resume = {"state_update": {
                        "gmail_access_token": tok,
                        "gmail_token_expiry": exp,
                    }}
                    st.rerun()

        elif itype == "USER_CHOICE":
            msg = idata.get("message", "Select a recipient:")
            st.markdown(
                f'<div class="cb-int blue">'
                f'<div class="cb-int-ttl">&#128101; {msg}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
            for opt in idata.get("options", []):
                lbl = f"**{opt.get('username', '')}**"
                if opt.get("name"):
                    lbl += f"  ·  _{opt['name']}_"
                key = f"ch_{opt.get('index', opt.get('username', ''))}"
                if st.button(lbl, key=key):
                    val = opt.get("username", str(opt.get("index", "")))
                    add_msg("user", f"Selected: {opt.get('username', '')}")
                    ss.interrupt_data = None
                    ss.interrupt_type = None
                    ss.is_processing = True
                    ss.pending_resume = {"user_input": val}
                    st.rerun()

        elif itype in ("EMAIL_BODY_CONFIRM", "EMAIL_BODY_EDIT"):
            eb = idata.get("email_body", "")
            st.markdown(
                f'<div class="cb-int blue">'
                f'<div class="cb-int-ttl">&#128231; Email Preview</div>'
                f'<pre class="cb-int-pre">{eb}</pre>'
                f'</div>',
                unsafe_allow_html=True
            )
            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button("Send Email", key="esend", type="primary"):
                    add_msg("user", "Confirmed: send email")
                    ss.interrupt_data = None
                    ss.interrupt_type = None
                    ss.is_processing = True
                    ss.pending_resume = {"user_input": "yes"}
                    st.rerun()
            with c2:
                edit_clicked = st.button("Edit", key="eedit")

            if edit_clicked or itype == "EMAIL_BODY_EDIT":
                new_body = st.text_area(
                    "Edit email body or describe changes:",
                    value=eb, height=160, key="ebody_edit"
                )
                if st.button("Apply & Continue", key="eapply"):
                    add_msg("user", "[Edited email body]")
                    ss.interrupt_data = None
                    ss.interrupt_type = None
                    ss.is_processing = True
                    ss.pending_resume = {"user_input": new_body}
                    st.rerun()

        elif itype == "MANUAL_EMAIL_INPUT":
            msg = idata.get("message", "Enter recipient email address:")
            st.markdown(
                f'<div class="cb-int yellow">'
                f'<div class="cb-int-ttl">&#128236; {msg}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
            manual = st.text_input("Email address", key="manual_email")
            if st.button("Continue", key="msub") and (manual or "").strip():
                add_msg("user", manual.strip())
                ss.interrupt_data = None
                ss.interrupt_type = None
                ss.is_processing = True
                ss.pending_resume = {"user_input": manual.strip()}
                st.rerun()

        else:
            # Generic fallback — user types response in input bar
            msg = idata.get("message", "Please respond below:")
            st.markdown(
                f'<div class="cb-int blue">'
                f'<div class="cb-int-ttl">&#128172; {msg}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

    # ── Thinking indicator ────────────────────────────────────────────────────
    status_ph = st.empty()
    if ss.is_processing and not ss.interrupt_type:
        status_ph.markdown(
            '<div class="cb-think">'
            '<div class="cb-av bot">&#129302;</div>'
            '<div class="cb-tbub">'
            '<div class="cb-dots">'
            '<div class="cb-dot"></div>'
            '<div class="cb-dot"></div>'
            '<div class="cb-dot"></div>'
            '</div>'
            '<span>Thinking&hellip;</span>'
            '</div></div>',
            unsafe_allow_html=True
        )

    # ── Execute pending resume (fires after interrupt response reruns) ─────────
    if ss.pending_resume and not ss.interrupt_type:
        payload = ss.pending_resume
        ss.pending_resume = None
        ok = api_resume(payload)
        if ok:
            stream_chat(msg_ph, status_ph)
        msg_ph.markdown(build_msgs(), unsafe_allow_html=True)
        st.rerun()

    # ── Input bar ─────────────────────────────────────────────────────────────
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    ph_text = "Type your response..." if ss.interrupt_type else "Type your message..."

    in_col, send_col = st.columns([7, 1])
    with in_col:
        user_input = st.text_input(
            "msg", label_visibility="collapsed",
            placeholder=ph_text, key="chat_input",
            disabled=ss.is_processing,
        )
    with send_col:
        send_hit = st.button(
            "Send ➤", key="send_btn",
            disabled=ss.is_processing or not (user_input or "").strip(),
            use_container_width=True, type="primary",
        )

    # ── Handle send ───────────────────────────────────────────────────────────
    if send_hit and (user_input or "").strip():
        text = user_input.strip()

        if ss.interrupt_type:
            # Any text-based interrupt — route through resume
            add_msg("user", text)
            ss.interrupt_data = None
            ss.interrupt_type = None
            ss.is_processing = True
            ss.pending_resume = {"user_input": text}
            st.rerun()
        else:
            # Normal message send → POST /chat/message → stream
            add_msg("user", text)
            if len(cur_msgs()) == 1:
                ss.thread_names[ss.current_thread] = make_name(text)
            ss.is_processing = True
            msg_ph.markdown(build_msgs(), unsafe_allow_html=True)

            if api_send(text):
                stream_chat(msg_ph, status_ph)

            msg_ph.markdown(build_msgs(), unsafe_allow_html=True)
            st.rerun()