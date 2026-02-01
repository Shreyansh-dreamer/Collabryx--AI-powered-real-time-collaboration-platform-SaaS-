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
from dotenv import load_dotenv
from pymongo import MongoClient

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.types import interrupt
from langgraph.prebuilt import ToolNode, tools_condition

from langchain_core.messages import BaseMessage
from langchain.messages import AIMessage, HumanMessage, SystemMessage
from langchain.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_community.vectorstores import MongoDBAtlasVectorSearch
from langchain_community.llms import HuggingFaceHub
from langchain_core.output_parsers import PydanticOutputParser

from pydantic import BaseModel, Field

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import Flow

# =====================================================
# SQLITE CHECKPOINTER (THREADS + CONFIGURABLE)
# =====================================================
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
conn = sqlite3.connect(database="chatbot.db", check_same_thread=False)
checkpointer = SqliteSaver(conn=conn)


# =====================================================
#  DATA
# =====================================================
load_dotenv()

MONGO_URI = os.getenv("MONGO_URL")
HF_API_KEY = os.getenv("HUGGINGFACE_API_KEY")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

mongo = MongoClient(MONGO_URI)
db = mongo["collabryxdb"]
UsersModel = db["users"]

app = FastAPI()
router = APIRouter(prefix="/chat", tags=["Chat"])
app.include_router(router)

# =====================================================
# VECTOR STORE
# =====================================================
chatllm = HuggingFaceEndpoint(
    repo_id="mistralai/Mistral-7B-Instruct-v0.3",
    huggingfacehub_api_token=HF_API_KEY,
    task="text-generation",
    max_new_tokens=512,
    temperature=0.1,
)

llm = ChatHuggingFace(llm=chatllm)

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

vectorstore = MongoDBAtlasVectorSearch(
    collection_name="embeddings",
    embedding=embeddings,
    connection_string=MONGO_URI,
    database_name="collabryxdb",
    index_name="vector_index"
)

# =====================================================
# CALENDAR STRUCTURED OUTPUT (Pydantic)
# =====================================================
class CalendarEventIntent(BaseModel):
    """
    Pydantic model to parse calendar event info from user messages
    """
    title: str = Field(description="Short event title")
    date: str = Field(description="Event date in YYYY-MM-DD format")
    start_time: str = Field(description="Event start time in HH:MM 24h format")
    end_time: Optional[str] = Field(default=None, description="Optional end time")
    duration_minutes: Optional[int] = Field(default=None, description="Duration if end_time missing")
    description: Optional[str] = Field(default=None, description="Optional detailed description")

calendar_parser = PydanticOutputParser(pydantic_object=CalendarEventIntent)

# =====================================================
# EMAIL STRUCTURED OUTPUT (Pydantic)
# =====================================================
class EmailIntentModel(BaseModel):
    """
    Pydantic model to parse email sending info from user messages
    """
    to: str
    cc: Optional[str]
    bcc: Optional[str]
    subject: str
    body_hint: str

email_parser = PydanticOutputParser(pydantic_object=EmailIntentModel)

# =====================================================
# STATE
# =====================================================
class ChatState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    user_email: str
    org: str
    calendar_intent: Optional[dict]

    # Email-related state
    to_hint: Optional[str]
    subject_hint: Optional[str]
    body_hint: Optional[str]
    cc: Optional[str]
    bcc: Optional[str]

    eligible_users: Optional[List[dict]]
    selected_user: Optional[dict]
    manual_email: Optional[str]
    email_body: Optional[str]

    gmail_access_token: Optional[str]
    gmail_token_expiry: Optional[str]

    # RAG state
    rag_docs: Optional[list]

    # Status flags
    email_sent: Optional[bool]
    email_error: Optional[str]

# =====================================================
# TOOLS
# =====================================================
search_tool = DuckDuckGoSearchRun(region="us-en")

@tool
def calculator(expression: str) -> str:
    try:
        return str(eval(expression, {"__builtins__": {}}))
    except Exception as e:
        return f"Error: {e}"

@tool
def github_profile(username: str) -> str:
    import requests
    r = requests.get(f"https://api.github.com/users/{username}")
    return f"https://github.com/{username}" if r.status_code == 200 else "Not found"

@tool
def get_stock_price(symbol: str) -> dict:
    return {"symbol": symbol, "price": "mock"}

