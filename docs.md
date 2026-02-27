# KeplerLab AI Notebook — Complete Technical Documentation

> **Version:** 2.0.0 | **Stack:** FastAPI + React + PostgreSQL + ChromaDB + LangGraph

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Tech Stack](#3-tech-stack)
4. [Directory Structure](#4-directory-structure)
5. [Backend — Deep Dive](#5-backend--deep-dive)
   - 5.1 [Application Entry Point (`main.py`)](#51-application-entry-point-mainpy)
   - 5.2 [Configuration (`core/config.py`)](#52-configuration-coreconfigpy)
   - 5.3 [Database Layer](#53-database-layer)
   - 5.4 [Authentication & Security](#54-authentication--security)
   - 5.5 [Routes (API Endpoints)](#55-routes-api-endpoints)
   - 5.6 [Background Worker](#56-background-worker)
   - 5.7 [Material Processing Pipeline](#57-material-processing-pipeline)
   - 5.8 [RAG Pipeline](#58-rag-pipeline)
   - 5.9 [LLM Service Layer](#59-llm-service-layer)
   - 5.10 [LangGraph Agent](#510-langgraph-agent)
   - 5.11 [Content Generation Services](#511-content-generation-services)
   - 5.12 [Code Execution Sandbox](#512-code-execution-sandbox)
   - 5.13 [WebSocket Manager](#513-websocket-manager)
   - 5.14 [Middleware Stack](#514-middleware-stack)
6. [Database Schema](#6-database-schema)
7. [Frontend — Deep Dive](#7-frontend--deep-dive)
   - 7.1 [App Structure & Routing](#71-app-structure--routing)
   - 7.2 [Context Providers](#72-context-providers)
   - 7.3 [Key Components](#73-key-components)
   - 7.4 [API Layer](#74-api-layer)
8. [End-to-End Data Flows](#8-end-to-end-data-flows)
   - 8.1 [Material Upload & Processing](#81-material-upload--processing)
   - 8.2 [Chat / RAG Query](#82-chat--rag-query)
   - 8.3 [Agent-Driven Requests](#83-agent-driven-requests)
   - 8.4 [Content Generation (Quiz, Flashcard, PPT, Podcast)](#84-content-generation-quiz-flashcard-ppt-podcast)
9. [Security Design](#9-security-design)
10. [Configuration Reference](#10-configuration-reference)
11. [Deployment](#11-deployment)

---

## 1. Project Overview

**KeplerLab AI Notebook** is a full-stack AI-powered study assistant that transforms raw educational materials (PDFs, DOCX, audio, video, web pages, YouTube) into interactive learning content. Users upload their materials into "Notebooks" (topic-based containers), then use AI features to:

- **Chat** with their material via Retrieval-Augmented Generation (RAG)
- **Generate** quizzes, flashcards, presentations, and audio podcasts
- **Analyze** structured data (CSV/Excel) with an AI data analyst
- **Research** topics via an agentic web-search loop
- **Execute** Python code in a secure sandbox (with LLM-assisted repair)
- **Watch** AI-narrated explainer videos from presentations

The system uses a **LangGraph state-machine agent** to classify user intent and route every chat message to the right tool automatically.

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        React 19 Frontend                            │
│              Vite + Tailwind CSS + React Router 7                   │
│   Pages: Home | Auth | Workspace (Chat + Studio) | FileViewer       │
└──────────────────────────┬──────────────────────────────────────────┘
                           │  HTTP REST + SSE + WebSocket
┌──────────────────────────▼──────────────────────────────────────────┐
│                      FastAPI Backend (v2.0.0)                       │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  ┌───────┐  │
│  │  Routes  │  │ Services │  │  Agent   │  │  RAG   │  │  LLM  │  │
│  │ /auth    │  │ material │  │ LangGraph│  │ embed  │  │ OLLAMA│  │
│  │ /chat    │  │ notebook │  │ intent   │  │ rerank │  │GOOGLE │  │
│  │ /agent   │  │ worker   │  │ planner  │  │retrieve│  │NVIDIA │  │
│  │ /upload  │  │ podcast  │  │ tools    │  │context │  │OpenLM │  │
│  │ /quiz    │  │ ppt      │  │ reflect  │  └────────┘  └───────┘  │
│  │ /flashcrd│  │ quiz     │  └──────────┘                         │
│  │ /ppt     │  │ flashcard│                                        │
│  │ /podcast │  │ tts      │                                        │
│  │ /ws      │  │ code exec│                                        │
│  └──────────┘  └──────────┘                                        │
└────────────┬───────────────────────────────────────────────────────┘
             │
   ┌──────────┼───────────────┐
   ▼          ▼               ▼
┌──────┐  ┌───────────┐  ┌─────────┐
│Postgr│  │ ChromaDB  │  │  File   │
│ SQL  │  │ (Vectors) │  │ Storage │
│Prisma│  │ ONNX embed│  │ FS/disk │
└──────┘  └───────────┘  └─────────┘
```

### Request Flow Summary

```
Browser Request
    │
    ├─ REST: POST /chat  →  Auth middleware  →  Route handler
    │                           │
    │                           ▼
    │                    LangGraph Agent
    │                           │
    │                    Intent Detection (keyword rules + LLM fallback)
    │                           │
    │                    Planner (tool selection)
    │                           │
    │                    Tool Execution (RAG / Code / Research / etc.)
    │                           │
    │                    Reflection (retry or respond)
    │                           │
    │                    SSE stream back to browser
    │
    └─ WebSocket: /ws/jobs/{user_id}  →  Real-time status pushes
```

---

## 3. Tech Stack

### Backend

| Component | Library / Version |
|---|---|
| Web Framework | FastAPI 0.115.6 |
| Python Runtime | Python 3.11+ |
| ORM | Prisma 0.15.0 (`prisma-client-py`) |
| Relational DB | PostgreSQL 15+ |
| Vector DB | ChromaDB 0.5.5 |
| LLM Orchestration | LangChain 0.2.16 + LangGraph ≥0.2 |
| Embeddings | ChromaDB built-in ONNX (MiniLM-L6-v2, 384-dim) |
| Reranker | BAAI/bge-reranker-large (sentence-transformers) |
| Audio Transcription | OpenAI Whisper |
| Text-to-Speech | edge-tts ≥ 6.1.0 |
| OCR | pytesseract + EasyOCR |
| PDF Processing | PyMuPDF + pypdf + pdfplumber |
| Audio/Video | pydub + ffmpeg-python |
| Web Scraping | BeautifulSoup4 + trafilatura + Playwright |
| YouTube | yt-dlp + youtube-transcript-api |
| Auth | python-jose (JWT) + passlib/bcrypt |
| Validation | Pydantic v2 + pydantic-settings |
| Async HTTP | httpx ≥ 0.25 |
| Caching | Redis (via fastapi-cache2) |

### Frontend

| Component | Library / Version |
|---|---|
| Framework | React 19.2.0 |
| Build Tool | Vite 7.2.4 |
| Routing | React Router 7.11.0 |
| Styling | Tailwind CSS 3.4.19 |
| HTTP Client | Fetch API (native) |
| Real-time | WebSocket (native) + SSE |

### Infrastructure

| Component | Technology |
|---|---|
| Web Server | NGINX (frontend reverse proxy) |
| Container | Docker + Docker Compose |
| Process Manager | uvicorn (ASGI) |
| Background Jobs | asyncio.Task (in-process worker) |

---

## 4. Directory Structure

```
KeplerLab-AI-Notebook/
├── backend/
│   ├── app/
│   │   ├── main.py                   # FastAPI app entry point, lifespan, middleware
│   │   ├── core/
│   │   │   ├── config.py             # Pydantic settings (all env vars)
│   │   │   └── utils.py              # Shared utility functions
│   │   ├── db/
│   │   │   ├── chroma.py             # ChromaDB collection factory
│   │   │   └── prisma_client.py      # Prisma singleton + connect/disconnect
│   │   ├── models/                   # Pydantic response models
│   │   ├── prompts/                  # System prompt text files (.txt)
│   │   │   ├── chat_prompt.txt
│   │   │   ├── quiz_prompt.txt
│   │   │   ├── flashcard_prompt.txt
│   │   │   ├── podcast_prompt.txt
│   │   │   ├── ppt_prompt.txt
│   │   │   ├── code_generation_prompt.txt
│   │   │   ├── code_repair_prompt.txt
│   │   │   └── data_analysis_prompt.txt
│   │   ├── routes/                   # FastAPI routers (one file per feature)
│   │   │   ├── auth.py               # /auth — signup, login, refresh, logout
│   │   │   ├── notebook.py           # /notebooks — CRUD
│   │   │   ├── upload.py             # /upload, /materials — file/URL/text ingestion
│   │   │   ├── chat.py               # /chat — agent-driven Q&A (SSE)
│   │   │   ├── agent.py              # /agent — code exec, data analysis, research (SSE)
│   │   │   ├── quiz.py               # /quiz — quiz generation
│   │   │   ├── flashcard.py          # /flashcard — flashcard generation
│   │   │   ├── ppt.py                # /presentation — slide deck generation
│   │   │   ├── podcast_router.py     # /podcast — audio podcast generation
│   │   │   ├── explainer.py          # /explainer — narrated video
│   │   │   ├── search.py             # /search — material/content search
│   │   │   ├── jobs.py               # /jobs — background job status
│   │   │   ├── models.py             # /models — available LLM model list
│   │   │   ├── health.py             # /health — liveness probe
│   │   │   ├── proxy.py              # /proxy — secure file proxy
│   │   │   ├── websocket_router.py   # /ws/jobs/{user_id} — realtime updates
│   │   │   └── utils.py              # Shared route helpers
│   │   └── services/
│   │       ├── agent/                # LangGraph agent (intent → plan → execute → reflect)
│   │       │   ├── graph.py
│   │       │   ├── intent.py
│   │       │   ├── planner.py
│   │       │   ├── router.py
│   │       │   ├── reflection.py
│   │       │   ├── state.py
│   │       │   ├── tools_registry.py
│   │       │   ├── tools/            # python_tool, data_profiler, file_generator, workspace_builder
│   │       │   └── subgraphs/
│   │       ├── auth/                 # register, authenticate, JWT helpers
│   │       ├── chat/                 # ChatService — session + history management
│   │       ├── code_execution/       # Sandbox Python executor + repair loop
│   │       ├── explainer/            # Narrated video builder
│   │       ├── flashcard/            # Flashcard generator
│   │       ├── llm_service/          # LLM factory (Ollama, Google, NVIDIA, OpenLM)
│   │       ├── podcast/              # Podcast script + TTS pipeline
│   │       ├── ppt/                  # Presentation (HTML slides) generator
│   │       ├── quiz/                 # Quiz generator
│   │       ├── rag/                  # Embedder, retriever, reranker, context builder
│   │       ├── text_processing/      # Chunker, extractor, OCR, Whisper, web scraping, YouTube
│   │       ├── text_to_speech/       # edge-tts wrapper
│   │       ├── audit_logger.py       # API usage & audit log
│   │       ├── file_validator.py     # MIME/magic file security validator
│   │       ├── gpu_manager.py        # GPU memory management
│   │       ├── job_service.py        # BackgroundJob CRUD helpers
│   │       ├── material_service.py   # Full material lifecycle
│   │       ├── model_manager.py      # Model download / cache utilities
│   │       ├── notebook_service.py   # Notebook CRUD
│   │       ├── performance_logger.py # Request timing middleware
│   │       ├── rate_limiter.py       # In-memory token-bucket rate limiter
│   │       ├── storage_service.py    # FS-based material text store
│   │       ├── token_counter.py      # tiktoken wrapper
│   │       ├── worker.py             # Async background document processor
│   │       └── ws_manager.py         # WebSocket connection registry
│   ├── data/
│   │   ├── chroma/                   # ChromaDB persistence directory
│   │   ├── material_text/            # Full material text files ({material_id}.txt)
│   │   ├── models/                   # Downloaded ML model weights (bge-m3, reranker)
│   │   ├── uploads/                  # Uploaded raw files
│   │   └── output/                   # Generated artifacts (podcasts, slides, etc.)
│   ├── prisma/
│   │   └── schema.prisma             # Database schema definition
│   ├── cli/                          # ChromaDB backup/restore CLI tools
│   ├── logs/                         # Rotating log files
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx                   # Root router + ProtectedRoute
│   │   ├── main.jsx                  # React DOM entry point
│   │   ├── index.css                 # Tailwind base styles
│   │   ├── api/                      # Typed fetch wrappers per feature
│   │   ├── assets/                   # Static assets
│   │   ├── components/               # UI components
│   │   ├── context/                  # React Context providers
│   │   └── hooks/                    # Custom hooks
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── nginx.conf                    # Production NGINX config
│   └── Dockerfile
└── README.md
```

---

## 5. Backend — Deep Dive

### 5.1 Application Entry Point (`main.py`)

`main.py` creates the FastAPI application and wires everything together through an **async lifespan context manager** that runs at startup and shutdown.

**Startup sequence (in order):**

1. **Prisma connect** — establishes PostgreSQL connection (3 retries with backoff)
2. **Embedding warm-up** — runs a dummy ChromaDB query in a thread pool to preload the ONNX MiniLM model; prevents cold-start latency on first upload
3. **Reranker preload** — loads `BAAI/bge-reranker-large` into GPU/CPU memory
4. **Background worker task** — creates an `asyncio.Task` that processes the document job queue in the background
5. **Sandbox setup** — ensures isolated Python packages for code execution are installed; cleans up stale temp dirs from crashed sessions
6. **Output directories** — creates `output/podcasts`, `output/presentations`, `output/generated`, `output/explainers` if missing

**Shutdown sequence:**

1. Signals the background worker to drain (graceful shutdown with 30 s timeout)
2. Cancels the job processor task
3. Disconnects Prisma

**Middleware stack** (applied in registration order):

| Middleware | Purpose |
|---|---|
| `performance_monitoring_middleware` | Records request latency, logs slow requests |
| `rate_limit_middleware` | Token-bucket rate limiter (per-IP/user) |
| `log_requests` | Assigns a `X-Request-ID`, logs method/path/status/time |
| `CORSMiddleware` | Cross-origin requests from configured frontend origins |
| `TrustedHostMiddleware` | Production-only: blocks host-header injection |
| `limit_request_body` | Rejects bodies > 100 MB |

All 18 routes are registered with their respective `APIRouter` instances.

---

### 5.2 Configuration (`core/config.py`)

All configuration is driven by a **Pydantic `BaseSettings`** class named `Settings`, loaded from `.env` via `pydantic-settings`. A cached singleton `settings = get_settings()` is imported throughout the app.

**Key configuration groups:**

| Group | Key Variables |
|---|---|
| Auth | `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` (15), `REFRESH_TOKEN_EXPIRE_DAYS` (7) |
| Database | `DATABASE_URL` (PostgreSQL DSN) |
| ChromaDB | `CHROMA_DIR` (default `./data/chroma`) |
| LLM | `LLM_PROVIDER` (OLLAMA/GOOGLE/NVIDIA/MYOPENLM), model names, API keys |
| Embeddings | `EMBEDDING_MODEL` (BAAI/bge-m3), `EMBEDDING_DIMENSION` (1024) |
| Retrieval | `INITIAL_VECTOR_K` (10), `MMR_K` (8), `FINAL_K` (10), `MAX_CONTEXT_TOKENS` (6000) |
| Code Exec | `CODE_EXECUTION_TIMEOUT` (15 s), `MAX_CODE_REPAIR_ATTEMPTS` (3) |
| File Limits | `MAX_UPLOAD_SIZE_MB` (25) |
| Timeouts | `OCR_TIMEOUT_SECONDS` (300), `WHISPER_TIMEOUT_SECONDS` (600) |
| LLM Temperatures | Structured: 0.1, Chat: 0.2, Creative: 0.7, Code: 0.1 |

All relative paths in config are resolved to absolute paths at startup relative to the project root.

---

### 5.3 Database Layer

**PostgreSQL + Prisma ORM**

The app uses [`prisma-client-py`](https://prisma-client-py.readthedocs.io/) with asyncio interface. A single global `Prisma()` instance is exported from `db/prisma_client.py`.

```python
from app.db.prisma_client import prisma
user = await prisma.user.find_unique(where={"id": user_id})
```

**ChromaDB (Vector Database)**

`db/chroma.py` exports a `get_collection()` factory that returns a persistent ChromaDB `Collection`. All embedding operations use ChromaDB's **built-in ONNX MiniLM-L6-v2 model** (384-dimensional vectors) for consistency between writes and reads. Each stored chunk carries metadata for tenant isolation:

```python
{
  "material_id": "...",
  "user_id": "...",
  "notebook_id": "...",
  "filename": "...",
  "embedding_version": "bge_m3_v1"
}
```

Queries always filter by `user_id` to enforce per-user data isolation.

---

### 5.4 Authentication & Security

**JWT dual-token strategy:**

- **Access Token** — short-lived (15 min), sent as `Authorization: Bearer <token>` header
- **Refresh Token** — long-lived (7 days), stored as an `HttpOnly; SameSite=Lax` cookie (`path=/auth`); never accessible to JavaScript

**Refresh token rotation:** each use invalidates the old token and issues a new one. Reuse detection (stolen token) invalidates the entire token *family*.

**Password requirements** (enforced at Pydantic level):
- Minimum 8 characters
- At least one uppercase, one lowercase, one digit

**File token:** a short-lived (5 min) JWT for serving generated files (podcasts, slides) via proxy without leaking the main access token.

---

### 5.5 Routes (API Endpoints)

All routes require `Authorization: Bearer <access_token>` unless noted.

#### `/auth` — Authentication

| Method | Path | Description |
|---|---|---|
| POST | `/auth/signup` | Register new user |
| POST | `/auth/login` | Login, receive access token + set refresh cookie |
| POST | `/auth/refresh` | Exchange refresh cookie for new access token |
| POST | `/auth/logout` | Revoke refresh token, clear cookie |
| GET | `/auth/me` | Get current user profile |

#### `/notebooks` — Notebook Management

| Method | Path | Description |
|---|---|---|
| POST | `/notebooks` | Create notebook |
| GET | `/notebooks` | List user's notebooks (paginated) |
| GET | `/notebooks/{id}` | Get single notebook |
| PUT | `/notebooks/{id}` | Update name/description |
| DELETE | `/notebooks/{id}` | Delete notebook + cascade |
| GET | `/notebooks/{id}/content` | Get saved notebook content blocks |
| POST | `/notebooks/{id}/content` | Save a content block |

#### `/upload` & `/materials` — Material Ingestion

| Method | Path | Description |
|---|---|---|
| POST | `/upload` | Upload file (PDF, DOCX, PPTX, image, audio, video) |
| POST | `/upload/url` | Ingest from URL or YouTube link |
| POST | `/upload/text` | Ingest raw text |
| GET | `/materials` | List user's materials |
| GET | `/materials/{id}` | Get single material metadata |
| PUT | `/materials/{id}` | Update material title |
| DELETE | `/materials/{id}` | Delete material + embeddings |

#### `/chat` — AI Chat (SSE Streaming)

| Method | Path | Description |
|---|---|---|
| POST | `/chat` | Send message, receive SSE stream |
| GET | `/chat/sessions` | List sessions for a notebook |
| GET | `/chat/sessions/{id}/messages` | Get message history |
| POST | `/chat/session` | Create named session |
| DELETE | `/chat/sessions/{id}` | Delete session |
| POST | `/chat/block/followup` | Ask followup about a response block |
| GET | `/chat/suggestions` | Autocomplete suggestions |

#### `/agent` — Code & Research (SSE)

| Method | Path | Description |
|---|---|---|
| POST | `/agent/execute` | Run user-written Python code in sandbox |
| POST | `/agent/analyze` | NL → code → execute (data analysis) |
| POST | `/agent/research` | Deep web research agent |
| GET | `/agent/status/{job_id}` | Check execution status |

#### Content Generation

| Method | Path | Description |
|---|---|---|
| POST | `/quiz` | Generate MCQ quiz from material |
| POST | `/flashcard` | Generate flashcards from material |
| POST | `/presentation` | Generate HTML slide deck |
| POST | `/podcast` | Generate audio podcast + transcript |
| POST | `/explainer` | Generate narrated explainer video |

#### Utilities

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check (returns DB + service status) |
| GET | `/jobs/{id}` | Background job status |
| GET | `/models` | List available LLM models |
| GET | `/search` | Full-text search over materials |
| GET | `/proxy/file` | Serve generated files with file token auth |
| WS | `/ws/jobs/{user_id}` | WebSocket for real-time job updates |

---

### 5.6 Background Worker

`services/worker.py` runs as a single `asyncio.Task` created at app startup. It implements a **concurrent document processor** with the following behavior:

```
Startup
  └► Recover stuck jobs (jobs in 'processing' state > 30 min → reset to 'pending')
  └► Start infinite poll loop

Poll loop (every 2 seconds when idle):
  └► Fetch up to MAX_CONCURRENT_JOBS (5) pending jobs
  └► For each job:
      ├─ Claim it (status → 'processing')
      ├─ Route to handler:
      │   ├─ file material    → process_material_by_id()
      │   ├─ url material     → process_url_material_by_id()
      │   └─ text material    → process_text_material_by_id()
      ├─ On success → status → 'completed'
      └─ On failure → status → 'failed', store error message

Shutdown:
  └► Sets _shutdown_event, waits up to 30 s for in-flight jobs
```

An **event-driven notification** (`_JobQueue` class) allows the upload route to wake the worker immediately after creating a job, eliminating polling latency for fast uploads.

---

### 5.7 Material Processing Pipeline

Every material type shares the same five-step pipeline:

```
1. TEXT EXTRACTION
   ├─ PDF:   PyMuPDF (primary) → pdfplumber (tables) → pytesseract/EasyOCR (scanned images)
   ├─ DOCX:  python-docx
   ├─ PPTX:  python-pptx (text extraction only)
   ├─ Image: EasyOCR (GPU-accelerated OCR)
   ├─ Audio: OpenAI Whisper (local, GPU)
   ├─ Video: ffmpeg → audio strip → Whisper
   ├─ URL:   trafilatura (article) / BeautifulSoup (generic HTML) / Playwright (JS-heavy)
   └─ YouTube: youtube-transcript-api → yt-dlp (fallback)

2. TEXT CLEANING
   └─ sanitize_null_bytes(), strip boilerplate

3. CHUNKING (services/text_processing/chunker.py)
   └─ LangChain RecursiveCharacterTextSplitter
      ├─ chunk_size  = adaptive (based on content type)
      └─ chunk_overlap = 150 tokens (CHUNK_OVERLAP_TOKENS)
   └─ CSV/Excel/TSV: bypass chunking → stored as-is for data analysis

4. EMBEDDING & STORAGE
   ├─ ChromaDB upsert (ONNX MiniLM-L6-v2, batches of 200)
   └─ Full text saved to data/material_text/{material_id}.txt

5. STATUS UPDATE
   └─ Prisma: status → 'completed', chunk_count updated
   └─ WebSocket push: {"type": "material_update", "status": "completed"}
```

**Status lifecycle:**
```
pending → processing → [ocr_running | transcribing] → embedding → completed
                                                                 ↓ (on error)
                                                               failed
```

---

### 5.8 RAG Pipeline

The RAG pipeline lives in `services/rag/` and is called for every `QUESTION` intent in the agent.

```
User Query
    │
    ▼
1. VECTOR RETRIEVAL (secure_retriever.py)
   └─ ChromaDB query → top INITIAL_VECTOR_K (10) chunks
      filtered by user_id + material_ids

    │
    ▼
2. RERANKING (reranker.py)
   └─ BAAI/bge-reranker-large (cross-encoder)
   └─ Scores all candidates, keeps top FINAL_K (10)
   └─ Disabled if USE_RERANKER=false

    │
    ▼
3. MMR DIVERSITY (secure_retriever.py)
   └─ Maximal Marginal Relevance: λ=0.5
   └─ Reduces redundant chunks while preserving relevance

    │
    ▼
4. CONTEXT BUILDING (context_builder.py)
   └─ Truncates to MAX_CONTEXT_TOKENS (6000) using tiktoken
   └─ Filters chunks < MIN_CONTEXT_CHUNK_LENGTH (150 chars)
   └─ Attaches source metadata (filename, chunk position)

    │
    ▼
5. CITATION VALIDATION (citation_validator.py)
   └─ Validates source references in LLM response

    │
    ▼
6. LLM GENERATION
   └─ Prompt = system_prompt + context + conversation_history + user_query
   └─ Streaming response via SSE
```

**Similarity threshold:** chunks with score < `MIN_SIMILARITY_SCORE` (0.3) are filtered out before sending to the LLM.

---

### 5.9 LLM Service Layer

`services/llm_service/llm.py` provides a **provider factory** with four backends unified under the same LangChain interface.

```python
from app.services.llm_service.llm import get_llm, get_llm_structured

llm = get_llm()                    # chat temperature (0.2)
llm = get_llm_structured()         # structured output temperature (0.1)
llm = get_llm(temperature=0.7)     # creative temperature
```

**Provider implementations:**

| Provider | LangChain Class | Model Config |
|---|---|---|
| `OLLAMA` | `ChatOllama` | `OLLAMA_MODEL` (default: `llama3`) |
| `GOOGLE` | `ChatGoogleGenerativeAI` | `GOOGLE_MODEL` (default: `models/gemini-2.5-flash`) |
| `NVIDIA` | `ChatNVIDIA` | `NVIDIA_MODEL` (default: `qwen/qwen3.5-397b-a17b`) |
| `MYOPENLM` | Custom `LLM` subclass | `MYOPENLM_API_URL` + `MYOPENLM_MODEL` |

**LLM instance caching:** up to 16 LLM instances are cached by `(provider, temperature, max_tokens, top_p)` key to avoid re-initializing clients on every request.

**Structured output** (`structured_invoker.py`): wraps LLM calls with JSON schema enforcement and `json_repair` fallback for malformed outputs.

---

### 5.10 LangGraph Agent

The agent is KeplerLab's "brain" — every chat message passes through it. It is a **compiled LangGraph `StateGraph`** defined in `services/agent/graph.py`.

#### State (`AgentState` TypedDict)

```python
class AgentState(TypedDict):
    # Input
    user_message: str
    notebook_id: str
    user_id: str
    material_ids: List[str]
    session_id: str

    # Intent
    intent: str                 # QUESTION | DATA_ANALYSIS | RESEARCH |
                                # CODE_EXECUTION | FILE_GENERATION | CONTENT_GENERATION
    intent_confidence: float

    # Planning
    plan: List[Dict]            # Ordered tool call list
    current_step: int

    # Execution
    selected_tool: str
    tool_input: Dict
    tool_results: List[ToolResult]

    # Safety
    iterations: int             # Hard limit: MAX_AGENT_ITERATIONS
    total_tokens: int           # Hard limit: TOKEN_BUDGET
    needs_retry: bool
    stopped_reason: str
```

#### Graph Topology

```
START → intent_and_plan → tool_router → reflection ─┐
                                │                    │
                          (respond) ←────────────────┘ (continue loop)
                                │
                          response_generator → END
```

#### Node Descriptions

**`intent_and_plan`** (merged node):
1. **Intent detection** (`intent.py`): Uses fast regex rules first. If confidence < 0.85 on ANY rule, falls back to LLM classifier (fast MYOPENLM model). Intents in priority order:
   - `FILE_GENERATION` — "create CSV / export as Excel / draw a graph"
   - `DATA_ANALYSIS` — "analyze data / show chart / calculate average"
   - `CODE_EXECUTION` — "run Python / write a script"
   - `RESEARCH` — "search the web / latest news / investigate"
   - `CONTENT_GENERATION` — "make a quiz / generate flashcards / create podcast"
   - `QUESTION` — default fallback

2. **Planning** (`planner.py`): maps intent → ordered list of tool calls (e.g. QUESTION → [`rag_tool`], DATA_ANALYSIS → [`data_profiler`, `python_tool`])

**`tool_router`** (`router.py`): executes the next tool in the plan, updates state with `ToolResult`.

**`reflection`** (`reflection.py`): evaluates tool output. If failed and retries < 2, sets `needs_retry=True`. Otherwise sets `stopped_reason` and moves to response.

**`response_generator`**: synthesizes all successful `ToolResult` outputs into a final human-readable response. Handles special cases: DATA_ANALYSIS JSON pass-through for frontend chart rendering.

#### Available Tools

| Tool | Intent | Description |
|---|---|---|
| `rag_tool` | QUESTION | RAG retrieval + LLM answer |
| `python_tool` | CODE_EXEC / DATA_ANALYSIS | Sandbox Python execution |
| `data_profiler` | DATA_ANALYSIS | Reads CSV, profiles columns, feeds to python_tool |
| `file_generator` | FILE_GENERATION | Generates downloadable files (CSV, docx, etc.) |
| `workspace_builder` | CONTENT_GENERATION | Routes to quiz/flashcard/ppt/podcast generators |
| `research_tool` | RESEARCH | Web search + synthesis via external search service |

---

### 5.11 Content Generation Services

All generators follow the same pattern: **load full material text → build LLM prompt → call `get_llm_structured()` → parse JSON → return**.

#### Quiz Generator (`services/quiz/generator.py`)
- Parameters: `mcq_count` (1–50), `difficulty` (Easy/Medium/Hard), `additional_instructions`
- Output: JSON array of `{ question, options[4], correct_answer, explanation }`
- Backed by `quiz_prompt.txt` system prompt

#### Flashcard Generator (`services/flashcard/`)
- Output: JSON array of `{ front, back, hint? }`
- Backed by `flashcard_prompt.txt`

#### Presentation Generator (`services/ppt/generator.py`)
- Output: Full HTML presentation (custom CSS themes, slide animations)
- Parameters: `max_slides` (3–60), `theme` description, `additional_instructions`
- Themes: stored in `backend/app/themes/`
- Can generate 10+ slides with speaker notes

#### Podcast Generator (`services/podcast/generator.py`)
- Two-phase process:
  1. **Script generation** — LLM produces host/guest dialogue in JSON
  2. **TTS synthesis** — `edge-tts` generates separate MP3 per speaker, then concatenates with `pydub`
- Output: combined audio file + transcript JSON saved to `output/podcasts/`

#### Explainer Video (`services/explainer/`)
- Converts a saved presentation into a narrated video
- Per-slide: TTS narration → audio, LibreOffice renders slide thumbnails
- Chapters metadata for player navigation

---

### 5.12 Code Execution Sandbox

`services/code_execution/executor.py` provides isolated Python execution.

**Sandbox features:**
- Runs code in a subprocess (isolated process)
- Configurable timeout (default 15 s, max 120 s via API parameter)
- Captures `stdout`, `stderr`, `exit_code`
- Captures `matplotlib` chart output as `base64` data URI
- Temp directory per execution (`/tmp/kepler_sandbox_*`) → cleaned up after

**Code repair loop** (up to `MAX_CODE_REPAIR_ATTEMPTS = 3`):
```
Execute code
    ├─ Success → return result
    └─ Failure (stderr) → LLM repair using code_repair_prompt.txt
                          → re-execute patched code
                             ├─ Success → return result
                             └─ Still failing → return error after N attempts
```

**Security:**
- Packages installed in an isolated venv (`sandbox_env.py`)
- No network access from sandbox by default
- Stale sandbox dirs from previous crashes cleaned at startup

---

### 5.13 WebSocket Manager

`services/ws_manager.py` maintains a registry of active WebSocket connections keyed by `user_id` (supporting multiple tabs per user).

```python
# Subscribe
await ws_manager.connect(websocket, user_id)

# Broadcast to all tabs of a user
await ws_manager.send_to_user(user_id, {"type": "material_update", "status": "completed"})

# Cleanup
await ws_manager.disconnect(websocket, user_id)
```

**Message types:**
- `material_update` — emitted by the background worker on every status change
- `ping` — keepalive sent every 30 s to prevent connection timeouts

**Authentication:** JWT passed as `?token=` query parameter OR as the first WebSocket message `{"type": "auth", "token": "..."}`. 10 s timeout for first-message auth.

---

### 5.14 Middleware Stack

| Middleware | File | Behavior |
|---|---|---|
| Performance | `performance_logger.py` | Logs requests > 1 s as warnings; > 5 s as errors |
| Rate Limiter | `rate_limiter.py` | Token-bucket, per-IP/user; configurable burst limit |
| Request Logger | `main.py` | UUID request ID, logs all requests with timing |
| CORS | FastAPI built-in | Configurable origins via `CORS_ORIGINS` env var |
| Trusted Host | FastAPI built-in | Production-only host header validation |
| Body Size | `main.py` | 413 if `Content-Length` > 100 MB |

---

## 6. Database Schema

The Prisma schema defines 14 models. Here is the entity relationship:

```
User
 ├─── Notebook (1:N)
 │     ├─── Material (1:N)         ← uploaded files
 │     ├─── ChatSession (1:N)
 │     │     └─── ChatMessage (1:N)
 │     │           └─── ResponseBlock (1:N)  ← individual blocks in a response
 │     └─── GeneratedContent (1:N) ← quizzes, flashcards, presentations
 │           └─── ExplainerVideo (1:N)
 ├─── RefreshToken (1:N)           ← token rotation table
 ├─── BackgroundJob (1:N)          ← job queue for document processing
 ├─── UserTokenUsage (1:N)         ← LLM token consumption tracking
 ├─── ApiUsageLog (1:N)            ← audit log
 ├─── AgentExecutionLog (1:N)      ← LangGraph run logs
 ├─── CodeExecutionSession (1:N)   ← sandbox execution history
 └─── ResearchSession (1:N)        ← research agent run history
```

**Key model details:**

| Model | Important Fields |
|---|---|
| `Material` | `status` (enum: pending→completed), `sourceType` (file/url/youtube/text), `chunkCount`, `metadata` (JSON) |
| `ChatMessage` | `role` (user/assistant), `agentMeta` (JSON: intent, tools_used, step_log) |
| `GeneratedContent` | `contentType` (quiz/flashcard/presentation/podcast), `data` (JSON), `materialIds` (array) |
| `RefreshToken` | `family` (rotation group), `used` (boolean), `expiresAt` |
| `BackgroundJob` | `status`, `jobType` (material_processing), `payload` (JSON) |

---

## 7. Frontend — Deep Dive

### 7.1 App Structure & Routing

`App.jsx` defines routes using React Router 7:

```
/                    → HomePage (landing / notebook selector)
/auth                → AuthPage (login or signup)
/notebook/:id        → Workspace (ChatPanel + StudioPanel + Sidebar)
/notebook/draft      → Workspace (new, unsaved notebook)
/file/:token         → FileViewerPage (preview generated files)
```

All routes except `/auth` are wrapped in `ProtectedRoute` which checks `AuthContext.isAuthenticated`. Unauthenticated users are redirected to `/auth`.

The `Workspace` component handles loading a notebook from the URL `id` parameter, reconciling it with the global `AppContext` state, and rendering the two-panel layout.

### 7.2 Context Providers

Three contexts wrap the entire app:

**`AuthContext`** (`context/AuthContext.jsx`)
- Manages: `user`, `isAuthenticated`, `isLoading`
- Handles: login, signup, logout, token refresh (silent, on access token expiry)
- Auto-refreshes access token before expiry using the HttpOnly refresh cookie

**`AppContext`** (`context/AppContext.jsx`)
- Manages: `currentNotebook`, `materials`, `messages`, `currentMaterial`, `selectedSources`, `draftMode`
- Global state for the active workspace session

**`ThemeContext`** (`context/ThemeContext.jsx`)
- Manages: light/dark/system theme preference
- Persists to `localStorage`

### 7.3 Key Components

| Component | Description |
|---|---|
| `Header.jsx` | Top navigation, user avatar, theme toggle, notebook title |
| `Sidebar.jsx` | Material list, upload button, source selector for chat |
| `ChatPanel.jsx` | Chat UI, SSE stream handler, message rendering with `react-markdown` |
| `ChatMessage.jsx` | Renders individual messages; supports code blocks, charts (base64), citations |
| `StudioPanel.jsx` | Tabbed panel for Quiz, Flashcard, PPT, Podcast generation |
| `UploadDialog.jsx` | Upload modal: file drag-drop, URL input, text paste |
| `PresentationView.jsx` | Full-screen HTML slide viewer |
| `FileViewerPage.jsx` | Serve downloaded files (podcasts, presentations) via proxy token |
| `ExplainerDialog.jsx` | Configure and launch explainer video generation |
| `WebSearchDialog.jsx` | Trigger research agent from UI |
| `Modal.jsx` | Reusable modal container |
| `ErrorBoundary.jsx` | Catches React render errors, shows fallback UI |

### 7.4 API Layer

`src/api/` contains typed fetch wrappers organized by feature:

```
api/
├── auth.js         → login, signup, logout, refreshToken, getMe
├── notebooks.js    → create, list, get, update, delete notebook
├── materials.js    → upload, listMaterials, deleteMaterial, updateMaterial
├── chat.js         → sendMessage (SSE), getSessions, getMessages, clearSession
├── agent.js        → executeCode, analyzeData, research (SSE)
├── quiz.js         → generateQuiz
├── flashcard.js    → generateFlashcards
├── ppt.js          → generatePresentation
├── podcast.js      → generatePodcast
├── explainer.js    → generateExplainer
├── jobs.js         → getJobStatus
└── search.js       → searchMaterials
```

All API functions attach the `Authorization: Bearer` header from `AuthContext`. SSE endpoints use `EventSource` or `fetch` with `ReadableStream` for streaming.

---

## 8. End-to-End Data Flows

### 8.1 Material Upload & Processing

```
User selects file in UploadDialog
    │
    ▼
POST /upload (multipart/form-data)
    │
    ▼
File security validation (python-magic MIME check, size check)
    │
    ▼
Save raw file to data/uploads/{uuid}.{ext}
    │
    ▼
Create Material record (status=pending) in PostgreSQL
    │
    ▼
Create BackgroundJob record (status=pending)
    │
    ▼
Notify background worker via _JobQueue.notify()
    │
    ▼
Return 201 { material_id, job_id, status: "pending" }
    │
    │   (background, async)
    ▼
Worker picks up job
    │
    ├─ Text extraction (PDF/DOCX/audio/etc.)
    │   Status updates pushed via WebSocket:
    │   pending → processing → ocr_running/transcribing → embedding
    │
    ├─ Chunking (LangChain RecursiveCharacterTextSplitter)
    │
    ├─ Embed & upsert into ChromaDB (batch 200)
    │
    ├─ Save full text to data/material_text/{material_id}.txt
    │
    └─ Update Material: status=completed, chunkCount=N
       WS push: {"type": "material_update", "status": "completed"}
          │
          ▼
    Frontend Sidebar refreshes material list automatically
```

### 8.2 Chat / RAG Query

```
User types message → ChatPanel
    │
    ▼
POST /chat { message, material_ids, notebook_id, session_id }
    │
    ▼
Validate materials belong to user + are completed
    │
    ▼
LangGraph Agent: AgentState initialized
    │
    ▼
intent_and_plan:
  keyword regex rules → QUESTION intent (confidence 0.90)
    │
    ▼
tool_router: selects rag_tool
    │
    ▼
RAG Pipeline:
  1. ChromaDB query: top 10 chunks, filtered by user_id + material_ids
  2. Reranker: bge-reranker-large → scored, top 10
  3. MMR: remove redundant chunks
  4. Context builder: truncate to 6000 tokens
  5. Format retrieval prompt
    │
    ▼
LLM call (Ollama / Google / NVIDIA):
  system_prompt + context + conversation_history + user_message
    │
    ▼
SSE stream: token-by-token to browser
{ "type": "token", "content": "..." }
{ "type": "done", "session_id": "...", "sources": [...] }
    │
    ▼
Save ChatMessage to PostgreSQL (role=assistant, agentMeta=JSON)
```

### 8.3 Agent-Driven Requests

```
User: "Analyze the sales data in my CSV and show me a trend chart"
    │
    ▼
POST /chat or POST /agent/analyze
    │
    ▼
LangGraph Agent:
  intent_and_plan:
    keyword match: "analyze", "chart" → DATA_ANALYSIS (confidence 0.90)
    plan: [data_profiler, python_tool]
    │
    ▼
tool_router step 1: data_profiler
  - Reads CSV from data/material_text/{id}.txt
  - Profiles columns: types, nulls, sample values
  - Appends profile to state
    │
    ▼
tool_router step 2: python_tool
  - LLM generates pandas/matplotlib code using data profile
  - execute_code() runs in sandbox subprocess
  - Captures chart as base64 PNG
  - On failure: code_repair loop (up to 3 attempts)
    │
    ▼
reflection: success → respond
    │
    ▼
response_generator:
  - Wraps DATA_ANALYSIS JSON: { explanation, stdout, chart_base64 }
    │
    ▼
SSE stream → frontend ChartRenderer renders interactive chart
```

### 8.4 Content Generation (Quiz, Flashcard, PPT, Podcast)

```
User clicks "Generate Quiz" in StudioPanel
    │
    ▼
POST /quiz { material_ids, mcq_count: 10, difficulty: "Medium" }
    │
    ▼
Load full text from data/material_text/{id}.txt
    │
    ▼
get_llm_structured() with quiz_prompt.txt
    │
    ▼
LLM generates JSON: [{question, options[4], correct_answer, explanation}, ...]
    │
    ▼
json_repair() on malformed output
    │
    ▼
Return JSON to frontend
    │
    ▼
StudioPanel renders interactive quiz with score tracking
```

---

## 9. Security Design

| Threat | Mitigation |
|---|---|
| Unauthorized API access | JWT access tokens (15 min expiry), required on all endpoints |
| XSS token theft | Refresh token in HttpOnly cookie, never readable by JS |
| CSRF | SameSite=Lax cookie attribute |
| Token replay / theft | Refresh token rotation; reuse detection invalidates entire family |
| Host header injection | `TrustedHostMiddleware` in production |
| DoS via large bodies | 100 MB body size limit middleware |
| DoS via request rate | Token-bucket rate limiter per IP/user |
| Malicious file uploads | python-magic MIME validation (checked against actual file bytes, not just extension), MIME whitelist |
| Cross-user data leakage | `user_id` filter on all ChromaDB queries; Prisma queries always scope by `userId` |
| Code execution exploits | Sandboxed subprocess, configurable timeout, isolated package environment |
| Path traversal | `safe_path()` helper in route utils validates all file paths |
| Production credentials | API keys loaded from `.env`, never logged or returned in responses |

---

## 10. Configuration Reference

Create `backend/.env` with these variables:

```ini
# ── Required ──────────────────────────────────────────────
DATABASE_URL=postgresql://user:pass@localhost:5432/keplerlab
JWT_SECRET_KEY=<64-byte-random-string>

# ── LLM Provider (choose one) ────────────────────────────
LLM_PROVIDER=OLLAMA            # or GOOGLE, NVIDIA, MYOPENLM
OLLAMA_MODEL=llama3            # if OLLAMA

# For Google Gemini:
# LLM_PROVIDER=GOOGLE
# GOOGLE_API_KEY=AIza...
# GOOGLE_MODEL=models/gemini-2.5-flash

# For NVIDIA AI:
# LLM_PROVIDER=NVIDIA
# NVIDIA_API_KEY=nvapi-...
# NVIDIA_MODEL=qwen/qwen3.5-397b-a17b

# ── Optional ──────────────────────────────────────────────
ENVIRONMENT=development        # development | staging | production
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
CHROMA_DIR=./data/chroma
UPLOAD_DIR=./data/uploads
EMBEDDING_MODEL=BAAI/bge-m3
USE_RERANKER=true
MAX_UPLOAD_SIZE_MB=25
CODE_EXECUTION_TIMEOUT=15
MAX_CODE_REPAIR_ATTEMPTS=3
```

---

## 11. Deployment

### Development

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
prisma generate
prisma db push
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend
cd frontend
npm install
npm run dev       # starts on http://localhost:5173
```

### Production (Docker)

```bash
# Build and start all services
docker compose up --build -d

# Services:
#   backend  → http://localhost:8000
#   frontend → http://localhost (NGINX on port 80)
#   postgres → port 5432
#   redis    → port 6379
```

**NGINX configuration** (`frontend/nginx.conf`):
- Serves React SPA at `/`
- Proxies `/api/*` and `/ws/*` to backend at port 8000
- Handles SPA fallback routing (`try_files $uri /index.html`)

### Data Persistence

| Data | Location | Backup Strategy |
|---|---|---|
| PostgreSQL | Docker volume / external DB | `pg_dump` |
| ChromaDB vectors | `backend/data/chroma/` | `cli/backup_chroma.py` |
| Uploaded files | `backend/data/uploads/` | Filesystem backup |
| Material text | `backend/data/material_text/` | Filesystem backup |
| Generated output | `backend/output/` | Optional (regeneratable) |

**ChromaDB CLI tools** (`backend/cli/`):
```bash
python cli/backup_chroma.py    # Export all embeddings
python cli/restore_chroma.py   # Restore from backup
python cli/reindex.py           # Re-embed all materials
python cli/export_embeddings.py # Export as Parquet
```

### Health Check

```
GET /health
→ { "status": "ok", "database": "connected", "version": "2.0.0" }
```

---

*Documentation generated from source code analysis — KeplerLab AI Notebook v2.0.0*
