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
from langgraph.types import Command, interrupt
from langgraph.prebuilt import ToolNode, tools_condition

from langchain_core.messages import BaseMessage
from langchain.messages import AIMessage, HumanMessage, SystemMessage
from langchain.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_core.output_parsers import PydanticOutputParser

from pydantic import BaseModel, Field

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import Flow

import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

conn = sqlite3.connect(database="chatbot.db", check_same_thread=False)
checkpointer = SqliteSaver(conn=conn)

load_dotenv()

MONGO_URI = os.getenv("MONGO_URL")
HF_API_KEY = os.getenv("HUGGINGFACE_API_KEY")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

mongo = MongoClient(MONGO_URI)
db = mongo["collabryxdb"]
collection = db["embeddings"]
UsersModel = db["users"]

app = FastAPI()
router = APIRouter(prefix="/chat", tags=["Chat"])
app.include_router(router)


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
    collection=collection,
    embedding=embeddings,
    index_name="vector_index"
)


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




class ChatState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    user_email: str
    org: str
    calendar_intent: Optional[dict]

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

    rag_docs: Optional[list]
    
    email_sent: Optional[bool]
    email_error: Optional[str]






search_tool = DuckDuckGoSearchRun(region="us-en")

@tool
def calculator(expression: str) -> str:
    """Calculate mathematical expressions"""
    try:
        return str(eval(expression, {"__builtins__": {}}))
    except Exception as e:
        return f"Error: {e}"

@tool
def github_profile(username: str) -> str:
    """Get GitHub profile URL for a username"""
    import requests
    r = requests.get(f"https://api.github.com/users/{username}")
    return f"https://github.com/{username}" if r.status_code == 200 else "Not found"

@tool
def get_stock_price(symbol: str) -> dict:
    """Get stock price for a symbol (mock)"""
    return {"symbol": symbol, "price": "mock"}

@tool
def gmail_send_intent(to_hint: str, subject_hint: str, body_hint: str, cc: Optional[str] = None, bcc: Optional[str] = None):
    """Intent to send an email via Gmail"""
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
    Use this tool when we have to create or schedule some events in the calendar
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





def chat_node(state: ChatState):
    """Main chat node with LLM and tools"""
    system_prompt = SystemMessage(content=(
        "You are a helpful assistant. Use tools only when necessary. "
        "If a user wants to send an email, use gmail_send_intent. "
        "If they want to schedule a meeting, use calendar_create_intent. "
        "If they ask about documents, use doc_infoRetrieval_rag_intent."
    ))
    messages = [system_prompt] + state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


# =====================================================
# CALENDAR NODES
# =====================================================
def extract_calendar_intent(state: ChatState):
    """Extract calendar event details from user message"""
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
        return {"calendar_intent": data}
    except Exception as e:
        return {"messages": [AIMessage(content=f"I had trouble parsing that date: {e}. Could you tell me the date and time clearly?")]}


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
    return {"messages": [AIMessage(content=f"✓ Calendar event '{intent['title']}' created successfully for {intent['date']} at {intent['start_time']}")]}


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
        docs = retriever.get_relevant_documents(query)
        return {"rag_docs": docs}
    except Exception as e:
        return {"email_error": str(e), "rag_docs": []}


def rag_reframe_node(state: ChatState):
    """LLM node to answer based on retrieved documents"""
    if not state.get("rag_docs"):
        return {"messages": [AIMessage(content="No relevant information found in the documents.")]}

    context = "\n\n".join(d.page_content for d in state["rag_docs"][:3])
    question = state["messages"][-1].content
    prompt = f"""
Answer the question using ONLY the context below.
Be concise and helpful.

Context:
{context}

Question:
{question}

Answer:
"""
    try:
        answer = llm.invoke(prompt).content
        return {"messages": [AIMessage(content=answer)]}
    except Exception as e:
        return {"messages": [AIMessage(content=f"Error generating answer: {str(e)}")]}


# =====================================================
# EMAIL NODES
# =====================================================
def extract_email_info(state: ChatState):
    """Extract structured email info from tool call"""
    try:
        last_msg = state["messages"][-1]
        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
            args = last_msg.tool_calls[0]["args"]
            return {
                "to_hint": args.get("to_hint"),
                "subject_hint": args.get("subject_hint"),
                "body_hint": args.get("body_hint"),
                "cc": args.get("cc"),
                "bcc": args.get("bcc")
            }
    except Exception as e:
        return {"email_error": str(e)}
    return state


def find_recipients(state: ChatState):
    """Find eligible users in Database based on to_hint"""
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
        return {"eligible_users": users}
    except Exception as e:
        return {"email_error": str(e), "eligible_users": []}