@tool
def gmail_send_intent(to_hint: str,subject_hint: str,body_hint: str,cc: Optional[str] = None,bcc: Optional[str] = None,):
    return {
        "to_hint": to_hint,
        "subject_hint": subject_hint,
        "body_hint": body_hint,
        "cc": cc,
        "bcc": bcc,
    }

@tool
def doc_infoRetrieval_rag_intent(question: str) -> str:
    """
    Use this tool when we have to do some question answering or extract 
    information from already stored documents
    """
    return "RAG_QUERY"

@tool
def calendar_create_intent(message: str) -> str:
    """
    Use this tool when we have to create or schedule some events in the calender
    """
    return "CALENDAR_CREATE"


tools = [
    search_tool,
    calculator,
    github_profile,
    get_stock_price,
    gmail_send_intent,
    doc_infoRetrieval_rag_intent,
    calendar_create_intent,
]
llm_with_tools = llm.bind_tools(tools)
tool_node = ToolNode(tools)

# =====================================================
# CHAT NODES
# =====================================================
def chat_node(state: ChatState):
    system_prompt = SystemMessage(content=(
        "You are a helpful assistant. Use tools only when necessary. "
        "If a user wants to send an email, use gmail_send_intent. "
        "If they want to schedule a meeting, use calendar_create_intent."
    ))
    messages = [system_prompt] + state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}



def extract_calendar_intent(state: ChatState):
    prompt = f"""
    {calendar_parser.get_format_instructions()}
    Convert the following user request into JSON:
    "{state['messages'][-1].content}"
    """
    raw_output = llm.invoke([HumanMessage(content=prompt)]).content
    if "{" in raw_output:
        raw_output = raw_output[raw_output.find("{"):raw_output.rfind("}")+1]
    try:
        parsed = calendar_parser.parse(raw_output)
        data = parsed.model_dump()
        dt = dateparser.parse(
            f"{data['date']} {data['start_time']}",
            settings={"PREFER_DATES_FROM": "future", "TIMEZONE": "Asia/Kolkata"}
        )
        if dt:
            data['date'] = dt.date().isoformat()
            data['start_time'] = dt.strftime("%H:%M")
        state["calendar_intent"] = data
        return state
    except Exception as e:
        return {"messages": [AIMessage(content="I had trouble parsing that date. Could you tell me the date and time clearly?")]}



def get_google_credentials(state: ChatState):
    """Helper to build credentials from state tokens"""
    return Credentials(
        token=state.get("gmail_access_token"),
    )



def create_calendar_event_node(state: ChatState):
    """Create Google Calendar event using parsed intent"""
    intent = state["calendar_intent"]
    tz = pytz.timezone("Asia/Kolkata")
    start_dt = tz.localize(datetime.fromisoformat(f"{intent['date']}T{intent['start_time']}"))
    if intent.get("end_time"):
        end_dt = tz.localize(datetime.fromisoformat(f"{intent['date']}T{intent['end_time']}"))
    else:
        end_dt = start_dt + timedelta(minutes=intent.get("duration_minutes", 60))
    creds = get_google_credentials(state)
    service = build("calendar", "v3", credentials=creds)
    event = {
        "summary": intent["title"],
        "description": intent.get("description"),
        "start": {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Kolkata"},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": "Asia/Kolkata"},
    }
    service.events().insert(calendarId="primary", body=event).execute()
    return {"messages": [AIMessage(content="Event created successfully")]}

# =====================================================
# ROUTE AFTER TOOL
# =====================================================
def route_after_tool(state: ChatState) -> str:
    """
    Determines which node to route to after a tool is called
    """
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        name = last.tool_calls[0]["name"]
        if name == "gmail_send_intent":
            return "extract_email"
        if name == "doc_infoRetrieval_rag_intent":
            return "docRag"
        if name == "calendar_create_intent":
            return "extract_calendar_intent"
    return "chat"


# =====================================================
# RAG NODES
# =====================================================
def rag_flow(state: ChatState):
    """Retrieve relevant documents from vector store"""
    try:
        retriever = vectorstore.as_retriever(
            search_kwargs={"k": 5, "filter": {"metadata.org": state["org"]}}
        )
        query = state["messages"][-1].content
        state["rag_docs"] = retriever.get_relevant_documents(query)
    except Exception as e:
        state["email_error"] = str(e)
    return state


