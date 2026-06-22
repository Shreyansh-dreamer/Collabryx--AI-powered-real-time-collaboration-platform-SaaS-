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
from fastapi.responses import HTMLResponse
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
from google.auth.transport.requests import Request as GoogleRequest

import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from tavily import TavilyClient

load_dotenv()

conn         = sqlite3.connect(database="chatbot.db", check_same_thread=False)
checkpointer = SqliteSaver(conn=conn)

MONGO_URI            = os.getenv("MONGO_URL")
GROQ_API_KEY         = os.getenv("GROQ-API-KEY")
GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI  = os.getenv("GOOGLE_REDIRECT_URI")
TAVILY_API_KEY       = os.getenv("TAVILY_API_KEY")

mongo      = MongoClient(MONGO_URI)
db_mongo   = mongo["collabryxdb"]
collection = db_mongo["embeddings"]
UsersModel = db_mongo["users"]

_pending_messages: dict = {}
_pending_resumes:  dict = {}

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501","http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
router = APIRouter(prefix="/chat", tags=["Chat"])
app.include_router(router)

llm         = ChatGroq(model="llama-3.3-70b-versatile", api_key=GROQ_API_KEY, temperature=0.2)
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

class DocRelevance(BaseModel):
    index: int = Field(description="The 0-based index of the document being evaluated.")
    score: float = Field(description="Relevance confidence score between 0.00 and 1.00.")

class RelevanceEvaluation(BaseModel):
    evaluations: List[DocRelevance] = Field(description="List of document relevance evaluations.")

relevance_parser = PydanticOutputParser(pydantic_object=RelevanceEvaluation)

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
def gmail_send_intent(to_hint: str, subject_hint: str, body_hint: str,cc: Optional[str] = None, bcc: Optional[str] = None,):
    """Intent to send an email via Gmail."""
    return {"to_hint": to_hint, "subject_hint": subject_hint,
            "body_hint": body_hint, "cc": cc, "bcc": bcc}

@tool
def doc_infoRetrieval_rag_intent(question: str) -> str:
    """Use this tool for question answering from stored documents."""
    return "RAG_QUERY"

@tool
def calendar_create_intent(message: str) -> str:
    """Use this tool when the user wants to schedule, create, add, or mark an event/meeting/appointment in Google Calendar. Input parameter 'message' must contain the user's event request details."""
    return "CALENDAR_CREATE"

@tool
def web_search(message:str)->str:
    """Use this tool to get information from the web."""
    tavily = TavilyClient(api_key=TAVILY_API_KEY)
    results = tavily.search(query=message)
    return results['results']

tools = [search_tool, calculator, github_profile, get_stock_price, gmail_send_intent, # doc_infoRetrieval_rag_intent,
         calendar_create_intent, web_search]
llm_with_tools = llm.bind_tools(tools)
tool_node = ToolNode(tools)

