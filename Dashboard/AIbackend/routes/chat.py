from __future__ import annotations

import os
import base64
import json
import pytz
import dateparser

from typing import Annotated, TypedDict, Optional, List
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI, APIRouter, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pymongo import MongoClient

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.types import Command, interrupt
from langgraph.prebuilt import ToolNode, tools_condition

from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_core.output_parsers import PydanticOutputParser
from langchain_groq import ChatGroq

from pydantic import BaseModel, Field

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import Flow

import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

load_dotenv()

conn         = sqlite3.connect(database="chatbot.db", check_same_thread=False)
checkpointer = SqliteSaver(conn=conn)

MONGO_URI            = os.getenv("MONGO_URL")
GROQ_API_KEY         = os.getenv("GROQ_API_KEY")
GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI  = os.getenv("GOOGLE_REDIRECT_URI")

mongo      = MongoClient(MONGO_URI)
db_mongo   = mongo["collabryxdb"]
collection = db_mongo["embeddings"]
UsersModel = db_mongo["users"]

_pending_messages: dict = {}
_pending_resumes:  dict = {}

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
router = APIRouter(prefix="/chat", tags=["Chat"])
app.include_router(router)

llm         = ChatGroq(model="llama-3.3-70b-versatile", api_key=GROQ_API_KEY, temperature=0.7)
embeddings  = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vectorstore = MongoDBAtlasVectorSearch(
    collection=collection, embedding=embeddings, index_name="vector_index"
)

class CalendarEventIntent(BaseModel):
    title:            str
    date:             str
    start_time:       str
    end_time:         Optional[str] = None
    duration_minutes: Optional[int] = None
    description:      Optional[str] = None

class EmailIntentModel(BaseModel):
    to:        str
    cc:        Optional[str]
    bcc:       Optional[str]
    subject:   str
    body_hint: str

calendar_parser = PydanticOutputParser(pydantic_object=CalendarEventIntent)
email_parser    = PydanticOutputParser(pydantic_object=EmailIntentModel)

class ChatState(TypedDict):
    messages:           Annotated[List[BaseMessage], add_messages]
    user_email:         str
    org:                str
    calendar_intent:    Optional[dict]
    to_hint:            Optional[str]
    subject_hint:       Optional[str]
    body_hint:          Optional[str]
    cc:                 Optional[str]
    bcc:                Optional[str]
    eligible_users:     Optional[List[dict]]
    selected_user:      Optional[dict]
    manual_email:       Optional[str]
    email_body:         Optional[str]
    gmail_access_token: Optional[str]
    gmail_token_expiry: Optional[str]
    rag_docs:           Optional[list]
    email_sent:         Optional[bool]
    email_error:        Optional[str]

search_tool = DuckDuckGoSearchRun(region="us-en")

@tool
def calculator(expression: str) -> str:
    """Calculate mathematical expressions."""
    try:
        return str(eval(expression, {"__builtins__": {}}))
    except Exception as e:
        return f"Error: {e}"

@tool
def github_profile(username: str) -> str:
    """Get GitHub profile URL for a username."""
    import requests as _req
    r = _req.get(f"https://api.github.com/users/{username}")
    return f"https://github.com/{username} " if r.status_code == 200 else "Not found"

@tool
def get_stock_price(symbol: str) -> dict:
    """Get stock price for a symbol."""
    return {"symbol": symbol, "price": "mock"}

@tool
def gmail_send_intent(
    to_hint: str, subject_hint: str, body_hint: str,
    cc: Optional[str] = None, bcc: Optional[str] = None,
):
    """Intent to send an email via Gmail."""
    return {"to_hint": to_hint, "subject_hint": subject_hint,
            "body_hint": body_hint, "cc": cc, "bcc": bcc}

@tool
def doc_infoRetrieval_rag_intent(question: str) -> str:
    """Use this tool for question answering from stored documents."""
    return "RAG_QUERY"

@tool
def calendar_create_intent(message: str) -> str:
    """Use this tool to create or schedule calendar events."""
    return "CALENDAR_CREATE"

tools          = [search_tool, calculator, github_profile, get_stock_price,
                  gmail_send_intent, doc_infoRetrieval_rag_intent, calendar_create_intent]
llm_with_tools = llm.bind_tools(tools)
tool_node      = ToolNode(tools)