def rag_reframe_node(state: ChatState):
    """LLM node to answer based on retrieved documents"""
    if not state.get("rag_docs"):
        return {"messages": [AIMessage(content="No relevant information found.")]}

    context = "\n\n".join(d.page_content for d in state["rag_docs"][:3])
    question = state["messages"][-1].content
    prompt = f"""
Answer the question using ONLY the context below.
Be concise and helpful.

Context:
{context}

Question:
{question}
"""
    try:
        answer = llm.invoke(prompt).content
        return {"messages": [AIMessage(content=answer)]}
    except Exception as e:
        return {"messages": [AIMessage(content=str(e))]}

# =====================================================
# EMAIL NODES
# =====================================================
def extract_email_info(state: ChatState):
    """Extract structured email info from message"""
    try:
        prompt = f"{email_parser.get_format_instructions()}\nMessage:\n{state['messages'][-1].content}"
        parsed = email_parser.parse(llm.invoke([HumanMessage(content=prompt)]).content)
        state.update(parsed.model_dump())
    except Exception as e:
        state["email_error"] = str(e)
    return state



def find_recipients(state: ChatState):
    """Find eligible users in DataBase based on to_hint"""
    try:
        users = list(
            UsersModel.find(
                {
                    "org": state["org"],
                    "$or": [
                        {"username": {"$regex": state["to_hint"], "$options": "i"}},
                        {"name": {"$regex": state["to_hint"], "$options": "i"}},
                    ],
                    "email": {"$ne": state["user_email"]},
                },
                {"_id": 0},
            )
        )
        if not users:
            interrupt({
                "type": "MANUAL_EMAIL_REQUIRED",
                "message": "No matching users found. Enter email manually."
            })
        state["eligible_users"] = users
    except Exception as e:
        state["email_error"] = str(e)
    return state



def select_recipient(state: ChatState):
    """Select recipient from eligible users"""
    if not state.get("eligible_users"):
        return state
    choice = interrupt({
                "type": "USER_CHOICE",
                "message": "Choose index or username:",
                "options": [
                    {"index": i, "username": u["username"]}
                    for i, u in enumerate(state["eligible_users"])
                ]
            })
    for i, u in enumerate(state["eligible_users"]):
        if choice == u["username"] or choice == str(i):
            state["selected_user"] = u
            return state
    return state



def manual_email_node(state: ChatState):
    """Ask user to manually enter recipient email if no selection"""
    if not state.get("selected_user"):
        state["manual_email"] = interrupt({
                                    "type": "USER_INPUT",
                                    "message": "Enter recipient email:"
                                })
    return state



def generate_body_node(state: ChatState):
    """Generate professional email body from hints"""
    prompt = f"Write a concise professional email.\nSubject: {state['subject_hint']}\nContext: {state['body_hint']}"
    try:
        state["email_body"] = llm.invoke(prompt).content
    except Exception as e:
        state["email_error"] = str(e)
    return state



def confirm_body_node(state: ChatState):
    """Ask user to confirm or edit email body"""
    ans = interrupt(f"{state['email_body']}\nSend? (yes/no)")
    if ans.lower() != "yes":
        state["email_body"] = interrupt("Provide corrected body:")
    return state

# =====================================================
# GMAIL AUTH
# =====================================================
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]



def build_gmail_oauth_flow():
    return Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [GOOGLE_REDIRECT_URI],
            }
        },
        scopes=GMAIL_SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI,
    )



def ensure_gmail_auth(state: ChatState):
    """Ensure valid Gmail OAuth token exists"""
    try:
        token = state.get("gmail_access_token")
        expiry = state.get("gmail_token_expiry")
        if token and expiry and datetime.fromisoformat(expiry) > datetime.now(timezone.utc):
            return state
        interrupt({
            "type": "GMAIL_AUTH_REQUIRED",
            "auth_start_endpoint": "/chat/gmail/auth/start",
            "resume_node": "ensure_auth"
        })
    except Exception as e:
        state["email_error"] = str(e)
    return state



@router.get("/gmail/auth/start")
def gmail_auth_start():
    flow = build_gmail_oauth_flow()
    auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent")
    return {"auth_url": auth_url}



