# Collabryx

Collabryx is a next-generation AI-powered enterprise collaboration suite. Designed for modern teams, it unifies real-time code collaboration, intelligent communication, and automated agentic workflows into a single, cohesive ecosystem.

## 🚀 Key Features

### 💻 Real-Time Collaborative IDE
*   **Multi-User Editing:** Simultaneous collaborative coding environment.
*   **Language Support:** Multi-language environment with syntax highlighting and robust execution support.
*   **AI Autocomplete:** Context-aware code completion utilizing surrounding code (pre and post-pointer) to predict developer intent.

### 💬 Real-Time Chat & Collaboration
*   **Organization-Wide Hubs:** Create dedicated discussion groups for rapid problem-solving and team synchronization.
*   **Rich Media Support:** Seamless sharing of files and images, powered by **Cloudinary** and **Multer**.
*   **Data Isolation:** Built-in organization scoping ensures chat visibility is restricted to authorized members of the same organization.

### 🤖 Agentic AI Ecosystem
*   **Multi-Agent Workflow:** Powered by LangGraph and LangChain to execute complex tasks.
*   **Human-in-the-Loop (HITL):** Critical agentic workflows integrate human intervention. The AI prompts users for necessary input at key decision points, ensuring precision and control.
*   **Diverse Toolset:** Built-in agents for Email management, Google Calendar scheduling, Stock market data, and real-time News & Weather updates.
*   **Persistent Threading:** Create multiple discussion threads. Switch between them seamlessly; the AI maintains full context and memory for every individual thread, allowing you to pick up exactly where you left off.
*   **Adaptive Memory:** Persistent state management using SQLite checkpointers ensures the AI remembers conversation context across sessions.

### 🧠 Advanced RAG Pipeline
Our RAG system goes beyond standard retrieval:
*   **Relevance Scoring:** Every retrieved document is scored from 0 to 1.
    *   **Score ≥ 0.8:** Highly relevant; used directly for accurate responses.
    *   **Score 0.3 - 0.8:** Triggers a hybrid RAG + Tavily search to synthesize precise answers.
    *   **Score < 0.3:** Fallback to direct Tavily web search for maximum accuracy.
*   **Document Processing:** Automated pipeline for uploading, chunking, and vectorizing documents into MongoDB Atlas.

### 🛡️ Security & Authentication
*   **Dual-Method Auth:** Standard Email/Password + OTP verification or seamless Google OAuth.
*   **Persistent Sessions:** JWT + Cookie-based authentication with middleware-level route protection.

---

## 🏗️ Technical Architecture

### Tech Stack
*   **Frontend:** React (Web IDE & Dashboard)
*   **Backend:** Node.js
*   **AI Engine:** Python, LangGraph, LangChain, FastAPI (Uvicorn)
*   **Database:** MongoDB Atlas (Application Data + Vector Store)
*   **Storage:** Cloudinary (Media/File Handling)

---

## ⚙️ Getting Started

Ensure you have [Node.js](https://nodejs.org/) and [Python 3.x](https://www.python.org/) installed, along with a running instance of MongoDB Atlas.

### 1. Main Frontend
```bash
cd frontend
npm install
npm run dev

```

### 2. Backend API

```bash
cd backend
npm install
npm start

```

### 3. Dashboard Frontend

```bash
cd Dashboard/frontend
npm install
npm run dev

```

### 4. Dashboard AI Backend (LangGraph)

*Navigate to the AI backend directory, set up your virtual environment, and launch the service:*

```bash
cd Dashboard/AIbackend
python3 -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload

```

---

## 📂 Project Structure

```text
├── frontend/           # Primary application React frontend
├── backend/            # Primary Node.js API server
├── Dashboard/
│   ├── frontend/       # User dashboard interface
│   └── AIbackend/      # LangGraph workflows and Agent orchestration
└── ...

```

## 🔒 Security & Persistence

* **Authentication:** All routes are protected by JWT middleware.
* **State:** Conversation history and agent state are maintained using SQLite checkpointers, allowing users to resume complex tasks exactly where they left off.