def select_recipient(state: ChatState):
    """Handle recipient selection with interrupt for user choice or manual entry"""
    users = state.get("eligible_users", [])
    
    if not users:
        manual_email = interrupt({
            "type": "MANUAL_EMAIL_INPUT",
            "message": "No matching recipients found in your organization. Please enter the recipient's email address:"
        })
        return {"manual_email": manual_email, "selected_user": None}

    elif len(users) == 1:
        return {"selected_user": users[0], "manual_email": None}
    else:
        choice = interrupt({
            "type": "USER_CHOICE",
            "message": "Multiple recipients found. Please select one:",
            "options": [
                {
                    "index": i,
                    "username": u["username"],
                    "name": u.get("name", ""),
                    "email": u["email"]
                }
                for i, u in enumerate(users)
            ]
        })
        
        for i, u in enumerate(users):
            if choice == u["username"] or choice == str(i) or choice == u["email"]:
                return {"selected_user": u, "manual_email": None}
        return {"selected_user": users[0], "manual_email": None}


def generate_body_node(state: ChatState):
    """Generate professional email body from hints"""
    prompt = f"""Write a concise professional email.

Subject: {state['subject_hint']}
Context: {state['body_hint']}

Email body:"""
    
    try:
        email_body = llm.invoke(prompt).content
        return {"email_body": email_body}
    except Exception as e:
        return {"email_error": str(e)}


def confirm_body_node(state: ChatState):
    """Ask user to confirm or edit email body with interrupt"""
    recipient = state.get("selected_user", {}).get("email") if state.get("selected_user") else state.get("manual_email")
    confirmed = interrupt({
        "type": "EMAIL_BODY_CONFIRM",
        "message": f"Here's the email I've drafted. Would you like to send it or make changes?",
        "email_body": state.get("email_body", ""),
        "subject": state.get("subject_hint", ""),
        "recipient": recipient
    })
    
    if confirmed.lower() in ["edit", "no", "change", "modify"]:
        new_body = interrupt({
            "type": "EMAIL_BODY_EDIT",
            "message": "Please provide the corrected email body or describe the changes you'd like:",
            "current_body": state.get("email_body", "")
        })
        if len(new_body.split()) < 20:
            prompt = f"""Original email:
{state.get('email_body', '')}

User's edit request:
{new_body}

Please provide the edited email incorporating the user's changes.
Edited email:"""
            try:
                edited_body = llm.invoke(prompt).content
                return {"email_body": edited_body}
            except:
                return {"email_body": new_body}
        else:
            return {"email_body": new_body}
    return state


# =====================================================
# GMAIL AUTH
# =====================================================
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def build_gmail_oauth_flow():
    """Build Gmail OAuth flow"""
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
    """Ensure valid Gmail OAuth token exists, interrupt if needed"""
    token = state.get("gmail_access_token")
    expiry = state.get("gmail_token_expiry")
    if token and expiry:
        try:
            if datetime.fromisoformat(expiry) > datetime.now(timezone.utc):
                return state
        except:
            pass
    
    interrupt({
        "type": "GMAIL_AUTH_REQUIRED",
        "message": "Gmail authentication is required to send emails. Please authorize access.",
        "auth_start_endpoint": "/chat/gmail/auth/start"
    })
    return state


@router.get("/gmail/auth/start")
def gmail_auth_start(thread_id: str):
    """Start Gmail OAuth flow"""
    flow = build_gmail_oauth_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        state=thread_id 
    )
    return {"auth_url": auth_url}


@router.get("/gmail/auth/callback")
def gmail_auth_callback(code: str, state: str):
    """Handle Gmail OAuth callback"""
    try:
        flow = build_gmail_oauth_flow()
        flow.fetch_token(code=code)
        creds = flow.credentials
        thread_id = state 
        config = {"configurable": {"thread_id": thread_id}}
        app_graph.update_state(config, {
            "gmail_access_token": creds.token,
            "gmail_token_expiry": creds.expiry.isoformat() if creds.expiry else None
        })
        app_graph.stream(Command(resume=None), config)
        
        return {
            "success": True,
            "thread_id": thread_id,
            "message": "Authentication successful. Returning to chat..."
        }
    except Exception as e:
        return {"error": str(e)}


def send_email_node(state: ChatState):
    """Send email using Gmail API"""
    try:
        to_email = state["selected_user"]["email"] if state.get("selected_user") else state["manual_email"]
        message = f"To: {to_email}\n"
        if state.get("cc"):
            message += f"Cc: {state['cc']}\n"
        if state.get("bcc"):
            message += f"Bcc: {state['bcc']}\n"
        message += f"Subject: {state['subject_hint']}\n\n"
        message += state['email_body']
        raw = base64.urlsafe_b64encode(message.encode()).decode()
        creds = Credentials(token=state["gmail_access_token"])
        service = build("gmail", "v1", credentials=creds)
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        
        return {
            "messages": [AIMessage(content=f"✓ Email sent successfully to {to_email}!")],
            "email_sent": True
        }
    except Exception as e:
        return {
            "messages": [AIMessage(content=f"Failed to send email: {str(e)}")],
            "email_error": str(e),
            "email_sent": False
        }


