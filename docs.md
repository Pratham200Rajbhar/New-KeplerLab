# KeplerLab AI Notebook — Complete Project Documentation

> **Version**: 2.0.0 | **Last Updated**: February 2026  
> An AI-powered learning platform that transforms educational materials into interactive study experiences.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Directory Structure](#4-directory-structure)
5. [Backend — Deep Dive](#5-backend--deep-dive)
   - 5.1 [Application Startup & Lifespan](#51-application-startup--lifespan)
   - 5.2 [Configuration System](#52-configuration-system)
   - 5.3 [Database Layer](#53-database-layer)
   - 5.4 [Authentication & Security](#54-authentication--security)
   - 5.5 [Material Ingestion Pipeline](#55-material-ingestion-pipeline)
   - 5.6 [Background Worker & Job Queue](#56-background-worker--job-queue)
   - 5.7 [RAG System (Retrieval-Augmented Generation)](#57-rag-system-retrieval-augmented-generation)
   - 5.8 [LangGraph Agent System](#58-langgraph-agent-system)
   - 5.9 [LLM Provider Abstraction](#59-llm-provider-abstraction)
   - 5.10 [Content Generation Services](#510-content-generation-services)
   - 5.11 [WebSocket Manager](#511-websocket-manager)
   - 5.12 [API Routes Reference](#512-api-routes-reference)
   - 5.13 [Middleware Stack](#513-middleware-stack)
6. [Frontend — Deep Dive](#6-frontend--deep-dive)
   - 6.1 [Application Structure](#61-application-structure)
   - 6.2 [Routing & Navigation](#62-routing--navigation)
   - 6.3 [Context & State Management](#63-context--state-management)
   - 6.4 [Key Components](#64-key-components)
   - 6.5 [API Layer](#65-api-layer)
7. [Data Models (Prisma Schema)](#7-data-models-prisma-schema)
8. [End-to-End Data Flows](#8-end-to-end-data-flows)
   - 8.1 [User Registration & Login](#81-user-registration--login)
   - 8.2 [Material Upload & Processing](#82-material-upload--processing)
   - 8.3 [RAG Chat Flow](#83-rag-chat-flow)
   - 8.4 [Quiz Generation](#84-quiz-generation)
   - 8.5 [Presentation (PPT) Generation](#85-presentation-ppt-generation)
   - 8.6 [Podcast Generation](#86-podcast-generation)
   - 8.7 [Explainer Video Flow](#87-explainer-video-flow)
9. [Security Architecture](#9-security-architecture)
10. [Configuration Reference](#10-configuration-reference)
11. [Infrastructure & Deployment](#11-infrastructure--deployment)
12. [Performance Characteristics](#12-performance-characteristics)
13. [Troubleshooting & FAQs](#13-troubleshooting--faqs)

---

## 1. Project Overview

KeplerLab AI Notebook is a **multi-tenant, full-stack AI learning platform**. Users upload educational materials in any format (PDF, DOCX, PPTX, audio, video, web pages, YouTube videos) and the platform automatically:

- Extracts and indexes text from all source types.
- Enables **conversational question-answering** grounded in the uploaded content via a RAG-powered agent.
- Auto-generates **quizzes**, **flashcard decks**, **PowerPoint presentations**, **audio podcasts**, and narrated **explainer videos**.
- Runs code, performs data analysis, and can do web research — all within the same chat interface.

The system enforces strict **per-user data isolation**: every query to ChromaDB is filtered by `user_id` so one user can never see another user's data.

---

## 2. High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         Browser (React SPA)                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐ │
│  │ AuthPage │  │ HomePage │  │ Sidebar  │  │ ChatPanel/StudioPanel│ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────────┘ │
└──────────────────────────┬────────────────────────────────────────────┘
                           │  REST / SSE / WebSocket
┌──────────────────────────▼────────────────────────────────────────────┐
│                      FastAPI Backend (Python 3.11)                    │
│                                                                       │
│  ┌─────────────────────────────── Middleware ──────────────────────┐  │
│  │  Performance Logger │ Rate Limiter │ CORS │ Request Logger      │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌──────────────────────────────── Routes ────────────────────────┐  │
│  │ /auth  /notebooks  /upload  /chat  /quiz  /flashcard  /ppt     │  │
│  │ /jobs  /models  /search  /agent  /explainer  /proxy  /ws       │  │
│  └─────────────────────────┬──────────────────────────────────────┘  │
│                             │                                         │
│  ┌──────────────────────────▼──────────────────────────────────────┐ │
│  │                        Services Layer                           │ │
│  │                                                                 │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐ │ │
│  │  │  LangGraph   │  │   RAG Stack  │  │   Generation Services │ │ │
│  │  │    Agent     │  │  (ChromaDB)  │  │ Quiz/Flash/PPT/Podcast│ │ │
│  │  └──────────────┘  └──────────────┘  └───────────────────────┘ │ │
│  │                                                                 │ │
│  │  ┌──────────────┐  ┌───────────────┐  ┌──────────────────────┐ │ │
│  │  │ LLM Service  │  │  Text Process │  │  Background Worker   │ │ │
│  │  │ (multi-llm)  │  │  (OCR/ASR/   │  │  (Async Job Queue)   │ │ │
│  │  │              │  │   Scraping)   │  │                      │ │ │
│  │  └──────────────┘  └───────────────┘  └──────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└──────────┬──────────────────────────────────┬─────────────────────────┘
           │                                  │
 ┌─────────▼──────────┐             ┌─────────▼──────────┐
 │   PostgreSQL        │             │      ChromaDB       │
 │  (via Prisma ORM)   │             │  (Vector Database)  │
 │  Users, Materials,  │             │  Text chunks with   │
 │  Notebooks, Jobs,   │             │  384-dim embeddings │
 │  Generated Content  │             │  + metadata filters │
 └────────────────────┘             └────────────────────┘
                                              │
                                    ┌─────────▼──────────┐
                                    │   File System       │
                                    │  /data/uploads      │
                                    │  /data/material_text│
                                    │  /output/           │
                                    └────────────────────┘
```

---

## 3. Technology Stack

### Backend
| Component | Technology | Version |
|-----------|-----------|---------|
| Web Framework | FastAPI | 0.115.6 |
| Runtime | Python | 3.11+ |
| ASGI Server | Uvicorn | 0.30.6 |
| ORM | Prisma (Python client) | asyncio interface |
| Database | PostgreSQL | 15+ |
| Vector DB | ChromaDB | 0.5.5 |
| LLM Orchestration | LangChain + LangGraph | 0.2.16 / ≥0.2.0 |
| Embeddings | ChromaDB ONNX (MiniLM-L6-v2, 384-dim) | built-in |
| Reranker | BAAI/bge-reranker-large | via Sentence Transformers |
| LLM Providers | Ollama, Google Gemini, NVIDIA AI, Custom | — |
| Audio Transcription | OpenAI Whisper | — |
| OCR | Tesseract + EasyOCR | — |
| TTS / Podcast | edge-tts | ≥6.1.0 |
| PDF Extraction | PyMuPDF, pdfplumber, pypdf | — |
| Browser Automation | Playwright | 1.40.0 |
| Data Validation | Pydantic v2 | 2.9.2 |

### Frontend
| Component | Technology | Version |
|-----------|-----------|---------|
| UI Framework | React | 19.2.0 |
| Router | React Router | 7.11.0 |
| Styling | Tailwind CSS | 3.4.19 |
| Build Tool | Vite | 7.2.4 |
| Web Server (prod) | NGINX | — |

### Infrastructure
| Component | Technology |
|-----------|-----------|
| Containerization | Docker + Docker Compose |
| Reverse Proxy (prod) | NGINX |
| Caching (optional) | Redis |

---

## 4. Directory Structure

```
KeplerLab-AI-Notebook/
│
├── README.md                      # Quick-start guide
├── docs.md                        # ← This file (complete documentation)
│
├── backend/
│   ├── requirements.txt           # Python dependencies
│   ├── prisma/
│   │   └── schema.prisma          # Database schema & Prisma config
│   ├── app/
│   │   ├── main.py                # FastAPI app, middleware, lifespan
│   │   ├── core/
│   │   │   ├── config.py          # Pydantic settings (env-var based)
│   │   │   └── utils.py           # Shared helpers
│   │   ├── db/
│   │   │   ├── prisma_client.py   # DB connect/disconnect
│   │   │   └── chroma.py          # ChromaDB collection accessor
│   │   ├── models/                # Pydantic response/request models
│   │   ├── prompts/               # LLM prompt templates (*.txt)
│   │   │   ├── chat_prompt.txt
│   │   │   ├── quiz_prompt.txt
│   │   │   ├── flashcard_prompt.txt
│   │   │   ├── ppt_prompt.txt
│   │   │   ├── data_analysis_prompt.txt
│   │   │   └── code_generation_prompt.txt
│   │   ├── routes/                # FastAPI routers
│   │   │   ├── auth.py            # /auth/*
│   │   │   ├── notebook.py        # /notebooks
│   │   │   ├── upload.py          # /upload, /materials
│   │   │   ├── chat.py            # /chat
│   │   │   ├── quiz.py            # /quiz
│   │   │   ├── flashcard.py       # /flashcard
│   │   │   ├── ppt.py             # /ppt
│   │   │   ├── jobs.py            # /jobs
│   │   │   ├── health.py          # /health
│   │   │   ├── agent.py           # /agent
│   │   │   ├── explainer.py       # /explainer
│   │   │   ├── search.py          # /search
│   │   │   ├── proxy.py           # /proxy
│   │   │   ├── models.py          # /models
│   │   │   └── websocket_router.py # /ws
│   │   └── services/
│   │       ├── worker.py          # Async background job processor
│   │       ├── material_service.py# Upload/process/delete materials
│   │       ├── notebook_service.py# CRUD for notebooks
│   │       ├── job_service.py     # BackgroundJob CRUD
│   │       ├── storage_service.py # File system text storage
│   │       ├── ws_manager.py      # WebSocket connection manager
│   │       ├── rate_limiter.py    # Token-bucket rate limiting
│   │       ├── performance_logger.py
│   │       ├── audit_logger.py
│   │       ├── token_counter.py   # Token estimation & tracking
│   │       ├── file_validator.py  # Security validation for uploads
│   │       ├── gpu_manager.py     # GPU detection/management
│   │       ├── model_manager.py   # Downloaded model management
│   │       ├── auth/              # JWT, bcrypt, token rotation
│   │       ├── agent/             # LangGraph agent system
│   │       │   ├── graph.py       # StateGraph wiring
│   │       │   ├── state.py       # AgentState TypedDict
│   │       │   ├── intent.py      # Intent detection
│   │       │   ├── planner.py     # Execution planning
│   │       │   ├── router.py      # Tool routing
│   │       │   ├── reflection.py  # Should-continue logic
│   │       │   ├── tools_registry.py  # All agent tools
│   │       │   └── tools/             # Individual tool implementations
│   │       ├── chat/              # Chat orchestration service
│   │       ├── rag/               # RAG pipeline
│   │       │   ├── embedder.py    # Embed & store into ChromaDB
│   │       │   ├── reranker.py    # BGE reranker
│   │       │   ├── secure_retriever.py  # Vector search with user filter
│   │       │   ├── context_builder.py   # Chunk assembly
│   │       │   ├── context_formatter.py # Prompt context formatting
│   │       │   └── citation_validator.py
│   │       ├── llm_service/       # LLM provider factory
│   │       │   ├── llm.py         # get_llm(), get_llm_structured()
│   │       │   ├── llm_schemas.py
│   │       │   └── structured_invoker.py
│   │       ├── text_processing/   # Document parsing
│   │       │   ├── extractor.py   # Unified file extractor
│   │       │   ├── chunker.py     # Text splitting
│   │       │   ├── file_detector.py  # MIME-type detection
│   │       │   ├── pdf_extractor.py
│   │       │   ├── ocr_service.py
│   │       │   ├── transcription_service.py  # Whisper
│   │       │   ├── table_extractor.py
│   │       │   ├── web_scraping.py  # Playwright + BeautifulSoup
│   │       │   └── youtube_service.py
│   │       ├── flashcard/         # Flashcard generation
│   │       ├── quiz/              # Quiz generation
│   │       ├── ppt/               # Slide generation
│   │       ├── podcast/           # Podcast generation
│   │       ├── explainer/         # Explainer video pipeline
│   │       └── code_execution/    # Sandboxed Python execution
│   ├── data/
│   │   ├── chroma/                # ChromaDB persistent store
│   │   ├── material_text/         # Full extracted text files
│   │   ├── models/                # Downloaded HuggingFace models
│   │   └── uploads/               # Raw uploaded files
│   ├── output/
│   │   ├── presentations/         # Generated PPTX + slide PNGs
│   │   ├── podcast/               # Generated audio files
│   │   └── html/
│   └── logs/                      # Rotating log files
│
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── tailwind.config.js
    ├── index.html
    ├── nginx.conf                 # Production NGINX config
    ├── Dockerfile
    └── src/
        ├── main.jsx               # React entry point
        ├── App.jsx                # Router + layout + guards
        ├── index.css              # Global styles + Tailwind
        ├── api/                   # Axios/fetch API wrappers
        │   ├── auth.js
        │   ├── notebooks.js
        │   ├── materials.js
        │   ├── chat.js
        │   ├── generation.js
        │   ├── jobs.js
        │   ├── agent.js
        │   └── explainer.js
        ├── context/               # React context providers
        │   ├── AppContext.jsx      # Global app state
        │   ├── AuthContext.jsx     # Auth state + token refresh
        │   └── ThemeContext.jsx    # Dark/light theme
        ├── components/            # UI components
        │   ├── Header.jsx
        │   ├── Sidebar.jsx        # Materials list, source selection
        │   ├── ChatPanel.jsx      # Main chat interface
        │   ├── StudioPanel.jsx    # Content generation UI
        │   ├── ChatMessage.jsx    # Renders agent response blocks
        │   ├── UploadDialog.jsx
        │   ├── PresentationView.jsx
        │   ├── ExplainerDialog.jsx
        │   ├── FileViewerPage.jsx
        │   ├── HomePage.jsx
        │   ├── AuthPage.jsx
        │   ├── Login.jsx / Signup.jsx
        │   ├── Modal.jsx
        │   ├── ErrorBoundary.jsx
        │   ├── FeatureCard.jsx
        │   ├── WebSearchDialog.jsx
        │   ├── SourceItem.jsx
        │   └── chat/              # Chat-specific sub-components
        └── hooks/                 # Custom React hooks
```

---

## 5. Backend — Deep Dive

### 5.1 Application Startup & Lifespan

**File**: [backend/app/main.py](backend/app/main.py)

The FastAPI application uses an `asynccontextmanager` lifespan that runs these steps **on startup** in order:

| Step | What happens |
|------|-------------|
| 1 | `connect_db()` — opens Prisma/PostgreSQL async connection |
| 2 | `warm_up_embeddings()` — run in thread-pool executor to pre-load ChromaDB ONNX model |
| 3 | `get_reranker()` — pre-loads BGE-reranker-large into memory |
| 4 | `asyncio.create_task(job_processor())` — starts the background queue worker |
| 5 | `ensure_packages()` — installs any missing sandbox Python packages |
| 5b | Cleans `/tmp/kepler_sandbox_*` leftovers from previous crashes |
| 6 | Creates output directories (`output/presentations`, `output/generated`, etc.) |

On **shutdown**:
- `graceful_shutdown()` waits up to 30 s for in-flight jobs.
- Cancels the `job_processor` task.
- `disconnect_db()` — closes Prisma connection.

**Logging** uses a `RotatingFileHandler` (`logs/app.log`, 10 MB, 3 backups) plus a `StreamHandler`. Noisy libs (`httpx`, `httpcore`, `uvicorn.access`) are suppressed to `WARNING`.

---

### 5.2 Configuration System

**File**: [backend/app/core/config.py](backend/app/core/config.py)

All configuration is driven by a **Pydantic `BaseSettings`** class named `Settings`. Values can be overridden via a `.env` file or environment variables.

Key configuration groups:

| Group | Variables |
|-------|-----------|
| Environment | `ENVIRONMENT`, `DEBUG` |
| Database | `DATABASE_URL` |
| Vector DB | `CHROMA_DIR` |
| Storage | `UPLOAD_DIR`, `MAX_UPLOAD_SIZE_MB` |
| JWT | `JWT_SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS` |
| CORS | `CORS_ORIGINS` (comma-separated list) |
| LLM | `LLM_PROVIDER` (OLLAMA/GOOGLE/NVIDIA/MYOPENLM), per-provider keys and models |
| LLM Params | Temperature presets for structured/chat/creative/code outputs |
| Embeddings | `EMBEDDING_MODEL`, `EMBEDDING_DIMENSION`, `EMBEDDING_VERSION` |
| RAG | `INITIAL_VECTOR_K`, `MMR_K`, `FINAL_K`, `MIN_SIMILARITY_SCORE`, etc. |
| Timeouts | `OCR_TIMEOUT_SECONDS`, `WHISPER_TIMEOUT_SECONDS`, `CODE_EXECUTION_TIMEOUT` |
| Output Paths | `PRESENTATIONS_OUTPUT_DIR`, `GENERATED_OUTPUT_DIR` |

The `_resolve_paths_and_cross_validate` model validator automatically:
- Converts relative paths to absolute using `_PROJECT_ROOT`.
- Sets `COOKIE_SECURE=True` in production.
- Emits warnings if a provider is configured without its API key.

A `@lru_cache` singleton is used — `settings` is imported directly across the app.

---

### 5.3 Database Layer

**Files**: [backend/app/db/prisma_client.py](backend/app/db/prisma_client.py), [backend/app/db/chroma.py](backend/app/db/chroma.py), [backend/prisma/schema.prisma](backend/prisma/schema.prisma)

#### PostgreSQL via Prisma

- **Client**: `prisma-client-py` with `asyncio` interface.
- **Operations**: All DB calls are fully async `await prisma.model.create(...)` style.
- **Schema** managed entirely through `schema.prisma`; run `prisma db push` to sync.

#### ChromaDB

- **Persistent** store at `CHROMA_DIR` (default `./data/chroma`).
- A single shared collection (named using `EMBEDDING_VERSION` so bumping the version triggers re-indexing).
- **Tenant isolation** is enforced at query time using `where={"user_id": user_id}` metadata filter.
- Embeddings are generated by ChromaDB's built-in ONNX model (all-MiniLM-L6-v2, 384-dim).

---

### 5.4 Authentication & Security

**Files**: [backend/app/routes/auth.py](backend/app/routes/auth.py), [backend/app/services/auth/](backend/app/services/auth/)

#### Flow

```
POST /auth/signup  →  bcrypt hash password  →  create User in DB
POST /auth/login   →  verify bcrypt  →  issue access token (JWT, 15 min)
                                     →  issue refresh token (JWT, 7 days, stored hashed in DB)
                                     →  set refresh_token HTTP-only cookie

GET  /protected    →  validate Bearer JWT  →  get_current_user()

POST /auth/refresh →  read cookie  →  validate_and_rotate_refresh_token()
                   →  new access + refresh tokens  →  update cookie

POST /auth/logout  →  revoke_user_tokens()  →  clear cookie
```

#### JWT Token Rotation

- Refresh tokens are stored **hashed** (SHA-256) in the `refresh_tokens` table.
- Each refresh token belongs to a **family** (random UUID per login session).
- If a used token is presented again → **entire family is revoked** (theft detection).
- `FILE_TOKEN_EXPIRE_MINUTES` (5 min) provides short-lived tokens for file downloads.

#### Password Rules (enforced by Pydantic validator)
- Minimum 8 characters
- At least one uppercase, one lowercase, one digit

---

### 5.5 Material Ingestion Pipeline

**File**: [backend/app/services/material_service.py](backend/app/services/material_service.py)

The system supports **four ingestion paths**:

| Source | Trigger | Processing |
|--------|---------|-----------|
| File upload | `POST /upload` | File extractor (PDF/DOCX/PPTX/image/audio/video) |
| URL | `POST /upload/url` | Playwright web scraping + BeautifulSoup |
| YouTube | `POST /upload/url` (YouTube URL detected) | `yt-dlp` download + Whisper transcription |
| Raw text | `POST /upload/text` | Direct ingest, no extraction needed |

#### Status Lifecycle

```
pending ──► processing ──► ocr_running ──► transcribing ──► embedding ──► completed
                                                                     └──► failed
```

Every status transition:
1. Updates the `materials` table in PostgreSQL.
2. Pushes a real-time `material_update` WebSocket event to the user.

#### Text Extraction

The `extractor.py` unified dispatcher routes to the correct sub-extractor:

| Format | Service |
|--------|---------|
| PDF | PyMuPDF + pdfplumber (table-aware) |
| DOCX | python-docx |
| PPTX | python-pptx |
| Images | Tesseract OCR + EasyOCR fallback |
| Audio/Video | OpenAI Whisper (GPU-accelerated if available) |
| Web URL | Playwright headless browser → BeautifulSoup clean text |
| YouTube | yt-dlp audio extraction → Whisper |
| CSV/Excel | openpyxl/xlrd — passed raw (no chunking) |

#### Chunking

`chunker.py` splits text into ~1000-char chunks with 150-token overlap using LangChain's `RecursiveCharacterTextSplitter`. Structured sources (CSV, Excel) bypass chunking.

#### Storage

- **Full text**: stored to disk at `data/material_text/{material_id}.txt` (avoids DB bloat).
- **Database**: stores only chunk count, source type, metadata JSON, and first ~1000 chars as summary.
- Deletion removes the DB record, all ChromaDB vectors (`where={"material_id": mid}`), and the text file.

---

### 5.6 Background Worker & Job Queue

**File**: [backend/app/services/worker.py](backend/app/services/worker.py)

A single `asyncio.Task` named `job_processor` runs an **infinite polling loop**:

```
while True:
    job = fetch_next_pending_job()  # SELECT ... WHERE status='pending' FOR UPDATE SKIP LOCKED
    if job:
        update status → processing
        call process_material_by_id(job.payload.material_id)
        update status → completed | failed
    else:
        await asyncio.sleep(2.0)   # idle poll interval
```

#### Event-driven Wake-up

A `_JobQueue` class holds an `asyncio.Event`. After `POST /upload` creates a `BackgroundJob` record, it calls `job_queue.notify()` — the worker wakes up immediately instead of waiting the 2-second poll interval.

#### Concurrency

Up to `MAX_CONCURRENT_JOBS = 5` can run concurrently using a semaphore.

#### Stuck Job Recovery

At startup, any job stuck in `processing` for > 30 minutes is reset to `pending` (handles server crash recovery).

#### Graceful Shutdown

On SIGTERM, `_shutdown_event` is set. The worker finishes in-progress jobs (up to 30 s), then exits.

---

### 5.7 RAG System (Retrieval-Augmented Generation)

**Files**: [backend/app/services/rag/](backend/app/services/rag/)

#### Pipeline

```
User Query
    │
    ▼
secure_retriever.py
    │  embed query via ChromaDB ONNX
    │  query ChromaDB with where={"user_id": uid, "material_id": {"$in": ids}}
    │  initial_k=10 candidates
    ▼
reranker.py (BAAI/bge-reranker-large)
    │  reranks candidates by semantic relevance to query
    │  returns top final_k=10
    ▼
context_builder.py
    │  filters chunks below MIN_CONTEXT_CHUNK_LENGTH (150 chars)
    │  trims to MAX_CONTEXT_TOKENS (6000) using tiktoken
    ▼
context_formatter.py
    │  formats chunks as numbered references: [1] source: ...
    ▼ 
LLM (chat_prompt.txt template)
    │  "Answer based only on the following context..."
    ▼
citation_validator.py
    │  validates [1], [2]... citations in the response
    ▼
Streaming response to frontend (SSE)
```

#### MMR (Maximal Marginal Relevance)

The retriever uses MMR (`MMR_LAMBDA=0.5`) to balance relevance vs. diversity in retrieved chunks — prevents 10 nearly-identical chunks from the same paragraph dominating the context.

#### Tenant Isolation

Every ChromaDB query includes `where={"user_id": user_id}`. Additionally, `material_id` whitelist filtering ensures only materials belonging to the current notebook are used.

---

### 5.8 LangGraph Agent System

**Files**: [backend/app/services/agent/](backend/app/services/agent/)

The chat endpoint is powered by a **LangGraph StateGraph** that replaces simple linear RAG with a multi-step agent.

#### Agent Graph

```
intent_and_plan ──► tool_router ──► reflection ──┐
                         ▲              │         │ continue (max 10 iterations)
                         └──────────────┘         │
                                           respond │
                                                   ▼
                                        response_generator ──► streaming SSE
```

#### Agent State (`state.py`)

The `AgentState` TypedDict carries through all graph nodes:

| Field | Purpose |
|-------|---------|
| `intent` | Detected user intent (QUESTION, CONTENT_GENERATION, DATA_ANALYSIS, CODE_EXECUTION, RESEARCH) |
| `plan` | List of tool invocations to execute |
| `tool_results` | List of `ToolResult` objects from executed tools |
| `iterations` | Guard against infinite loops (max 10) |
| `total_tokens` | Token budget tracking (max 50,000) |
| `stopped_reason` | Why the agent stopped |

#### Intent Detection (`intent.py`)

Uses keyword matching first (fast path, confidence ≥ 0.85). Falls back to an LLM call for ambiguous queries.

Intents recognized:
- `QUESTION` → triggers `rag_tool`
- `CONTENT_GENERATION` → triggers `quiz_tool`, `flashcard_tool`, or `ppt_tool`
- `DATA_ANALYSIS` → triggers `data_profiler` + `python_tool`
- `CODE_EXECUTION` → triggers `python_tool`
- `RESEARCH` → triggers `research_tool`

#### Tools (`tools_registry.py`)

| Tool | Maps to Service | Intent |
|------|----------------|--------|
| `rag_tool` | RAG retrieval pipeline | QUESTION |
| `quiz_tool` | Quiz generator | CONTENT_GENERATION |
| `flashcard_tool` | Flashcard generator | CONTENT_GENERATION |
| `ppt_tool` | Presentation generator | CONTENT_GENERATION |
| `python_tool` | Sandboxed code execution | DATA_ANALYSIS, CODE_EXECUTION |
| `data_profiler` | pandas-based data profiling | DATA_ANALYSIS (intermediate step) |
| `research_tool` | External search service | RESEARCH |

#### Reflection (`reflection.py`)

After each tool execution, reflection decides:
- **Continue**: plan has more steps and budgets allow.
- **Respond**: all planned tools completed, or hard limits hit.

---

### 5.9 LLM Provider Abstraction

**File**: [backend/app/services/llm_service/llm.py](backend/app/services/llm_service/llm.py)

A unified factory pattern provides `get_llm()` and `get_llm_structured()` functions. The active provider is selected by `LLM_PROVIDER` in config.

```python
# Usage throughout the app:
from app.services.llm_service.llm import get_llm, get_llm_structured

llm = get_llm()           # chat temperature (0.2), higher creativity
llm = get_llm_structured()  # structured temperature (0.1), deterministic
```

#### Temperature Presets

| Mode | Temperature | Top-P | Use Case |
|------|------------|-------|----------|
| Structured | 0.1 | 0.9 | Quiz, flashcard, PPT JSON generation |
| Chat | 0.2 | 0.95 | Conversational RAG responses |
| Creative | 0.7 | — | Podcast scripts |
| Code | 0.1 | — | Code generation, repair |

#### Supported Providers

| Provider | Class | Notes |
|----------|-------|-------|
| `OLLAMA` | `ChatOllama` | Local, free, requires Ollama daemon running |
| `GOOGLE` | `ChatGoogleGenerativeAI` | Gemini 2.5 Flash (default) |
| `NVIDIA` | `ChatNVIDIA` | NVIDIA AI Endpoints |
| `MYOPENLM` | Custom `LLM` subclass | Fallback OpenLM API |

LLM instances are **cached** in `_llm_cache` (max 16 entries) to avoid rebuilding for every request.

---

### 5.10 Content Generation Services

#### Quiz (`services/quiz/`)

- Takes material text + difficulty + count parameters.
- Sends text to LLM with `quiz_prompt.txt`.
- LLM returns JSON array of `{question, options: [A-D], correct_answer, explanation}`.
- JSON is parsed and validated, then returned directly.

#### Flashcards (`services/flashcard/`)

- Similar to quiz but uses `flashcard_prompt.txt`.
- Returns `{front, back}` card pairs.

#### Presentations — PPT (`services/ppt/`)

Pipeline:
1. Material text → LLM with `ppt_prompt.txt` → JSON outline (title, slides, bullet points, speaker notes).
2. Fetch slide images from Unsplash/Pexels based on slide topic.
3. Build PPTX with `python-pptx`.
4. Export slides to PNG via LibreOffice headless (`soffice --headless --convert-to png`).
5. Store at `output/presentations/{presentation_id}/`.
6. Save `GeneratedContent` record in PostgreSQL.

#### Podcast (`services/podcast/`)

1. Material text → LLM with `ppt_prompt.txt` adapted for dialogue → JSON script `{host_lines, guest_lines}`.
2. Each line synthesized to MP3 via `edge-tts` (multiple voices supported).
3. Audio segments merged with `pydub` + `ffmpeg`.
4. Stored at `output/podcast/{id}.mp3`.

#### Explainer Video (`services/explainer/`)

1. Takes an existing presentation (slides + speaker notes).
2. Generates per-slide narration script with LLM.
3. Synthesizes narration audio via `edge-tts`.
4. Assembles slide image + audio = video segment per slide using `ffmpeg`.
5. Concatenates all segments into final MP4.
6. Saves `ExplainerVideo` record with status tracking.

#### Code Execution (`services/code_execution/`)

- Sandboxed Python execution in isolated `/tmp/kepler_sandbox_{id}` directories.
- Timeout enforced (`CODE_EXECUTION_TIMEOUT = 15 s`).
- Up to `MAX_CODE_REPAIR_ATTEMPTS = 3` automatic repair cycles: if code throws an exception, the LLM re-tries with the error output + `code_repair_prompt.txt`.
- Stale sandbox directories cleaned at startup.

---

### 5.11 WebSocket Manager

**File**: [backend/app/services/ws_manager.py](backend/app/services/ws_manager.py)

`ws_manager` maintains a dictionary of `{user_id: [WebSocket, ...]}`. Any service can call `await ws_manager.send_to_user(user_id, payload)` to push real-time events (material status updates, job completion) to all active browser tabs of a user.

`/ws` endpoint (in `websocket_router.py`) authenticates via JWT query parameter, registers the socket, and keeps it alive with a ping loop.

---

### 5.12 API Routes Reference

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/signup` | Register new user |
| POST | `/auth/login` | Login, returns JWT in body + refresh cookie |
| POST | `/auth/refresh` | Rotate refresh token, returns new access token |
| GET | `/auth/me` | Get current user profile |
| POST | `/auth/logout` | Revoke tokens + clear cookie |
| POST | `/notebooks` | Create notebook |
| GET | `/notebooks` | List user's notebooks |
| GET | `/notebooks/{id}` | Get notebook detail |
| PUT | `/notebooks/{id}` | Update notebook |
| DELETE | `/notebooks/{id}` | Delete notebook |
| POST | `/upload` | Upload file (multipart/form-data) |
| POST | `/upload/url` | Submit URL or YouTube link |
| POST | `/upload/text` | Submit raw text |
| GET | `/materials` | List user's materials |
| GET | `/materials/{id}` | Get material detail |
| PUT | `/materials/{id}` | Update material metadata |
| DELETE | `/materials/{id}` | Delete material + vectors |
| POST | `/chat` | Send chat message (SSE streaming or JSON) |
| GET | `/chat/sessions/{notebook_id}` | List chat sessions |
| POST | `/chat/sessions` | Create chat session |
| GET | `/chat/history/{session_id}` | Get session messages |
| DELETE | `/chat/{session_id}` | Clear session |
| POST | `/quiz` | Generate quiz |
| POST | `/flashcard` | Generate flashcards |
| POST | `/ppt` | Generate presentation |
| GET | `/ppt/{id}/slides` | Get slide images |
| POST | `/ppt/{id}/explainer` | Start explainer video |
| GET | `/explainer/{id}` | Get explainer status |
| GET | `/jobs` | List background jobs |
| GET | `/jobs/{id}` | Get job status |
| GET | `/health` | Health check |
| GET | `/models` | List available LLM models |
| POST | `/search` | Web search proxy |
| WS | `/ws` | WebSocket connection |

---

### 5.13 Middleware Stack

Middleware is applied in **inner-to-outer** order (last added = outermost, runs first):

```
Request →  limit_request_body (100 MB guard)
        →  CORS (preflight handling)
        →  log_requests (per-request ID, timing)
        →  rate_limit_middleware (token-bucket per user)
        →  performance_monitoring_middleware (telemetry)
        →  Route handler
```

**Rate Limiter**: sliding-window token bucket, limits per `user_id` (from JWT) or IP for unauthenticated requests.

**TrustedHostMiddleware**: enabled in production only; rejects requests with invalid `Host` headers.

---

## 6. Frontend — Deep Dive

### 6.1 Application Structure

**Entry**: [frontend/src/main.jsx](frontend/src/main.jsx) renders `<App />` into `#root`.

**App.jsx** provides:
- The `<Router>` context (React Router v7).
- Three context providers: `AuthProvider` → `ThemeProvider` → `AppProvider`.
- Route definitions and `ProtectedRoute` guard.

---

### 6.2 Routing & Navigation

| Route | Component | Auth Required |
|-------|-----------|--------------|
| `/` | `HomePage` | No |
| `/auth` | `AuthPage` (Login/Signup) | No |
| `/notebook/draft` | Workspace (draft mode) | Yes |
| `/notebook/:id` | Workspace (existing) | Yes |
| `/file/:materialId` | `FileViewerPage` | Yes |

`ProtectedRoute` checks `isAuthenticated` from `AuthContext`. Unauthenticated users are redirected to `/auth`.

The `Workspace` component reads the `:id` param and either:
- Loads the notebook via `getNotebook(id)` if the route has a real UUID.
- Sets draft mode for `/notebook/draft`.

---

### 6.3 Context & State Management

#### `AuthContext` (`context/AuthContext.jsx`)
- Stores `user`, `accessToken`, `isAuthenticated`, `isLoading`.
- On mount, calls `GET /auth/me` with the stored token to restore session.
- Implements silent token refresh: intercepts 401 responses, calls `POST /auth/refresh`, retries the original request transparently.

#### `AppContext` (`context/AppContext.jsx`)
Global UI state:
- `currentNotebook` — currently open notebook.
- `materials` — list of materials in the notebook sidebar.
- `selectedMaterialIds` — which materials are ticked for RAG queries.
- `messages` — current chat session messages.
- `currentMaterial` — material highlighted in the sidebar.
- `draftMode` — true while creating an unsaved notebook.

#### `ThemeContext` (`context/ThemeContext.jsx`)
- Persists theme preference to `localStorage`.
- Applies `dark`/`light` CSS class to `<html>`.

---

### 6.4 Key Components

#### `Sidebar.jsx`
- Lists all materials in the current notebook.
- Each `SourceItem` shows: filename, status badge (pending/processing/completed/failed), chunk count.
- Checkboxes allow multi-select for targeted RAG queries.
- Upload button opens `UploadDialog`.

#### `ChatPanel.jsx`
- Main conversational interface.
- Sends `POST /chat` with `stream: true` → receives Server-Sent Events.
- Parses agent step events (`intent_detected`, `tool_start`, `tool_result`, `response_chunk`, `done`) to build the streaming message display.
- Shows agent "thinking" steps and tool calls in a collapsible step log.

#### `ChatMessage.jsx`
- Renders individual messages.
- Detects structured response blocks (quiz, flashcard, chart, code output, data analysis) and delegates to specialized renderers.
- Inline citation links `[1]` navigate to the source chunk.

#### `StudioPanel.jsx`
- Right-side panel for content generation.
- Tabs: Quiz, Flashcards, Presentation, Podcast.
- Each tab has form controls (difficulty, count, language, theme) and a "Generate" button.
- Displays results inline (quiz questions, flashcard deck, slide preview).

#### `PresentationView.jsx`
- Slide carousel rendering PNG exports.
- "Create Explainer Video" button triggers `ExplainerDialog`.

#### `ExplainerDialog.jsx`
- Polls `GET /explainer/{id}` until video is ready.
- Shows progress bar during generation.
- Provides download link when done.

#### `UploadDialog.jsx`
- Tabbed interface: File / URL / YouTube / Text.
- Drag-and-drop file upload with progress.
- Real-time status updates via WebSocket.

---

### 6.5 API Layer

All API modules in `src/api/` share a base `fetch`/`axios` config that:
- Attaches `Authorization: Bearer {accessToken}` header automatically.
- On 401, triggers the silent refresh flow from `AuthContext`.
- Uses `config.js` to determine base URL (env-aware: `VITE_API_URL` or `localhost:8000`).

```
api/auth.js       → /auth/* endpoints
api/notebooks.js  → /notebooks
api/materials.js  → /upload, /materials
api/chat.js       → /chat (including SSE reading)
api/generation.js → /quiz, /flashcard, /ppt
api/jobs.js       → /jobs
api/agent.js      → /agent
api/explainer.js  → /explainer
```

---

## 7. Data Models (Prisma Schema)

**File**: [backend/prisma/schema.prisma](backend/prisma/schema.prisma)

### Entity Relationship Overview

```
User (1) ─────────────────────────────────────────────── (many) Notebook
  │                                                                     │
  ├── (many) Material ─────────────────────────────────── (of) Notebook
  │             └── (many) GeneratedContent ──────────── (of) Notebook
  │
  ├── (many) ChatSession ──────────────────────────────── (of) Notebook
  │             └── (many) ChatMessage
  │
  ├── (many) BackgroundJob
  ├── (many) RefreshToken
  ├── (many) UserTokenUsage
  ├── (many) ApiUsageLog
  ├── (many) AgentExecutionLog
  ├── (many) CodeExecutionSession
  ├── (many) ResearchSession
  └── (many) ExplainerVideo ─────────────────────── (of) GeneratedContent
```

### Key Models

| Model | Key Fields | Purpose |
|-------|-----------|---------|
| `User` | `id`, `email`, `username`, `hashedPassword`, `role` | Auth & ownership |
| `Notebook` | `id`, `userId`, `name`, `description` | Container for materials |
| `Material` | `id`, `notebookId`, `filename`, `status`, `sourceType`, `chunkCount` | Document records |
| `ChatSession` | `id`, `notebookId`, `title` | Conversation threads |
| `ChatMessage` | `id`, `role`, `content`, `agentMeta` | Individual messages with agent metadata |
| `GeneratedContent` | `id`, `contentType`, `data` (JSON), `materialIds[]` | Quizzes, flashcards, PPTs, podcasts |
| `ExplainerVideo` | `id`, `status`, `script`, `audioFiles`, `videoUrl` | Narrated video status |
| `BackgroundJob` | `id`, `status`, `jobType`, `payload` JSON | Async job tracking |
| `RefreshToken` | `tokenHash`, `family`, `used`, `expiresAt` | Token rotation |
| `UserTokenUsage` | `promptTokens`, `completionTokens`, `model` | LLM usage tracking |
| `ResponseBlock` | `messageId`, `blockType`, `content` | Structured response blocks in messages |

### Material Status Enum

```
pending → processing → ocr_running → transcribing → embedding → completed
                                                              └→ failed
```

---

## 8. End-to-End Data Flows

### 8.1 User Registration & Login

```
1. Browser: POST /auth/signup {email, username, password}
2. Backend: validate Pydantic → bcrypt hash password → INSERT into users
3. Response: 201 Created {id, email, username}

4. Browser: POST /auth/login {email, password}
5. Backend: SELECT user WHERE email → bcrypt.verify() → create access JWT + refresh JWT
6.         → store refresh token hash in refresh_tokens table
7. Response: {access_token} + Set-Cookie: refresh_token=...; HttpOnly; SameSite=Lax

8. Browser: stores access_token in memory (React state)
9. All subsequent requests: Authorization: Bearer {access_token}
```

---

### 8.2 Material Upload & Processing

```
1. Browser: POST /upload (multipart file) + {notebook_id}
2. Backend: file_validator.validate_upload() → check MIME type, size
3.         → stream to /data/uploads/{uuid}{ext}
4.         → CREATE material record (status=pending)
5.         → CREATE background_job record (type=material_processing)
6.         → job_queue.notify() → worker wakes immediately
7. Response: {material_id, status: "pending"}

8. [Worker task picks up job]
9.  → set status = processing
10. → text_processing.extractor.extract(file_path) → raw text
     ├─ PDF: PyMuPDF → layout text → pdfplumber table extraction
     ├─ DOCX: python-docx paragraphs + tables
     ├─ PPTX: python-pptx shapes text
     ├─ Image: pytesseract → EasyOCR fallback → set status=ocr_running
     ├─ Audio/Video: Whisper → set status=transcribing
     ├─ URL: Playwright headless → BeautifulSoup → clean text
     └─ YouTube: yt-dlp audio → Whisper
11. → sanitize_null_bytes(text)
12. → save_material_text(material_id, text) → /data/material_text/{id}.txt
13. → set status = embedding
14. → chunker.chunk_text(text) → [{id, text}, ...] chunks
15. → embedder.embed_and_store(chunks, material_id, user_id, notebook_id)
     → ChromaDB upsert in batches of 200
16. → UPDATE material SET status=completed, chunk_count=N
17. → ws_manager.send_to_user(user_id, {type: material_update, status: completed})
18. → UPDATE background_job SET status=completed

[Browser receives WS event → sidebar status badge updates to "ready"]
```

---

### 8.3 RAG Chat Flow

```
1. Browser: POST /chat {message, material_ids[], notebook_id, session_id, stream: true}
2. Backend: validate user owns all material_ids
3.         → filter to only completed materials
4.         → run LangGraph agent:

   [intent_and_plan node]
   → keyword check: "explain X" → QUESTION intent
   → plan: [{tool: "rag_tool", params: {query: message}}]

   [tool_router node]
   → execute rag_tool:
     a. embed query → ChromaDB query (where user_id + material_ids filter, k=10)
     b. reranker.rerank(query, candidates) → top 10 chunks
     c. context_builder.build(chunks, max_tokens=6000)
     d. context_formatter.format(chunks) → numbered references
     e. LLM invoke(chat_prompt + context + question)
        → streaming tokens
     f. citation_validator.validate response citations

   [reflection node]
   → all plan steps done → "respond"

   [response_generator node]
   → combine rag_tool output into final response

5. Backend: yield SSE events:
   data: {"type": "intent_detected", "intent": "QUESTION"}
   data: {"type": "tool_start", "tool": "rag_tool"}
   data: {"type": "response_chunk", "content": "The..."}  ← per LLM token
   data: {"type": "done", "session_id": "..."}

6. Browser: reads SSE stream → renders tokens in real-time
7. Backend: save ChatMessage(role=user), ChatMessage(role=assistant, agentMeta=JSON)
```

---

### 8.4 Quiz Generation

```
1. Browser: POST /quiz {material_ids[], mcq_count: 10, difficulty: "Medium"}
2. Backend: require_materials_text(ids) → reads /data/material_text/{id}.txt for each
3.         → concatenate texts
4.         → run_in_executor (blocking LLM call off event loop):
            generate_quiz(text, mcq_count=10, difficulty="Medium")
            → format quiz_prompt.txt with text
            → get_llm_structured().invoke(prompt)
            → JSON parse response → [{question, options, correct_answer, explanation}]
5. Response: {questions: [...]}
6. Browser: renders interactive quiz in StudioPanel
```

---

### 8.5 Presentation (PPT) Generation

```
1. Browser: POST /ppt {material_ids[], theme, slide_count, language}
2. Backend: fetch material texts
3.         → LLM generate JSON outline:
            [{slide_title, bullet_points[], speaker_notes, image_query}]
4.         → fetch_slide_images(image_query) → Unsplash/Pexels API
5.         → build PPTX:
               python-pptx Presentation()
               for each slide: add_slide, add text boxes, add images
6.         → export to PNG:
               LibreOffice headless: soffice --convert-to png
7.         → save to output/presentations/{id}/slide_{n}.png
8.         → INSERT GeneratedContent(contentType='presentation', data={slides_json})
9. Response: {presentation_id, slide_urls[]}
```

---

### 8.6 Podcast Generation

```
1. Browser: POST /podcast {material_ids[], host_voice, guest_voice, language}
2. Backend: fetch material texts
3.         → LLM generate dialogue script:
            [{speaker: "host"|"guest", text: "..."}]
4.         → for each line: edge_tts.Communicate(text, voice_id).save(mp3)
5.         → pydub AudioSegment concat all lines → final.mp3
6.         → save to output/podcast/{id}.mp3
7.         → INSERT GeneratedContent(contentType='podcast', data={transcript})
8. Response: {audio_url, transcript}
```

---

### 8.7 Explainer Video Flow

```
1. Browser: POST /ppt/{presentation_id}/explainer {voice_gender, narration_language}
2. Backend: fetch presentation slides + speaker notes
3.         → INSERT ExplainerVideo(status=pending)
4.         → start background task:
               for each slide:
                 a. LLM generate narration from speaker_notes
                 b. edge_tts synthesize narration → slide_N_audio.mp3
                 c. ffmpeg: combine slide_N.png + audio → slide_N.mp4
               d. ffmpeg concat all slide_N.mp4 → final_{id}.mp4
5.         → UPDATE ExplainerVideo(status=completed, videoUrl=...)
6.         → ws_manager.send_to_user(user_id, {type: explainer_update})
7. Browser: polls GET /explainer/{id} → shows progress bar → plays/downloads video
```

---

## 9. Security Architecture

### Defense-in-Depth Layers

| Layer | Mechanism |
|-------|----------|
| Transport | HTTPS in production (NGINX TLS termination) |
| Authentication | JWT Bearer tokens (RS/HS256), 15-min expiry |
| Session Management | HTTP-only, SameSite=Lax refresh token cookies |
| Token Theft Detection | Refresh token family rotation; reuse → full family revocation |
| Authorization | Every route checks `current_user = Depends(get_current_user)` |
| Data Isolation | ChromaDB `where={"user_id": uid}` on every query |
| File Security | MIME-type validation (python-magic checks actual file header, not extension) |
| File Access | Short-lived signed tokens (5 min) for file downloads |
| Input Validation | Pydantic v2 strict validation on all request bodies |
| Rate Limiting | Token-bucket per authenticated user / IP |
| Request Size | 100 MB hard cap middleware |
| SSRF Protection | IP allowlist/blocklist on URL upload endpoint |
| Host Header | TrustedHostMiddleware in production |
| Password | bcrypt with per-user salts |
| SQL Injection | Prisma ORM parameterized queries (no raw SQL in application code) |

---

## 10. Configuration Reference

All settings loaded from `.env` file in `backend/`:

```bash
# ── Required ──────────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/keplerlab
JWT_SECRET_KEY=<64-byte-url-safe-random>   # python -c "import secrets; print(secrets.token_urlsafe(64))"

# ── LLM Provider (choose one) ─────────────────────────────────
LLM_PROVIDER=OLLAMA           # OLLAMA | GOOGLE | NVIDIA | MYOPENLM

# Ollama (local)
OLLAMA_MODEL=llama3           # or llama3.1, mistral, etc.

# Google Gemini
GOOGLE_API_KEY=AIza...
GOOGLE_MODEL=models/gemini-2.5-flash

# NVIDIA AI
NVIDIA_API_KEY=nvapi-...
NVIDIA_MODEL=qwen/qwen3.5-397b-a17b

# ── Paths (relative to backend/) ──────────────────────────────
CHROMA_DIR=./data/chroma
UPLOAD_DIR=./data/uploads
MODELS_DIR=./data/models
PRESENTATIONS_OUTPUT_DIR=output/presentations
GENERATED_OUTPUT_DIR=output/generated

# ── CORS ──────────────────────────────────────────────────────
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# ── Optional Tuning ───────────────────────────────────────────
MAX_UPLOAD_SIZE_MB=25
LLM_TIMEOUT=               # leave empty for no timeout
CODE_EXECUTION_TIMEOUT=15
USE_RERANKER=true
INITIAL_VECTOR_K=10
FINAL_K=10
MIN_SIMILARITY_SCORE=0.3
MAX_CONTEXT_TOKENS=6000

# ── Environment ───────────────────────────────────────────────
ENVIRONMENT=development    # development | staging | production
DEBUG=false

# ── External Services ─────────────────────────────────────────
SEARCH_SERVICE_URL=http://localhost:8002   # optional web-search microservice
IMAGE_GENERATION_ENDPOINT=               # optional image generation API
```

---

## 11. Infrastructure & Deployment

### Local Development

```bash
# 1. Start PostgreSQL
# 2. Start Ollama (if using local LLM)
ollama serve && ollama pull llama3

# 3. Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # edit with your values
prisma generate
prisma db push
uvicorn app.main:app --reload --port 8000

# 4. Frontend
cd frontend
npm install
npm run dev  # → http://localhost:5173
```

### Docker Deployment

```bash
docker-compose up -d
# Frontend: http://localhost:3000 (NGINX)
# Backend:  http://localhost:8000
```

Docker setup includes:
- **Frontend** container: NGINX serving the Vite production build.
- **Backend** container: Uvicorn + FastAPI.
- **PostgreSQL** container.
- Volume mounts for `data/`, `output/`, `logs/`.

### Production Checklist

- [ ] Set `ENVIRONMENT=production`
- [ ] Use a strong `JWT_SECRET_KEY`
- [ ] Enable HTTPS on NGINX
- [ ] Set `COOKIE_SECURE=true`, `COOKIE_SAMESITE=strict`
- [ ] Review `CORS_ORIGINS`
- [ ] Set up PostgreSQL connection pooling (PgBouncer)
- [ ] Configure a proper log drain
- [ ] Enable Redis for caching

---

## 12. Performance Characteristics

| Operation | Typical Time | Notes |
|-----------|-------------|-------|
| 100-page PDF extraction | 10–30 s | PyMuPDF; OCR adds 2–5× |
| Batch embedding (1000 chunks) | 30–60 s | ONNX, CPU; 3–8s on GPU |
| RAG chat response (first token) | 1–3 s | Depends on LLM provider |
| Quiz generation (10 questions) | 3–8 s | |
| Flashcard generation (20 cards) | 3–8 s | |
| Slide generation (10 slides) | 15–45 s | Includes LibreOffice PNG export |
| Podcast generation (5 min audio) | 30–90 s | TTS + ffmpeg concat |
| Whisper transcription | 0.5–2× real-time | GPU highly recommended |

**Optimization highlights**:
- Embedding batches of 200 items reduce ChromaDB overhead by 10–40× vs. single inserts.
- Worker semaphore (5 concurrent) prevents GPU OOM during parallel uploads.
- LLM instance caching avoids cold-start per request.
- Embedding model warm-up at startup eliminates first-request latency.

---

## 13. Troubleshooting & FAQs

### Backend won't start: `JWT_SECRET_KEY must be set`
```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
# Paste output into .env as JWT_SECRET_KEY=...
```

### ChromaDB errors after model change
```bash
# Bump EMBEDDING_VERSION in .env to force new collection
EMBEDDING_VERSION=bge_m3_v2
# Delete old data if needed:
rm -rf backend/data/chroma/*
```

### Material stuck in `processing` state
- Check `backend/logs/app.log` for the specific error.
- The worker resets stuck jobs (>30 min) automatically on next restart.
- Delete and re-upload the material if it keeps failing.

### LLM timeout errors
```bash
# Increase or remove timeout in .env:
LLM_TIMEOUT=300   # or leave blank for no timeout
# Or switch to a faster provider:
LLM_PROVIDER=GOOGLE
```

### Frontend CORS errors
```bash
# Add your frontend URL to .env:
CORS_ORIGINS=http://localhost:5173,http://your-domain.com
```

### LibreOffice not found (PPT PNG export fails)
```bash
# Ubuntu/Debian:
sudo apt-get install libreoffice

# Verify:
which soffice
```

### Whisper model download
Whisper models are downloaded automatically on first use to `~/.cache/whisper/`. Ensure internet access on first transcription.

### `EasyOCR` CUDA errors
```bash
# Force EasyOCR to CPU:
EASYOCR_GPU=false
# Or ensure CUDA drivers and torch versions match requirements.txt
```

---

*This document covers KeplerLab AI Notebook v2.0.0. For API interactive docs, visit `http://localhost:8000/docs` after starting the backend.*
