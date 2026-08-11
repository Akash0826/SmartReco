# 🚀 SmartReco: Behavioral AI Recommendation Agent

SmartReco is an agentic, AI-powered course recommendation platform built for modern learning environments. It actively observes real-time user behavior (clicks, searches, views, duration), reasons over behavioral patterns using a LangGraph state machine[cite: 3], retrieves candidate courses via local vector embeddings (RAG)[cite: 3], filters out courses the user has already enrolled in, and generates personalized, persuasive learning paths accompanied by actionable course cards[cite: 3].

---

## 🌟 Architecture & Key Features

SmartReco is built following the Single Responsibility Principle (SRP) and production-ready Python asynchronous patterns[cite: 3]:

### 1. Non-Blocking Behavioral Tracking
* A lightweight Vanilla JS tracker monitors user actions (page views, course clicks, search queries) without blocking UI rendering[cite: 3].
* Flushes events asynchronously to the `/api/tracking/batch` FastAPI webhook using `navigator.sendBeacon`[cite: 3].

### 2. Dual-Write Catalog & Local Embedding Engine
* **Relational Storage:** Course details, prices, and categories are stored in PostgreSQL via SQLAlchemy 2.0 and `asyncpg`[cite: 3].
* **Local RAG Integration:** Switched to local HuggingFace embeddings (`all-MiniLM-L6-v2`, 384 dimensions) via `sentence-transformers` for 100% offline, free, and zero-latency vector generation.
* **Vector Storage:** Embedded records are dual-written to an embedded LanceDB database[cite: 3].
* **Safe Deletions:** Product deletion in `catalog_service.py` safely cascade-deletes related foreign keys in `events` and `enrollments` tables to maintain relational integrity.

### 3. Agentic Recommendation Engine (LangGraph)
The core AI engine operates as an explicit, multi-node LangGraph state machine[cite: 3]:
* **Node 1 (`analyze_behavior`):** Extracts search terms, topics, clicked categories, and course titles from user tracking events to build a rich semantic intent summary. Fallback logic handles new users with zero history[cite: 1].
* **Node 2 (`retrieve_products`):** Queries LanceDB via vector semantic search[cite: 1]. Cross-references PostgreSQL's `enrollments` table to **filter out courses the user has already joined**[cite: 1].
* **Node 3 (`generate_recommendation`):** Leverages LLMs to craft a concise, 2–3 sentence narrative explaining *why* these non-enrolled courses match the user's specific demonstrated actions[cite: 1, 2].

### 4. Interactive UI & Un-enrolled Course Cards
* **Unified Views Router:** Unified routing under `/recommended` and `/recommendations`[cite: 2].
* **Dynamic Card Hydration:** Fetches full `Product` model objects for non-enrolled candidate IDs and passes them to Jinja2 templates.
* **Direct Enrollment:** Displays course cards with course details, category tags, pricing, and direct "Enroll Now" form submit actions beneath the personalized AI narrative.

### 5. Pattern Protocol (Statistical Pattern Discovery)
* Integrates **Pattern** (*Statistical Pattern Inference & Recognition Engine*)[cite: 3]:
  * **Merlin (Discovery):** Executes unconstrained $\chi^2$ statistical tests across global user event history to discover non-obvious behavioral relationships[cite: 3].
  * **Arthur (Validation):** Stress-tests relationships using Cascading Negligence to construct a structural Jacobian matrix[cite: 3].
  * **DAG Builder:** Produces a validated Directed Acyclic Graph (DAG) used during retrieval to re-rank candidate courses based on platform-wide behavioral dependencies[cite: 3].

---

## 🛠️ Tech Stack

* **Framework & Web:** FastAPI, Uvicorn, Jinja2 Templates, Bootstrap 5 / Tailwind CSS, Vanilla JS[cite: 3]
* **AI & Agent Workflow:** LangGraph, LangChain Core, OpenAI API / Groq API[cite: 3]
* **Embeddings & Vector Search:** HuggingFace `all-MiniLM-L6-v2` (`sentence-transformers`), LanceDB (Embedded)[cite: 3]
* **Database & ORM:** PostgreSQL, Async SQLAlchemy 2.0, `asyncpg`[cite: 3]
* **Statistical Analytics:** Pattern Recognition Engine (Polars, NumPy, SciPy, NetworkX)[cite: 3]
* **Task Queuing:** Celery, Redis, APScheduler[cite: 3]

---

## 📁 Project Structure

```text
smartreco/
├── app/
│   ├── agent/
│   │   ├── nodes.py              # LangGraph workflow nodes (analyze, retrieve, generate)
│   │   ├── prompts.py            # AI system prompts and instructions
│   │   └── state.py              # AgentState definition
│   ├── api/
│   │   ├── routes_admin.py        # Admin panel product CRUD & management
│   │   ├── routes_auth.py         # Login, logout, session cookie & user lookup
│   │   ├── routes_tracking.py     # Beacon event batch collector
│   │   └── routes_views.py        # Views, homepage, catalog, and /recommended UI
│   ├── core/
│   │   ├── lancedb_client.py      # Local HuggingFace embedding & LanceDB search
│   │   ├── postgres_db.py         # Async PostgreSQL session manager
│   │   └── vector_db.py           # LanceDB table schema configuration
│   ├── models/
│   │   ├── enrollment.py          # User enrollment model
│   │   ├── event.py               # Tracking event model
│   │   ├── product.py             # Product/Course catalog model
│   │   └── user.py                # User and role definitions
│   ├── services/
│   │   ├── catalog_service.py     # Product dual-write and cascade delete logic
│   │   ├── recommendation_service.py # LangGraph agent execution & storage
│   │   └── tracking_service.py    # Event batch processor
│   └── templates/
│       ├── admin.html             # Admin dashboard
│       ├── index.html             # Home dashboard
│       ├── product_list.html      # Course catalog
│       └── recommended_courses.html # AI narrative + course cards UI
├── run.py                         # Application entrypoint
├── init_db.py                     # PostgreSQL table initialization script
└── .env                           # Environment configuration