def chat_node(state: ChatState):
    system_prompt = SystemMessage(content=(
        "You are Collabryx AI, a highly capable assistant. "
        "A document retrieval search has already run in the background and found no highly relevant organization documents. "
        "Therefore, you must answer the user's questions using either your internal weights (pre-trained knowledge) or one of the available tools.\n\n"
        
        "RULES FOR ANSWERING AND TOOL USAGE:\n"
        "1. Check if you can fully and accurately answer the user's query using your internal knowledge weights. If so, answer directly and professionally.\n"
        "2. If you lack the required details, if the query requests real-time/recent information, or if you need to verify facts, you MUST use the `web_search` tool (powered by Tavily) to fetch the latest details from the web. Do not guess or hallucinate.\n"
        "3. You have access to the following tools, which you MUST use under the specified circumstances:\n"
        "   - `web_search`: Use this to query the web for real-time information, recent developments, or general search queries.\n"
        "   - `gmail_send_intent`: Use this tool when the user wants to write, draft, or send an email.\n"
        "   - `calendar_create_intent`: Use this tool when the user wants to schedule, create, add, or mark a meeting, event, or appointment in Google Calendar. Do NOT print dates, times, or JSON; call it silently.\n"
        "   - `calculator`: Use this tool to perform mathematical or arithmetic calculations.\n"
        "   - `github_profile`: Use this tool to lookup GitHub profile URLs for a given username.\n"
        "   - `get_stock_price`: Use this tool to query stock prices for a ticker symbol.\n"
        "   - `search_tool`: General search tool (DuckDuckGo search) if needed as a secondary fallback.\n\n"
        
        "TOOL CALLING PROTOCOL:\n"
        "- Call the tool directly and silently without any prefix, suffix, explanation, conversational thoughts, or JSON wrappers. Just invoke the tool call.\n"
        "- Do NOT write any conversational text before or after calling a tool."
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
        
        tz_settings = {"PREFER_DATES_FROM": "future", "TIMEZONE": "Asia/Kolkata", "RETURN_AS_TIMEZONE_AWARE": False}
        
        start_dt = None
        try:
            start_dt = datetime.fromisoformat(f"{data['date']}T{data['start_time']}")
        except Exception:
            pass
            
        if not start_dt:
            start_dt = dateparser.parse(f"{data['date']} {data['start_time']}", settings=tz_settings)
            
        if not start_dt:
            parsed_date = dateparser.parse(data['date'], settings=tz_settings)
            parsed_time = dateparser.parse(data['start_time'], settings=tz_settings)
            if parsed_date and parsed_time:
                start_dt = datetime.combine(parsed_date.date(), parsed_time.time())
            elif parsed_date:
                start_dt = datetime.combine(parsed_date.date(), datetime.strptime("09:00", "%H:%M").time())
            else:
                start_dt = datetime.combine(datetime.now().date(), datetime.strptime("09:00", "%H:%M").time())
                
        end_dt = None
        duration = data.get("duration_minutes") or 60
        
        if data.get("end_time"):
            try:
                end_dt = datetime.fromisoformat(f"{data['date']}T{data['end_time']}")
            except Exception:
                pass
                
            if not end_dt:
                end_dt = dateparser.parse(f"{data['date']} {data['end_time']}", settings=tz_settings)
                
            if not end_dt:
                parsed_end_time = dateparser.parse(data['end_time'], settings=tz_settings)
                if parsed_end_time:
                    end_dt = datetime.combine(start_dt.date(), parsed_end_time.time())
                    
            if end_dt and end_dt <= start_dt:
                if (end_dt - start_dt).days < 0:
                    end_dt += timedelta(days=1)
                    
        if not end_dt:
            end_dt = start_dt + timedelta(minutes=duration)
            
        data["date"] = start_dt.date().isoformat()
        data["start_time"] = start_dt.time().strftime("%H:%M")
        data["end_date"] = end_dt.date().isoformat()
        data["end_time"] = end_dt.time().strftime("%H:%M")
        
        return {"calendar_intent": data}
    except Exception as e:
        try:
            fallback_dt = dateparser.parse(last_human_content, settings={"PREFER_DATES_FROM": "future", "TIMEZONE": "Asia/Kolkata"})
            if fallback_dt:
                data = {
                    "title": "Calendar Event",
                    "date": fallback_dt.date().isoformat(),
                    "start_time": fallback_dt.time().strftime("%H:%M"),
                    "end_date": fallback_dt.date().isoformat(),
                    "end_time": (fallback_dt + timedelta(hours=1)).time().strftime("%H:%M"),
                    "description": f"Created from chat: {last_human_content}"
                }
                return {"calendar_intent": data}
        except Exception:
            pass
            
        return {"messages": [AIMessage(
            content=f"I had trouble parsing that date: {e}. Could you give me the date and time clearly?"
        )]}

def get_google_credentials(state: ChatState):
    user_email = state.get("user_email")
    refresh_token = None
    if user_email:
        try:
            user_doc = UsersModel.find_one({"email": user_email})
            if user_doc:
                refresh_token = user_doc.get("refreshToken") or user_doc.get("googleRefreshToken")
        except Exception as e:
            print(f"Error querying user's refresh token from MongoDB: {e}")

    creds = Credentials(
        token=state.get("gmail_access_token"),
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
    )
    
    if refresh_token and not creds.valid:
        try:
            creds.refresh(GoogleRequest())
        except Exception as e:
            print(f"Error refreshing google credentials: {e}")
            
    return creds

def create_calendar_event_node(state: ChatState):
    intent = state.get("calendar_intent")
    if not intent:
        return {"messages": [AIMessage(content="Could not mark the event because the calendar intent was not successfully extracted.")]}
    try:
        tz       = pytz.timezone("Asia/Kolkata")
        start_date = intent.get("date")
        start_time = intent.get("start_time")
        
        start_dt = tz.localize(datetime.fromisoformat(f"{start_date}T{start_time}"))
        
        end_date = intent.get("end_date") or start_date
        end_time = intent.get("end_time")
        
        if end_time:
            end_dt = tz.localize(datetime.fromisoformat(f"{end_date}T{end_time}"))
        else:
            duration = intent.get("duration_minutes") or 60
            end_dt = start_dt + timedelta(minutes=duration)
            
        creds   = get_google_credentials(state)
        service = build("calendar", "v3", credentials=creds)
        event   = {
            "summary":     intent.get("title", "Meeting"),
            "description": intent.get("description"),
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Kolkata"},
            "end":   {"dateTime": end_dt.isoformat(),   "timeZone": "Asia/Kolkata"},
        }
        service.events().insert(calendarId="primary", body=event).execute()
        return {"messages": [AIMessage(
            content=f"Event has been marked: '{intent.get('title')}' on {intent.get('date')} at {intent.get('start_time')}"
        )]}
    except Exception as e:
        print(f"Error creating calendar event: {e}")
        return {"messages": [AIMessage(
            content=f"Failed to mark the event in Google Calendar: {str(e)}"
        )]}

def route_after_tool(state: ChatState) -> str:
    for msg in reversed(state["messages"]):
        if getattr(msg, "type", None) == "ai" and getattr(msg, "tool_calls", None):
            name = msg.tool_calls[0]["name"]
            if name == "gmail_send_intent":            return "extract_email"
            # if name == "doc_infoRetrieval_rag_intent": return "docRag"
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
            search_kwargs={"k": 5, "pre_filter": {"org": {"$eq": state["org"]}}}
        )
        docs = retriever.invoke(query)
        return {"rag_docs": docs}
    except Exception as e:
        return {"email_error": str(e), "rag_docs": []}

def rag_reframe_node(state: ChatState):
    if not state.get("rag_docs"):
        return {"messages": [AIMessage(content="No relevant information found in the documents.")]}
    
    context = "\n\n".join(d.page_content for d in state["rag_docs"][:3])
    
    question = ""
    for msg in reversed(state["messages"]):
        if getattr(msg, "type", None) == "human":
            question = msg.content
            break
            
    try:
        prompt = (
            f"You are a helpful assistant. Use the following document context to answer the user's question.\n"
            f"Please generate a complete, helpful, and natural answer related to the actual question asked, based strictly on the context provided.\n"
            f"Do not mention the source documents, their relevance scores, or metadata in your answer.\n"
            f"If the context does not contain the answer, answer generally and use your own knowledge base.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\n\n"
            f"Answer:"
        )
        answer = llm.invoke(prompt).content
        return {"messages": [AIMessage(content=answer)]}
    except Exception as e:
        return {"messages": [AIMessage(content=f"Error: {e}")]}

import re

def check_rag_node(state: ChatState):
    query = ""
    for msg in reversed(state["messages"]):
        if getattr(msg, "type", None) == "human":
            query = msg.content
            break
    if not query:
        return {"rag_docs": []}
    
    try:
        retriever = vectorstore.as_retriever(
            search_kwargs={"k": 10, "pre_filter": {"org": {"$eq": state["org"]}}}
        )
        results = retriever.invoke(query)
        if not results:
            return {"rag_docs": []}

        system_prompt = (
            "You are a strict JSON generator. "
            "Evaluate the relevance of retrieved documents to the user query. "
            "Output ONLY a JSON object that matches the requested schema."
            "Do not include any explanation, conversational text, or reasoning."
            "Do not include the eveluations in the response"
            "Do not include anything like the relevance of each document towards the users querry, and dont show that in the output"
        )

        user_content = f"User Query: {query}\n\n"
        for idx, doc in enumerate(results):
            user_content += f"--- Document {idx} ---\nContent: {doc.page_content}\n\n"
        user_content += f"\n{relevance_parser.get_format_instructions()}"

        response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_content)]).content.strip()

        # Robust extraction: look for the first '{' and last '}'
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            cleaned_response = json_match.group(0)
        else:
            cleaned_response = response

        parsed = relevance_parser.parse(cleaned_response)
        
        good_docs = []
        for item in parsed.evaluations:
            idx = item.index
            score = item.score
            if idx is not None and 0 <= idx < len(results) and score > 0.70:
                # Create a shallow copy and strip the relevance score
                doc = results[idx].copy()
                doc.metadata.pop("relevance_score", None) 
                good_docs.append(doc)

        # Sort good_docs by score (if you have the score available in your logic)
        # Note: Since we stripped it, you might want to sort BEFORE stripping
        
        # Return ONLY the rag_docs update. 
        # Do NOT include "messages" key so the LLM reasoning doesn't show in chat.
        return {"rag_docs": good_docs}

    except Exception as e:
        print(f"RAG check error: {e}")
        return {"rag_docs": []}

