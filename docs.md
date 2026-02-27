# KeplerLab AI Notebook — Complete Project Documentation

> **Version**: 2.0.0 · **Last Updated**: February 2026  
> Full end-to-end technical reference: architecture, data flows, code structure, API surface, security, and deployment.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Repository Structure](#4-repository-structure)
5. [Database Schema](#5-database-schema)
6. [Backend — Deep Dive](#6-backend--deep-dive)
   - 6.1 [Entry Point & Lifespan](#61-entry-point--lifespan)
   - 6.2 [Configuration System](#62-configuration-system)
   - 6.3 [Authentication Service](#63-authentication-service)
   - 6.4 [Material Ingestion Pipeline](#64-material-ingestion-pipeline)
   - 6.5 [Background Job Worker](#65-background-job-worker)
   - 6.6 [RAG System](#66-rag-system)
   - 6.7 [LangGraph Agent](#67-langgraph-agent)
   - 6.8 [LLM Service Layer](#68-llm-service-layer)
   - 6.9 [Content Generation Services](#69-content-generation-services)
   - 6.10 [Code Execution Sandbox](#610-code-execution-sandbox)
   - 6.11 [WebSocket Manager](#611-websocket-manager)
   - 6.12 [Supporting Services](#612-supporting-services)
7. [API Routes Reference](#7-api-routes-reference)
8. [Frontend — Deep Dive](#8-frontend--deep-dive)
   - 8.1 [Application Shell](#81-application-shell)
   - 8.2 [Context & State Management](#82-context--state-management)
   - 8.3 [Key UI Components](#83-key-ui-components)
   - 8.4 [API Client Modules](#84-api-client-modules)
9. [End-to-End Data Flows](#9-end-to-end-data-flows)
   - 9.1 [File Upload Flow](#91-file-upload-flow)
   - 9.2 [RAG Chat Flow](#92-rag-chat-flow)
   - 9.3 [Agent-Powered Chat Flow](#93-agent-powered-chat-flow)
   - 9.4 [Content Generation Flow](#94-content-generation-flow)
   - 9.5 [Podcast Generation Flow](#95-podcast-generation-flow)
10. [Security Architecture](#10-security-architecture)
11. [Configuration Reference](#11-configuration-reference)
12. [Deployment](#12-deployment)
13. [Performance Notes](#13-performance-notes)
14. [Roadmap](#14-roadmap)

---

## 1. Project Overview

**KeplerLab AI Notebook** is a full-stack, AI-powered study platform that transforms raw educational materials (PDFs, DOCX files, YouTube videos, web pages, images, audio, spreadsheets) into interactive learning experiences.

### Core Capabilities

| Feature | Description |
|---|---|
| **Smart Ingestion** | Uploads, URLs, YouTube, pasted text; OCR for images; Whisper for audio/video |
| **RAG Chat** | Conversational Q&A grounded in the user's uploaded materials with source citations |
| **Agent Chat** | LangGraph state machine that auto-detects intent and routes to the right tool |
| **Quiz Generation** | Multiple-choice quizzes with configurable difficulty and count |
| **Flashcard Generation** | Spaced-repetition ready card decks |
| **Podcast Generation** | Host–guest audio dialogue synthesized via TTS |
| **Presentation (PPT)** | AI-generated slide decks exported as PPTX and PNG previews |
| **Code Execution** | Securely runs Python (+ data-analysis) code in an isolated sandbox |
| **Research Tool** | Web-search-backed deep research answers |
| **Data Analysis** | Tabular data (CSV/Excel) profiling, charts, and LLM-driven insights |

---

## 2. High-Level Architecture

```
┌────────────────────────────────────────────────────────────┐
│                  React Frontend  (Vite 7)                  │
│  Router · AppContext · AuthContext · ChatPanel · Studio    │
└──────────────────────────┬─────────────────────────────────┘
                           │  HTTP REST / SSE / WebSocket
┌──────────────────────────▼─────────────────────────────────┐
│               FastAPI 0.115  (Python 3.11+)                │
│                                                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐ │
│  │  Routes  │ │ Services │ │LLM Layer │ │ Agent Graph  │ │
│  │ /auth    │ │ material │ │ Ollama   │ │ LangGraph    │ │
│  │ /upload  │ │ worker   │ │ Gemini   │ │ intent detect│ │
│  │ /chat    │ │ rag      │ │ NVIDIA   │ │ tool router  │ │
│  │ /quiz etc│ │ notebook │ │ MyOpenLM │ │ reflection   │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘ │
│                                                            │
│  Middleware: CORS · Rate Limiter · Performance Logger      │
└──────┬───────────────────────┬──────────────────┬──────────┘
       │                       │                  │
 ┌─────▼──────┐   ┌────────────▼──────┐   ┌──────▼───────┐
 │ PostgreSQL │   │    ChromaDB       │   │ File System  │
 │  (Prisma)  │   │  (Vector Store)   │   │  /data/      │
 │  users     │   │  ONNX embeddings  │   │  uploads/    │
 │  notebooks │   │  BGE-M3 384-dim   │   │  material_   │
 │  materials │   │  per-user tenant  │   │  text/       │
 │  chat msgs │   │  isolation        │   │  models/     │
 │  jobs etc  │   └───────────────────┘   └──────────────┘
 └────────────┘
```

### Communication Protocols

| Pattern | Used For |
|---|---|
| REST (JSON) | All CRUD, chat, generation endpoints |
| Server-Sent Events (SSE) | Streaming LLM tokens during chat |
| WebSocket (`/ws`) | Real-time material processing status updates |

---

## 3. Technology Stack

### Backend

| Library | Version | Purpose |
|---|---|---|
| FastAPI | 0.115.6 | Async web framework |
| Uvicorn | 0.30.6 | ASGI server |
| Pydantic v2 | 2.9.2 | Data validation, settings |
| LangChain | 0.2.16 | LLM orchestration |
| LangGraph | ≥0.2.0 | Agent state machine |
| langchain-google-genai | 1.0.10 | Google Gemini provider |
| langchain-nvidia-ai-endpoints | latest | NVIDIA provider |
| langchain-ollama | 0.1.3 | Ollama local provider |
| ChromaDB | 0.5.5 | Vector database |
| Sentence-Transformers | 3.1.1 | BGE-M3 embeddings |
| Prisma (Python) | async | PostgreSQL ORM |
| OpenAI Whisper | latest | Audio/video transcription |
| PyMuPDF / pypdf / pdfplumber | various | PDF extraction |
| python-docx, python-pptx | various | DOCX/PPTX parsing |
| EasyOCR / Pytesseract | various | Image OCR |
| yt-dlp / youtube-transcript-api | various | YouTube ingestion |
| BeautifulSoup4 / Playwright | various | Web scraping |
| pydub / ffmpeg-python | various | Audio processing |
| tiktoken | 0.7.0 | Token counting |
| PyTorch (CUDA 12.1) | latest | ML inference |

### Frontend

| Library | Version | Purpose |
|---|---|---|
| React | 19.2.0 | UI framework |
| React Router | 7.11.0 | Client-side routing |
| Vite | 7.2.4 | Build tool / dev server |
| Tailwind CSS | 3.4.19 | Utility-first styling |
| react-markdown | 10.1.0 | Markdown rendering in chat |
| react-syntax-highlighter | 16.1.0 | Code block syntax highlighting |
| KaTeX | 0.16.33 | Math formula rendering |
| remark-gfm / remark-math | latest | Markdown plugins |
| jsPDF | 4.0.0 | Client-side PDF export |

### Infrastructure

| Component | Role |
|---|---|
| PostgreSQL 15+ | Primary relational database |
| ChromaDB | Local vector store |
| NGINX | Frontend reverse proxy (production) |
| Docker Compose | Multi-container dev/prod setup |
| Redis | Rate limiting / caching (optional) |

---

## 4. Repository Structure

```
KeplerLab-AI-Notebook/
├── README.md
├── docs.md                        ← THIS FILE
│
├── backend/
│   ├── requirements.txt
│   ├── prisma/
│   │   └── schema.prisma          ← Full DB schema (Prisma DSL)
│   ├── logs/                      ← Rotating log files (app.log)
│   ├── data/
│   │   ├── chroma/                ← ChromaDB persistent storage
│   │   ├── material_text/         ← Full extracted text per material
│   │   ├── models/                ← Downloaded ML model weights
│   │   └── uploads/               ← Raw uploaded files
│   ├── output/
│   │   ├── generated/             ← Generated files (reports, CSVs)
│   │   ├── html/                  ← HTML slide previews
│   │   ├── podcasts/              ← Generated MP3 files
│   │   └── presentations/         ← PPTX + PNG slide exports
│   ├── templates/                 ← Jinja2 / HTML templates
│   └── app/
│       ├── main.py                ← FastAPI app, lifespan, middleware
│       ├── core/
│       │   ├── config.py          ← Pydantic settings (env-var driven)
│       │   └── utils.py           ← Shared utilities
│       ├── db/
│       │   ├── chroma.py          ← ChromaDB client singleton
│       │   └── prisma_client.py   ← Prisma async client singleton
│       ├── models/                ← Pydantic response models
│       ├── prompts/               ← Prompt template files (.txt)
│       │   ├── chat_prompt.txt
│       │   ├── quiz_prompt.txt
│       │   ├── flashcard_prompt.txt
│       │   ├── podcast_prompt.txt
│       │   ├── ppt_prompt.txt
│       │   ├── data_analysis_prompt.txt
│       │   ├── code_generation_prompt.txt
│       │   └── code_repair_prompt.txt
│       ├── routes/                ← FastAPI routers (one per domain)
│       │   ├── auth.py
│       │   ├── notebook.py
│       │   ├── upload.py
│       │   ├── chat.py
│       │   ├── quiz.py
│       │   ├── flashcard.py
│       │   ├── podcast_router.py
│       │   ├── ppt.py
│       │   ├── jobs.py
│       │   ├── models.py          ← LLM model list endpoint
│       │   ├── health.py
│       │   ├── agent.py
│       │   ├── search.py
│       │   ├── proxy.py
│       │   ├── websocket_router.py
│       │   └── utils.py           ← Shared route helpers
│       └── services/              ← Business logic (domain services)
│           ├── worker.py          ← Async background job queue
│           ├── material_service.py
│           ├── notebook_service.py
│           ├── notebook_name_generator.py
│           ├── job_service.py
│           ├── storage_service.py
│           ├── token_counter.py
│           ├── audit_logger.py
│           ├── performance_logger.py
│           ├── rate_limiter.py
│           ├── file_validator.py
│           ├── gpu_manager.py
│           ├── model_manager.py
│           ├── ws_manager.py
│           ├── auth/              ← JWT, hashing, user management
│           ├── chat/              ← RAG chat session service
│           ├── llm_service/       ← Provider factory, structured invoker
│           ├── rag/               ← Embedder, retriever, reranker, context
│           ├── agent/             ← LangGraph graph + nodes + tools
│           ├── text_processing/   ← Extractor, chunker, OCR, TTS
│           ├── code_execution/    ← Sandbox, executor, security
│           ├── flashcard/
│           ├── quiz/
│           ├── podcast/
│           ├── ppt/
│           └── text_to_speech/
│
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── index.html
│   ├── nginx.conf
│   ├── Dockerfile
│   └── src/
│       ├── main.jsx               ← ReactDOM root
│       ├── App.jsx                ← Router + layout + auth gates
│       ├── index.css              ← Tailwind base + custom design tokens
│       ├── api/                   ← Axios / fetch wrappers
│       │   ├── config.js          ← Base URL + interceptors
│       │   ├── auth.js
│       │   ├── notebooks.js
│       │   ├── materials.js
│       │   ├── chat.js
│       │   ├── generation.js
│       │   ├── jobs.js
│       │   └── agent.js
│       ├── context/
│       │   ├── AppContext.jsx     ← Global app state (notebook, materials, chat)
│       │   ├── AuthContext.jsx    ← Auth state + token refresh logic
│       │   └── ThemeContext.jsx   ← Dark/light theme toggle
│       ├── components/            ← All React UI components
│       │   ├── Header.jsx
│       │   ├── Sidebar.jsx        ← Notebook list + material list
│       │   ├── ChatPanel.jsx      ← Main chat interface with SSE streaming
│       │   ├── StudioPanel.jsx    ← Content generation launcher
│       │   ├── UploadDialog.jsx   ← File/URL/YouTube/text upload modal
│       │   ├── AuthPage.jsx       ← Login + Signup container
│       │   ├── HomePage.jsx       ← Landing page
│       │   ├── FileViewerPage.jsx ← In-app file preview
│       │   ├── PresentationView.jsx
│       │   ├── ChatMessage.jsx    ← Message bubble + source citations
│       │   ├── Modal.jsx          ← Reusable modal wrapper
│       │   ├── ErrorBoundary.jsx
│       │   └── chat/              ← Chat sub-components (charts, code etc.)
│       └── hooks/                 ← Custom React hooks
│
├── cli/
│   ├── backup_chroma.py
│   ├── export_embeddings.py
│   ├── import_embeddings.py
│   └── reindex.py
│
└── tools/
    ├── test_python_tool.py
    └── test_research_tool.py
```

---

## 5. Database Schema

The database uses **PostgreSQL** managed via **Prisma Python client (async/asyncio interface)**.

### Entity Relationships

```
User
 ├── Notebook[]          (owns one or many notebooks)
 ├── Material[]          (owns materials, optionally in a notebook)
 ├── ChatSession[]       (per-notebook conversation threads)
 ├── ChatMessage[]       (individual messages)
 ├── GeneratedContent[]  (quizzes, flashcards, podcasts, slides)
 ├── BackgroundJob[]     (material processing queue entries)
 ├── RefreshToken[]      (token rotation tracking)
 ├── UserTokenUsage[]    (daily LLM token budget tracking)
 ├── ApiUsageLog[]       (per-request audit logging)
 ├── AgentExecutionLog[] (agent step analytics)
 ├── CodeExecutionSession[]
 └── ResearchSession[]

Notebook
 ├── Material[]
 ├── ChatSession[]
 ├── ChatMessage[]
 └── GeneratedContent[]

Material
 └── GeneratedContent[]

ChatMessage
 └── ResponseBlock[]   (paragraph-level blocks for follow-up actions)
```

### Key Models

#### User
```
id UUID PK | email UNIQUE | username | hashedPassword
isActive | role (user/admin) | createdAt | updatedAt
```

#### Material
```
id UUID PK | userId | notebookId | filename | title
originalText (first 1000 chars only — full text on filesystem)
status: pending | processing | ocr_running | transcribing | embedding | completed | failed
chunkCount | sourceType (file/url/youtube/text) | metadata JSON | error
```

#### BackgroundJob
```
id UUID PK | userId | jobType | status (matches MaterialStatus)
result JSON | error Text | createdAt | updatedAt
```

#### ChatMessage
```
id UUID PK | notebookId | userId | chatSessionId
role (user/assistant) | content Text
agentMeta JSON (intent, tools_used, step_log, tokens, elapsed)
```

#### GeneratedContent
```
id UUID PK | notebookId | userId | materialId
contentType (quiz/flashcard/podcast/presentation) | title | data JSON
```

---

## 6. Backend — Deep Dive

### 6.1 Entry Point & Lifespan

**File**: `backend/app/main.py`

The FastAPI application uses an `asynccontextmanager` lifespan that performs ordered startup tasks:

1. **Connect Prisma** — establishes the PostgreSQL async connection pool.
2. **Warm embedding model** — runs `warm_up_embeddings()` in a thread-pool executor to pre-load the ChromaDB ONNX runtime, preventing cold-start on the first upload.
3. **Pre-load reranker** — loads the `BAAI/bge-reranker-large` model into memory.
4. **Start background worker** — creates an `asyncio.Task` running the `job_processor()` infinite loop.
5. **Ensure sandbox packages** — installs Python packages needed by the code execution sandbox.
6. **Clean stale sandboxes** — removes `/tmp/kepler_sandbox_*` leftover directories from previous crashes.
7. **Create output directories** — ensures `output/podcasts`, `output/presentations`, `output/generated` exist.

**Middleware stack** (applied in order):
- `TrustedHostMiddleware` — blocks unexpected Host headers in production.
- `CORSMiddleware` — allows origins listed in `CORS_ORIGINS` setting.
- `rate_limit_middleware` — in-memory sliding-window rate limiter.
- `performance_monitoring_middleware` — logs request latency and injects a `X-Request-ID` header.

**Request ID tracing**: Every request gets a UUID injected via middleware so all log lines are correlated.

### 6.2 Configuration System

**File**: `backend/app/core/config.py`

All configuration is driven by a single **Pydantic `BaseSettings` class** (`Settings`) that reads from environment variables and an optional `.env` file.

Key configuration groups:

| Group | Settings |
|---|---|
| Environment | `ENVIRONMENT`, `DEBUG` |
| Database | `DATABASE_URL` |
| Vector DB | `CHROMA_DIR` |
| Storage | `UPLOAD_DIR`, `MAX_UPLOAD_SIZE_MB`, output dirs |
| JWT/Auth | `JWT_SECRET_KEY`, `JWT_ALGORITHM`, token expiry, cookie params |
| CORS | `CORS_ORIGINS` (comma-separated string or list) |
| LLM | `LLM_PROVIDER`, model names, API keys, timeouts, generation params |
| Embeddings | `EMBEDDING_MODEL` (BGE-M3), `EMBEDDING_DIMENSION` (1024) |
| Retrieval | `INITIAL_VECTOR_K`, `MMR_K`, `FINAL_K`, `MMR_LAMBDA`, `MAX_CONTEXT_TOKENS` |
| Reranking | `RERANKER_MODEL`, `USE_RERANKER` |
| Timeouts | `OCR_TIMEOUT_SECONDS` (300s), `WHISPER_TIMEOUT_SECONDS` (600s) |
| Code execution | `MAX_CODE_REPAIR_ATTEMPTS`, `CODE_EXECUTION_TIMEOUT` |

The singleton `settings` is created via `@lru_cache` so the environment is parsed exactly once. Relative paths are resolved to absolute paths at validation time against `_PROJECT_ROOT`.

### 6.3 Authentication Service

**Files**: `backend/app/services/auth/`, `backend/app/routes/auth.py`

#### Flow

```
POST /auth/signup
  └── validate email + password strength (Pydantic)
  └── hash password with bcrypt
  └── create User record in DB

POST /auth/login
  └── fetch user by email
  └── verify bcrypt hash
  └── create access token (JWT, HS256, 15-min expiry)
  └── create refresh token (opaque UUID, hashed and stored in DB)
  └── set refresh token as HttpOnly cookie (path=/auth)
  └── return access token in response body

POST /auth/refresh
  └── read refresh token from cookie
  └── look up token hash in DB
  └── detect reuse (token rotation — revoke entire family on reuse)
  └── issue new access + refresh token pair
  └── update DB record

POST /auth/logout
  └── hash cookie value → find + revoke DB record
  └── clear cookie

GET /auth/me
  └── validate Bearer JWT in Authorization header
  └── return user profile
```

#### Security details
- **bcrypt** hashing with salts for passwords.
- **Token families** for refresh token rotation. If a previously-used token is replayed, the entire family is revoked, indicating a stolen token.
- Refresh token cookie is `HttpOnly`, `SameSite=lax`, and `Secure=true` in production. Path is restricted to `/auth` so it is never sent to other endpoints.
- Access tokens are short-lived (15 minutes) and not stored server-side.

### 6.4 Material Ingestion Pipeline

**Files**: `backend/app/routes/upload.py`, `backend/app/services/material_service.py`

#### Ingestion Sources

| Source | Route | Handler |
|---|---|---|
| File upload | `POST /upload` | `UploadFile` form field |
| URL / web page | `POST /upload/url` | URL string in body |
| YouTube video | `POST /upload/url` | YouTube URL detected by `YouTubeService` |
| Pasted text | `POST /upload/text` | Plain text in body |

#### Status State Machine

```
pending
   │  (worker picks up job)
   ▼
processing
   ├──► ocr_running    (image/scanned PDF)
   ├──► transcribing   (audio/video/YouTube)
   └──► embedding      (text chunked, now storing vectors)
              │
              ▼
           completed
              │ (any error)
              └──► failed
```

#### Processing Pipeline (per material)

```
1. Upload handler:
   a. Write raw file to /data/uploads/{uuid}{ext}
   b. Validate MIME type against whitelist
   c. Create Material record (status=pending) in PostgreSQL
   d. Create BackgroundJob record (type=material_processing, status=pending)
   e. Notify background worker (event-driven wake-up)
   f. Return 202 Accepted with {material_id, job_id}

2. Worker (background asyncio.Task):
   a. Fetch oldest pending job
   b. Atomically claim it (status → processing)
   c. Call process_material_by_id(material_id)

3. process_material_by_id:
   a. Extract text:
      - PDF → PyMuPDF / pdfplumber / pdf2image + OCR
      - DOCX → python-docx
      - PPTX → python-pptx
      - Images → EasyOCR / Tesseract
      - Audio/Video → OpenAI Whisper (status=transcribing)
      - URL → BeautifulSoup4 / trafilatura
      - YouTube → yt-dlp / youtube-transcript-api
      - CSV/Excel → pandas (structured raw pass-through)
   b. Save full text to /data/material_text/{material_id}.txt
   c. Update Material.originalText = first 1000 chars
   d. Chunk text (status=embedding):
      - LangChain RecursiveCharacterTextSplitter
      - chunk_size ≈ 1000 chars, overlap = CHUNK_OVERLAP_TOKENS (150)
      - Skip chunks shorter than MIN_CHUNK_LENGTH (100 chars)
   e. embed_and_store(chunks, material_id, user_id, notebook_id):
      - ChromaDB collection.upsert() in batches of 200
      - Metadata: material_id, user_id, notebook_id, source, filename
   f. Update Material: status=completed, chunkCount=N
   g. Push WebSocket event: {type: material_update, status: completed}
   h. Mark BackgroundJob: status=completed
```

#### File Validation

`FileValidator` checks:
- File size ≤ `MAX_UPLOAD_SIZE_MB` (default 25 MB)
- MIME type via `python-magic` (reads magic bytes, not just extension)
- Extension against `FileTypeDetector.SUPPORTED_TYPES` whitelist
- Sanitizes filename to prevent path traversal

### 6.5 Background Job Worker

**File**: `backend/app/services/worker.py`

A single `asyncio.Task` (`job_processor`) runs an infinite loop, started at application startup.

Key behaviours:
- **Event-driven wake-up**: A `_JobQueue` class wraps an `asyncio.Event`. When a new job is created by the upload route, `notify()` is called and the worker wakes immediately (no 2-second polling delay).
- **Concurrency control**: Up to `MAX_CONCURRENT_JOBS = 5` materials are processed in parallel via `asyncio.gather`.
- **Stuck job recovery**: On startup, any jobs stuck in `processing` for > 30 minutes are reset to `pending` (handles server crash recovery).
- **Graceful shutdown**: On SIGTERM/SIGINT, a `_shutdown_event` is set, the worker finishes in-flight jobs and exits within 30 seconds.
- **Error isolation**: Each job's exception is caught, logged, and stored in `BackgroundJob.error`. The loop continues for subsequent jobs.

### 6.6 RAG System

**Files**: `backend/app/services/rag/`

#### Components

| File | Responsibility |
|---|---|
| `embedder.py` | UPSERT text chunks into ChromaDB (ONNX embedding) |
| `secure_retriever.py` | Tenant-isolated vector search with MMR |
| `reranker.py` | Cross-encoder reranking via `BAAI/bge-reranker-large` |
| `context_builder.py` | Assembles final context from ranked chunks |
| `context_formatter.py` | Formats context into `[SOURCE N]` numbered blocks |
| `citation_validator.py` | Strips hallucinated out-of-range source citations |

#### Retrieval Pipeline

```
User query
    │
    ▼
SecureRetriever.retrieve(query, material_ids, user_id)
    │
    ├─ Step 1: ChromaDB query (n_results = INITIAL_VECTOR_K=10)
    │          Filter: {material_id: {$in: [...]}, user_id: user_id}
    │
    ├─ Step 2: MMR re-ranking (MMR_K=8, lambda=0.5)
    │          - Balances relevance vs diversity
    │
    ├─ Step 3: Cross-encoder reranking (if USE_RERANKER=True)
    │          - BAAI/bge-reranker-large scores each (query, chunk) pair
    │          - Returns top FINAL_K=10 chunks
    │
    ├─ Step 4: Token budget enforcement (MAX_CONTEXT_TOKENS=6000)
    │          - Skip chunks shorter than MIN_CONTEXT_CHUNK_LENGTH=150
    │          - Stop adding once tiktoken count exceeds budget
    │
    └─ Step 5: context_formatter formats as numbered [SOURCE N] blocks
               with filename attribution
```

#### Tenant Isolation

Every chunk stored in ChromaDB carries `user_id` as metadata. All queries include a `where={user_id: <id>}` filter so users can never retrieve each other's data.

### 6.7 LangGraph Agent

**Files**: `backend/app/services/agent/`

The agent replaces simple one-shot RAG with a **multi-step reasoning loop** built on LangGraph.

#### Graph Structure

```
intent_and_plan  ──►  tool_router  ──►  reflection
       ▲                                     │
       │              (continue)  ◄──────────┘
       │              (respond)   ──► response_generator ──► END
```

#### Nodes

| Node | File | Description |
|---|---|---|
| `intent_and_plan` | `intent.py` + `planner.py` | Classify intent, build execution plan |
| `tool_router` | `router.py` | Execute the next planned tool |
| `reflection` | `reflection.py` | Decide continue / respond / abort |
| `response_generator` | `graph.py` | Synthesize final answer from tool results |

#### Intent Detection (`intent.py`)

Intent is detected using a **two-stage approach**:

1. **Keyword rules** (regex, ordered top-to-bottom with confidence thresholds):
   - `FILE_GENERATION` (0.92) — "create a CSV", "generate a chart"
   - `DATA_ANALYSIS` (0.90) — "average", "plot", "histogram", "visualize"
   - `CODE_EXECUTION` (0.90) — "run Python", "write a script"
   - `RESEARCH` (0.90) — "search the web", "latest news"
   - `CONTENT_GENERATION` (0.92) — "make a quiz", "generate flashcards"
   - `QUESTION` (0.50) — default fallback

2. **LLM fallback** (fast MyOpenLM) — only triggered when keyword confidence < 0.85.

#### Tools (`agent/tools/`)

| Tool | Intent | Description |
|---|---|---|
| RAG lookup | QUESTION | Retrieves and synthesizes answers from material chunks |
| `data_profiler` | DATA_ANALYSIS | Profiles CSV/Excel structure, passes schema to python_tool |
| `python_tool` | DATA_ANALYSIS / CODE_EXECUTION | Executes Python in isolated sandbox |
| `file_generator` | FILE_GENERATION | Creates downloadable files (CSV, Excel, etc.) |
| `workspace_builder` | CODE_EXECUTION | Multi-file code workspace setup |
| Research tool | RESEARCH | Web search + synthesis |
| Content generation tools | CONTENT_GENERATION | Delegates to quiz/flashcard/podcast/ppt services |

#### Agent State (`state.py`)

The `AgentState` TypedDict tracks:
- `messages`, `intent`, `confidence`, `plan` (list of tool calls to make)
- `tool_results` (accumulated across iterations)
- `iterations`, `total_tokens` (hard-limit guards: `MAX_AGENT_ITERATIONS`, `TOKEN_BUDGET`)
- `stopped_reason` (completed / max_iterations / token_budget)

#### Streaming

The agent streams results via **Server-Sent Events (SSE)**. Each `yield` in the event loop emits a JSON payload of type:
- `agent_start` — intent + plan metadata
- `tool_start` / `tool_end` — per-tool execution events
- `rag_token` — individual LLM response tokens (streamed)
- `agent_complete` — final metadata (tokens used, elapsed time, tools used)

### 6.8 LLM Service Layer

**Files**: `backend/app/services/llm_service/`

#### Provider Factory (`llm.py`)

Supports four providers via LangChain:

| Provider | Env var | Model example |
|---|---|---|
| `OLLAMA` | `OLLAMA_MODEL` | `llama3`, `mistral` |
| `GOOGLE` | `GOOGLE_API_KEY`, `GOOGLE_MODEL` | `models/gemini-2.5-flash` |
| `NVIDIA` | `NVIDIA_API_KEY`, `NVIDIA_MODEL` | `qwen/qwen3.5-397b-a17b` |
| `MYOPENLM` | `MYOPENLM_API_URL` | proxied OpenAI-compatible API |

`get_llm()` returns a cached LangChain chat model instance; `get_llm_structured()` uses lower temperature optimised for deterministic JSON output.

Generation parameters exposed via settings:

| Parameter | Chat | Structured | Creative |
|---|---|---|---|
| Temperature | 0.2 | 0.1 | 0.7 |
| Top-P | 0.95 | 0.9 | — |
| Max tokens | 3000 | 4000 | — |

#### Structured Invoker (`structured_invoker.py`)

`invoke_structured(prompt, OutputSchema, max_retries=2)` — invokes the LLM and parses response as a Pydantic model. Uses `json_repair` to fix malformed JSON before parsing. Retries up to `max_retries` times on validation failure.

#### LLM Schemas (`llm_schemas.py`)

Pydantic output models for structured generation:
- `QuizOutput` — list of MCQ questions with options + correct answer
- `FlashcardOutput` — list of front/back card pairs
- `PodcastScriptOutput` — title + list of `{speaker, text}` dialogue turns
- `PPTOutput` — slide list with title, bullets, notes, image query

### 6.9 Content Generation Services

#### Quiz (`services/quiz/`)
1. Load material text from filesystem.
2. Build prompt from `quiz_prompt.txt` template (difficulty, count, format instructions).
3. `invoke_structured(prompt, QuizOutput)` → validated question list.
4. Save to `GeneratedContent` table as JSON.
5. Return to client.

#### Flashcards (`services/flashcard/`)
Same pipeline using `flashcard_prompt.txt` and `FlashcardOutput`.

#### Podcast (`services/podcast/generator.py`)
1. Truncate material text to 8000 chars.
2. `invoke_structured(prompt, PodcastScriptOutput)` → title + dialogue array.
3. `generate_dialogue_audio(dialogue)` — iterates speaker turns, calls TTS per turn, concatenates audio with `pydub`.
4. Returns `BytesIO` MP3 buffer + timing data.
5. File saved to `output/podcasts/{uuid}.mp3`.

#### Presentation (`services/ppt/`)
1. Build prompt from `ppt_prompt.txt` with theme and scope parameters.
2. LLM returns structured slide JSON (title, bullets, notes, image_query per slide).
3. Fetch images from Unsplash/Pexels APIs for each slide.
4. Build PPTX using `python-pptx`.
5. Export to PNG preview images via LibreOffice headless.
6. Return slide image URLs to frontend.

### 6.10 Code Execution Sandbox

**Files**: `backend/app/services/code_execution/`

| File | Role |
|---|---|
| `sandbox.py` | Creates an isolated temp directory, writes code, runs `subprocess` |
| `executor.py` | Async wrapper with timeout enforcement |
| `security.py` | AST-level static analysis — blocks dangerous imports and builtins |
| `sandbox_env.py` | Ensures required packages (pandas, matplotlib, etc.) are installed |

**Execution flow**:
1. `security.py` scans the AST for banned patterns (`os.system`, `subprocess`, `__import__`, file writes outside sandbox, socket calls).
2. Code is written to `/tmp/kepler_sandbox_{uuid}/script.py`.
3. Subprocess runs `python script.py` with `CODE_EXECUTION_TIMEOUT` (default 15s).
4. stdout/stderr captured and base64-encoded charts detected (matplotlib output).
5. If execution fails and `MAX_CODE_REPAIR_ATTEMPTS > 0`, the LLM is asked to fix the code using `code_repair_prompt.txt` and the cycle repeats.
6. `CodeExecutionSession` record saved to DB.
7. Temp directory cleaned up.

### 6.11 WebSocket Manager

**File**: `backend/app/services/ws_manager.py`

`WebSocketManager` maintains a dict of `{user_id → set[WebSocket]}`. Routes use `send_to_user(user_id, payload)` to push events. Used primarily for real-time material processing status updates. The WebSocket endpoint is at `/ws?token={access_token}` (token validated on connect).

### 6.12 Supporting Services

| Service | File | Description |
|---|---|---|
| Audit Logger | `audit_logger.py` | Writes `ApiUsageLog` records: endpoint, tokens, LLM latency |
| Token Counter | `token_counter.py` | `tiktoken`-based counting; daily budget tracking in `UserTokenUsage` |
| Rate Limiter | `rate_limiter.py` | Sliding-window in-memory rate limit middleware |
| Performance Logger | `performance_logger.py` | Per-request timing middleware; logs slow requests |
| Storage Service | `storage_service.py` | Read/write/delete material text files; summarise |
| GPU Manager | `gpu_manager.py` | Checks CUDA availability; controls model device placement |
| Model Manager | `model_manager.py` | Downloads and caches ML model weights |
| Notebook Name Generator | `notebook_name_generator.py` | LLM-based auto-naming for new notebooks |
| File Validator | `file_validator.py` | MIME validation using `python-magic` |
| Text Processing | `text_processing/extractor.py` | Dispatches to the correct extraction method |
| Material Chunker | `text_processing/chunker.py` | LangChain splitter wrapper |
| OCR Service | `text_processing/ocr_service.py` | EasyOCR + Tesseract fallback |
| Transcription | `text_processing/transcription_service.py` | OpenAI Whisper |
| YouTube Service | `text_processing/youtube_service.py` | `yt-dlp` download + transcript fetch |
| Web Scraping | `text_processing/web_scraping.py` | BeautifulSoup4 + Playwright headless |
| TTS | `text_to_speech/tts.py` | Text-to-speech audio synthesis |

---

## 7. API Routes Reference

All routes are prefixed at `http://localhost:8000`. Interactive Swagger docs at `/docs`.

### Authentication (`/auth`)  — `routes/auth.py`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/signup` | — | Register new account |
| POST | `/auth/login` | — | Login → access token + refresh cookie |
| POST | `/auth/refresh` | Cookie | Rotate refresh token |
| POST | `/auth/logout` | Cookie | Revoke refresh token |
| GET | `/auth/me` | Bearer | Get current user profile |

### Notebooks — `routes/notebook.py`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/notebooks` | Bearer | Create notebook |
| GET | `/notebooks` | Bearer | List user's notebooks |
| GET | `/notebooks/{id}` | Bearer | Get single notebook |
| PUT | `/notebooks/{id}` | Bearer | Update name/description |
| DELETE | `/notebooks/{id}` | Bearer | Delete notebook (cascades) |

### Upload / Materials — `routes/upload.py`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/upload` | Bearer | Upload file (multipart/form-data) |
| POST | `/upload/url` | Bearer | Ingest URL or YouTube |
| POST | `/upload/text` | Bearer | Ingest pasted text |
| GET | `/materials` | Bearer | List materials (filter by notebook) |
| GET | `/materials/{id}` | Bearer | Get material metadata |
| PUT | `/materials/{id}` | Bearer | Update title |
| DELETE | `/materials/{id}` | Bearer | Delete material + vectors |

### Chat — `routes/chat.py`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/chat` | Bearer | Agent-powered chat (SSE stream) |
| GET | `/chat/sessions/{notebook_id}` | Bearer | List chat sessions |
| POST | `/chat/sessions` | Bearer | Create new session |
| DELETE | `/chat/sessions/{id}` | Bearer | Delete session + history |
| GET | `/chat/history/{notebook_id}` | Bearer | Get chat history |
| POST | `/chat/block-followup` | Bearer | Follow-up on a specific response block |
| POST | `/chat/suggestions` | Bearer | Autocomplete suggestions |

### Jobs — `routes/jobs.py`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/jobs` | Bearer | List user's background jobs |
| GET | `/jobs/{id}` | Bearer | Get job status + result |

### Content Generation

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/quiz` | Bearer | Generate quiz from materials |
| POST | `/flashcard` | Bearer | Generate flashcard deck |
| POST | `/podcast` | Bearer | Generate podcast audio |
| GET | `/podcast/{id}/audio` | File token | Stream/download MP3 |
| POST | `/ppt` | Bearer | Generate presentation |
| GET | `/ppt/{id}/slides` | Bearer | Get slide preview images |

### Agent — `routes/agent.py`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/agent/chat` | Bearer | Direct agent endpoint (SSE) |

### Search — `routes/search.py`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/search` | Bearer | Semantic search across materials |

### Models — `routes/models.py`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/models` | Bearer | List available LLM models for current provider |

### Health — `routes/health.py`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | — | Service health + DB connectivity check |

### WebSocket — `routes/websocket_router.py`

| Protocol | Path | Auth | Description |
|---|---|---|---|
| WS | `/ws` | `?token=` | Real-time push events (material_update, job_update) |

### Proxy — `routes/proxy.py`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/proxy/file` | File token | Serve uploaded file with signed URL validation |

---

## 8. Frontend — Deep Dive

### 8.1 Application Shell

**File**: `frontend/src/App.jsx`

`App.jsx` is wrapped with three context providers:
```
<ThemeProvider>
  <AuthProvider>
    <AppProvider>
      <Router>
        routes...
      </Router>
    </AppProvider>
  </AuthProvider>
</ThemeProvider>
```

**Routes**:

| Path | Component | Notes |
|---|---|---|
| `/` | `HomePage` | Public landing page |
| `/auth` | `AuthPage` | Login / signup |
| `/notebook/draft` | Workspace (draft) | New notebook before first save |
| `/notebook/:id` | Workspace (loaded) | Existing notebook by ID |

`ProtectedRoute` wraps authenticated paths — redirects to `/auth` if not logged in.

The `Workspace` component reads the `:id` param and calls `getNotebook(id)` to hydrate the `AppContext` with the correct notebook state.

### 8.2 Context & State Management

#### `AuthContext.jsx`
- Stores: `user`, `isAuthenticated`, `isLoading`
- On mount: calls `GET /auth/me` using a stored access token
- Automatically calls `POST /auth/refresh` when a 401 is intercepted (silent token renewal)
- Provides `login(token, user)`, `logout()` actions

#### `AppContext.jsx`
- Stores: `currentNotebook`, `materials`, `messages`, `currentMaterial`, `selectedSources`, `draftMode`
- Provides actions: `setCurrentNotebook`, `setMaterials`, `addMessage`, `setCurrentMaterial`, `deselectAllSources`, etc.
- This is the single source of truth for the active workspace state

#### `ThemeContext.jsx`
- Stores: `theme` (light / dark)
- Persists to `localStorage`
- Toggles `data-theme` attribute on `<html>` for Tailwind CSS class-based theming

### 8.3 Key UI Components

#### `Sidebar.jsx`
- Lists all notebooks with create/rename/delete actions
- Lists materials in the active notebook with status indicators (spinner for processing, checkmark for completed, error for failed)
- Multi-select checkboxes for choosing which materials to chat against (reflected in `AppContext.selectedSources`)

#### `ChatPanel.jsx`
- Primary interaction surface
- Sends chat requests to `POST /chat` with selected material IDs
- Handles **SSE streaming**: parses `data:` lines, accumulates tokens, renders incrementally
- Renders `ChatMessage` components with Markdown (via `react-markdown`) + KaTeX math + code highlighting
- Shows agent intent badge and tool steps in collapsible metadata section
- Source citations shown as clickable `[SOURCE N]` links

#### `StudioPanel.jsx`
- Tabbed panel for content generation
- Quiz: difficulty selector (easy/medium/hard), question count
- Flashcard: card count
- Podcast: one-click generation with audio player on completion
- Presentation: theme and scope selectors with slide preview carousel

#### `UploadDialog.jsx`
- Tabbed upload modal
- File tab: drag-and-drop + file picker with MIME validation client-side preview
- URL tab: paste any web URL
- YouTube tab: paste YouTube video URL
- Text tab: textarea for pasting raw content
- Shows processing progress via `GET /jobs/{id}` polling (or WebSocket updates)

#### `ChatMessage.jsx`
- Renders a single message bubble
- Role = user → right-aligned, accent color
- Role = assistant → left-aligned, with source citation tooltips
- Agent metadata: intent label, tool execution timeline, token count
- Each paragraph block has hover actions: "Simplify", "Ask follow-up", "Translate"

### 8.4 API Client Modules

All API modules in `frontend/src/api/` use the base configuration from `config.js` which sets `VITE_API_BASE_URL` and attaches the JWT `Authorization: Bearer <token>` header to every request. The interceptor hooks into 401 responses to trigger silent token refresh.

| Module | Key functions |
|---|---|
| `auth.js` | `login()`, `signup()`, `refresh()`, `logout()`, `getMe()` |
| `notebooks.js` | `getNotebooks()`, `createNotebook()`, `updateNotebook()`, `deleteNotebook()` |
| `materials.js` | `uploadFile()`, `uploadUrl()`, `uploadText()`, `getMaterials()`, `deleteMaterial()` |
| `chat.js` | `sendMessage()` (SSE), `getChatHistory()`, `createSession()`, `deleteSession()` |
| `generation.js` | `generateQuiz()`, `generateFlashcards()`, `generatePodcast()`, `generatePresentation()` |
| `jobs.js` | `getJob()`, `getJobs()` |
| `agent.js` | `agentChat()` (SSE) |

---

## 9. End-to-End Data Flows

### 9.1 File Upload Flow

```
User                Frontend              Backend              Storage
 │                     │                     │                    │
 │  Drop PDF file       │                     │                    │
 │─────────────────────►│                     │                    │
 │                     │  POST /upload        │                    │
 │                     │  (multipart)         │                    │
 │                     │─────────────────────►│                    │
 │                     │                     │  Write temp file   │
 │                     │                     │───────────────────►│
 │                     │                     │  Validate MIME     │
 │                     │                     │  Create Material   │
 │                     │                     │  Create BackgroundJob
 │                     │                     │  Notify worker     │
 │                     │  202 {material_id}   │                    │
 │                     │◄─────────────────────│                    │
 │                     │                     │                    │
 │  (Worker async)     │                     │                    │
 │                     │                     │  Extract text      │
 │                     │                     │  Chunk text        │
 │                     │                     │  Embed → ChromaDB  │
 │                     │                     │  status=completed  │
 │                     │                     │  WS push →         │
 │                     │  WS: material_update │                    │
 │                     │◄─────────────────────│                    │
 │  (Sidebar updates)  │                     │                    │
```

### 9.2 RAG Chat Flow

```
User asks: "What is supervised learning?"

1. Frontend: POST /chat {material_ids:[...], message, notebook_id}
2. Route: validates materials belong to user, filters completed ones
3. Agent graph starts: intent_and_plan node
   → intent = QUESTION (keyword: "what is")
   → plan = [rag_lookup]
4. tool_router: calls SecureRetriever.retrieve(query, material_ids, user_id)
   a. ChromaDB query: find top 10 similar chunks (filtered by user_id + material_ids)
   b. MMR re-ranking: select 8 most diverse relevant chunks
   c. BGE reranker: score all 8, keep top 10 by cross-encoder score
   d. Token budget: add chunks until 6000 token limit
5. context_formatter: wrap chunks as [SOURCE 1], [SOURCE 2], ...
6. chat service generate_rag_response:
   a. Fetch last 10 messages from DB for conversation history
   b. Render chat_prompt.txt with {context, history, question}
   c. LLM.astream() → yield tokens via SSE
7. citation_validator: strip any [SOURCE N] where N > num_sources
8. Save ChatMessage to DB (user + assistant)
9. Save ApiUsageLog (tokens, latency)
10. Client: renders streamed markdown with citation tooltips
```

### 9.3 Agent-Powered Chat Flow

```
User asks: "Visualize the grade distribution from my CSV"

1. Intent detection: DATA_ANALYSIS (keyword: "visualize", "distribution", "csv")
2. Planner: plan = [data_profiler, python_tool]
3. tool_router iteration 1: data_profiler
   → loads CSV from material filesystem
   → profiles column types, dtypes, sample rows
   → stores schema in agent state
4. reflection: continue (plan has more steps)
5. tool_router iteration 2: python_tool
   → LLM generates matplotlib code using schema from data_profiler
   → security.py AST scan: no dangerous calls
   → subprocess executes code in /tmp/kepler_sandbox_{uuid}/
   → captures stdout + base64-encoded PNG chart
   → code_repair loop if execution fails (up to 3 retries)
6. reflection: respond (plan complete)
7. response_generator: formats tool results + synthesizes answer
8. SSE stream: yields tokens + final agent_complete event
   {intent, tools_used, tokens_used, elapsed_time}
9. Frontend: ChatMessage renders:
   - Text explanation
   - Inline chart image (base64 data URI)
   - Collapsible agent metadata
```

### 9.4 Content Generation Flow

```
User: "Generate a quiz"

1. POST /quiz {material_ids:[...], notebook_id, difficulty:"medium", count:10}
2. Route: load material text from /data/material_text/{id}.txt
3. Build prompt: quiz_prompt.txt + {material_text, difficulty, count}
4. invoke_structured(prompt, QuizOutput, max_retries=2):
   a. LLM generates JSON
   b. json_repair fixes minor issues
   c. QuizOutput.model_validate(json)
   d. Retry if Pydantic validation fails
5. Save GeneratedContent {contentType:"quiz", data: quiz_json}
6. Return quiz JSON to frontend
7. Frontend: StudioPanel renders interactive quiz card UI
```

### 9.5 Podcast Generation Flow

```
1. POST /podcast {material_ids:[...], notebook_id}
2. Load + concatenate material texts
3. generate_podcast_audio_async(text):
   a. invoke_structured(podcast_prompt, PodcastScriptOutput)
      → {title, dialogue:[{speaker:"Host",text:"..."},
                           {speaker:"Guest",text:"..."},...]}
   b. For each turn:
      - TTS synthesis (speaker voice mapping)
      - pydub AudioSegment
   c. Concatenate all segments
   d. Export BytesIO MP3
4. Save MP3 to output/podcasts/{uuid}.mp3
5. Save GeneratedContent record
6. Return {podcast_id, title, duration, transcript_with_timing}
7. Frontend: inline audio player + scrolling transcript
```

---

## 10. Security Architecture

### Authentication & Authorization

| Layer | Implementation |
|---|---|
| Password storage | bcrypt with random salts |
| Access tokens | JWT (HS256), 15-minute expiry, stored in memory only |
| Refresh tokens | Opaque UUID, SHA-256 hash stored in DB, 7-day expiry |
| Cookie security | `HttpOnly`, `SameSite=lax`, `Secure=true` (production), path=`/auth` |
| Token rotation | Refresh tokens are single-use; replay detected via `family` + `used` flag |
| CORS | Configurable origin whitelist; credentials mode enabled only for listed origins |

### Multi-Tenant Data Isolation

- Every ChromaDB query includes a `where={user_id: <id>}` filter — users cannot access other users' vectors.
- All Prisma queries include `userId` in `where` clauses — enforced at the service layer, not just routes.
- File paths use UUIDs, not user-supplied names, preventing path traversal.

### File Security

- `python-magic` reads file magic bytes (not just extension) to prevent MIME spoofing.
- Extensions validated against `FileTypeDetector.SUPPORTED_TYPES` whitelist.
- Filename sanitized to prevent path traversal (`../`).
- Downloads served through a signed file-token system (`FILE_TOKEN_EXPIRE_MINUTES=5`).
- Max upload size enforced at 25 MB (configurable).

### Code Execution Security

- AST-level static analysis blocks: `os.system`, `subprocess`, `socket`, `__import__`, `eval`, `exec`, dangerous file writes.
- Execution in isolated `/tmp/kepler_sandbox_{uuid}/` directory.
- Hard timeout (`CODE_EXECUTION_TIMEOUT=15s`) via subprocess timeout.
- Temp directories cleaned up after execution.

### Rate Limiting

Sliding-window in-memory rate limiter (configurable RPM per user). All requests from unauthenticated IPs are rate-limited globally.

### Input Validation

All request bodies are Pydantic models with field-level validators. SQL injection is not possible (Prisma uses parameterized queries). ChromaDB queries use metadata filter objects, not string interpolation.

---

## 11. Configuration Reference

Copy `backend/.env.example` to `backend/.env` and set the following:

```bash
# ── Required ─────────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/keplerlab
JWT_SECRET_KEY=<generate: python -c "import secrets; print(secrets.token_urlsafe(64))">

# ── LLM Provider (pick one) ──────────────────────────────────
LLM_PROVIDER=OLLAMA          # OLLAMA | GOOGLE | NVIDIA | MYOPENLM
OLLAMA_MODEL=llama3

# --- Google Gemini ---
# LLM_PROVIDER=GOOGLE
# GOOGLE_API_KEY=your-api-key
# GOOGLE_MODEL=models/gemini-2.5-flash

# --- NVIDIA AI ---
# LLM_PROVIDER=NVIDIA
# NVIDIA_API_KEY=your-api-key
# NVIDIA_MODEL=qwen/qwen3.5-397b-a17b

# ── Storage ───────────────────────────────────────────────────
CHROMA_DIR=./data/chroma
UPLOAD_DIR=./data/uploads
MODELS_DIR=./data/models

# ── Auth ──────────────────────────────────────────────────────
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
COOKIE_SECURE=false           # true in production

# ── CORS ──────────────────────────────────────────────────────
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# ── Retrieval ─────────────────────────────────────────────────
USE_RERANKER=true
INITIAL_VECTOR_K=10
FINAL_K=10
MAX_CONTEXT_TOKENS=6000

# ── Performance ───────────────────────────────────────────────
MAX_UPLOAD_SIZE_MB=25
LLM_TIMEOUT=          # leave blank for no timeout
CODE_EXECUTION_TIMEOUT=15
MAX_CODE_REPAIR_ATTEMPTS=3
```

---

## 12. Deployment

### Development (local)

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
prisma generate
prisma db push
cp .env.example .env   # fill in DATABASE_URL + JWT_SECRET_KEY
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev            # → http://localhost:5173
```

### Docker Compose (production-like)

```bash
docker-compose up -d
# Frontend → http://localhost:3000  (served by NGINX)
# Backend  → http://localhost:8000
```

NGINX (`frontend/nginx.conf`) serves the Vite build as static files and proxies `/api` to the backend.

### External Dependencies

| Dependency | Required | Notes |
|---|---|---|
| PostgreSQL 15+ | Yes | Must be running before backend starts |
| Ollama | If OLLAMA provider | `ollama pull llama3 && ollama serve` |
| LibreOffice | Optional | Only for PPTX → PNG slide export |
| Tesseract | Optional | Fallback OCR (EasyOCR is primary) |
| Redis | Optional | Rate limiter / cache enhancement |

---

## 13. Performance Notes

| Operation | Typical Time |
|---|---|
| 100-page PDF extraction | 10–30s |
| 1000-chunk embedding batch | 30–60s |
| RAG chat response (no stream) | 2–5s |
| Slide generation (10 slides) | 15–45s |
| Podcast generation (3 min audio) | 30–90s |
| Intent detection (keyword) | < 5ms |
| Intent detection (LLM fallback) | 200–500ms |

**Key optimisations**:
- Embedding warm-up at startup eliminates first-request ONNX cold-start.
- Reranker pre-loaded in thread pool during startup.
- Batch ChromaDB upsert (200 chunks/batch) is 10–40× faster than sequential.
- LLM instances are cached (`_llm_cache`) — no re-instantiation per request.
- Background worker runs up to `MAX_CONCURRENT_JOBS=5` materials in parallel.

---

## 14. Roadmap

- [ ] Real-time collaborative notebooks (multi-user)
- [ ] Advanced quiz analytics and progress tracking
- [ ] Export to Anki, Quizlet, Notion
- [ ] Mobile app (React Native)
- [ ] Multi-language UI and content support
- [ ] LMS integration (Canvas, Moodle)
- [ ] Spaced repetition scheduler
- [ ] Plagiarism detection and citation tracking
- [ ] Redis-backed chat session persistence (currently in-memory)

---

*Generated from source analysis — KeplerLab AI Notebook v2.0.0*
