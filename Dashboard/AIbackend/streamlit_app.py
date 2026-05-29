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
    edit_box_open=False, edit_body_text="",
)
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

ss = st.session_state

PAGE_BG = "#080d18"; SB_BG  = "#0d1424"; SB_BDR = "#1a2540"
HDR_BG  = "#0d1424"; IN_BG  = "#111c33"; IN_BDR = "#1e3058"
BOT_BG  = "#111c33"; BOT_COL= "#e2eaf8"; USR_BG = "#1a4fd6"
TP      = "#e8edf8"; TS     = "#8896b0"; TM     = "#4a5a78"
BTN_BG  = "#111c33"; BTN_HV = "#1a2a4a"; BTN_ACT= "#1a4fd6"
BADGE_BG= "#1a2540"; SCR    = "#1e3058"
Y_BG    = "#1f1500"; Y_BDR  = "#5c3000"
BL_BG   = "#060d22"; BL_BDR = "#0d2255"
ACCENT  = "#3b82f6"; ACCENT2= "#6366f1"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
html,body,[data-testid="stAppViewContainer"],[data-testid="stMain"],
section[data-testid="stMain"],section[data-testid="stMain"]>.block-container,
div[data-testid="stMainBlockContainer"]{{
  background:{PAGE_BG}!important;padding:0!important;margin:0!important;
  max-width:100vw!important;font-family:'Inter',sans-serif!important;}}
header,footer,[data-testid="stHeader"],[data-testid="stToolbar"],
[data-testid="stDecoration"],[data-testid="stStatusWidget"],
[data-testid="stBottom"],[data-testid="stSidebar"],
[data-testid="collapsedControl"]{{display:none!important;}}
[data-testid="stVerticalBlock"]{{gap:0!important;padding:0!important;}}
[data-testid="stMarkdownContainer"]{{margin:0!important;padding:0!important;}}
::-webkit-scrollbar{{width:4px;height:4px;}}
::-webkit-scrollbar-thumb{{background:{SCR};border-radius:4px;}}
::-webkit-scrollbar-track{{background:transparent;}}
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
div[data-testid="stColumns"]{{gap:8px!important;}}
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

st.markdown("""
<script>
(function() {
  if (window.__gmailListenerInstalled) return;
  window.__gmailListenerInstalled = true;
  window.addEventListener('message', function(e) {
    if (e.data && e.data.type === 'GMAIL_AUTH_SUCCESS') {
      setTimeout(function() { window.location.reload(); }, 300);
    }
  });
})();
</script>
""", unsafe_allow_html=True)

if ss.is_processing:
    ss.is_processing = False
    new_msgs, interrupt_payload = stream_and_collect()
    for m in new_msgs: add_msg(m["role"], m["content"])
    if interrupt_payload:
        ss.interrupt_data = interrupt_payload; ss.interrupt_type = interrupt_payload.get("type")
    else:
        ss.interrupt_data = None; ss.interrupt_type = None


sidebar_col, main_col = st.columns([1, 4], gap="small")