def chat_node(state: ChatState):
    system_prompt = SystemMessage(content=(
        "You are a helpful assistant. Use tools only when necessary. "
        "If a user wants to send an email, use gmail_send_intent. "
        "If they want to schedule a meeting, use calendar_create_intent. "
        "If they ask about documents, use doc_infoRetrieval_rag_intent."
    ))
    response = llm_with_tools.invoke([system_prompt] + state["messages"])
    return {"messages": [response]}

def extract_calendar_intent(state: ChatState):
    last_human_content = ""
    for msg in reversed(state["messages"]):
        if getattr(msg, "type", None) == "human":
            last_human_content = msg.content
            break
    prompt = (
        f"{calendar_parser.get_format_instructions()}\n"
        f'Convert this calendar request to JSON: "{last_human_content}"'
    )
    raw = llm.invoke([HumanMessage(content=prompt)]).content
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()
    if "{" in raw:
        raw = raw[raw.find("{"):raw.rfind("}")+1]
    try:
        parsed = calendar_parser.parse(raw)
        data   = parsed.model_dump()
        dt     = dateparser.parse(
            f"{data['date']} {data['start_time']}",
            settings={"PREFER_DATES_FROM": "future", "TIMEZONE": "Asia/Kolkata"}
        )
        if dt:
            data["date"]       = dt.date().isoformat()
            data["start_time"] = dt.strftime("%H:%M")
        return {"calendar_intent": data}
    except Exception as e:
        return {"messages": [AIMessage(
            content=f"I had trouble parsing that date: {e}. Could you give me the date and time clearly?"
        )]}

def get_google_credentials(state: ChatState):
    return Credentials(
        token=state.get("gmail_access_token"),
        refresh_token=None,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
    )

def create_calendar_event_node(state: ChatState):
    intent   = state["calendar_intent"]
    tz       = pytz.timezone("Asia/Kolkata")
    start_dt = tz.localize(datetime.fromisoformat(f"{intent['date']}T{intent['start_time']}"))
    end_dt   = (
        tz.localize(datetime.fromisoformat(f"{intent['date']}T{intent['end_time']}"))
        if intent.get("end_time")
        else start_dt + timedelta(minutes=intent.get("duration_minutes", 60))
    )
    creds   = get_google_credentials(state)
    service = build("calendar", "v3", credentials=creds)
    event   = {
        "summary":     intent["title"],
        "description": intent.get("description"),
        "start": {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Kolkata"},
        "end":   {"dateTime": end_dt.isoformat(),   "timeZone": "Asia/Kolkata"},
    }
    service.events().insert(calendarId="primary", body=event).execute()
    return {"messages": [AIMessage(
        content=f"Calendar event '{intent['title']}' created for {intent['date']} at {intent['start_time']}"
    )]}

def route_after_tool(state: ChatState) -> str:
    for msg in reversed(state["messages"]):
        if getattr(msg, "type", None) == "ai" and getattr(msg, "tool_calls", None):
            name = msg.tool_calls[0]["name"]
            if name == "gmail_send_intent":            return "extract_email"
            if name == "doc_infoRetrieval_rag_intent": return "docRag"
            if name == "calendar_create_intent":       return "extract_calendar_intent"
            return "chat"
    return "chat"

def rag_flow(state: ChatState):
    try:
        query = ""
        for msg in reversed(state["messages"]):
            if getattr(msg, "type", None) == "human":
                query = msg.content
                break
        retriever = vectorstore.as_retriever(
            search_kwargs={"k": 5, "filter": {"metadata.org": state["org"]}}
        )
        docs = retriever.get_relevant_documents(query)
        return {"rag_docs": docs}
    except Exception as e:
        return {"email_error": str(e), "rag_docs": []}

def rag_reframe_node(state: ChatState):
    if not state.get("rag_docs"):
        return {"messages": [AIMessage(content="No relevant information found in the documents.")]}
    context  = "\n\n".join(d.page_content for d in state["rag_docs"][:3])
    question = ""
    for msg in reversed(state["messages"]):
        if getattr(msg, "type", None) == "human":
            question = msg.content
            break
    try:
        answer = llm.invoke(
            f"Answer using ONLY this context:\n{context}\n\nQuestion: {question}\n\nAnswer:"
        ).content
        return {"messages": [AIMessage(content=answer)]}
    except Exception as e:
        return {"messages": [AIMessage(content=f"Error: {e}")]}

def extract_email_info(state: ChatState):
    try:
        for msg in reversed(state["messages"]):
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    if tc["name"] == "gmail_send_intent":
                        a = tc["args"]
                        return {
                            "to_hint":      a.get("to_hint"),
                            "subject_hint": a.get("subject_hint"),
                            "body_hint":    a.get("body_hint"),
                            "cc":           a.get("cc"),
                            "bcc":          a.get("bcc"),
                        }
    except Exception as e:
        return {"email_error": str(e)}
    return state

def find_recipients(state: ChatState):
    try:
        users = list(UsersModel.find(
            {
                "org": state["org"],
                "$or": [
                    {"username": {"$regex": state["to_hint"], "$options": "i"}},
                    {"name":     {"$regex": state["to_hint"], "$options": "i"}},
                ],
                "email": {"$ne": state["user_email"]},
            },
            {"_id": 0},
        ))
        return {"eligible_users": users}
    except Exception as e:
        return {"email_error": str(e), "eligible_users": []}

def select_recipient(state: ChatState):
    users = state.get("eligible_users", [])
    if not users:
        manual_email = interrupt({
            "type":    "MANUAL_EMAIL_INPUT",
            "message": "No matching recipients found. Please enter the recipient's email address:",
        })
        return {"manual_email": manual_email, "selected_user": None}
    elif len(users) == 1:
        return {"selected_user": users[0], "manual_email": None}
    else:
        choice = interrupt({
            "type":    "USER_CHOICE",
            "message": "Multiple recipients found. Please select one:",
            "options": [
                {"index": i, "username": u["username"],
                 "name": u.get("name", ""), "email": u["email"]}
                for i, u in enumerate(users)
            ],
        })
        for i, u in enumerate(users):
            if choice in (u["username"], str(i), u["email"]):
                return {"selected_user": u, "manual_email": None}
        return {"selected_user": users[0], "manual_email": None}

def generate_body_node(state: ChatState):
    prompt = (
        f"Write a concise professional email.\n"
        f"Subject: {state['subject_hint']}\nContext: {state['body_hint']}\n\nEmail body:"
    )
    try:
        return {"email_body": llm.invoke(prompt).content}
    except Exception as e:
        return {"email_error": str(e)}

def confirm_body_node(state: ChatState):
    recipient = (
        state.get("selected_user", {}).get("email")
        if state.get("selected_user")
        else state.get("manual_email")
    )
    confirmed = interrupt({
        "type":       "EMAIL_BODY_CONFIRM",
        "message":    "Here's the email I've drafted. Send it or make changes?",
        "email_body": state.get("email_body", ""),
        "subject":    state.get("subject_hint", ""),
        "recipient":  recipient,
    })
    if confirmed.lower() in ("edit", "no", "change", "modify"):
        new_body = interrupt({
            "type":         "EMAIL_BODY_EDIT",
            "message":      "Provide the corrected body or describe the changes:",
            "current_body": state.get("email_body", ""),
        })
        if len(new_body.split()) < 20:
            prompt = (
                f"Original email:\n{state.get('email_body', '')}\n\n"
                f"Edit request:\n{new_body}\n\nEdited email:"
            )
            try:
                return {"email_body": llm.invoke(prompt).content}
            except Exception:
                return {"email_body": new_body}
        return {"email_body": new_body}
    return state

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar",
]