# =====================================================
# GRAPH 
# =====================================================
graph = StateGraph(ChatState)

graph.add_node("chat", chat_node)
graph.add_node("tools", tool_node)

# RAG nodes
graph.add_node("docRag", rag_flow)
graph.add_node("rag_reframe", rag_reframe_node)

# Email nodes
graph.add_node("extract_email", extract_email_info)
graph.add_node("find_recipients", find_recipients)
graph.add_node("select_recipient", select_recipient)
graph.add_node("generate_body", generate_body_node)
graph.add_node("confirm_body", confirm_body_node)
graph.add_node("ensure_auth", ensure_gmail_auth)
graph.add_node("send_email", send_email_node)

# Calendar nodes
graph.add_node("extract_calendar_intent", extract_calendar_intent)
graph.add_node("create_calendar_event", create_calendar_event_node)


graph.add_edge(START, "chat")
graph.add_conditional_edges("chat", tools_condition, {"tools": "tools", "end": END})
graph.add_conditional_edges("tools", route_after_tool)

# RAG flow
graph.add_edge("docRag", "rag_reframe")
graph.add_edge("rag_reframe", END)

# Email flow - complete chain
graph.add_edge("extract_email", "find_recipients")
graph.add_edge("find_recipients", "select_recipient")
graph.add_edge("select_recipient", "generate_body")
graph.add_edge("generate_body", "confirm_body")
graph.add_edge("confirm_body", "ensure_auth")
graph.add_edge("ensure_auth", "send_email")
graph.add_edge("send_email", END)

# Calendar flow
graph.add_edge("extract_calendar_intent", "create_calendar_event")
graph.add_edge("create_calendar_event", END)
app_graph = graph.compile(checkpointer=checkpointer)


# =====================================================
# API ENDPOINTS
# =====================================================

@router.get("/stream")
def chat_stream(request: Request):
    """Stream chat responses with interrupt handling"""
    thread_id = request.query_params.get("thread_id")
    
    def event_generator():
        config = {"configurable": {"thread_id": thread_id}}
        for chunk in app_graph.stream(None, config, stream_mode="values"):
            state = app_graph.get_state(config)
            if state.next:  
                for task in state.tasks:
                    if task.interrupts:
                        for interrupt_data in task.interrupts:
                            yield f"event: interrupt\ndata: {json.dumps(interrupt_data.value)}\n\n"
                        return
            
            if "messages" in chunk and chunk["messages"]:
                last_msg = chunk["messages"][-1]
                data = {
                    "role": getattr(last_msg, "role", "assistant"),
                    "content": last_msg.content
                }
                yield f"event: message\ndata: {json.dumps(data)}\n\n"
        
        yield f"event: end\ndata: {json.dumps({'status': 'complete'})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "X-Thread-Id": thread_id,
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )


class ResumeRequest(BaseModel):
    thread_id: str
    value: str


@router.post("/resume")
def resume_graph(req: ResumeRequest):
    """Resume graph execution after an interrupt with user's response"""
    config = {"configurable": {"thread_id": req.thread_id}}
    
    try:
        result = None
        for chunk in app_graph.stream(Command(resume=req.value), config, stream_mode="values"):
            state = app_graph.get_state(config)
            if state.next:
                for task in state.tasks:
                    if task.interrupts:
                        for interrupt_data in task.interrupts:
                            return {
                                "status": "interrupted",
                                "data": interrupt_data.value
                            }
            result = chunk
        
        return {"status": "complete", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/threads/{thread_id}")
def get_thread_messages(thread_id: str):
    """Get all messages for a specific thread"""
    config = {"configurable": {"thread_id": thread_id}}
    state = app_graph.get_state(config)
    
    if not state or not state.values:
        return {"messages": []}
    
    messages = state.values.get("messages", [])
    return {
        "messages": [
            {
                "role": getattr(msg, "role", "assistant"),
                "content": msg.content
            }
            for msg in messages
        ]
    }


@router.get("/threads")
def list_all_threads():
    """List all available thread IDs"""
    all_threads = set()
    for checkpoint in checkpointer.list(None):
        if checkpoint.config and "configurable" in checkpoint.config and "thread_id" in checkpoint.config["configurable"]:
            all_threads.add(checkpoint.config["configurable"]["thread_id"])
    return {"threads": list(all_threads)}


def retrieve_all_threads():
    """Helper function to retrieve all threads"""
    all_threads = set()
    for checkpoint in checkpointer.list(None):
        if checkpoint.config and "configurable" in checkpoint.config and "thread_id" in checkpoint.config["configurable"]:
            all_threads.add(checkpoint.config["configurable"]["thread_id"])
    return list(all_threads)