with sidebar_col:
    st.markdown(f"""
    <div style="background:{SB_BG};border-right:1px solid {SB_BDR};min-height:100vh;padding:0;">
      <div style="display:flex;align-items:center;gap:10px;padding:14px 12px;border-bottom:1px solid {SB_BDR};">
        <div style="width:34px;height:34px;border-radius:10px;flex-shrink:0;
                    background:linear-gradient(135deg,{ACCENT},{ACCENT2});
                    display:flex;align-items:center;justify-content:center;font-size:16px;">✨</div>
        <span style="font-size:14px;font-weight:700;color:{TP};">CogniSync AI</span>
      </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="new-chat-btn">', unsafe_allow_html=True)
    if st.button("＋  New Chat", key="btn_new_chat"):
        create_thread(); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    badge = f"{len(ss.threads)}/{MAX_THREADS}"
    st.markdown(f"""
    <div style="display:flex;align-items:center;justify-content:space-between;
                padding:6px 4px 4px;font-size:10px;font-weight:700;
                letter-spacing:.08em;text-transform:uppercase;color:{TM};">
      <span>Chats</span>
      <span style="padding:2px 6px;border-radius:20px;background:{BADGE_BG};color:{TS};font-size:10px;">{badge}</span>
    </div>
    """, unsafe_allow_html=True)

    for tid in ss.threads:
        name   = ss.thread_names.get(tid, "New Conversation")
        active = tid == ss.current_thread
        if active: st.markdown('<div class="active-thread">', unsafe_allow_html=True)
        if st.button(f"{'▶ ' if active else '💬 '}{name[:32]}", key=f"thread_{tid}"):
            switch_thread(tid); st.rerun()
        if active: st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(f"""
    <div style="padding:14px 10px 10px;border-top:1px solid {SB_BDR};margin-top:20px;">
      <div style="font-size:11px;color:{TS};word-break:break-all;">👤 {esc(ss.user_email or '')}</div>
      <div style="font-size:10px;color:{TM};margin-top:2px;">🏢 {esc(ss.user_org or '')}</div>
    </div></div>
    """, unsafe_allow_html=True)


with main_col:
    st.markdown(f"""
    <div style="background:{PAGE_BG};min-height:100vh;display:flex;flex-direction:column;">
      <div style="background:{HDR_BG};border-bottom:1px solid {SB_BDR};
                  padding:12px 18px;display:flex;align-items:center;gap:10px;">
        <div style="width:32px;height:32px;border-radius:9px;
                    background:linear-gradient(135deg,#ede9fe,#fce7f3);
                    display:flex;align-items:center;justify-content:center;font-size:16px;">🤖</div>
        <span style="font-size:15px;font-weight:700;color:{TP};">CogniSync AI Assistant</span>
        <span style="margin-left:auto;font-size:11px;color:{TS};">
          {esc(ss.thread_names.get(ss.current_thread,'')[:40])}</span>
      </div>
    """, unsafe_allow_html=True)

    msgs = cur_msgs()
    if not msgs:
        st.markdown(f"""
        <div style="display:flex;flex-direction:column;align-items:center;
                    justify-content:center;padding:80px 20px;text-align:center;">
          <div style="font-size:56px;margin-bottom:18px;">✨</div>
          <h3 style="font-size:20px;font-weight:700;margin:0 0 8px;color:{TP};">Start a conversation</h3>
          <p style="font-size:13px;color:{TS};margin:0;">Search · Email · Calendar · Documents</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        for m in msgs:
            role    = m.get("role", "assistant")
            content = linkify(m.get("content", ""))
            is_user = role == "user"
            bub_bg  = USR_BG if is_user else BOT_BG
            bub_col = "#fff" if is_user else BOT_COL
            bub_br  = "18px 18px 4px 18px" if is_user else "18px 18px 18px 4px"
            row_dir = "row-reverse" if is_user else "row"
            av_bg   = "#059669" if is_user else "#3b82f6"
            av      = "👤" if is_user else "🤖"
            st.markdown(f"""
            <div style="display:flex;flex-direction:{row_dir};gap:8px;
                        align-items:flex-end;margin-bottom:14px;padding:0 4px;">
              <div style="width:30px;height:30px;border-radius:8px;flex-shrink:0;
                          background:{av_bg};display:flex;align-items:center;
                          justify-content:center;font-size:14px;">{av}</div>
              <div style="max-width:72%;border-radius:{bub_br};padding:10px 14px;
                          font-size:13px;line-height:1.7;word-break:break-word;white-space:pre-wrap;
                          background:{bub_bg};color:{bub_col};
                          box-shadow:0 1px 6px rgba(0,0,0,.2);">{content}</div>
            </div>
            """, unsafe_allow_html=True)

    if ss.is_processing:
        st.markdown(f"""
        <div style="display:flex;gap:8px;align-items:flex-end;margin-bottom:14px;">
          <div style="width:30px;height:30px;border-radius:8px;background:{ACCENT};
                      display:flex;align-items:center;justify-content:center;font-size:14px;">🤖</div>
          <div style="border-radius:18px 18px 18px 4px;padding:10px 16px;
                      background:{BOT_BG};color:{TS};font-size:13px;">Thinking…</div>
        </div>
        """, unsafe_allow_html=True)

    if ss.interrupt_data and ss.interrupt_type:
        itype = ss.interrupt_type
        idata = ss.interrupt_data

        if itype == "GMAIL_AUTH_REQUIRED":
            msg = idata.get("message", "Gmail authorization required.")
            auth_url = ""
            try:
                ep = idata.get("auth_start_endpoint", "/chat/gmail/auth/start")
                r  = requests.get(f"{API_BASE}{ep}", params={"thread_id": ss.current_thread}, timeout=8)
                auth_url = r.json().get("auth_url", "")
            except Exception: pass
            st.markdown(f"""
            <div style="border-radius:12px;padding:16px;margin:8px 0;background:{Y_BG};border:1px solid {Y_BDR};">
              <div style="font-weight:700;color:{TP};margin-bottom:6px;">⚠️ Gmail Authorization Required</div>
              <div style="font-size:13px;color:{TS};margin-bottom:12px;">{esc(msg)}</div>
              {"" if not auth_url else f'<a href="{esc(auth_url)}" target="_blank" style="display:inline-block;padding:9px 18px;border-radius:10px;background:{ACCENT};color:#fff;font-weight:700;font-size:13px;text-decoration:none;">🔑 Authorize Gmail</a><div style="font-size:11px;color:{TS};margin-top:8px;">After authorizing, this page will refresh automatically.</div>'}
            </div>
            """, unsafe_allow_html=True)

        elif itype == "USER_CHOICE":
            msg  = idata.get("message", "Select a recipient:")
            opts = idata.get("options", [])
            st.markdown(f"""
            <div style="border-radius:12px;padding:16px;margin:8px 0;background:{BL_BG};border:1px solid {BL_BDR};">
              <div style="font-weight:700;color:{TP};margin-bottom:10px;">👥 {esc(msg)}</div>
            """, unsafe_allow_html=True)
            for opt in opts:
                uname = opt.get("username", "")
                oname = opt.get("name", "")
                label = uname + (f" · {oname}" if oname else "")
                st.markdown('<div class="action-btn-neutral">', unsafe_allow_html=True)
                if st.button(label, key=f"choice_{uname}_{ss.current_thread}"):
                    do_resume({"user_input": uname}, f"Selected: {uname}"); st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        elif itype in ("EMAIL_BODY_CONFIRM", "EMAIL_BODY_EDIT"):
            email_body = idata.get("email_body", "")
            subject    = idata.get("subject", "")
            recipient  = idata.get("recipient", "")
            st.markdown(f"""
            <div style="border-radius:12px;padding:16px;margin:8px 0;background:{BL_BG};border:1px solid {BL_BDR};">
              <div style="font-weight:700;color:{TP};margin-bottom:10px;">📧 Email Preview</div>
              {"" if not recipient else f'<div style="font-size:12px;color:{TS};margin-bottom:4px;">To: {esc(recipient)}</div>'}
              {"" if not subject else f'<div style="font-size:12px;color:{TS};margin-bottom:8px;">Subject: {esc(subject)}</div>'}
              <pre style="background:{IN_BG};border:1px solid {IN_BDR};border-radius:8px;padding:12px;
                          font-size:12px;white-space:pre-wrap;word-break:break-word;color:{TP};
                          margin:0 0 12px;max-height:220px;overflow-y:auto;font-family:'Inter',sans-serif;">
{esc(email_body)}</pre>
            """, unsafe_allow_html=True)
            col_send, col_edit, _ = st.columns([1, 1, 3])
            with col_send:
                st.markdown('<div class="action-btn-blue">', unsafe_allow_html=True)
                if st.button("Send ✓", key=f"send_email_{ss.current_thread}"):
                    do_resume({"user_input": "yes"}, "Confirmed: send email")
                    ss.edit_box_open = False; st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            with col_edit:
                st.markdown('<div class="action-btn-neutral">', unsafe_allow_html=True)
                if st.button("Edit ✏️", key=f"edit_email_{ss.current_thread}"):
                    ss.edit_box_open = True; ss.edit_body_text = email_body; st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            if ss.edit_box_open:
                new_body = st.text_area("edit_body_area", value=ss.edit_body_text, height=140,
                    key=f"edit_body_area_{ss.current_thread}", label_visibility="collapsed")
                st.markdown('<div class="action-btn-blue">', unsafe_allow_html=True)
                if st.button("Apply & Continue", key=f"apply_edit_{ss.current_thread}"):
                    body_val = new_body.strip()
                    if body_val:
                        do_resume({"user_input": body_val}, body_val)
                        ss.edit_box_open = False; st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        elif itype == "MANUAL_EMAIL_INPUT":
            msg = idata.get("message", "Enter recipient email address:")
            st.markdown(f"""
            <div style="border-radius:12px;padding:16px;margin:8px 0;background:{Y_BG};border:1px solid {Y_BDR};">
              <div style="font-weight:700;color:{TP};margin-bottom:10px;">📨 {esc(msg)}</div>
            """, unsafe_allow_html=True)
            email_val = st.text_input("manual_email_input", placeholder="email@example.com",
                key=f"manual_email_{ss.current_thread}", label_visibility="collapsed")
            st.markdown('<div class="action-btn-blue">', unsafe_allow_html=True)
            if st.button("Submit", key=f"submit_manual_email_{ss.current_thread}"):
                val = (email_val or "").strip()
                if val: do_resume({"user_input": val}, val); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        else:
            msg = idata.get("message", "Please type your response:")
            st.markdown(f"""
            <div style="border-radius:12px;padding:16px;margin:8px 0;background:{BL_BG};border:1px solid {BL_BDR};">
              <div style="font-weight:700;color:{TP};margin-bottom:10px;">💬 {esc(msg)}</div>
            """, unsafe_allow_html=True)
            resp_val = st.text_input("interrupt_text_input", placeholder="Type your response…",
                key=f"interrupt_text_{ss.current_thread}", label_visibility="collapsed")
            st.markdown('<div class="action-btn-blue">', unsafe_allow_html=True)
            if st.button("Send Response", key=f"send_interrupt_{ss.current_thread}"):
                val = (resp_val or "").strip()
                if val: do_resume({"user_input": val}, val); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(f"""
    <div style="background:{HDR_BG};border-top:1px solid {SB_BDR};padding:12px 4px 16px;margin-top:16px;">
    """, unsafe_allow_html=True)

    input_disabled = bool(ss.interrupt_type)
    input_col, send_col = st.columns([6, 1], gap="small")
    with input_col:
        user_input = st.text_input("message_input",
            placeholder="Type your response…" if ss.interrupt_type else "Type your message…",
            key="chat_input", disabled=input_disabled, label_visibility="collapsed")
    with send_col:
        st.markdown('<div class="send-btn">', unsafe_allow_html=True)
        send_clicked = st.button("Send ➤", key="btn_send", disabled=input_disabled)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div></div>', unsafe_allow_html=True)

    if send_clicked and user_input and user_input.strip() and not input_disabled:
        do_send(user_input.strip()); st.rerun()