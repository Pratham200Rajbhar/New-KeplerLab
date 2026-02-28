# KeplerLab AI Notebook — Complete Project Documentation

> Version 2.0.0 | Last Updated: February 2026

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Core Features](#2-core-features)
3. [Tech Stack](#3-tech-stack)
4. [High-Level Architecture](#4-high-level-architecture)
5. [Directory Structure](#5-directory-structure)
6. [Backend — Deep Dive](#6-backend--deep-dive)
   - 6.1 [Application Entry Point (`main.py`)](#61-application-entry-point-mainpy)
   - 6.2 [Configuration (`core/config.py`)](#62-configuration-coreconfigpy)
   - 6.3 [Database Layer](#63-database-layer)
   - 6.4 [Routes (API Endpoints)](#64-routes-api-endpoints)
   - 6.5 [Services](#65-services)
   - 6.6 [Background Worker](#66-background-worker)
   - 6.7 [Middleware](#67-middleware)
7. [Document Processing Pipeline](#7-document-processing-pipeline)
8. [RAG (Retrieval-Augmented Generation) System](#8-rag-retrieval-augmented-generation-system)
9. [LangGraph Agent System](#9-langgraph-agent-system)
10. [LLM Provider Layer](#10-llm-provider-layer)
11. [Content Generation Features](#11-content-generation-features)
12. [Authentication & Security](#12-authentication--security)
13. [Frontend — Deep Dive](#13-frontend--deep-dive)
14. [Database Schema (Prisma)](#14-database-schema-prisma)
15. [API Reference](#15-api-reference)
16. [Data Flow Diagrams](#16-data-flow-diagrams)
17. [Configuration & Environment Variables](#17-configuration--environment-variables)
18. [Deployment](#18-deployment)
19. [Performance & Optimization](#19-performance--optimization)

---

## 1. Project Overview

**KeplerLab AI Notebook** is a full-stack, AI-powered educational platform. It lets users upload learning materials in virtually any format (PDF, DOCX, PPTX, audio, video, web pages, YouTube videos) and transforms them into interactive learning tools:

- Intelligent **RAG chat** with citations
- AI-generated **quizzes**, **flashcards**, and **presentations**
- Fully narrated **podcast-style audio** from documents
- **Explainer videos** with voice-over narration
- **Agentic chat** with intent-routing, code execution, file generation, and web research

All computation is scoped per user with full tenant isolation across both PostgreSQL (relational data) and ChromaDB (vector embeddings).

---

## 2. Core Features

| Feature | Description |
|---|---|
| **Smart Material Management** | Upload PDF, DOCX, PPTX, images, audio, video, URLs, YouTube links, or raw text. Automatic text extraction, OCR, and transcription. |
| **Notebook Organization** | Group related materials into notebooks by topic or course. |
| **Intelligent RAG Chat** | Ask questions about uploaded materials. Multi-source queries, reranked results, citation tracking. |
| **AI Quiz Generation** | Multiple-choice questions at easy/medium/hard difficulty, configurable count (1–50). |
| **AI Flashcard Generation** | Spaced-repetition-ready front/back cards from any material. |
| **AI Presentations** | Full HTML presentations with smart slide layouts, auto-fetched images. |
| **Live Podcast** | Host-guest dialogue audio with synchronized transcripts, chapters, bookmarks, annotations, and export to PDF/JSON. |
| **Explainer Videos** | Slide-by-slide narrated video generation with Edge TTS voices. |
| **Agent Chat** | LangGraph-powered chat agent with intent detection, code execution sandbox, data analysis (Pandas/Matplotlib), web research, and file generation. |
| **Multiple LLM Providers** | Ollama (local), Google Gemini, NVIDIA AI, custom API. Hot-swap without code changes. |
| **Token & Usage Tracking** | Per-user daily token consumption, API usage logs, agent execution logs. |
| **WebSocket Updates** | Real-time material processing status pushed to the browser. |

---

## 3. Tech Stack

### Backend

| Layer | Technology |
|---|---|
| Web Framework | FastAPI 0.115.6 (Python 3.11+) |
| ASGI Server | Uvicorn with standard extras |
| ORM | Prisma (async Python client) |
| Relational DB | PostgreSQL 15+ |
| Vector DB | ChromaDB 0.5.5 (ONNX MiniLM embeddings) |
| LLM Orchestration | LangChain 0.2.16 + LangGraph |
| LLM Providers | LangChain-Ollama, LangChain-Google-GenAI, LangChain-NVIDIA-AI-Endpoints |
| Embeddings | ChromaDB built-in ONNX (all-MiniLM-L6-v2, 384-dim) |
| Reranker | Cross-encoder reranker via `sentence-transformers` |
| Audio TTS | `edge-tts` (Microsoft Edge Neural Voices) |
| Speech Transcription | OpenAI Whisper |
| PDF Extraction | PyMuPDF + pypdf + pdfplumber |
| OCR | Tesseract (pytesseract) + EasyOCR |
| Document Parsing | python-docx, python-pptx, openpyxl |
| Web Scraping | BeautifulSoup4 + Selenium + Playwright |
| YouTube | yt-dlp + youtube-transcript-api |
| Data Analysis | Pandas + NumPy + Matplotlib (sandboxed) |
| Validation | Pydantic v2 |
| Auth | JWT (access) + HttpOnly cookie (refresh) + bcrypt |

### Frontend

| Layer | Technology |
|---|---|
| Framework | React 19.2.0 |
| Build Tool | Vite 7.2.4 |
| Routing | React Router 7.11.0 |
| Styling | Tailwind CSS 3.4.19 |
| HTTP Client | Fetch API (custom wrappers in `src/api/`) |
| Real-time | WebSocket (native browser API) |
| Audio | Web Audio API |
| Markdown | react-markdown |

### Infrastructure

| Component | Technology |
|---|---|
| Containerization | Docker + Docker Compose |
| Web Server / Reverse Proxy | NGINX |
| Caching Layer | Redis |

---

## 4. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         BROWSER (React SPA)                         │
│                                                                     │
│  ┌──────────┐  ┌───────────┐  ┌────────────┐  ┌────────────────┐  │
│  │ AuthPage │  │  Sidebar  │  │ ChatPanel  │  │  StudioPanel   │  │
│  │  Signup  │  │ (Sources) │  │ (RAG/Agent)│  │ (Quiz,PPT,Pod) │  │
│  │  Login   │  └───────────┘  └────────────┘  └────────────────┘  │
│  └──────────┘                                                       │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ HTTPS REST + SSE + WebSocket
┌──────────────────────────▼──────────────────────────────────────────┐
│                      FASTAPI BACKEND (:8000)                        │
│                                                                     │
│  ┌─────┐ ┌────────┐ ┌──────┐ ┌──────┐ ┌─────┐ ┌─────┐ ┌──────┐  │
│  │Auth │ │Upload  │ │Chat  │ │Quiz  │ │PPT  │ │Pod. │ │Agent │  │
│  │Route│ │Route   │ │Route │ │Route │ │Route│ │Route│ │Route │  │
│  └──┬──┘ └───┬────┘ └──┬───┘ └──┬───┘ └──┬──┘ └──┬──┘ └──┬───┘  │
│     │        │         │        │         │       │        │       │
│  ┌──▼────────▼─────────▼────────▼─────────▼───────▼────────▼────┐  │
│  │                      SERVICE LAYER                            │  │
│  │  Auth | Material | RAG | LLM | Agent | TTS | Worker | WS     │  │
│  └────────────────────┬───────────────────────────────────────┘  │
│                        │                                           │
└────────────────────────┼───────────────────────────────────────────┘
                         │
        ┌────────────────┼───────────────────────┐
        ▼                ▼                        ▼
┌──────────────┐  ┌──────────────┐   ┌──────────────────────────┐
│  PostgreSQL  │  │   ChromaDB   │   │   File System (./data/)  │
│  (Prisma)    │  │  (Vectors)   │   │   uploads/, material_txt/│
│  All records │  │  Embeddings  │   │   models/, output/       │
└──────────────┘  └──────────────┘   └──────────────────────────┘
```

---

## 5. Directory Structure

```
KeplerLab-AI-Notebook/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app, lifespan, middleware, router registration
│   │   ├── core/
│   │   │   ├── config.py            # Pydantic Settings (env vars)
│   │   │   └── utils.py             # Shared utilities
│   │   ├── db/
│   │   │   ├── chroma.py            # ChromaDB client singleton
│   │   │   └── prisma_client.py     # Prisma async client singleton
│   │   ├── models/                  # Pydantic response/request models (shared)
│   │   ├── prompts/                 # LLM prompt templates (.txt files)
│   │   │   ├── chat_prompt.txt
│   │   │   ├── quiz_prompt.txt
│   │   │   ├── flashcard_prompt.txt
│   │   │   ├── ppt_prompt.txt
│   │   │   ├── podcast_script_prompt.txt
│   │   │   ├── podcast_qa_prompt.txt
│   │   │   ├── data_analysis_prompt.txt
│   │   │   ├── code_generation_prompt.txt
│   │   │   └── code_repair_prompt.txt
│   │   ├── routes/                  # FastAPI routers (one file per feature)
│   │   │   ├── auth.py              # /auth/*
│   │   │   ├── notebook.py          # /notebooks/*
│   │   │   ├── upload.py            # /upload, /materials/*
│   │   │   ├── chat.py              # /chat
│   │   │   ├── quiz.py              # /quiz
│   │   │   ├── flashcard.py         # /flashcard
│   │   │   ├── ppt.py               # /presentation
│   │   │   ├── podcast_live.py      # /podcast/*
│   │   │   ├── explainer.py         # /explainer/*
│   │   │   ├── agent.py             # /agent/*
│   │   │   ├── search.py            # /search
│   │   │   ├── jobs.py              # /jobs/*
│   │   │   ├── models.py            # /models (LLM info)
│   │   │   ├── health.py            # /health
│   │   │   ├── proxy.py             # /proxy (image proxy)
│   │   │   ├── websocket_router.py  # /ws
│   │   │   └── utils.py             # Route helper functions
│   │   └── services/
│   │       ├── agent/               # LangGraph agent (intent→plan→execute→reflect)
│   │       │   ├── graph.py         # StateGraph wiring
│   │       │   ├── intent.py        # Intent classifier
│   │       │   ├── planner.py       # Execution planner
│   │       │   ├── router.py        # Tool router
│   │       │   ├── reflection.py    # Self-reflection / retry logic
│   │       │   ├── state.py         # AgentState TypedDict
│   │       │   ├── persistence.py   # Chat session persistence
│   │       │   ├── tools_registry.py
│   │       │   ├── tools/
│   │       │   │   ├── code_repair.py
│   │       │   │   ├── data_profiler.py
│   │       │   │   ├── file_generator.py
│   │       │   │   └── workspace_builder.py
│   │       │   └── subgraphs/
│   │       │       └── research_graph.py # Deep web-research sub-agent
│   │       ├── auth/                # JWT, bcrypt, token rotation
│   │       ├── chat/                # Chat session service
│   │       ├── code_execution/      # Sandboxed Python executor
│   │       ├── explainer/           # Explainer video processor + TTS
│   │       ├── flashcard/           # Flashcard generator
│   │       ├── llm_service/
│   │       │   ├── llm.py           # LLM factory (Ollama/Google/NVIDIA/Custom)
│   │       │   ├── llm_schemas.py   # Structured output schemas
│   │       │   └── structured_invoker.py
│   │       ├── podcast/             # Podcast session, TTS, export
│   │       ├── ppt/                 # Presentation generator
│   │       ├── quiz/                # Quiz generator
│   │       ├── rag/
│   │       │   ├── embedder.py      # ChromaDB upsert
│   │       │   ├── reranker.py      # Cross-encoder reranker
│   │       │   ├── secure_retriever.py  # Tenant-isolated query
│   │       │   ├── context_builder.py
│   │       │   ├── context_formatter.py # Citation formatting
│   │       │   └── citation_validator.py
│   │       ├── text_processing/
│   │       │   ├── chunker.py       # Structure-aware text splitter
│   │       │   ├── extractor.py     # Unified extraction dispatcher
│   │       │   ├── file_detector.py # MIME type detection
│   │       │   ├── ocr_service.py   # Tesseract + EasyOCR
│   │       │   ├── pdf_extractor.py # Multi-strategy PDF extraction
│   │       │   ├── table_extractor.py
│   │       │   ├── transcription_service.py # Whisper ASR
│   │       │   ├── web_scraping.py
│   │       │   ├── youtube_service.py
│   │       │   └── resilient_runner.py
│   │       ├── audit_logger.py      # API usage audit
│   │       ├── file_validator.py    # Secure file upload validator
│   │       ├── gpu_manager.py       # GPU availability detection
│   │       ├── job_service.py       # BackgroundJob CRUD
│   │       ├── material_service.py  # Full material lifecycle
│   │       ├── model_manager.py     # Model download/management
│   │       ├── notebook_name_generator.py
│   │       ├── notebook_service.py
│   │       ├── performance_logger.py
│   │       ├── rate_limiter.py
│   │       ├── storage_service.py   # File-system text storage
│   │       ├── token_counter.py
│   │       ├── worker.py            # Async background job processor
│   │       └── ws_manager.py        # WebSocket connection manager
│   ├── cli/                         # CLI tools (backup, reindex, export)
│   ├── data/
│   │   ├── chroma/                  # ChromaDB persistent storage
│   │   ├── material_text/           # Full extracted text files
│   │   ├── models/                  # Downloaded model weights
│   │   ├── output/                  # Generated files
│   │   └── uploads/                 # User-uploaded raw files
│   ├── logs/                        # Rotating log files
│   ├── output/                      # Presentations, podcasts, explainers
│   ├── prisma/
│   │   └── schema.prisma            # Database schema
│   ├── templates/                   # HTML/CSS templates
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx                  # Root component, routing
│   │   ├── main.jsx                 # React entry point
│   │   ├── index.css                # Tailwind base styles
│   │   ├── api/                     # REST client wrappers
│   │   │   ├── auth.js
│   │   │   ├── chat.js
│   │   │   ├── generation.js
│   │   │   ├── materials.js
│   │   │   ├── notebooks.js
│   │   │   ├── jobs.js
│   │   │   ├── agent.js
│   │   │   ├── explainer.js
│   │   │   ├── podcast.js
│   │   │   └── config.js            # Base URL config
│   │   ├── components/
│   │   │   ├── AuthPage.jsx         # Login / Signup
│   │   │   ├── HomePage.jsx         # Landing / notebook list
│   │   │   ├── Header.jsx           # Top nav
│   │   │   ├── Sidebar.jsx          # Material sources panel
│   │   │   ├── ChatPanel.jsx        # Main chat interface
│   │   │   ├── StudioPanel.jsx      # Content generation tabs
│   │   │   ├── ChatMessage.jsx      # Message renderer
│   │   │   ├── UploadDialog.jsx     # Upload modal
│   │   │   ├── WebSearchDialog.jsx
│   │   │   ├── ExplainerDialog.jsx
│   │   │   ├── PresentationView.jsx # Slide viewer
│   │   │   ├── FileViewerPage.jsx   # Raw file viewer
│   │   │   ├── SourceItem.jsx       # Material list item
│   │   │   ├── FeatureCard.jsx
│   │   │   ├── Modal.jsx
│   │   │   ├── ErrorBoundary.jsx
│   │   │   ├── chat/                # Chat sub-components
│   │   │   └── podcast/             # Podcast player components
│   │   ├── context/
│   │   │   ├── AppContext.jsx        # Global notebook/material state
│   │   │   ├── AuthContext.jsx       # Auth state (user, tokens)
│   │   │   ├── ThemeContext.jsx      # Dark/light mode
│   │   │   └── PodcastContext.jsx    # Podcast session state
│   │   └── hooks/
│   │       ├── useMaterialUpdates.js  # WebSocket listener for material status
│   │       ├── useMicInput.js         # Microphone recording
│   │       ├── usePodcastPlayer.js    # Audio playback logic
│   │       └── usePodcastWebSocket.js # Podcast real-time events
│   ├── index.html
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── nginx.conf
│   └── Dockerfile
└── docker-compose.yml (not shown but implied)
```

---

## 6. Backend — Deep Dive

### 6.1 Application Entry Point (`main.py`)

The application lifecycle (managed by FastAPI's `asynccontextmanager` `lifespan`) performs these startup steps in order:

1. **Connect to PostgreSQL** via Prisma async client.
2. **Warm up ChromaDB ONNX embedding model** — a dummy query forces the ONNX runtime to pre-load `all-MiniLM-L6-v2` so the first real upload doesn't stall.
3. **Preload cross-encoder reranker** model into memory.
4. **Start background job processor** as an `asyncio.Task` — this is the document processing worker loop.
5. **Install sandbox Python packages** — ensures the code execution sandbox has required packages.
6. **Clean up stale sandbox temp dirs** from any previous crash (`/tmp/kepler_sandbox_*`, `/tmp/kepler_analysis_*`).
7. **Create output directories** (`output/generated`, `output/presentations`, `output/explainers`, `output/podcast`).

**Middleware stack** (applied in order):
- `TrustedHostMiddleware` — blocks requests with invalid Host headers
- `CORSMiddleware` — configurable allowed origins from `settings.CORS_ORIGINS`
- `rate_limit_middleware` — in-memory sliding-window rate limiter
- `performance_monitoring_middleware` — logs slow requests

**Router registration** — every feature is a separate `APIRouter` included with appropriate prefixes:

```
/auth/*         → auth_router
/notebooks/*    → notebook_router
/upload, /materials/* → upload_router
/chat, /chat/*  → chat_router
/quiz           → quiz_router
/flashcard      → flashcard_router
/presentation   → ppt_router
/podcast/*      → podcast_live_router
/explainer/*    → explainer_router
/agent/*        → agent_router
/search         → search_router
/jobs/*         → jobs_router
/models         → models_router
/health         → health_router
/proxy          → proxy_router
/ws             → ws_router (WebSocket)
```

---

### 6.2 Configuration (`core/config.py`)

Uses `pydantic-settings` `BaseSettings` — every value can be overridden by an environment variable or `.env` file.

**Key setting groups:**

| Group | Key Settings |
|---|---|
| **Environment** | `ENVIRONMENT`, `DEBUG` |
| **Database** | `DATABASE_URL` (PostgreSQL asyncpg URL) |
| **Vector DB** | `CHROMA_DIR` |
| **File Storage** | `UPLOAD_DIR`, `MAX_UPLOAD_SIZE_MB` (default 25 MB) |
| **JWT / Auth** | `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` (15 min), `REFRESH_TOKEN_EXPIRE_DAYS` (7 days) |
| **LLM** | `LLM_PROVIDER` (OLLAMA/GOOGLE/NVIDIA/MYOPENLM), model names, API keys |
| **LLM Generation** | `LLM_TEMPERATURE_STRUCTURED` (0.1), `LLM_TEMPERATURE_CHAT` (0.2), `LLM_TEMPERATURE_CREATIVE` (0.7), `LLM_MAX_TOKENS` (4000) |
| **Embeddings** | `EMBEDDING_MODEL` (BAAI/bge-m3), `EMBEDDING_DIMENSION` (1024) |
| **Chunking** | `CHUNK_OVERLAP_TOKENS` (150), `MIN_CHUNK_LENGTH` (100) |
| **Code Execution** | `MAX_CODE_REPAIR_ATTEMPTS` (3), `CODE_EXECUTION_TIMEOUT` (15 s) |

---

### 6.3 Database Layer

#### PostgreSQL via Prisma

- **Client**: `prisma-client-py` in asyncio mode
- **Global singleton**: `app/db/prisma_client.py` exposes `prisma`, `connect_db()`, `disconnect_db()`
- **Schema file**: `backend/prisma/schema.prisma`

#### ChromaDB

- **Client**: `app/db/chroma.py` exposes a `get_collection()` singleton that returns the single shared collection.
- **Storage**: `./data/chroma/` (SQLite + binary index files)
- **Embeddings**: ChromaDB's built-in ONNX runtime (`all-MiniLM-L6-v2`, 384-dim)
- **Tenant isolation**: every document chunk is tagged with `user_id` and `material_id` metadata; all queries include `where={"user_id": user_id}` filter.

#### File System Storage

Full extracted text is **not** stored in PostgreSQL (too large). Instead:

- `data/material_text/{material_id}.txt` — full extracted text
- `data/uploads/{uuid}_{filename}` — raw uploaded files
- `data/output/` — generated presentations, podcasts, explainer videos

`storage_service.py` manages read/write/delete for all these files.

---

### 6.4 Routes (API Endpoints)

#### `auth.py` — Authentication

| Method | Path | Description |
|---|---|---|
| `POST` | `/auth/signup` | Register user. Validates email, password complexity (min 8 chars, upper, lower, digit), username (2–50 chars). Stores bcrypt hash. |
| `POST` | `/auth/login` | Authenticate user. Returns JWT access token in response body + HttpOnly refresh token cookie (path `/auth`). |
| `POST` | `/auth/refresh` | Rotate refresh token. Reads cookie, validates, issues new access + refresh tokens. |
| `POST` | `/auth/logout` | Revoke refresh token family, clear cookie. |
| `GET` | `/auth/me` | Return current user profile. |

#### `upload.py` — Material Ingestion

| Method | Path | Description |
|---|---|---|
| `POST` | `/upload` | Upload a file (PDF/DOCX/PPTX/image/audio/video/CSV/Excel). Saved to disk, a `BackgroundJob` + `Material` record created, worker notified. |
| `POST` | `/upload/url` | Ingest a web URL or YouTube link. |
| `POST` | `/upload/text` | Ingest pasted raw text. |
| `GET` | `/materials` | List user materials (optionally filtered by notebook). |
| `DELETE` | `/materials/{id}` | Delete material, all its ChromaDB chunks, and its text file. |
| `PUT` | `/materials/{id}` | Update material metadata (title, notebook). |

Security: every uploaded file goes through `file_validator.py` — `python-magic` header inspection, MIME whitelist check, filename sanitization.

#### `chat.py` — Conversational Chat

| Method | Path | Description |
|---|---|---|
| `POST` | `/chat` | Main chat endpoint. Resolves materials, validates ownership, filters completed ones, then delegates to the **LangGraph agent** for intent-aware response. Supports SSE streaming. |
| `GET` | `/chat/history/{notebook_id}` | Return chat sessions + messages for a notebook. |
| `GET` | `/chat/sessions/{notebook_id}` | List chat sessions. |
| `POST` | `/chat/sessions` | Create a new chat session. |
| `DELETE` | `/chat/sessions/{session_id}` | Delete a session and all its messages. |
| `POST` | `/chat/block-followup` | Ask a follow-up question on a specific response block. |

#### `quiz.py`

`POST /quiz` — accepts `material_ids`, `mcq_count` (1–50), `difficulty` (Easy/Medium/Hard), optional `topic` and `additional_instructions`. Calls `quiz/generator.py` synchronously in a thread-pool executor (blocking LLM call).

#### `flashcard.py`

`POST /flashcard` — same pattern as quiz. Returns JSON array of `{front, back}` cards.

#### `ppt.py` — Presentation Generation

`POST /presentation` — generates a full HTML presentation from material text. Accepts `max_slides` (3–60), `theme` string, `additional_instructions`. Returns JSON with slides array and raw HTML.

#### `podcast_live.py` — Live Podcast

Full podcast lifecycle:

| Method | Path | Description |
|---|---|---|
| `POST` | `/podcast/sessions` | Create podcast session (mode, topic, language, voices, material_ids). |
| `POST` | `/podcast/sessions/{id}/generate` | Start async script + audio generation. |
| `GET` | `/podcast/sessions` | List user's podcast sessions. |
| `GET` | `/podcast/sessions/{id}` | Get session details + segments. |
| `POST` | `/podcast/sessions/{id}/question` | Ask a live question, generate clarification audio. |
| `POST` | `/podcast/sessions/{id}/bookmark` | Bookmark a segment. |
| `POST` | `/podcast/sessions/{id}/annotation` | Annotate a segment. |
| `POST` | `/podcast/sessions/{id}/export` | Export as PDF or JSON. |
| `GET` | `/podcast/audio/{session_id}/{segment_idx}` | Stream segment audio file. |
| `GET` | `/podcast/voices/{language}` | List available neural voices for a language. |

Supported podcast modes: `overview`, `deep-dive`, `debate`, `q-and-a`, `full`, `topic`.

#### `explainer.py` — Explainer Videos

| Method | Path | Description |
|---|---|---|
| `POST` | `/explainer/check-presentations` | Check if PPTs already exist for given materials. |
| `POST` | `/explainer/generate` | Start video generation (creates/reuses PPT, generates narration audio per slide, assembles video). |
| `GET` | `/explainer/{id}/status` | Poll generation progress. |
| `GET` | `/explainer/{id}/video` | Download finished video file. |

#### `agent.py` / `websocket_router.py`

`agent.py` exposes agentic endpoints (code execution, data analysis, research results). `websocket_router.py` manages the single `/ws` WebSocket endpoint for real-time material processing updates.

---

### 6.5 Services

#### `material_service.py`

The core of the document processing pipeline. Handles:
- Creating `Material` + `BackgroundJob` database records
- Dispatching to `text_processing.extractor`
- Chunking via `chunker.py`
- Embedding + storing via `rag/embedder.py`
- Status transitions (`pending → processing → ocr_running/transcribing → embedding → completed/failed`)
- WebSocket status pushes via `ws_manager`
- Full text stored on disk via `storage_service.py`

#### `auth/` service

- `register_user()` — duplicate email check, bcrypt hash, Prisma insert
- `authenticate_user()` — lookup + `bcrypt.checkpw`
- `create_access_token()` / `create_refresh_token()` — JWT generation
- `store_refresh_token()` — hash + Prisma insert with token family
- `validate_and_rotate_refresh_token()` — family-based rotation (detect reuse attacks)
- `get_current_user()` — FastAPI dependency, validates Bearer token from `Authorization` header

#### `rag/` services

See [Section 8](#8-rag-retrieval-augmented-generation-system) for details.

#### `llm_service/llm.py`

- `get_llm()` — returns a LangChain chat model configured for chat temperature
- `get_llm_structured()` — lower temperature (0.1) for deterministic JSON outputs
- Internal LRU cache (max 16 instances) prevents re-instantiation
- Supports: `OLLAMA`, `GOOGLE`, `NVIDIA`, `MYOPENLM`

#### `worker.py` — Background Job Processor

Single `asyncio.Task` running an infinite loop:
1. At startup: resets jobs stuck in `processing` state (crash recovery)
2. Polls for `pending` jobs every 2 seconds (or wakes immediately on `_job_queue.notify()`)
3. Runs up to `MAX_CONCURRENT_JOBS` (5) jobs concurrently via asyncio semaphore
4. Dispatches to `process_material_by_id`, `process_url_material_by_id`, or `process_text_material_by_id` based on job type
5. Marks job `completed` or `failed`
6. Never crashes the loop — all exceptions caught and stored in the job record

#### `ws_manager.py`

Maintains a `dict[user_id → list[WebSocket]]` of active connections. `send_to_user(user_id, payload)` broadcasts JSON to all open connections for a given user. Used to push real-time `material_update` events (status changes) without polling.

#### `rate_limiter.py`

Sliding-window in-memory rate limiter using a `deque` of timestamps per IP. Plugged as ASGI middleware.

#### `performance_logger.py`

ASGI middleware that logs request duration. Flags requests over a configurable threshold as slow.

#### `audit_logger.py`

Writes `ApiUsageLog` records to PostgreSQL for every LLM call: endpoint, material IDs, context/response token counts, model used, LLM latency, retrieval latency, total latency.

---

### 6.6 Background Worker

```
[Upload Route]
     │
     ▼ create BackgroundJob (status=pending) + Material (status=pending)
     │ notify _job_queue

[job_processor loop (asyncio.Task)]
     │
     ▼ fetch_next_pending_job()
     │ acquire semaphore (max 5 concurrent)
     │
     ▼ process_material_by_id(material_id)
         │
         ▼ _set_status("processing")
         │ extractor.extract_text(file_path)
         │   ├── PDF → PyMuPDF / pdfplumber / OCR fallback
         │   ├── DOCX → python-docx
         │   ├── Audio/Video → Whisper transcription
         │   ├── Image → OCR (Tesseract/EasyOCR)
         │   ├── URL → web_scraping / Playwright
         │   └── YouTube → yt-dlp + transcript API
         │
         ▼ _set_status("embedding")
         │ save_material_text(material_id, full_text)
         │ chunk_text(full_text)
         │ embed_and_store(chunks, material_id, user_id, notebook_id)
         │   └── ChromaDB collection.upsert() in batches of 200
         │
         ▼ _set_status("completed", chunkCount=N)
         │ ws_manager.send_to_user(user_id, material_update)
```

---

### 6.7 Middleware

```
Request → TrustedHostMiddleware
        → CORSMiddleware
        → rate_limit_middleware
        → performance_monitoring_middleware
        → FastAPI Router
```

---

## 7. Document Processing Pipeline

### Supported Input Types

| Format | Processing Method |
|---|---|
| PDF | PyMuPDF (digital) → pdfplumber (tables) → OCR fallback (scanned) |
| DOCX | python-docx paragraph extraction |
| PPTX | python-pptx slide text extraction |
| Images (JPG/PNG/TIFF/BMP/WEBP) | Tesseract OCR + EasyOCR |
| Audio (MP3/WAV/M4A/OGG/FLAC) | OpenAI Whisper ASR |
| Video (MP4/MOV/AVI/MKV) | ffmpeg audio extraction → Whisper |
| CSV / Excel (XLS/XLSX/ODS/TSV) | Pandas DataFrame parsing |
| Web URL | BeautifulSoup4 + Playwright screenshot |
| YouTube | yt-dlp download → Whisper, or youtube-transcript-api |
| Raw Text | Direct storage |

### Chunking Strategy (`text_processing/chunker.py`)

The chunker uses a **structure-aware** strategy:

1. **Structured data** (CSV/Excel): split on `===` separators from the spreadsheet extractor. Schema header prepended to each chunk. Full dataset also stored on disk and expanded at retrieval time.

2. **Markdown/structured prose** (digital PDFs, DOCX):
   - Split by Markdown headings (`#`, `##`, `###`, `####`)
   - Within each section: split large paragraphs on sentence boundaries
   - `CHUNK_OVERLAP_CHARS` (600 chars = 150 tokens) carried over between chunks

3. **Plain prose** (no headings): whole text treated as one section, paragraph/sentence splitting applied.

**Quality filters**: discard chunks below `MIN_CHUNK_CHARS` (100) or with less than 10% alphabetic content.

**Chunk size targets**: 500 tokens (~2000 chars) target, 150-token overlap.

Each chunk dict contains: `id` (UUID), `text`, `chunk_index`, `total_chunks`.

---

## 8. RAG (Retrieval-Augmented Generation) System

### Embedding & Storage

`rag/embedder.py`:
- Uses **ChromaDB's built-in ONNX model** (`all-MiniLM-L6-v2`, 384-dim) — no external embedding server needed
- `embed_and_store()` uses `collection.upsert()` for idempotent re-processing
- Batches of 200 chunks, 3 retries per batch
- Metadata attached per chunk: `user_id`, `material_id`, `notebook_id`, `filename`, `source`, `chunk_index`, `total_chunks`

### Secure Retrieval (`rag/secure_retriever.py`)

Every query enforces `user_id` filter — the only sanctioned entry point for similarity search.

**Retrieval algorithm:**

1. **Per-material retrieval**: for each material in the query, retrieve up to `DEFAULT_PER_MATERIAL_K` (10) or `CROSS_DOC_PER_MATERIAL_K` (15) chunks
2. **Cross-document query detection**: keywords like "compare", "contrast", "difference" trigger cross-doc mode
3. **MMR (Maximal Marginal Relevance)**: diversity control to avoid redundant chunks
4. **Cross-encoder reranking** (`rag/reranker.py`): reorder chunks by semantic similarity to the full query (not just vector distance)
5. **Source diversity caps**: min 1 / max 3 chunks per material to prevent any one source dominating
6. **Structured data expansion**: CSV/Excel chunks swap out their summary placeholder for the full dataset (capped at 50,000 chars)

### Context Building (`rag/context_builder.py` + `context_formatter.py`)

- Assembles retrieved chunks into a numbered context block
- Each chunk annotated with `[Source N]` citations
- `citation_validator.py` strips hallucinated in-line citations not backed by actual retrieved sources

### Chat Prompt

`prompts/chat_prompt.txt` instructs the LLM to:
- Answer only from provided context
- Reference sources using `[Source N]` notation
- Admit when the context doesn't have enough information

---

## 9. LangGraph Agent System

The chat endpoint delegates to a **LangGraph state machine** rather than a simple RAG chain. This enables multi-step reasoning, intent-aware routing, and tool execution.

### State Schema (`agent/state.py`)

```python
class AgentState(TypedDict):
    user_message: str
    notebook_id: str
    user_id: str
    material_ids: List[str]
    session_id: str
    intent: str           # QUESTION | DATA_ANALYSIS | RESEARCH | CODE_EXECUTION | FILE_GENERATION | CONTENT_GENERATION
    intent_confidence: float
    plan: List[Dict]      # Ordered tool call plan
    current_step: int
    selected_tool: str
    tool_input: Dict
    tool_results: List[ToolResult]
    needs_retry: bool
    iterations: int       # Hard cap: MAX_AGENT_ITERATIONS
    total_tokens: int     # Hard cap: TOKEN_BUDGET
    stopped_reason: str
    ...
```

### Graph Topology

```
[user message]
      │
      ▼
intent_and_plan ─── merged node (intent detection + execution planning)
      │
      ▼
tool_router ──────── executes the next planned tool
      │
      ▼
reflection ──────────decides: continue (retry/next step) or respond
    │            │
    │ continue   │ respond
    ▼            ▼
tool_router  generate_response ──► [final answer to user]
```

**Hard limits:**
- `MAX_AGENT_ITERATIONS`: prevents infinite loops
- `TOKEN_BUDGET`: prevents runaway token consumption

### Intent Detection (`agent/intent.py`)

Priority-ordered keyword rules (`_INTENT_RULES`) checked via regex with confidence thresholds:

| Intent | Confidence | Example Triggers |
|---|---|---|
| `FILE_GENERATION` | 0.92 | "create a CSV", "generate a report", "save as Excel" |
| `DATA_ANALYSIS` | 0.90 | "csv", "average", "plot", "visualize", "histogram" |
| `CODE_EXECUTION` | 0.90 | "run python", "write a script", "execute code" |
| `RESEARCH` | 0.90 | "research", "search the web", "latest news" |
| `CONTENT_GENERATION` | 0.92 | "make a quiz", "create flashcards", "generate slides" |
| `QUESTION` | 0.50 | fallback — any message |

When keyword confidence is below threshold, the LLM (`MYOPENLM` fast model) is called for classification.

### Execution Planner (`agent/planner.py`)

Maps intent to an ordered plan of tool calls:
- `QUESTION` → `[rag_search]`
- `DATA_ANALYSIS` → `[data_profiler, python_tool]`
- `CODE_EXECUTION` → `[python_tool]`
- `FILE_GENERATION` → `[rag_search, file_generator_tool]`
- `CONTENT_GENERATION` → `[rag_search, content_generator_tool]`
- `RESEARCH` → `[research_subgraph]`

### Tools

| Tool | Description |
|---|---|
| `rag_search` | Calls `secure_retriever.py` to fetch relevant chunks from ChromaDB |
| `python_tool` | Executes Python code in an isolated sandbox (separate venv/Docker container); captures stdout, stderr, and Matplotlib charts as base64 images |
| `data_profiler` | Profiles a CSV/Excel file (dtypes, shapes, sample rows) as context for the Python tool |
| `file_generator_tool` | Generates downloadable files (CSV, Excel, Word, PDF) from LLM-structured output |
| `content_generator_tool` | Triggers quiz/flashcard/presentation generation inline in chat |
| `research_subgraph` | Deep web research using the `research_graph.py` sub-agent (web search → scrape → synthesize) |

### Code Execution Sandbox (`services/code_execution/`)

- Runs user-generated Python in an isolated temp directory (`/tmp/kepler_sandbox_*`)
- `MAX_CODE_REPAIR_ATTEMPTS` (3): if code fails, the LLM automatically repairs it using the error traceback + `code_repair_prompt.txt`
- Timeout enforced: `CODE_EXECUTION_TIMEOUT` (15 seconds)
- Matplotlib charts intercepted and returned as base64 PNG data URIs
- Temp dirs cleaned up on startup to recover from crashes

### Research Sub-Agent (`agent/subgraphs/research_graph.py`)

A dedicated LangGraph sub-graph for deep research:
1. Decomposes the query into multiple search sub-queries
2. Fetches web pages (BeautifulSoup + Playwright)
3. Extracts and summarizes relevant content
4. Synthesizes a structured research report with source URLs

### Reflection (`agent/reflection.py`)

After each tool execution, the reflector decides:
- **Retry**: if the tool failed with a recoverable error (up to `step_retries` limit)
- **Continue**: advance to the next planned step
- **Respond**: all steps complete, or hard limit reached

---

## 10. LLM Provider Layer

`services/llm_service/llm.py` is a **provider factory** with caching:

```python
get_llm()           # Chat temperature (0.2), top_p=0.95
get_llm_structured() # Low temperature (0.1), top_p=0.9 for JSON outputs
get_llm_creative()   # High temperature (0.7) for podcast/explainer scripts
```

### Supported Providers

| Provider | Class | Notes |
|---|---|---|
| `OLLAMA` | `ChatOllama` | Local LLM. `OLLAMA_MODEL` env var. Supports `top_k`. |
| `GOOGLE` | `ChatGoogleGenerativeAI` | Cloud. `GOOGLE_API_KEY` + `GOOGLE_MODEL`. |
| `NVIDIA` | `ChatNVIDIA` | Cloud. `NVIDIA_API_KEY` + `NVIDIA_MODEL`. |
| `MYOPENLM` | Custom `LLM` subclass | Custom REST API. Used for fast intent classification. |

Provider is selected by `LLM_PROVIDER` env var. Hot-swap without restart is NOT supported (change requires restart).

LLM instances are LRU-cached (max 16 unique configurations) to avoid re-instantiation cost.

---

## 11. Content Generation Features

### Quiz (`services/quiz/`)

**Flow:**
1. Fetch material full text (or combine multiple materials)
2. Load `prompts/quiz_prompt.txt`
3. Call `get_llm_structured()` with JSON schema for MCQ array
4. Parse and validate response
5. Return `{ questions: [{question, options, correct_answer, explanation}] }`

### Flashcards (`services/flashcard/`)

Same flow as quiz, using `prompts/flashcard_prompt.txt`. Returns `{ cards: [{front, back}] }`.

### Presentations (`services/ppt/generator.py`)

**Flow:**
1. Fetch material text
2. Load `prompts/ppt_prompt.txt` with theme, slide count, instructions
3. LLM returns JSON: `{ title, slides: [{title, bullets, speaker_notes, image_query}] }`
4. Fetch images from external sources for each slide (Unsplash/Pexels via proxy route)
5. Render to HTML using `templates/` CSS
6. Store in `output/presentations/`
7. Optional: export slide images via LibreOffice

### Podcast (`services/podcast/`)

**Script generation** (`prompts/podcast_script_prompt.txt` + `podcast_qa_prompt.txt`):
- Mode-specific prompts: `overview`, `deep-dive`, `debate`, `q-and-a`, `full`, `topic`
- LLM generates a structured JSON script with alternating HOST/GUEST segments, chapters

**Audio generation** (TTS via `edge-tts`):
- Each segment rendered to audio with a chosen Edge TTS neural voice
- Multiple languages supported via `VOICE_MAP` in `podcast/voice_map.py`
- Segment audio files stored: `output/podcast/{session_id}/segment_{idx}.mp3`

**Live Q&A**:
- User can pause and ask a question during playback
- `qa_service.py` generates a contextual answer and its audio
- Answer inserted as new segments in the session

**Export**: PDF (via fpdf2, showing transcript) or JSON (full segment data).

### Explainer Videos (`services/explainer/`)

1. Check for or create a PPT presentation for the materials
2. Generate narration script per slide using the LLM
3. Use Edge TTS (`services/explainer/tts.py`) to generate one audio file per slide
4. Store audio files, assemble metadata
5. Frontend plays slide images + audio synchronously to create a "video" experience

---

## 12. Authentication & Security

### Auth Flow

```
[Signup]
POST /auth/signup
  │ validate password complexity
  │ check email uniqueness
  │ bcrypt hash password
  └─► insert User record → return UserResponse

[Login]
POST /auth/login
  │ lookup user by email
  │ bcrypt.checkpw(plain, hash)
  │ create JWT access token (15 min expiry, HS256)
  │ create JWT refresh token (7 days)
  │ store refresh token hash + family in DB
  └─► return access_token in body
      set refresh_token as HttpOnly cookie (path=/auth)

[Authenticated Request]
Authorization: Bearer <access_token>
  │ get_current_user() dependency
  └─► decode JWT → lookup user in DB

[Token Refresh]
POST /auth/refresh
  │ read refresh_token cookie
  │ hash → lookup in DB
  │ check not used (prevent reuse attacks)
  │ mark old token used
  │ issue new access + refresh token pair (same family)
  └─► return new access_token, set new refresh cookie

[Logout]
POST /auth/logout
  │ revoke entire token family
  └─► clear cookie
```

### Security Controls

| Control | Implementation |
|---|---|
| Password hashing | `bcrypt` with salts |
| Token storage | Refresh token stored hashed (SHA-256) in DB; only hash travels after initial issuance |
| Token rotation | Family-based: if a used token is replayed, the entire family is revoked |
| Refresh cookie scope | `path=/auth` — cookie only sent to auth endpoints, not to API endpoints |
| File upload safety | `python-magic` header check, MIME whitelist, filename sanitization, size limit (25 MB) |
| Multi-tenant isolation | ChromaDB queries always include `user_id` filter; Prisma queries always include `userId` condition |
| CORS | `CORSMiddleware` with explicit origin whitelist |
| Rate limiting | Sliding-window per-IP limiter |
| Input validation | Pydantic v2 schemas on all request bodies |
| File access tokens | Time-limited signed tokens (5 min) for download URLs |

---

## 13. Frontend — Deep Dive

### Routing

```
/ (root)          → HomePage (notebook list)
/auth             → AuthPage (login/signup)
/notebook/:id     → Workspace (Sidebar + ChatPanel + StudioPanel)
/notebook/draft   → Draft workspace (before first save)
/file/:id         → FileViewerPage
```

### State Management

**`AppContext.jsx`** — Global state:
- `currentNotebook` — active notebook object
- `materials` — list of materials in current notebook
- `messages` — chat history for current session
- `currentMaterial` — currently selected material
- `selectedSources` — material IDs selected for chat queries
- `draftMode` — whether working in a new unsaved notebook

**`AuthContext.jsx`** — Auth state:
- `user`, `accessToken`
- `isAuthenticated`, `isLoading`
- `login()`, `logout()`, `refreshToken()`
- All API calls route through an interceptor that automatically refreshes the access token on 401 responses

**`ThemeContext.jsx`** — Dark/light mode toggle, persisted to localStorage.

**`PodcastContext.jsx`** — Podcast player state: current session, playback position, bookmarks, annotations.

### Key Components

| Component | Role |
|---|---|
| `Header.jsx` | Top navigation bar with notebook title, user menu, theme toggle |
| `Sidebar.jsx` | Left panel: material list, upload button, source selection checkboxes |
| `ChatPanel.jsx` | Center panel: chat history, input box, SSE streaming display |
| `StudioPanel.jsx` | Right panel: tabs for Quiz, Flashcards, Presentation, Podcast, Explainer |
| `ChatMessage.jsx` | Renders a single message with Markdown, code blocks, charts, citations |
| `UploadDialog.jsx` | Modal for file/URL/YouTube/text upload with progress feedback |
| `PresentationView.jsx` | Slide viewer with navigation controls |
| `ExplainerDialog.jsx` | Video creation wizard and player |
| `WebSearchDialog.jsx` | Quick web search from chat context |

### `useMaterialUpdates.js`

Connects to `/ws` WebSocket using the access token for auth. Listens for `material_update` events (status changes from the background worker) and updates the materials list in `AppContext` in real time.

### API Layer (`src/api/`)

Each file is a thin wrapper around `fetch` that:
- Prepends the base URL from `config.js`
- Injects the `Authorization: Bearer <token>` header
- Handles token refresh on 401 (via `AuthContext` interceptor)
- Returns parsed JSON or throws a structured error

---

## 14. Database Schema (Prisma)

### Models Overview

```
User
 ├── Notebook[]           (one user → many notebooks)
 ├── Material[]           (materials per user)
 ├── ChatSession[]        (chat sessions per notebook)
 ├── ChatMessage[]        (messages with optional agent metadata)
 ├── GeneratedContent[]   (quiz/flashcard/PPT/podcast data)
 ├── ExplainerVideo[]     (video generation results)
 ├── BackgroundJob[]      (async processing jobs)
 ├── RefreshToken[]       (JWT refresh token rotation)
 ├── UserTokenUsage[]     (daily token consumption)
 ├── ApiUsageLog[]        (per-request LLM usage audit)
 ├── AgentExecutionLog[]  (agent intent, tools, tokens, latency)
 ├── CodeExecutionSession[] (sandbox runs)
 ├── ResearchSession[]    (research sub-agent sessions)
 └── PodcastSession[]
      ├── PodcastSegment[]  (individual HOST/GUEST turns)
      ├── PodcastDoubt[]    (live Q&A questions + answers)
      ├── PodcastExport[]   (PDF/JSON exports)
      ├── PodcastBookmark[]
      └── PodcastAnnotation[]
```

### Material Status Lifecycle

```
pending → processing → [ocr_running | transcribing] → embedding → completed
                    └──────────────────────────────────────────────→ failed
```

### Key Model Fields

**`Material`**
- `sourceType`: `file | url | youtube | text`
- `status`: enum (pending through completed/failed)
- `chunkCount`: number of vectors stored in ChromaDB
- `metadata`: JSON string with extraction details
- `originalText`: NOT stored here — saved to file system

**`ChatMessage`**
- `agentMeta`: JSON with intent, tools_used, step_log, token counts, latency

**`GeneratedContent`**
- `contentType`: `quiz | flashcard | presentation | podcast`
- `data`: `Json` (full structured data for the content)
- `materialIds`: array of source material IDs

**`BackgroundJob`**
- `jobType`: `material_processing | url_processing | text_processing`
- `status`: mirrors MaterialStatus enum

---

## 15. API Reference

### Authentication

```
POST   /auth/signup           Register
POST   /auth/login            Login → JWT + cookie
POST   /auth/refresh          Rotate token
POST   /auth/logout           Revoke + clear cookie
GET    /auth/me               Current user
```

### Notebooks

```
POST   /notebooks             Create
GET    /notebooks             List (for current user)
GET    /notebooks/{id}        Get by ID
PUT    /notebooks/{id}        Update
DELETE /notebooks/{id}        Delete (cascades materials, chat, content)
```

### Materials

```
POST   /upload                Upload file
POST   /upload/url            Ingest URL/YouTube
POST   /upload/text           Ingest raw text
GET    /materials             List (optional: ?notebook_id=)
PUT    /materials/{id}        Update metadata
DELETE /materials/{id}        Delete (removes ChromaDB chunks + text file)
```

### Chat

```
POST   /chat                  Send message (SSE streaming supported)
GET    /chat/sessions/{notebook_id}   List sessions
POST   /chat/sessions         Create session
DELETE /chat/sessions/{id}    Delete session
GET    /chat/history/{notebook_id}    Full message history
POST   /chat/block-followup   Follow-up on a response block
```

### Generation

```
POST   /quiz                  Generate quiz
POST   /flashcard             Generate flashcards
POST   /presentation          Generate presentation
```

### Podcast

```
POST   /podcast/sessions                       Create session
POST   /podcast/sessions/{id}/generate         Start generation
GET    /podcast/sessions                       List sessions
GET    /podcast/sessions/{id}                  Get session + segments
PUT    /podcast/sessions/{id}                  Update metadata
DELETE /podcast/sessions/{id}                  Delete
POST   /podcast/sessions/{id}/question         Ask live question
POST   /podcast/sessions/{id}/bookmark         Bookmark segment
POST   /podcast/sessions/{id}/annotation       Annotate segment
POST   /podcast/sessions/{id}/export           Export PDF/JSON
GET    /podcast/audio/{session_id}/{seg_idx}   Stream audio
GET    /podcast/voices/{language}              List voices
GET    /podcast/preview-voice                  Voice preview audio
```

### Explainer Videos

```
POST   /explainer/check-presentations   Check existing PPTs
POST   /explainer/generate              Start video generation
GET    /explainer/{id}/status           Poll progress
GET    /explainer/{id}/video            Download video
```

### Jobs

```
GET    /jobs/{id}             Get job status
GET    /jobs                  List user's jobs
```

### Search

```
GET    /search?q=...&notebook_id=...   Semantic search across materials
```

### WebSocket

```
WS     /ws?token=<access_token>        Real-time material update events
```

### Health

```
GET    /health                Backend health check
```

---

## 16. Data Flow Diagrams

### Material Upload & Processing

```
Browser                  FastAPI                  Worker                 ChromaDB  PostgreSQL  FileSystem
   │                        │                        │                       │          │          │
   │── POST /upload ────────►│                        │                       │          │          │
   │                        │── save raw file ────────────────────────────────────────────────────►│
   │                        │── INSERT Material(pending) ─────────────────────────────►│           │
   │                        │── INSERT BackgroundJob(pending) ──────────────────────►│             │
   │                        │── _job_queue.notify() ──►│                    │          │          │
   │◄── {material_id} ───────│                        │                       │          │          │
   │                        │                        │── extract_text ────────────────────────────►│
   │                        │                        │◄── raw text ──────────────────────────────│
   │                        │                        │── chunk_text()         │          │          │
   │                        │                        │── embed_and_store() ──►│          │          │
   │                        │                        │── UPDATE Material(completed) ───►│           │
   │                        │                        │── WS push ────────────►│          │          │
   │◄── WS: material_update ─│◄──────────────────────│                       │          │          │
```

### RAG Chat Flow

```
Browser                  FastAPI                  Agent                  ChromaDB   LLM
   │                        │                        │                       │          │
   │── POST /chat ───────────►│                        │                       │          │
   │                        │── validate materials ───►│                       │          │
   │                        │── run agent graph ──────►│                       │          │
   │                        │                        │── intent_and_plan()    │          │
   │                        │                        │── rag_search tool ────►│          │
   │                        │                        │◄── top_k chunks ───────│          │
   │                        │                        │── rerank chunks ────────────────►│
   │                        │                        │◄── reranked chunks ─────────────│
   │                        │                        │── build_context()      │          │
   │                        │                        │── LLM call ────────────────────►│
   │                        │                        │◄── response ───────────────────│
   │◄── SSE stream ──────────│◄── generate_response ──│                       │          │
```

### Authentication Flow

```
Browser                  FastAPI                  PostgreSQL
   │                        │                        │
   │── POST /auth/login ─────►│                        │
   │                        │── lookup user ──────────►│
   │                        │◄── user record ──────────│
   │                        │── bcrypt.checkpw()       │
   │                        │── create JWT (15 min)    │
   │                        │── create refresh token   │
   │                        │── store refresh hash ───►│
   │◄── {access_token} ──────│                        │
   │◄── Set-Cookie:refresh ──│                        │
   │                        │                        │
   │── GET /some/api         │                        │
   │   Authorization: Bearer <access_token>           │
   │────────────────────────►│── decode JWT           │
   │                        │── get_current_user() ──►│
   │                        │◄── user ────────────────│
   │                        │── process request       │
   │◄── response ────────────│                        │
```

---

## 17. Configuration & Environment Variables

Create a `.env` file in the `backend/` directory:

```env
# ── Core ─────────────────────────────────────────────────
ENVIRONMENT=development
DEBUG=false

# ── Database ─────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://postgres:yourpassword@localhost:5432/keplerlab

# ── Auth ─────────────────────────────────────────────────
JWT_SECRET_KEY=<run: python -c "import secrets; print(secrets.token_urlsafe(64))">
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
COOKIE_SECURE=false          # set true in production (HTTPS)
COOKIE_SAMESITE=lax
COOKIE_DOMAIN=               # set to your domain in production

# ── LLM Provider (choose one) ────────────────────────────
LLM_PROVIDER=OLLAMA
OLLAMA_MODEL=llama3

# LLM_PROVIDER=GOOGLE
# GOOGLE_API_KEY=your-google-api-key
# GOOGLE_MODEL=models/gemini-2.5-flash

# LLM_PROVIDER=NVIDIA
# NVIDIA_API_KEY=your-nvidia-api-key
# NVIDIA_MODEL=meta/llama3-70b-instruct

# ── Generation Parameters ─────────────────────────────────
LLM_TEMPERATURE_STRUCTURED=0.1
LLM_TEMPERATURE_CHAT=0.2
LLM_TEMPERATURE_CREATIVE=0.7
LLM_MAX_TOKENS=4000
LLM_MAX_TOKENS_CHAT=3000

# ── Storage Paths ─────────────────────────────────────────
CHROMA_DIR=./data/chroma
UPLOAD_DIR=./data/uploads
MODELS_DIR=./data/models
MAX_UPLOAD_SIZE_MB=25

# ── CORS ──────────────────────────────────────────────────
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# ── Code Execution ────────────────────────────────────────
CODE_EXECUTION_TIMEOUT=15
MAX_CODE_REPAIR_ATTEMPTS=3
```

---

## 18. Deployment

### Local Development

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
prisma generate
prisma db push
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev   # http://localhost:5173
```

### Docker

```bash
# Start all services (PostgreSQL, Redis, backend, frontend/nginx)
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop
docker-compose down
```

Frontend served by NGINX on port 3000 (`frontend/nginx.conf`). Backend on port 8000. NGINX proxies `/api/*` to the backend.

### Production Checklist

- [ ] Set `ENVIRONMENT=production`
- [ ] Set `COOKIE_SECURE=true` and `COOKIE_SAMESITE=strict`
- [ ] Use a strong `JWT_SECRET_KEY` (64+ bytes)
- [ ] Set `CORS_ORIGINS` to your production domain only
- [ ] Use a managed PostgreSQL instance (e.g., RDS, Supabase)
- [ ] Configure Redis for rate limiting persistence
- [ ] Set up log rotation and monitoring
- [ ] Use `LLM_PROVIDER=GOOGLE` or `NVIDIA` for production scale

---

## 19. Performance & Optimization

### Key Performance Figures

| Operation | Typical Duration |
|---|---|
| 100-page PDF processing | 10–30 seconds |
| 1000-chunk batch embedding | 30–60 seconds |
| RAG chat response (no streaming) | 2–5 seconds |
| Slide generation | 15–45 seconds |
| Podcast generation (30 min audio) | 30–90 seconds |
| Intent detection (keyword path) | < 1 ms |
| Vector similarity search (1000 chunks) | < 100 ms |

### Optimization Techniques

| Technique | Where Used |
|---|---|
| **Embedding warm-up at startup** | ChromaDB ONNX model pre-loaded to avoid cold-start on first upload |
| **Reranker warm-up at startup** | Cross-encoder loaded into memory before first request |
| **LRU cache for LLM instances** | Avoid repeated model instantiation (max 16 cached configs) |
| **Concurrent background jobs** | Async semaphore allows up to 5 jobs in parallel |
| **Event-driven worker** | Job queue notification vs. 2-second polling eliminates unnecessary wake-ups |
| **Batch ChromaDB upsert** | 200-chunk batches stay within ChromaDB limits while maximizing throughput |
| **Structured data expansion at retrieval** | Only full dataset when needed (avoids storing huge blobs in vector store) |
| **Token budget enforcement** | Hard cap prevents runaway agent loops |
| **SSE streaming** | LLM responses stream to the browser incrementally, avoiding long wait times |
| **Thread-pool for blocking I/O** | `loop.run_in_executor(None, ...)` for sync LLM calls, file I/O, and heavy CPU work |

---

*This documentation covers the complete KeplerLab AI Notebook codebase as of version 2.0.0, February 2026.*
