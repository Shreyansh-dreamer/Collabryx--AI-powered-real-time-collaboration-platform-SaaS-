from fastapi import FastAPI, UploadFile, File, HTTPException, Form, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from pydantic import BaseModel

import tempfile
import os

from routes import chat
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import MongoDBAtlasVectorSearch
from langchain_core.prompts import PromptTemplate  
from langchain_core.output_parsers import StrOutputParser  
from langchain_community.llms import HuggingFaceHub

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)


MONGO_URI = os.getenv("MONGO_URL")
HF_API_KEY = os.getenv("HUGGINGFACE_API_KEY")


embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    huggingfacehub_api_token=HF_API_KEY
)


vectorstore = MongoDBAtlasVectorSearch(
    collection_name="embeddings",
    embedding=embeddings,
    connection_string=MONGO_URI,
    database_name="collabryxdb",
    index_name="vector_index"
)


splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50
)



# CoPilot like feature
llm = HuggingFaceHub(
    repo_id="mistralai/Mistral-7B-Instruct-v0.2",
    huggingfacehub_api_token=HF_API_KEY,
    model_kwargs={
        "temperature": 0.15,
        "max_new_tokens": 80,
        "stop": ["\n\n"]
    }
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



# RAG
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
            "filter": {"metadata.org": org}
        }
    )
    docs = retriever.get_relevant_documents(question)
    if not docs:
        raise HTTPException(status_code=404, detail="No results")
    return {
        "answer": docs[0].page_content,
        "sources": [d.metadata for d in docs]
    }

@app.get("/threads/{thread_id}")
def get_thread_messages(thread_id: str):
    """
    Returns all saved messages for a given thread from SqliteSaver
    """
    try:
        # Retrieve all checkpoints for this thread
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