def build_gmail_oauth_flow():
    return Flow.from_client_config(
        {"web": {
            "client_id":     GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri":      "https://accounts.google.com/o/oauth2/auth",
            "token_uri":     "https://oauth2.googleapis.com/token",
            "redirect_uris": [GOOGLE_REDIRECT_URI],
        }},
        scopes=GMAIL_SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI,
    )

def ensure_gmail_auth(state: ChatState):
    token  = state.get("gmail_access_token")
    expiry = state.get("gmail_token_expiry")
    if token and expiry:
        try:
            if datetime.fromisoformat(expiry) > datetime.now(timezone.utc):
                return state
        except Exception:
            pass
    interrupt({
        "type":    "GMAIL_AUTH_REQUIRED",
        "message": "Gmail authentication required. Please authorize access.",
        "auth_start_endpoint": "/chat/gmail/auth/start",
    })
    return state

def ensure_calendar_auth(state: ChatState):
    token  = state.get("gmail_access_token")
    expiry = state.get("gmail_token_expiry")
    if token and expiry:
        try:
            if datetime.fromisoformat(expiry) > datetime.now(timezone.utc):
                return state
        except Exception:
            pass
    interrupt({
        "type":    "GMAIL_AUTH_REQUIRED",
        "message": "Google authorization required to create calendar events. Please authorize access.",
        "auth_start_endpoint": "/chat/gmail/auth/start",
    })
    return state

@router.get("/gmail/auth/start")
def gmail_auth_start(thread_id: str):
    flow = build_gmail_oauth_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline", prompt="consent", state=thread_id
    )
    return {"auth_url": auth_url}

