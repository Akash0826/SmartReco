Markdown
# ⚡ SmartReco: Agentic Gamified Learning Management System

SmartReco is a next-generation, event-driven Learning Management System (LMS). It transforms passive course catalogs into a dynamic, personalized learning journey by tracking user behavior in real-time, reasoning over that intent using a **LangGraph** AI agent, and generating highly contextualized, semantic recommendations via the **Mesh API**.

---

## 🏆 Hackathon Requirements Checklist

*   ✅ **Backend:** Built with FastAPI (Python) for high-performance async processing.
*   ✅ **Mesh API (Mandatory):** All LLM generation and vector embedding calls are strictly routed through the Mesh API.
*   ✅ **Vector Database Dual-Write:** Product creations/updates are atomically dual-written to **PostgreSQL** (relational) and **LanceDB** (semantic vector store).
*   ✅ **Behavioral Tracking:** Frontend JavaScript captures rich DOM interactions and batches them asynchronously (non-blocking) to the backend.
*   ✅ **Agentic Recommendation Engine:** Uses a LangGraph state machine to extract user intent, perform RAG against LanceDB, and generate persuasive narratives.
*   ✅ **No Hardcoded Secrets:** All credentials (`MESH_API_KEY`, DB URLs) are isolated in a `.gitignore`'d `.env` file.
*   ⭐ **Bonus - Structured Agent Framework:** Built using LangGraph for explicit reasoning nodes.
*   ⭐ **Bonus - Observability:** Integrated with LangSmith for end-to-end LLM trace transparency.

---

## 🏗️ Framework Architecture & Data Flow

### [ 1. ASYNCHRONOUS INGRESS LAYER (Behavioral Tracking) ]
*   **tracker.js** instantly captures behavioral interactions (Clicks, Views, Dwell Time).
*   Pushes payloads to a Frontend Event Queue (Bypasses Main Thread Blocking).
*   `routes_tracking.py` (FastAPI) picks up batched tasks via a 5-second interval POST Webhook (`202 Accepted`).

### [ 2. STATE & GAMIFICATION LAYER (Memory) ]
*   **Core PostgreSQL Database:** Stores Users, Products, Events, and Recommendations.
*   **Gamification Engine:** Evaluates behavioral telemetry against activity thresholds to trigger the AI Agent without wasting LLM compute on every click.

### [ 3. REASONING & GUARDRAIL LAYER (LangGraph / Mesh API) ]
*   **Abstracted LLM Pipeline (Agent Executor):**
    *   **Node 1 (Analyze):** Ingests the behavioral subgraph (Recent clicks) and extracts user intent.
    *   **Node 2 (Retrieve):** Traverses the LanceDB vector catalog using Mesh API embeddings to find optimal matches (RAG).
    *   **Node 3 (Generate):** Uses Mesh API LLMs to generate a persuasive, personalized narrative.

### [ 4. OPTIMIZATION & STORAGE LAYER (Dual-Write) ]
*   **Catalog Service:** Guarantees that any product added or edited by an Admin is atomically written to both PostgreSQL (for UI rendering) and LanceDB (for AI semantic search).

### [ 5. OUTPUT LAYER (Server-Side Rendering) ]
*   `routes_views.py` (Jinja2) retrieves the structured recommendation JSON from PostgreSQL.
*   Injects personalized dashboard components upon user page navigation or refresh.

---

## 🚀 Getting Started (Local Setup)

### Prerequisites
*   Python 3.10+
*   PostgreSQL running locally or via Docker

### Installation & Setup

**1. Set up the virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt

**2. Configure Environment Variables:**
Create a .env file in the root directory. Do not commit this file.

# Database Configurations
DATABASE_URL=postgresql+asyncpg://user:password@localhost/smartreco
LANCEDB_URI=./.lancedb_data
VECTOR_DIMENSION=1536

# Mesh API (MANDATORY)
MESH_API_KEY=your_mesh_api_key_here
MESH_API_BASE_URL=[https://api.mesh.ai/v1](https://api.mesh.ai/v1)
LLM_MODEL=llama-3.1-8b-instant

# LangSmith Observability (Bonus Implementation)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT="[https://api.smith.langchain.com](https://api.smith.langchain.com)"
LANGCHAIN_API_KEY=your_langsmith_key

**3. Initialize the Database:**
This script creates the PostgreSQL tables and injects a mock user (ID: 1) to bypass complex auth flows for testing.

python seed.py

**4. Run the Application:**

python run.py

🧭 Navigation
Main Dashboard: http://localhost:8000/

Admin Panel: http://localhost:8000/admin

Login Shortcut: http://localhost:8000/login

📁 Repository Structure

SMARTRECO/
├── app/
│   ├── api/                 # FastAPI routes (Tracking, Views, Auth, Admin)
│   ├── core/                # Config, Postgres DB, and LanceDB/Mesh clients
│   ├── models/              # SQLAlchemy schemas (User, Product, Event, Recommendation)
│   ├── services/            # Business logic (Tracking logic, Catalog dual-writes)
│   ├── agent/               # LangGraph Workflow and Nodes
│   ├── templates/           # Jinja2 HTML views (index, feed, login)
│   └── static/              # CSS animations and JS tracker
├── seed.py                  # Database initialization script
├── run.py                   # Uvicorn entry point
├── requirements.txt         # Dependency map
└── .gitignore               # Credential and DB protection