def route_after_check_rag(state: ChatState) -> str:
    if state.get("rag_docs"):
        return "rag_reframe"
    return "chat"

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
    user_email = state.get("user_email")
    if user_email:
        try:
            user_doc = UsersModel.find_one({"email": user_email})
            if user_doc and (user_doc.get("refreshToken") or user_doc.get("googleRefreshToken")):
                creds = get_google_credentials(state)
                if creds and creds.valid:
                    return {
                        "gmail_access_token": creds.token,
                        "gmail_token_expiry": creds.expiry.isoformat() if creds.expiry else None
                    }
        except Exception as e:
            print(f"Error checking/refreshing Gmail auth from DB: {e}")

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
    if not state.get("calendar_intent"):
        return {}
    user_email = state.get("user_email")
    if user_email:
        try:
            user_doc = UsersModel.find_one({"email": user_email})
            if user_doc and (user_doc.get("refreshToken") or user_doc.get("googleRefreshToken")):
                creds = get_google_credentials(state)
                if creds and creds.valid:
                    return {
                        "gmail_access_token": creds.token,
                        "gmail_token_expiry": creds.expiry.isoformat() if creds.expiry else None
                    }
        except Exception as e:
            print(f"Error checking/refreshing Calendar auth from DB: {e}")

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
    try:
        flow = build_gmail_oauth_flow()
        flow.fetch_token(code=code)
        creds     = flow.credentials
        token     = creds.token
        expiry    = creds.expiry.isoformat() if creds.expiry else ""
        thread_id = state

        config = {"configurable": {"thread_id": thread_id}}
        
        # Save the refresh token to database if available
        thread_state = app_graph.get_state(config)
        user_email = thread_state.values.get("user_email") if (thread_state and thread_state.values) else None
        if user_email and creds.refresh_token:
            try:
                UsersModel.update_one(
                    {"email": user_email},
                    {"$set": {"refreshToken": creds.refresh_token}}
                )
            except Exception as mongo_err:
                print(f"Error saving refresh token to MongoDB for user {user_email}: {mongo_err}")

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
        creds   = get_google_credentials(state)
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