@router.get("/gmail/auth/callback")
def gmail_auth_callback(code: str, state: str):
    from fastapi.responses import HTMLResponse
    try:
        flow = build_gmail_oauth_flow()
        flow.fetch_token(code=code)
        creds     = flow.credentials
        token     = creds.token
        expiry    = creds.expiry.isoformat() if creds.expiry else ""
        thread_id = state

        config = {"configurable": {"thread_id": thread_id}}
        app_graph.update_state(config, {
            "gmail_access_token": token,
            "gmail_token_expiry": expiry,
        })
        _pending_resumes[thread_id] = {"type": "state_only"}

        return HTMLResponse(content="""<!DOCTYPE html>
<html>
<head><title>Gmail Authorized</title></head>
<body style="font-family:sans-serif;display:flex;align-items:center;
             justify-content:center;height:100vh;margin:0;background:#0d1424;">
  <div style="text-align:center;color:#e2eaf8;">
    <div style="font-size:48px;margin-bottom:16px;">&#10003;</div>
    <h2 style="margin:0 0 8px;">Authorized!</h2>
    <p style="color:#8896b0;">Processing now. This tab will close automatically.</p>
  </div>
  <script>
    if (window.opener) {
      window.opener.postMessage({ type: 'GMAIL_AUTH_SUCCESS', thread_id: '""" + thread_id + """' }, '*');
    }
    setTimeout(function() { window.close(); }, 1800);
  </script>
</body>
</html>""")
    except Exception as e:
        from fastapi.responses import HTMLResponse
        return HTMLResponse(status_code=400, content="""<!DOCTYPE html>
<html>
<body style="font-family:sans-serif;display:flex;align-items:center;
             justify-content:center;height:100vh;margin:0;background:#0d1424;">
  <div style="text-align:center;color:#e2eaf8;">
    <div style="font-size:48px;margin-bottom:16px;">&#10007;</div>
    <h2 style="margin:0 0 8px;">Authorization Failed</h2>
    <p style="color:#f87171;">""" + str(e) + """</p>
  </div>
</body>
</html>""")

def send_email_node(state: ChatState):
    try:
        to_email = (
            state["selected_user"]["email"]
            if state.get("selected_user")
            else state["manual_email"]
        )
        msg  = f"To: {to_email}\n"
        if state.get("cc"):  msg += f"Cc: {state['cc']}\n"
        if state.get("bcc"): msg += f"Bcc: {state['bcc']}\n"
        msg += f"Subject: {state['subject_hint']}\n\n{state['email_body']}"
        raw     = base64.urlsafe_b64encode(msg.encode()).decode()
        creds   = Credentials(token=state["gmail_access_token"])
        service = build("gmail", "v1", credentials=creds)
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return {
            "messages":   [AIMessage(content=f"Email sent successfully to {to_email}!")],
            "email_sent": True,
        }
    except Exception as e:
        return {
            "messages":    [AIMessage(content=f"Failed to send email: {e}")],
            "email_error": str(e),
            "email_sent":  False,
        }

graph = StateGraph(ChatState)

graph.add_node("chat",                    chat_node)
graph.add_node("tools",                   tool_node)
graph.add_node("docRag",                  rag_flow)
graph.add_node("rag_reframe",             rag_reframe_node)
graph.add_node("extract_email",           extract_email_info)
graph.add_node("find_recipients",         find_recipients)
graph.add_node("select_recipient",        select_recipient)
graph.add_node("generate_body",           generate_body_node)
graph.add_node("confirm_body",            confirm_body_node)
graph.add_node("ensure_auth",             ensure_gmail_auth)
graph.add_node("ensure_calendar_auth",    ensure_calendar_auth)
graph.add_node("send_email",              send_email_node)
graph.add_node("extract_calendar_intent", extract_calendar_intent)
graph.add_node("create_calendar_event",   create_calendar_event_node)

graph.add_edge(START, "chat")
graph.add_conditional_edges("chat", tools_condition, {"tools": "tools", END: END})
graph.add_conditional_edges(
    "tools", route_after_tool,
    {"extract_email": "extract_email", "docRag": "docRag",
     "extract_calendar_intent": "extract_calendar_intent", "chat": "chat"}
)
graph.add_edge("docRag",                   "rag_reframe")
graph.add_edge("rag_reframe",              END)
graph.add_edge("extract_email",            "find_recipients")
graph.add_edge("find_recipients",          "select_recipient")
graph.add_edge("select_recipient",         "generate_body")
graph.add_edge("generate_body",            "confirm_body")
graph.add_edge("confirm_body",             "ensure_auth")
graph.add_edge("ensure_auth",              "send_email")
graph.add_edge("send_email",               END)
graph.add_edge("extract_calendar_intent",  "ensure_calendar_auth")
graph.add_edge("ensure_calendar_auth",     "create_calendar_event")
graph.add_edge("create_calendar_event",    END)

