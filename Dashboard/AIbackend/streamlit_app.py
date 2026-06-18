import json, re, time, random, string, os
import requests
import streamlit as st

API_BASE    = os.getenv("API_BASE",  "http://localhost:8000")
AUTH_BASE   = os.getenv("AUTH_BASE", "http://localhost:3000")
CHAT_BASE   = f"{API_BASE}/chat"
MAX_THREADS = 10

st.set_page_config(
    page_title="CogniSync AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

_DEFAULTS = dict(
    threads=[], current_thread=None, messages={}, thread_names={},
    interrupt_data=None, interrupt_type=None, is_processing=False,
    user_email=None, user_org=None, auth_checked=False, threads_loaded=False,
    edit_box_open=False, edit_body_text="", sidebar_open=True,
)
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

ss = st.session_state


_qp = st.query_params
_theme = _qp.get("theme", "dark")
IS_DARK = (_theme != "light")

if IS_DARK:
    PAGE_BG = "#080d18"; SB_BG  = "#0e1e45"; SB_BDR = "#2a4080"
    HDR_BG  = "#0d1424"; IN_BG  = "#111c33"; IN_BDR = "#1e3058"
    BOT_BG  = "#111c33"; BOT_COL= "#e2eaf8"; USR_BG = "#1a4fd6"
    TP      = "#e8edf8"; TS     = "#8896b0"; TM     = "#4a5a78"
    BTN_BG  = "#111c33"; BTN_HV = "#1a2a4a"; BTN_ACT= "#1a4fd6"
    BADGE_BG= "#1a2540"; SCR    = "#1e3058"
    Y_BG    = "#1f1500"; Y_BDR  = "#5c3000"
    BL_BG   = "#060d22"; BL_BDR = "#0d2255"
    ACCENT  = "#3b82f6"; ACCENT2= "#6366f1"
else:
    PAGE_BG = "#f8fafc"; SB_BG  = "#f0f4ff"; SB_BDR = "#c7d7f8"
    HDR_BG  = "#ffffff"; IN_BG  = "#f1f5fb"; IN_BDR = "#c7d7f8"
    BOT_BG  = "#f0f4ff"; BOT_COL= "#1e293b"; USR_BG = "#2563eb"
    TP      = "#1e293b"; TS     = "#64748b"; TM     = "#94a3b8"
    BTN_BG  = "#e8edf8"; BTN_HV = "#dbeafe"; BTN_ACT= "#2563eb"
    BADGE_BG= "#e0e7ff"; SCR    = "#cbd5e1"
    Y_BG    = "#fefce8"; Y_BDR  = "#fde68a"
    BL_BG   = "#eff6ff"; BL_BDR = "#bfdbfe"
    ACCENT  = "#2563eb"; ACCENT2= "#4f46e5"


st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
html,body,[data-testid="stAppViewContainer"],[data-testid="stMain"],
section[data-testid="stMain"],section[data-testid="stMain"]>.block-container,
div[data-testid="stMainBlockContainer"]{{
  background:{PAGE_BG}!important;padding:0!important;margin:0!important;
  max-width:100vw!important;width:100vw!important;
  height:100vh!important;overflow:hidden!important;
  font-family:'Inter',sans-serif!important;}}
header,footer,[data-testid="stHeader"],[data-testid="stToolbar"],
[data-testid="stDecoration"],[data-testid="stStatusWidget"],
[data-testid="stBottom"],[data-testid="stSidebar"],
[data-testid="collapsedControl"]{{display:none!important;}}
[data-testid="stVerticalBlock"]{{gap:0!important;padding:0!important;}}
[data-testid="stMarkdownContainer"]{{margin:0!important;padding:0!important;}}
/* Column row */
[data-testid="stHorizontalBlock"]{{
  gap:0!important;display:flex!important;align-items:stretch!important;
  height:100vh!important;overflow:hidden!important;}}
/* Each column */
[data-testid="column"]{{
  display:flex!important;flex-direction:column!important;
  overflow:hidden!important;height:100vh!important;flex-shrink:0!important;}}
[data-testid="column"]>[data-testid="stVerticalBlock"]{{
  flex:1!important;overflow:hidden!important;
  display:flex!important;flex-direction:column!important;}}
/* Scrollbars */
::-webkit-scrollbar{{width:5px;}}
::-webkit-scrollbar-thumb{{background:{SCR};border-radius:4px;}}
::-webkit-scrollbar-track{{background:transparent;}}
/* st.container(height=X) — the scrollable messages area */
[data-testid="stVerticalBlockBorderWrapper"]{{
  flex:1!important;height:0!important;min-height:80px!important;
  overflow-y:auto!important;border:none!important;
  border-radius:0!important;background:transparent!important;
  box-shadow:none!important;}}
[data-testid="stVerticalBlockBorderWrapper"]>[data-testid="stVerticalBlock"]{{
  padding:14px 18px!important;gap:6px!important;overflow-y:visible!important;}}
/* Buttons */
div.stButton>button{{width:100%;padding:8px 12px;border-radius:10px;border:none;
  background:{BTN_BG};color:{TP};font-family:'Inter',sans-serif;font-size:12px;
  font-weight:600;cursor:pointer;text-align:left;transition:background 0.15s;margin-bottom:2px;}}
div.stButton>button:hover{{background:{BTN_HV};border:none;}}
div.stButton>button:focus{{outline:none;box-shadow:none;border:none;}}
div[data-testid="stButton"].new-chat-btn>button{{
  background:linear-gradient(135deg,{ACCENT},{ACCENT2});color:#fff;font-weight:700;
  font-size:13px;text-align:center;padding:10px;border-radius:12px;margin-bottom:10px;}}
div.active-thread>button{{background:{BTN_ACT}!important;color:#fff!important;}}
div.send-btn>button{{background:linear-gradient(135deg,{ACCENT},{ACCENT2})!important;
  color:#fff!important;font-size:14px!important;font-weight:700!important;
  text-align:center!important;padding:10px 20px!important;border-radius:13px!important;width:auto!important;}}
div.action-btn-blue>button{{background:{ACCENT}!important;color:#fff!important;
  font-weight:700!important;text-align:center!important;border-radius:9px!important;
  padding:8px 16px!important;width:auto!important;}}
div.action-btn-neutral>button{{background:{BTN_BG}!important;color:{TP}!important;
  font-weight:700!important;text-align:center!important;border-radius:9px!important;
  padding:8px 16px!important;width:auto!important;}}
div[data-testid="stTextInput"] input{{background:{IN_BG}!important;color:{TP}!important;
  border:2px solid {IN_BDR}!important;border-radius:13px!important;
  font-family:'Inter',sans-serif!important;font-size:14px!important;padding:10px 14px!important;}}
div[data-testid="stTextInput"] input:focus{{border-color:{ACCENT2}!important;
  box-shadow:0 0 0 2px rgba(99,102,241,0.2)!important;}}
div[data-testid="stTextInput"] label{{display:none!important;}}
div[data-testid="stTextInput"]{{margin:0!important;}}
div[data-testid="stTextArea"] textarea{{background:{IN_BG}!important;color:{TP}!important;
  border:1px solid {IN_BDR}!important;border-radius:10px!important;
  font-family:'Inter',sans-serif!important;font-size:12px!important;padding:8px!important;}}
div[data-testid="stTextArea"] label{{display:none!important;}}
/* Chat header */
.chat-header{{
  background:{HDR_BG}!important;padding:10px 18px!important;
  border-bottom:1px solid {SB_BDR}!important;
  display:flex!important;align-items:center!important;gap:10px!important;
  flex-shrink:0!important;}}
/* Toggle ☰ */
.toggle-btn-wrapper>button{{
  background:transparent!important;color:{TP}!important;
  font-size:18px!important;padding:2px 6px!important;
  width:auto!important;margin:0!important;
  border-radius:6px!important;min-width:30px!important;margin-bottom:0!important;}}
.toggle-btn-wrapper>button:hover{{background:{BTN_HV}!important;}}
/* Close ✕ */
.close-sb-btn>button{{
  background:transparent!important;color:{TS}!important;
  font-size:14px!important;padding:2px 6px!important;
  width:auto!important;margin:0!important;border-radius:6px!important;
  min-width:28px!important;margin-bottom:0!important;}}
.close-sb-btn>button:hover{{background:{BTN_HV}!important;color:{TP}!important;}}
/* Input area wrapper — sits below the scrollable container naturally */
.chat-input-bar{{
  flex-shrink:0!important;
  border-top:1px solid {SB_BDR}!important;
  background:{PAGE_BG}!important;
  padding:10px 18px 12px!important;}}
</style>
""", unsafe_allow_html=True)

def gen_id():
    s = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"thread-{int(time.time()*1000)}-{s}"

def make_name(msg):
    if not msg: return "New Conversation"
    w = " ".join(msg.split()[:5])
    return (w[:36] + "…") if len(w) > 36 else w

def cur_msgs():
    return ss.messages.get(ss.current_thread, [])

def add_msg(role, content, tid=None):
    t = tid or ss.current_thread
    ss.messages.setdefault(t, []).append({"role": role, "content": content})

def linkify(text):
    return re.sub(
        r'(https?://\S+)',
        r'<a href="\1" target="_blank" rel="noopener noreferrer" style="color:#7dd3fc;word-break:break-all;">\1</a>',
        text or ""
    )

def esc(s):
    return (str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
                  .replace('"',"&quot;").replace("'","&#39;"))

def create_thread():
    if len(ss.threads) >= MAX_THREADS: ss.threads.pop()
    tid = gen_id()
    ss.threads.insert(0, tid); ss.current_thread = tid
    ss.messages[tid] = []; ss.thread_names[tid] = "New Conversation"
    ss.interrupt_data = None; ss.interrupt_type = None
    ss.is_processing = False; ss.edit_box_open = False

def switch_thread(tid):
    ss.current_thread = tid
    ss.interrupt_data = None; ss.interrupt_type = None
    ss.is_processing = False; ss.edit_box_open = False
    try:
        r = requests.get(f"{CHAT_BASE}/threads/{tid}", timeout=8)
        msgs = r.json().get("messages", [])
        ss.messages[tid] = msgs
        first = next((m["content"] for m in msgs if m["role"] == "user"), "")
        if first: ss.thread_names[tid] = make_name(first)
    except Exception:
        ss.messages.setdefault(tid, [])

def fetch_user():
    if ss.auth_checked: return
    ss.auth_checked = True
    p = st.query_params
    if "email" in p and "org" in p:
        ss.user_email = p["email"]; ss.user_org = p["org"]; return
    try:
        r = requests.get(f"{AUTH_BASE}/whoAmI", timeout=5)
        if r.ok:
            d = r.json(); ss.user_email = d.get("email"); ss.user_org = d.get("org")
    except Exception: pass

def api_send_message(text):
    try:
        r = requests.post(f"{CHAT_BASE}/message", json={
            "thread_id": ss.current_thread, "message": text,
            "user_email": ss.user_email, "org": ss.user_org,
        }, timeout=15)
        r.raise_for_status(); return True
    except Exception as e:
        add_msg("assistant", f"⚠️ Send error: {e}"); return False

def api_resume(payload):
    body = {"thread_id": ss.current_thread}
    if "state_update" in payload: body["state_update"] = payload["state_update"]
    else: body["user_input"] = payload.get("user_input", "")
    try:
        r = requests.post(f"{CHAT_BASE}/resume", json=body, timeout=15)
        r.raise_for_status(); return True
    except Exception as e:
        add_msg("assistant", f"⚠️ Resume error: {e}"); return False

def stream_and_collect():
    tid = ss.current_thread
    assistant_content = ""
    interrupt_payload = None
    try:
        with requests.get(f"{CHAT_BASE}/stream?thread_id={tid}", stream=True, timeout=180) as resp:
            resp.raise_for_status()
            ev, dl = "message", []
            for raw in resp.iter_lines(decode_unicode=True):
                if raw.startswith("event:"): ev = raw[6:].strip(); dl = []
                elif raw.startswith("data:"): dl.append(raw[5:].strip())
                elif raw == "":
                    ps = "\n".join(dl); dl = []
                    if not ps: ev = "message"; continue
                    try: payload = json.loads(ps)
                    except Exception: ev = "message"; continue
                    if ev == "message":
                        chunk = payload.get("content", "")
                        if chunk: assistant_content += chunk
                    elif ev == "interrupt": interrupt_payload = payload; break
                    elif ev == "end": break
                    ev = "message"
    except Exception as e:
        return [{"role": "assistant", "content": f"⚠️ Stream error: {e}"}], None
    new_msgs = []
    if assistant_content: new_msgs.append({"role": "assistant", "content": assistant_content})
    return new_msgs, interrupt_payload

def do_send(text):
    add_msg("user", text)
    if len(cur_msgs()) == 1: ss.thread_names[ss.current_thread] = make_name(text)
    ss.is_processing = True
    if api_send_message(text):
        new_msgs, interrupt_payload = stream_and_collect()
        for m in new_msgs: add_msg(m["role"], m["content"])
        if interrupt_payload:
            ss.interrupt_data = interrupt_payload; ss.interrupt_type = interrupt_payload.get("type")
        else:
            ss.interrupt_data = None; ss.interrupt_type = None
    ss.is_processing = False

def do_resume(payload, user_display_msg=None):
    if user_display_msg: add_msg("user", user_display_msg)
    ss.interrupt_data = None; ss.interrupt_type = None; ss.is_processing = True
    if api_resume(payload):
        new_msgs, interrupt_payload = stream_and_collect()
        for m in new_msgs: add_msg(m["role"], m["content"])
        if interrupt_payload:
            ss.interrupt_data = interrupt_payload; ss.interrupt_type = interrupt_payload.get("type")
        else:
            ss.interrupt_data = None; ss.interrupt_type = None
    ss.is_processing = False

fetch_user()

if not ss.threads_loaded and ss.user_email:
    ss.threads_loaded = True
    try:
        r = requests.get(f"{CHAT_BASE}/threads", timeout=8)
        thread_ids = sorted(r.json().get("threads", []), reverse=True)[:MAX_THREADS]
        for tid in thread_ids:
            try:
                tr   = requests.get(f"{CHAT_BASE}/threads/{tid}", timeout=5)
                msgs = tr.json().get("messages", [])
                ss.messages[tid] = msgs
                first = next((m["content"] for m in msgs if m["role"] == "user"), "")
                ss.thread_names[tid] = make_name(first) if first else "New Conversation"
                ss.threads.append(tid)
            except Exception: pass
    except Exception: pass

if not ss.threads: create_thread()
if not ss.current_thread: ss.current_thread = ss.threads[0]

if not ss.user_email or not ss.user_org:
    st.markdown(f"""
    <div style="min-height:100vh;display:flex;align-items:center;justify-content:center;background:{PAGE_BG};">
      <div style="background:{SB_BG};border:1px solid {SB_BDR};border-radius:20px;padding:48px 40px;
                  text-align:center;max-width:380px;width:90%;box-shadow:0 20px 60px rgba(0,0,0,.5);">
        <div style="font-size:44px;margin-bottom:16px;">🔒</div>
        <h2 style="color:{TP};margin:0 0 8px;font-size:22px;font-weight:700;">Not Authenticated</h2>
        <p style="color:{TS};margin:0 0 28px;font-size:14px;">Please log in to access CogniSync AI</p>
        <a href="/login" style="padding:12px 32px;border-radius:12px;
           background:linear-gradient(135deg,{ACCENT},{ACCENT2});
           color:#fff;text-decoration:none;font-weight:700;font-size:14px;">Go to Login</a>
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

if ss.is_processing:
    ss.is_processing = False
    new_msgs, interrupt_payload = stream_and_collect()
    for m in new_msgs: add_msg(m["role"], m["content"])
    if interrupt_payload:
        ss.interrupt_data = interrupt_payload; ss.interrupt_type = interrupt_payload.get("type")
    else:
        ss.interrupt_data = None; ss.interrupt_type = None


st.markdown(f"""
<script>
(function(){{
  var SB='{SB_BG}',PG='{PAGE_BG}',BD='{SB_BDR}';
  function fix(){{
    // Sidebar column
    var cols=document.querySelectorAll('[data-testid="stHorizontalBlock"]>[data-testid="column"]');
    if(cols.length>=2){{
      var s=cols[0];
      s.style.background=SB;
      s.style.borderRight='2px solid '+BD;
      s.style.overflowY='auto';
      var sv=s.querySelector(':scope>[data-testid="stVerticalBlock"]');
      if(sv){{sv.style.background=SB;sv.style.overflowY='auto';sv.style.padding='12px 8px';sv.style.height='100%';}}
      // Main column: flex column so container fills space and input sits at bottom
      var m=cols[cols.length-1];
      m.style.background=PG;
      var mv=m.querySelector(':scope>[data-testid="stVerticalBlock"]');
      if(mv){{mv.style.display='flex';mv.style.flexDirection='column';mv.style.height='100%';mv.style.overflow='hidden';mv.style.background=PG;}}
    }} else {{
      // No columns (sidebar closed): fix root vertical block
      var root=document.querySelector('div[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"]');
      if(root){{root.style.display='flex';root.style.flexDirection='column';root.style.height='100vh';root.style.overflow='hidden';root.style.background=PG;}}
    }}
    // Messages border wrapper: make it fill remaining flex space and scroll
    var bw=document.querySelector('[data-testid="stVerticalBlockBorderWrapper"]');
    if(bw){{
      bw.style.flex='1';
      bw.style.height='0';
      bw.style.minHeight='80px';
      bw.style.overflowY='auto';
      bw.style.border='none';
      bw.style.borderRadius='0';
      bw.style.background='transparent';
      bw.style.boxShadow='none';
    }}
  }}
  var mo=new MutationObserver(fix);
  mo.observe(document.body,{{childList:true,subtree:true}});
  fix();
}})();
</script>
""", unsafe_allow_html=True)

if ss.sidebar_open:
    sidebar_col, main_col = st.columns([1, 4], gap="small")
else:
    sidebar_col = None
    main_col    = st.container()

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
if ss.sidebar_open and sidebar_col is not None:
    with sidebar_col:
        sb_hdr_left, sb_hdr_right = st.columns([5, 1], gap="small")
        with sb_hdr_left:
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:10px;padding:10px 4px;">
              <div style="width:30px;height:30px;border-radius:8px;
                   background:linear-gradient(135deg,{ACCENT},{ACCENT2});
                   display:flex;align-items:center;justify-content:center;flex-shrink:0;">✨</div>
              <span style="font-size:13px;font-weight:700;color:{TP};">CogniSync</span>
            </div>
            """, unsafe_allow_html=True)
        with sb_hdr_right:
            st.markdown('<div class="close-sb-btn">', unsafe_allow_html=True)
            if st.button("✕", key="btn_close_sb"): ss.sidebar_open = False; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="height:1px;background:{SB_BDR};margin:4px 0 10px;"></div>', unsafe_allow_html=True)
        st.markdown('<div class="new-chat-btn">', unsafe_allow_html=True)
        if st.button("＋ New Chat", key="btn_new_chat"): create_thread(); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        for tid in ss.threads:
            active = tid == ss.current_thread
            st.markdown(f'<div class="{"active-thread" if active else ""}">', unsafe_allow_html=True)
            if st.button(f"{'▶' if active else '💬'} {ss.thread_names.get(tid,'...')[:25]}", key=f"thread_{tid}"):
                switch_thread(tid); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

# ── MAIN CHAT AREA ────────────────────────────────────────────────────────────
with main_col:
    # Header bar: toggle ☰ + "Chat" title on same line
    hdr_toggle_col, hdr_title_col = st.columns([1, 10], gap="small")
    with hdr_toggle_col:
        if not ss.sidebar_open:
            st.markdown('<div class="toggle-btn-wrapper">', unsafe_allow_html=True)
            if st.button("☰", key="btn_open_sb"): ss.sidebar_open = True; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
    with hdr_title_col:
        st.markdown(f'<div class="chat-header"><span style="font-weight:700;color:{TP};font-size:15px;">Chat</span></div>', unsafe_allow_html=True)

    # Messages — use st.container(height=...) which Streamlit actually scrolls
    msgs = cur_msgs()
    with st.container(height=600, border=False):
        if msgs:
            for m in msgs:
                content = linkify(m.get("content", ""))
                role = m['role']
                if role == 'user':
                    bst = f"background:{USR_BG};color:#fff;border-radius:16px 16px 4px 16px;padding:10px 14px;margin:4px 0 4px auto;max-width:75%;width:fit-content;font-size:14px;line-height:1.5;word-break:break-word;"
                else:
                    bst = f"background:{BOT_BG};color:{BOT_COL};border-radius:16px 16px 16px 4px;padding:10px 14px;margin:4px auto 4px 0;max-width:82%;width:fit-content;font-size:14px;line-height:1.5;word-break:break-word;"
                st.markdown(f"<div style='{bst}'>{content}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="display:flex;align-items:center;justify-content:center;min-height:200px;">
              <div style="text-align:center;">
                <div style="font-size:40px;margin-bottom:12px;">💬</div>
                <p style="color:{TS};font-size:14px;">Start a conversation…</p>
              </div>
            </div>
            """, unsafe_allow_html=True)

    # Input / interrupt — sits BELOW the scrollable container (natural flex bottom)
    if ss.interrupt_data:
        itype = ss.interrupt_type
        idata = ss.interrupt_data
        st.markdown('<div class="input-area">', unsafe_allow_html=True)
        if itype == "confirm":
            st.markdown(f"<div style='color:{TP};font-size:13px;margin-bottom:8px;'>⚡ {esc(idata.get('message','Confirm?'))}</div>", unsafe_allow_html=True)
            c1, c2 = st.columns([1, 1], gap="small")
            with c1:
                st.markdown('<div class="action-btn-blue">', unsafe_allow_html=True)
                if st.button("✓ Yes", key="btn_yes"):
                    do_resume({"user_input": "yes"}, "Yes"); st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            with c2:
                st.markdown('<div class="action-btn-neutral">', unsafe_allow_html=True)
                if st.button("✗ No", key="btn_no"):
                    do_resume({"user_input": "no"}, "No"); st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
        elif itype == "edit_email":
            email_data = idata.get("email_data", {})
            st.markdown(f"<div style='color:{TP};font-size:13px;margin-bottom:6px;'>✉️ Review email draft:</div>", unsafe_allow_html=True)
            if not ss.edit_box_open:
                to_esc   = esc(email_data.get('to',''))
                subj_esc = esc(email_data.get('subject',''))
                body_esc = esc(email_data.get('body',''))
                st.markdown(f"""
                <div style='background:{BL_BG};border:1px solid {BL_BDR};border-radius:10px;padding:12px;margin-bottom:8px;font-size:12px;color:{TP};'>
                  <b>To:</b> {to_esc}<br><b>Subject:</b> {subj_esc}<br>
                  <div style='margin-top:6px;white-space:pre-wrap;'>{body_esc}</div>
                </div>
                """, unsafe_allow_html=True)
                c1, c2, c3 = st.columns([1,1,1], gap="small")
                with c1:
                    st.markdown('<div class="action-btn-blue">', unsafe_allow_html=True)
                    if st.button("📤 Send", key="btn_send_email"):
                        do_resume({"state_update": {"email_approved": True, "edited_email": None}}, "Send email"); st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                with c2:
                    st.markdown('<div class="action-btn-neutral">', unsafe_allow_html=True)
                    if st.button("✏️ Edit", key="btn_edit_email"):
                        ss.edit_box_open = True; ss.edit_body_text = email_data.get('body',''); st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                with c3:
                    st.markdown('<div class="action-btn-neutral">', unsafe_allow_html=True)
                    if st.button("✗ Cancel", key="btn_cancel_email"):
                        do_resume({"state_update": {"email_approved": False, "edited_email": None}}, "Cancel"); st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
            else:
                new_body = st.text_area("Edit email body:", value=ss.edit_body_text, height=120, key="email_edit_area")
                c1, c2 = st.columns([1,1], gap="small")
                with c1:
                    st.markdown('<div class="action-btn-blue">', unsafe_allow_html=True)
                    if st.button("📤 Send edited", key="btn_send_edited"):
                        edited = {**email_data, "body": new_body}
                        do_resume({"state_update": {"email_approved": True, "edited_email": edited}}, "Send edited email"); st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                with c2:
                    st.markdown('<div class="action-btn-neutral">', unsafe_allow_html=True)
                    if st.button("✗ Cancel", key="btn_cancel_edit"):
                        do_resume({"state_update": {"email_approved": False, "edited_email": None}}, "Cancel"); st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
        elif itype in ("calendar_confirm", "calendar"):
            evt = idata.get("event_data", {})
            st.markdown(f"<div style='color:{TP};font-size:13px;margin-bottom:6px;'>📅 Confirm calendar event:</div>", unsafe_allow_html=True)
            title_esc = esc(evt.get('title',''))
            date_esc  = esc(evt.get('date',''))
            start_esc = esc(evt.get('start_time',''))
            end_esc   = esc(evt.get('end_time',''))
            dur_esc   = esc(evt.get('duration_minutes',''))
            desc_esc  = esc(evt.get('description',''))
            st.markdown(f"""
            <div style='background:{Y_BG};border:1px solid {Y_BDR};border-radius:10px;padding:12px;margin-bottom:8px;font-size:12px;color:{TP};'>
              📌 <b>{title_esc}</b><br>📆 {date_esc} &nbsp;⏰ {start_esc}–{end_esc} ({dur_esc} min)<br>
              {('<p style="margin-top:4px;">' + desc_esc + '</p>') if desc_esc else ''}
            </div>
            """, unsafe_allow_html=True)
            c1, c2 = st.columns([1,1], gap="small")
            with c1:
                st.markdown('<div class="action-btn-blue">', unsafe_allow_html=True)
                if st.button("✓ Confirm", key="btn_cal_yes"):
                    do_resume({"user_input": "yes"}, "Confirm event"); st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            with c2:
                st.markdown('<div class="action-btn-neutral">', unsafe_allow_html=True)
                if st.button("✗ Cancel", key="btn_cal_no"):
                    do_resume({"user_input": "no"}, "Cancel event"); st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='color:{TP};font-size:13px;margin-bottom:8px;'>⚡ {esc(idata.get('message','Action required'))}</div>", unsafe_allow_html=True)
            extra_input = st.text_input("Your response:", key="generic_interrupt_input")
            st.markdown('<div class="action-btn-blue">', unsafe_allow_html=True)
            if st.button("Submit", key="btn_generic_submit"):
                if extra_input: do_resume({"user_input": extra_input}, extra_input); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        # Normal message input
        st.markdown('<div class="input-area">', unsafe_allow_html=True)
        user_input = st.text_input("message_input", key="chat_input", label_visibility="collapsed")
        st.markdown('<div class="send-btn">', unsafe_allow_html=True)
        if st.button("Send ➤", key="btn_send"):
            if user_input: do_send(user_input); st.rerun()
        st.markdown('</div></div>', unsafe_allow_html=True)