@router.get("/gmail/auth/callback")
def gmail_auth_callback(code: str):
    try:
        flow = build_gmail_oauth_flow()
        flow.fetch_token(code=code)
        creds = flow.credentials
        return {"patch_state": {"gmail_access_token": creds.token, "gmail_token_expiry": creds.expiry.isoformat() if creds.expiry else None}}
    except Exception as e:
        return {"patch_state": {"email_error": str(e)}}



def send_email_node(state: ChatState):
    """Send email using Gmail API"""
    try:
        to_email = state["selected_user"]["email"] if state.get("selected_user") else state["manual_email"]
        raw = base64.urlsafe_b64encode(f"To:{to_email}\nSubject:{state['subject_hint']}\n\n{state['email_body']}".encode()).decode()
        creds = Credentials(token=state["gmail_access_token"])
        service = build("gmail", "v1", credentials=creds)
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return {"messages": [AIMessage(content="Email sent successfully")]}
    except Exception as e:
        state["email_error"] = str(e)
        return {"messages": [AIMessage(content="Failed to send email")]}

# =====================================================
# GRAPH
# =====================================================
graph = StateGraph(ChatState)

# Chat + Tools
graph.add_node("chat", chat_node)
graph.add_node("tools", tool_node)

# RAG
graph.add_node("docRag", rag_flow)
graph.add_node("rag_reframe", rag_reframe_node)

# Email
graph.add_node("extract_email", extract_email_info)
graph.add_node("find_recipients", find_recipients)
graph.add_node("select_recipient", select_recipient)
graph.add_node("manual_email", manual_email_node)
graph.add_node("generate_body", generate_body_node)
graph.add_node("confirm_body", confirm_body_node)
graph.add_node("ensure_auth", ensure_gmail_auth)
graph.add_node("send_email", send_email_node)

# Calendar
graph.add_node("extract_calendar_intent", extract_calendar_intent)
graph.add_node("create_calendar_event", create_calendar_event_node)

# Edges
graph.add_edge(START, "chat")
graph.add_conditional_edges("chat", tools_condition, {"tools": "tools", "end": END})
graph.add_conditional_edges("tools", route_after_tool)

graph.add_edge("docRag", "rag_reframe")
graph.add_edge("rag_reframe", END)

graph.add_edge("extract_email", "find_recipients")
graph.add_edge("find_recipients", "select_recipient")
graph.add_edge("select_recipient", "manual_email")
graph.add_edge("manual_email", "generate_body")
graph.add_edge("generate_body", "confirm_body")
graph.add_edge("confirm_body", "ensure_auth")
graph.add_edge("ensure_auth", "send_email")
graph.add_edge("send_email", END)

graph.add_edge("extract_calendar_intent", "create_calendar_event")
graph.add_edge("create_calendar_event", END)

app_graph = graph.compile(checkpointer=checkpointer)
print(graph.get_graph().draw_ascii())


@router.get("/stream")
def chat_stream(request: Request):
    thread_id = request.query_params.get("thread_id")
    def event_generator():
        for event in app_graph.stream(
            {"messages": []},
            config={"configurable": {"thread_id": thread_id}},
            stream_mode="events",
        ):
            if event["event"] == "interrupt":
                yield f"event: interrupt\ndata: {json.dumps(event['data'])}\n\n"
                return
            else:
                yield f"event: message\ndata: {json.dumps(event)}\n\n"
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"X-Thread-Id": thread_id},
    )

class ResumeRequest(BaseModel):
    thread_id: str
    input: str

@router.post("/resume")
def resume_graph(req: ResumeRequest):
    for event in app_graph.stream(
        {"messages": [HumanMessage(content=req.input)]},
        config={"configurable": {"thread_id": req.thread_id}},
        stream_mode="events",
    ):
        if event["event"] == "interrupt":
            return event["data"]
        if event["event"] == "end":
            return {"type": "done"}
    return {"type": "done"}


def retrieve_all_threads():
    all_threads = set()
    for checkpoint in checkpointer.list(None):
        if checkpoint.config and "configurable" in checkpoint.config and "thread_id" in checkpoint.config["configurable"]:
            all_threads.add(checkpoint.config["configurable"]["thread_id"])
    return list(all_threads)