graph.add_node("check_rag",check_rag_node)
graph.add_node("chat",chat_node)
graph.add_node("tools",tool_node)
graph.add_node("docRag",rag_flow)
graph.add_node("rag_reframe",rag_reframe_node)
graph.add_node("extract_email",extract_email_info)
graph.add_node("find_recipients",find_recipients)
graph.add_node("select_recipient",select_recipient)
graph.add_node("generate_body",generate_body_node)
graph.add_node("confirm_body",confirm_body_node)
graph.add_node("ensure_auth",ensure_gmail_auth)
graph.add_node("ensure_calendar_auth",ensure_calendar_auth)
graph.add_node("send_email",send_email_node)
graph.add_node("extract_calendar_intent",extract_calendar_intent)
graph.add_node("create_calendar_event",create_calendar_event_node)

graph.add_edge(START,"check_rag")
graph.add_conditional_edges(
    "check_rag",route_after_check_rag,
    {"rag_reframe":"rag_reframe","chat":"chat"}
)
graph.add_conditional_edges("chat",tools_condition,{"tools":"tools",END:END})
graph.add_conditional_edges(
    "tools",route_after_tool,
    {"extract_email":"extract_email", # "docRag":"docRag",
     "extract_calendar_intent":"extract_calendar_intent","chat":"chat"}
)
graph.add_edge("docRag","rag_reframe")
graph.add_edge("rag_reframe",END)
graph.add_edge("extract_email","find_recipients")
graph.add_edge("find_recipients","select_recipient")
graph.add_edge("select_recipient","generate_body")
graph.add_edge("generate_body","confirm_body")
graph.add_edge("confirm_body","ensure_auth")
graph.add_edge("ensure_auth","send_email")
graph.add_edge("send_email",END)
graph.add_edge("extract_calendar_intent","ensure_calendar_auth")
graph.add_edge("ensure_calendar_auth","create_calendar_event")
graph.add_edge("create_calendar_event",END)

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