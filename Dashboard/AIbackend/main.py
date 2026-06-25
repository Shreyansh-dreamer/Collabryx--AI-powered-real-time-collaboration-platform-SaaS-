from fastapi import FastAPI, UploadFile, File, HTTPException, Form, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from pydantic import BaseModel
from langchain_groq import ChatGroq

import tempfile
import os
import sqlite3

from routes import chat
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_core.prompts import PromptTemplate  
from langchain_core.output_parsers import StrOutputParser  
from langchain_huggingface import HuggingFaceEndpoint
from langgraph.checkpoint.sqlite import SqliteSaver

conn = sqlite3.connect(database="chatbot.db", check_same_thread=False)
checkpointer = SqliteSaver(conn=conn)

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "http://localhost:8501"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)

from dotenv import load_dotenv
import os

load_dotenv()


MONGO_URI = os.getenv("MONGO_URL")
GROQ_API_KEY = os.getenv("GROQ-API-KEY")

print("="*50)
print(f"GROQ_API_KEY exists: {GROQ_API_KEY is not None}")
print(f"GROQ_API_KEY length: {len(GROQ_API_KEY) if GROQ_API_KEY else 0}")
print(f"GROQ_API_KEY starts with 'gsk_': {GROQ_API_KEY.startswith('gsk_') if GROQ_API_KEY else False}")
print(f"First 10 chars: {GROQ_API_KEY[:10] if GROQ_API_KEY else 'NONE'}")
print("="*50)


embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
    # huggingfacehub_api_token=HF_API_KEY
)

mongo = MongoClient(MONGO_URI)
db = mongo["collabryxdb"]
collection = db["embeddings"]

vectorstore = MongoDBAtlasVectorSearch(
    collection=collection,
    embedding=embeddings,
    index_name="vector_index"
)


splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50
)

@app.on_event("startup")
def warmup():
    embeddings.embed_query("warmup")

@app.get("/")
def health():
    return {"status": "AI backend running"}



llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=GROQ_API_KEY,
    temperature=0.1,  
)

class CodeCompletionRequest(BaseModel):
    language: str
    prefix: str
    suffix: str | None = ""


@app.post("/ai/complete")
async def ai_complete(req: CodeCompletionRequest):
    copilot_prompt = PromptTemplate.from_template("""
    You are a code completion engine.
    Rules:
    - Output ONLY valid {language} code
    - Do NOT explain
    - Do NOT use markdown
    - Do NOT repeat input
    Code before cursor:
    {prefix}
    Code after cursor:
    {suffix}
    Completion:
    """)
    completion_chain = ( copilot_prompt | llm | StrOutputParser())
    completion = completion_chain.invoke({
        "language": req.language,
        "prefix": req.prefix,
        "suffix": req.suffix or ""
    })
    return {"completion": completion.strip()}




@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...),org: str = Form(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDFs allowed")
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Max file size is 10MB")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(contents)
        temp_path = tmp.name
    try:
        loader = PyPDFLoader(temp_path)
        docs = loader.load()
    finally:
        os.remove(temp_path)
    chunks = splitter.split_documents(docs)
    texts = [c.page_content for c in chunks]
    metadatas = [{"org": org} for _ in texts]
    vectorstore.add_texts(texts=texts, metadatas=metadatas)
    return {"chunks_added": len(texts)}


@app.post("/query")
async def query_rag(question: str = Form(...),org: str = Form(...)):
    retriever = vectorstore.as_retriever(
        search_kwargs={
            "k": 5,
            "filter": {"org": org}
        }
    )
    docs = retriever.get_relevant_documents(question)
    if not docs:
        raise HTTPException(status_code=404, detail="No results")
    
    context = "\n\n".join(d.page_content for d in docs[:3])
    try:
        prompt = (
            f"You are a helpful assistant. Use the following document context to answer the user's question.\n"
            f"Please generate a complete, helpful, and natural answer related to the actual question asked, based on the documents.\n"
            f"If the context does not contain the answer, answer generally or say you cannot find it in the documents.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\n\n"
            f"Answer:"
        )
        answer = llm.invoke(prompt).content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM generation failed: {e}")
        
    return {
        "answer": answer,
        "sources": [d.metadata for d in docs]
    }

@app.get("/threads/{thread_id}")
def get_thread_messages(thread_id: str):
    """
    Returns all saved messages for a given thread from SqliteSaver
    """
    try:
        checkpoints = checkpointer.list(
            {"configurable.thread_id": thread_id}
        )
        messages = []
        for cp in checkpoints:
            state = cp.state
            msgs = state.get("messages", [])
            messages.extend([{"role": m.role, "content": m.content} for m in msgs])
        return {"messages": messages}
    except Exception as e:
        return {"messages": [], "error": str(e)}