app_graph = graph.compile(checkpointer=checkpointer)

def _sse_stream(input_payload, config):
    for chunk, metadata in app_graph.stream(
        input_payload, config, stream_mode="messages"
    ):
        if (
            isinstance(chunk, AIMessage)
            and chunk.content
            and not getattr(chunk, "tool_calls", None)
        ):
            payload = {"role": "assistant", "content": chunk.content}
            yield f"event: message\ndata: {json.dumps(payload)}\n\n"

    current_state = app_graph.get_state(config)
    if current_state.next:
        for task in current_state.tasks:
            if task.interrupts:
                for idata in task.interrupts:
                    yield f"event: interrupt\ndata: {json.dumps(idata.value)}\n\n"
                return

    yield f"event: end\ndata: {json.dumps({'status': 'complete'})}\n\n"

class ChatRequest(BaseModel):
    thread_id:  str
    message:    str
    user_email: str
    org:        str

class ResumeRequest(BaseModel):
    thread_id:    str
    user_input:   Optional[str]  = None
    state_update: Optional[dict] = None

@router.post("/message")
def send_message(req: ChatRequest):
    config = {"configurable": {"thread_id": req.thread_id}}
    state  = app_graph.get_state(config)

    if not state.values:
        app_graph.update_state(config, {
            "messages":   [],
            "user_email": req.user_email,
            "org":        req.org,
        })
    elif not state.values.get("user_email"):
        app_graph.update_state(config, {
            "user_email": req.user_email,
            "org":        req.org,
        })

    _pending_messages[req.thread_id] = req.message
    return {"status": "processing", "thread_id": req.thread_id}

@router.get("/stream")
def chat_stream(request: Request):
    thread_id = request.query_params.get("thread_id")

    def event_generator():
        config = {"configurable": {"thread_id": thread_id}}

        pending_resume = _pending_resumes.pop(thread_id, None)
        if pending_resume:
            if pending_resume["type"] == "resume":
                input_payload = Command(resume=pending_resume["value"])
            else:
                input_payload = Command(resume="authorized")
            yield from _sse_stream(input_payload, config)
            return

        message_text = _pending_messages.pop(thread_id, None)
        if not message_text:
            yield f"event: end\ndata: {json.dumps({'status': 'complete'})}\n\n"
            return
        input_payload = {"messages": [HumanMessage(content=message_text)]}
        yield from _sse_stream(input_payload, config)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )

@router.post("/resume")
def resume_graph(req: ResumeRequest):
    config = {"configurable": {"thread_id": req.thread_id}}

    if req.state_update:
        app_graph.update_state(config, req.state_update)
        _pending_resumes[req.thread_id] = {"type": "state_only"}
    else:
        _pending_resumes[req.thread_id] = {
            "type":  "resume",
            "value": req.user_input,
        }

    return {"status": "resuming", "thread_id": req.thread_id}

@router.get("/threads/{thread_id}")
def get_thread_messages(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    state  = app_graph.get_state(config)
    if not state or not state.values:
        return {"messages": []}

    result = []
    for msg in state.values.get("messages", []):
        msg_type = getattr(msg, "type", None)
        if msg_type == "human":
            result.append({"role": "user", "content": msg.content})
        elif (
            msg_type == "ai"
            and msg.content
            and not getattr(msg, "tool_calls", None)
        ):
            result.append({"role": "assistant", "content": msg.content})
    return {"messages": result}


@router.get("/threads")
def list_all_threads():
    all_threads = set()
    for checkpoint in checkpointer.list(None):
        cfg = checkpoint.config
        if cfg and "configurable" in cfg and "thread_id" in cfg["configurable"]:
            all_threads.add(cfg["configurable"]["thread_id"])
    return {"threads": list(all_threads)}

def retrieve_all_threads():
    all_threads = set()
    for checkpoint in checkpointer.list(None):
        cfg = checkpoint.config
        if cfg and "configurable" in cfg and "thread_id" in cfg["configurable"]:
            all_threads.add(cfg["configurable"]["thread_id"])
    return list(all_threads)