# KeplerLab AI Notebook — Complete Architecture Documentation

> **Date:** February 2026  
> **Stack:** FastAPI (Python 3.11) · PostgreSQL + Prisma · ChromaDB · LangGraph · React 19 · Vite · TailwindCSS

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Repository Layout](#2-repository-layout)
3. [Backend — Deep Dive](#3-backend--deep-dive)
   - 3.1 [Entry Point & Lifespan](#31-entry-point--lifespan)
   - 3.2 [Configuration (`settings`)](#32-configuration-settings)
   - 3.3 [Database Layer](#33-database-layer)
   - 3.4 [Middleware Stack](#34-middleware-stack)
   - 3.5 [Authentication System](#35-authentication-system)
   - 3.6 [Routes Catalogue](#36-routes-catalogue)
   - 3.7 [Background Worker & Job Queue](#37-background-worker--job-queue)
   - 3.8 [RAG Pipeline](#38-rag-pipeline)
   - 3.9 [LangGraph Agent](#39-langgraph-agent)
   - 3.10 [LLM Service](#310-llm-service)
   - 3.11 [Text Processing & Ingestion](#311-text-processing--ingestion)
   - 3.12 [Generation Services](#312-generation-services)
   - 3.13 [Code Execution Sandbox](#313-code-execution-sandbox)
   - 3.14 [Text-to-Speech & Podcast](#314-text-to-speech--podcast)
   - 3.15 [WebSocket Manager](#315-websocket-manager)
   - 3.16 [Rate Limiter](#316-rate-limiter)
   - 3.17 [Performance Logger](#317-performance-logger)
   - 3.18 [Audit Logger](#318-audit-logger)
   - 3.19 [Token Counter](#319-token-counter)
   - 3.20 [File Validator](#320-file-validator)
   - 3.21 [Storage Service](#321-storage-service)
4. [Frontend — Deep Dive](#4-frontend--deep-dive)
   - 4.1 [Project Setup & Tooling](#41-project-setup--tooling)
   - 4.2 [Routing & App Shell](#42-routing--app-shell)
   - 4.3 [State Management (Contexts)](#43-state-management-contexts)
   - 4.4 [API Layer](#44-api-layer)
   - 4.5 [Key Components](#45-key-components)
   - 4.6 [Hooks](#46-hooks)
5. [End-to-End Request Flows](#5-end-to-end-request-flows)
   - 5.1 [Upload a File](#51-upload-a-file)
   - 5.2 [Chat / Ask a Question](#52-chat--ask-a-question)
   - 5.3 [Generate Flashcards](#53-generate-flashcards)
   - 5.4 [Generate a Podcast](#54-generate-a-podcast)
   - 5.5 [Generate a Presentation](#55-generate-a-presentation)
   - 5.6 [Code Execution / Data Analysis](#56-code-execution--data-analysis)
   - 5.7 [Research Mode](#57-research-mode)
6. [Data Models (Prisma Schema)](#6-data-models-prisma-schema)
7. [Environment Variables Reference](#7-environment-variables-reference)
8. [How to Run](#8-how-to-run)

---

## 1. Project Overview

KeplerLab AI Notebook is a **full-stack AI-powered study assistant**. Users:

1. Create **notebooks** (logical containers for study sessions).
2. Upload **materials** — PDFs, DOCX, PPTX, audio/video files, URLs, YouTube links, or raw text.
3. **Chat** with those materials using an agentic RAG pipeline.
4. **Generate** flashcards, MCQ quizzes, AI podcasts, and HTML slide presentations.
5. **Execute Python code** inside a secure sandbox for data analysis.
6. **Research** topics using web search + automated summarisation.

---

## 2. Repository Layout

```
KeplerLab-AI-Notebook/
├── backend/                  # FastAPI application
│   ├── app/
│   │   ├── main.py           # FastAPI app, lifespan, middleware, router mounting
│   │   ├── core/
│   │   │   ├── config.py     # Pydantic Settings — single source of truth
│   │   │   └── utils.py      # Utility helpers (e.g. null-byte sanitiser)
│   │   ├── db/
│   │   │   ├── chroma.py     # ChromaDB singleton client + collection
│   │   │   └── prisma_client.py  # Prisma async client connect/disconnect
│   │   ├── models/           # (Pydantic response models — currently minimal)
│   │   ├── prompts/          # Plain-text LLM prompt templates
│   │   │   ├── chat_prompt.txt
│   │   │   ├── flashcard_prompt.txt
│   │   │   ├── quiz_prompt.txt
│   │   │   ├── podcast_prompt.txt
│   │   │   └── ppt_prompt.txt
│   │   ├── routes/           # FastAPI APIRouters (one file per domain)
│   │   │   ├── auth.py       # /auth/signup, /login, /refresh, /me, /logout
│   │   │   ├── notebook.py   # /notebooks CRUD + generated content
│   │   │   ├── upload.py     # /upload, /upload/url, /upload/text, /materials
│   │   │   ├── chat.py       # /chat, /chat/history, /chat/sessions
│   │   │   ├── flashcard.py  # /flashcard
│   │   │   ├── quiz.py       # /quiz
│   │   │   ├── podcast_router.py  # /podcast, /podcast/audio, /podcast/download
│   │   │   ├── ppt.py        # /presentation, /presentation/*, /ppt/download
│   │   │   ├── agent.py      # /agent/execute, /agent/analyze, /agent/research
│   │   │   ├── search.py     # /web (external search bridge)
│   │   │   ├── jobs.py       # /jobs/{job_id}
│   │   │   ├── models.py     # /models (available LLM models)
│   │   │   ├── health.py     # /health (system status)
│   │   │   ├── proxy.py      # /proxy (URL proxy for CORS)
│   │   │   ├── websocket_router.py  # WS /ws/{notebook_id}
│   │   │   └── utils.py      # Shared helpers (require_material, safe_path, etc.)
│   │   └── services/         # All business-logic services
│   │       ├── agent/        # LangGraph agentic pipeline
│   │       ├── auth/         # Auth helpers (hash, JWT, token store)
│   │       ├── chat/         # Chat session management & persistence
│   │       ├── code_execution/  # Python sandbox executor
│   │       ├── flashcard/    # Flashcard generator
│   │       ├── llm_service/  # Unified LLM abstraction (multi-provider)
│   │       ├── podcast/      # Podcast script + TTS
│   │       ├── ppt/          # HTML presentation generator
│   │       ├── quiz/         # Quiz generator
│   │       ├── rag/          # Vector retrieval pipeline
│   │       ├── text_processing/  # Extractors, chunkers, YouTube, web scraping
│   │       ├── text_to_speech/   # TTS voices
│   │       ├── audit_logger.py
│   │       ├── file_validator.py
│   │       ├── gpu_manager.py
│   │       ├── job_service.py
│   │       ├── material_service.py
│   │       ├── model_manager.py
│   │       ├── notebook_name_generator.py
│   │       ├── notebook_service.py
│   │       ├── performance_logger.py
│   │       ├── rate_limiter.py
│   │       ├── storage_service.py
│   │       ├── token_counter.py
│   │       ├── worker.py
│   │       └── ws_manager.py
│   ├── prisma/
│   │   └── schema.prisma     # Prisma schema — PostgreSQL source of truth
│   ├── data/
│   │   ├── chroma/           # ChromaDB persistence files
│   │   ├── material_text/    # Extracted plain-text cache (UUID.txt)
│   │   ├── models/           # Downloaded HuggingFace models
│   │   └── uploads/          # Raw uploaded files
│   ├── output/
│   │   ├── podcasts/         # Generated WAV files
│   │   ├── presentations/    # Generated HTML presentations
│   │   └── html/
│   ├── logs/                 # Rotating app.log (10 MB × 3 backups)
│   ├── requirements.txt
│   └── cli/                  # Admin CLI tools (backup, export, reindex)
│
├── frontend/                 # React 19 + Vite application
│   ├── src/
│   │   ├── App.jsx           # Root router + protected routes
│   │   ├── main.jsx          # Vite entry — mounts <App/>
│   │   ├── index.css         # TailwindCSS base + custom vars
│   │   ├── api/              # Thin fetch wrappers per domain
│   │   │   ├── config.js     # apiFetch (Bearer + 401 auto-refresh)
│   │   │   ├── auth.js       # login, signup, logout, getCurrentUser, refreshToken
│   │   │   ├── chat.js       # streamChat, sendChatMessage, sessions API
│   │   │   ├── generation.js # generateFlashcards, generateQuiz, generatePresentation, generatePodcast
│   │   │   ├── jobs.js       # pollJob
│   │   │   ├── materials.js  # uploadFile, uploadUrl, getMaterials, deleteMaterial
│   │   │   └── notebooks.js  # getNotebooks, createNotebook, saveGeneratedContent, etc.
│   │   ├── context/
│   │   │   ├── AppContext.jsx   # Global app state (notebook, materials, messages, loading)
│   │   │   ├── AuthContext.jsx  # Auth state + silent refresh scheduler
│   │   │   └── ThemeContext.jsx # Dark/light theme toggle
│   │   ├── hooks/
│   │   │   └── useMaterialUpdates.js  # Polls material status until `completed`
│   │   └── components/
│   │       ├── App.jsx / AuthPage.jsx / HomePage.jsx
│   │       ├── Header.jsx     # Top bar — user avatar, back button, theme toggle
│   │       ├── Sidebar.jsx    # Notebook list + source (material) list + upload dialog
│   │       ├── ChatPanel.jsx  # Main chat interface (SSE streams, sessions, research mode)
│   │       ├── StudioPanel.jsx  # Flashcard / Quiz / Podcast / Presentation generator + history
│   │       ├── ChatMessage.jsx  # Renders Markdown, code blocks, citations, response blocks
│   │       ├── UploadDialog.jsx  # File / URL / YouTube / text upload modal
│   │       ├── PresentationView.jsx  # Inline slide viewer + config dialog
│   │       ├── FileViewerPage.jsx    # Full-page file preview
│   │       ├── WebSearchDialog.jsx   # Quick web-search UI
│   │       ├── SourceItem.jsx        # Single material row in sidebar
│   │       ├── FeatureCard.jsx       # Studio feature entry card
│   │       ├── Modal.jsx             # Re-usable modal wrapper
│   │       └── chat/
│   │           ├── SuggestionDropdown.jsx   # Auto-complete query suggestions
│   │           └── ResearchProgress.jsx     # Animated step-progress for research mode
│   ├── public/
│   ├── index.html
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── eslint.config.js
│   ├── nginx.conf            # Production Nginx config
│   └── Dockerfile
│
├── prompt/
│   └── prompt.md             # Prompt engineering notes
├── test/
│   ├── test_pipeline.py      # Integration tests
│   └── test_all_features.py
└── README.md
```

---

## 3. Backend — Deep Dive

### 3.1 Entry Point & Lifespan

**File:** `backend/app/main.py`

The application boots via `FastAPI(lifespan=lifespan)`. The async context manager performs a strict **ordered startup sequence**:

| Step | Action | Notes |
|------|--------|-------|
| 1 | `await connect_db()` | Opens the Prisma/PostgreSQL connection |
| 2 | `warm_up_embeddings()` | Loads ChromaDB's ONNX model in a thread-pool executor — prevents cold-start stall on first upload |
| 3 | `_get_reranker()` | Pre-loads the BGE-reranker-large cross-encoder model |
| 4 | `asyncio.create_task(job_processor())` | Starts the infinite background worker coroutine |

On shutdown (SIGTERM / `Ctrl+C`): the job-processor task is cancelled, then `disconnect_db()` closes the Prisma connection cleanly.

**All 14 routers** are mounted at startup with their prefix:

```
POST/GET  /auth/*
GET/POST  /notebooks/*
POST      /upload, /upload/url, /upload/text
GET/DELETE /materials/*
POST      /chat
GET/DELETE /chat/history/*
GET/POST/DELETE /chat/sessions/*
POST      /flashcard
POST      /quiz
POST      /podcast, /podcast/audio/*, /podcast/download
POST      /presentation, /presentation/*, /ppt/download
POST      /agent/execute, /agent/analyze, /agent/research
GET       /agent/status/*
POST      /web
GET       /jobs/{job_id}
GET       /health
WS        /ws/{notebook_id}
GET       /proxy
```

---

### 3.2 Configuration (`settings`)

**File:** `backend/app/core/config.py`

A single Pydantic `BaseSettings` instance called `settings` is imported everywhere. It reads values from environment variables (`.env` file via `python-dotenv`).

Key configuration groups:

| Group | Key Variables |
|-------|--------------|
| **Database** | `DATABASE_URL` — PostgreSQL connection string |
| **ChromaDB** | `CHROMA_DIR` — path to persistent ChromaDB storage |
| **File Storage** | `UPLOAD_DIR`, `MAX_UPLOAD_SIZE_MB` (default 25) |
| **Output** | `PODCAST_OUTPUT_DIR`, `PRESENTATIONS_OUTPUT_DIR` |
| **JWT / Auth** | `JWT_SECRET_KEY`, `JWT_ALGORITHM` (HS256), `ACCESS_TOKEN_EXPIRE_MINUTES` (15), `REFRESH_TOKEN_EXPIRE_DAYS` (7), `FILE_TOKEN_EXPIRE_MINUTES` (5) |
| **Cookies** | `COOKIE_SECURE`, `COOKIE_SAMESITE`, `COOKIE_DOMAIN`, `COOKIE_NAME` |
| **CORS** | `CORS_ORIGINS` — comma-separated or list |
| **LLM** | `LLM_PROVIDER` (`MYOPENLM`/`GOOGLE`/`NVIDIA`/`OLLAMA`), model names, API keys, timeouts, temperatures, `LLM_MAX_TOKENS` |
| **Embeddings** | `EMBEDDING_MODEL` (`BAAI/bge-m3`), `EMBEDDING_VERSION`, `EMBEDDING_DIMENSION` (1024) |
| **Reranker** | `RERANKER_MODEL` (`BAAI/bge-reranker-large`), `USE_RERANKER` |
| **Retrieval** | `INITIAL_VECTOR_K` (10), `MMR_K` (8), `FINAL_K` (10), `MMR_LAMBDA` (0.5) |

All temperature, top-p, max-token, frequency-penalty, and presence-penalty values are centrally tunable without touching service code.

---

### 3.3 Database Layer

#### PostgreSQL via Prisma

**File:** `backend/prisma/schema.prisma`

The ORM is **Prisma with the `prisma-client-py` asyncio interface**. Every call to the DB uses `await prisma.<model>.<operation>()`.

Connection management:

```python
# backend/app/db/prisma_client.py
from prisma import Prisma
prisma = Prisma()

async def connect_db():   await prisma.connect()
async def disconnect_db(): await prisma.disconnect()
```

Full schema is described in [Section 6](#6-data-models-prisma-schema).

#### ChromaDB (Vector Store)

**File:** `backend/app/db/chroma.py`

A **single collection** (`chapters`) holds all user embeddings. Tenant isolation is enforced at query time through metadata filters (`user_id`, `material_id`, `notebook_id`).

```python
_client = chromadb.PersistentClient(path=settings.CHROMA_DIR)
_collection = _client.get_or_create_collection(name="chapters")
```

Telemetry is disabled by monkey-patching `posthog.capture` before import, silencing console noise.

---

### 3.4 Middleware Stack

Applied in order (outermost to innermost):

```
Request
  │
  ▼
PerformanceMonitoringMiddleware   ← records start time in ContextVar
  │
  ▼
RateLimitMiddleware               ← sliding-window per-user throttle (see §3.16)
  │
  ▼
log_requests (inline @app.middleware) ← logs METHOD PATH STATUS elapsed
  │
  ▼
CORSMiddleware                    ← from settings.CORS_ORIGINS
  │
  ▼
Route handler
```

---

### 3.5 Authentication System

**Files:** `backend/app/routes/auth.py`, `backend/app/services/auth/`

#### Flow

```
POST /auth/signup  → hash password (bcrypt) → store User in Postgres → return UserResponse
POST /auth/login   → verify password → create JWT pair → store refresh token hash → set HttpOnly cookie → return {access_token}
POST /auth/refresh → read HttpOnly cookie → validate & rotate refresh token → new token pair → return {access_token}
GET  /auth/me      → Bearer token → Depends(get_current_user) → return UserResponse
POST /auth/logout  → revoke all refresh tokens for user → clear cookie
```

#### Token Design

| Token | Transport | TTL | Storage |
|-------|-----------|-----|---------|
| Access JWT | `Authorization: Bearer` header | 15 min | In-memory (frontend) |
| Refresh JWT | HttpOnly `refresh_token` cookie (path `/auth`) | 7 days | Hash stored in `refresh_tokens` table |

**Token rotation** — every refresh call:
1. Validates the incoming refresh token hash against the DB.
2. Marks the old token as `used = true`.
3. Issues a new refresh token in the same *family*.
4. If a used token is seen again → family **revocation** (all tokens in that family are invalidated — signals token theft).

#### Signed File Tokens

A short-lived (5-minute) signed JWT is issued for audio/file download endpoints. This avoids exposing the real access token in URL parameters.

```
create_file_token(user_id) → signed JWT in payload
GET /podcast/audio/{user_id}/{filename}?token=<jwt>
```

#### `get_current_user` Dependency

```python
async def get_current_user(token: str = Depends(OAuth2PasswordBearer(...))):
    payload = decode_jwt(token)
    user = await prisma.user.find_unique(where={"id": payload["sub"]})
    if not user or not user.isActive:
        raise HTTPException(401)
    return user
```

All protected endpoints use `current_user = Depends(get_current_user)`.

---

### 3.6 Routes Catalogue

#### `POST /upload` — File Upload

1. Streams the file to a temp path.
2. Validates: MIME type, magic bytes (python-magic), file size ≤ 25 MB.
3. Moves the file to `data/uploads/<uuid>.<ext>`.
4. Creates a `Material` record in Postgres (status = `pending`).
5. Creates a `BackgroundJob` record (type = `material_processing`).
6. Calls `job_queue.notify()` to wake the background worker immediately.
7. Returns HTTP 202 with `{job_id, material_id}`.

#### `POST /upload/url` — URL / YouTube

- Detects `youtube.com` or `youtu.be` → YouTube transcript path.
- Otherwise → web-scraping path.
- Same job queue pattern.

#### `POST /upload/text` — Raw text paste

- Directly creates material record + job.

#### `GET /materials` — List user's materials

Returns all `Material` records for the current user (optionally filtered by `notebook_id`).

#### `DELETE /materials/{material_id}`

Deletes DB record, physical file, and all ChromaDB vectors for that material.

#### `POST /chat` — Main chat endpoint

Accepts `message`, `notebook_id`, `material_ids[]`, optional `session_id`.

- Creates/reuses a `ChatSession`.
- Builds `AgentState` and runs `run_agent_stream(initial_state)` (LangGraph).
- Returns a **streaming SSE response** with events:
  - `event: start` — agent started
  - `event: step` — agent step metadata (intent, tool name)
  - `event: token` — partial LLM output token
  - `event: meta` — final agent metadata (tokens, iterations, tools used)
  - `event: done` — stream complete
  - `event: error` — error payload

After streaming finishes, the full response is persisted to `ChatMessage` table.

#### `POST /flashcard`

Calls `generate_flashcards(text, card_count, difficulty, instructions)`. Returns JSON array of `{front, back}` cards.

#### `POST /quiz`

Calls `generate_quiz(text, mcq_count, difficulty, instructions)`. Returns JSON with `{questions: [{question, options: [A-D], correct_answer, explanation}]}`.

#### `POST /podcast`

Calls `generate_podcast_audio_async(text)`. Saves WAV to disk. Returns `{title, audio_filename, dialogue, file_token}`.

#### `POST /presentation`

Calls `generate_presentation(text, user_id, max_slides, theme, additional_instructions)`. Returns `{title, slide_count, slides, html, theme}`.

#### `POST /agent/execute`

Accepts user-authored Python code. Runs it in the secure sandbox. Streams `stdout` line-by-line via SSE, then final `result` event with `{stdout, stderr, exit_code, chart_base64, elapsed}`.

#### `POST /agent/analyze`

NL → generates Python code (LLM) → executes in sandbox. Driven by `DATA_ANALYSIS` intent in the LangGraph agent.

#### `POST /agent/research`

Triggers web research agent. Multi-step: plan queries → DuckDuckGo search → fetch pages → cluster → write report.

#### `GET /jobs/{job_id}`

Polls a `BackgroundJob`. Returns `{id, type, status, result, error, created_at, updated_at}`.

#### `GET /health`

Returns system health: DB connectivity, ChromaDB status, GPU availability, uptime.

#### `WS /ws/{notebook_id}`

WebSocket for real-time push notifications (e.g., when a material finishes processing). The `ws_manager.py` broadcasts to all connections belonging to a notebook.

---

### 3.7 Background Worker & Job Queue

**File:** `backend/app/services/worker.py`

The worker is an `asyncio.Task` started at lifespan. It runs a `while True` loop:

```
while True:
    clean up completed asyncio tasks
    if slots available (< MAX_CONCURRENT_JOBS=5):
        job = fetch_next_pending_job()
        if job:
            atomically set status = processing
            create asyncio.Task(_process_job(job))
    await job_queue.wait(timeout=2s)   ← event-driven, wakes on notify()
```

`_process_job(job)` dispatches based on `job.jobType`:
- `material_processing` (file) → `process_material_by_id()`
- `url_processing` → `process_url_material_by_id()`
- `text_processing` → `process_text_material_by_id()`

**Status lifecycle:**

```
pending → processing → [ocr_running | transcribing] → embedding → completed
                                                                 └──► failed
```

All exceptions are caught; errors are stored on the job record so the worker loop never dies.

---

### 3.8 RAG Pipeline

**Directory:** `backend/app/services/rag/`

#### a) Embedding & Storage (`embedder.py`)

- Uses ChromaDB's built-in **ONNX all-MiniLM-L6-v2** (384-dim) — no external embedding server needed.
- External config shows `BAAI/bge-m3` (1024-dim) as target, but currently ChromaDB handles embeddings internally.
- `embed_and_store(chunks, material_id, user_id, notebook_id, filename)`:
  - Upserts in batches of 200 (to stay within ChromaDB's 256-item limit).
  - Attaches tenant metadata (`material_id`, `user_id`, `notebook_id`, `embedding_version`).
  - Each batch is retried up to 3 times on transient errors.

#### b) Retrieval (`secure_retriever.py`)

The **only authorised entry point** for similarity search. Key security: every query **must** have a `user_id` filter.

Retrieval algorithm (multi-source):

```
1. For each material_id:
   a. Vector search → top INITIAL_VECTOR_K (10) chunks
   b. Apply MMR (Maximal Marginal Relevance, λ=0.5) → MMR_K (8) diverse chunks
2. Merge all per-material results
3. Cross-encoder reranking (BGE-reranker-large) → FINAL_K (10) best chunks
4. Source diversity: clamp per-material contribution [MIN=1, MAX=3] chunks
   (increases for cross-document queries to MAX=5)
```

Cross-document query detection uses keyword matching (`compare`, `vs`, `contrast`, etc.).

#### c) Context Builder (`context_builder.py`)

Assembles the ranked chunks into a structured context string, grouping by material/source.

#### d) Context Formatter (`context_formatter.py`)

Formats context with inline citation markers `[1]`, `[2]`, etc. paired with source metadata so the LLM can cite accurately.

#### e) Reranker (`reranker.py`)

Wraps the `BAAI/bge-reranker-large` cross-encoder via `sentence-transformers`. Lazy-loaded on first use; warm-up at startup. Returns re-scored chunk list.

#### f) Citation Validator (`citation_validator.py`)

Post-processes LLM output to strip hallucinated citation numbers (i.e., `[N]` not backed by a real source in the context).

---

### 3.9 LangGraph Agent

**Directory:** `backend/app/services/agent/`

The agent is a **compiled LangGraph `StateGraph`** with nodes:

```
[intent_and_plan] → [tool_router] → [reflection]
       ▲                                  │
       └──────────── (continue) ──────────┘
                                          │
                                    (respond)
                                          │
                                [generate_response]
```

#### State (`state.py`)

`AgentState` (`TypedDict`) carries everything:

| Field | Type | Purpose |
|-------|------|---------|
| `user_message` | `str` | The user's input |
| `intent` | `str` | Detected intent type |
| `intent_confidence` | `float` | 0.0–1.0 |
| `plan` | `List[Dict]` | Ordered tool call plan |
| `tool_results` | `List[ToolResult]` | Accumulated outputs |
| `iterations` | `int` | Safety counter |
| `total_tokens` | `int` | Token budget counter |
| `response` | `str` | Final synthesised answer |
| `agent_metadata` | `Dict` | Sent to frontend (tools, intent, tokens) |

Hard limits: `MAX_AGENT_ITERATIONS = 7`, `TOKEN_BUDGET = 12_000`, `MAX_TOOL_CALLS = 10`.

#### Intent Detection (`intent.py`)

Two-stage classification:

1. **Fast keyword rules** (regex, ordered priority):
   - `DATA_ANALYSIS` — CSV, chart, average, pandas, …
   - `CODE_EXECUTION` — run/execute/write python/script, …
   - `RESEARCH` — research, deep dive, latest, search the web, …
   - `CONTENT_GENERATION` — create/make quiz/flashcard/presentation, …
   - `QUESTION` — fallback (matches everything)
2. **LLM fallback** (only when confidence < threshold) — single token classification via MYOPENLM with `temperature=0.0`.

#### Planner (`planner.py`)

Given the intent, selects which tool(s) to call and in what order. For simple `QUESTION` intents, the plan is a single `rag_search` call. For `RESEARCH`, it plans multiple web-search + extraction steps.

#### Tool Router (`router.py`)

Executes the current plan step. Dispatches to:

| Tool | Intent |
|------|--------|
| `rag_search` | `QUESTION` |
| `web_search` | `RESEARCH` |
| `code_executor` | `CODE_EXECUTION`, `DATA_ANALYSIS` |
| `quiz_generator` | `CONTENT_GENERATION` (quiz) |
| `flashcard_generator` | `CONTENT_GENERATION` (flashcard) |
| `presentation_generator` | `CONTENT_GENERATION` (PPT) |
| `podcast_generator` | `CONTENT_GENERATION` (podcast) |

#### Reflection (`reflection.py`)

After each tool execution, decides:
- **continue** — more steps in the plan remain.
- **retry** — tool failed but retries are allowed (`step_retries < 2`).
- **respond** — all steps done or limits reached.

#### Response Generator (`graph.py::generate_response`)

Synthesises all successful `ToolResult` outputs. For multi-tool results, wraps each in `[Source N — tool_name]` blocks, joined by `---`. Builds `agent_metadata` dict for the frontend.

#### Streaming (`run_agent_stream`)

```python
async for event in run_agent_stream(initial_state):
    yield event   # Server-Sent Event string
```

Events are yielded as SSE-formatted strings. Token-level streaming happens inside the `rag_search` tool when the LLM streams its response.

---

### 3.10 LLM Service

**Directory:** `backend/app/services/llm_service/`

The `get_llm(temperature, max_tokens, ...)` factory returns a LangChain `BaseChatModel` based on `settings.LLM_PROVIDER`:

| Provider | Class | Notes |
|----------|-------|-------|
| `MYOPENLM` | Custom HTTP wrapper | Proxy to `openlmfallback.herokuapp.com` |
| `GOOGLE` | `ChatGoogleGenerativeAI` | `gemini-2.5-flash` |
| `NVIDIA` | `ChatNVIDIA` | `qwen/qwen3.5-397b-a17b` |
| `OLLAMA` | `ChatOllama` | Local Ollama instance |

All providers are called through the same LangChain interface — `await llm.ainvoke(prompt)` or `llm.astream(messages)`.

Temperature presets (from `settings`):

| Use case | Temperature |
|----------|-------------|
| Structured (quiz/flashcard/PPT) | 0.1 |
| Chat / RAG answers | 0.2 |
| Creative (podcast scripts) | 0.7 |
| Code generation | 0.1 |

---

### 3.11 Text Processing & Ingestion

**Directory:** `backend/app/services/text_processing/`

Material processing pipeline (runs inside the background worker):

```
Raw File / URL / Text
      │
      ▼
FileTypeDetector     ← MIME detection, dispatch to right extractor
      │
      ├── PDF         → pdfplumber (text) + PyMuPDF (structure) + OCR fallback (EasyOCR / pytesseract)
      ├── DOCX        → python-docx
      ├── PPTX        → python-pptx (text extraction only)
      ├── XLSX / CSV  → openpyxl / xlrd / pandas
      ├── Image       → OCR (EasyOCR / pytesseract)
      ├── Audio/Video → Whisper transcription (openai-whisper)
      ├── YouTube URL → youtube-transcript-api (captions first) → yt-dlp + Whisper fallback
      └── Web URL     → trafilatura / BeautifulSoup4 / Playwright screenshot
      │
      ▼
LangChain RecursiveCharacterTextSplitter
  chunk_size=1000, chunk_overlap=200
      │
      ▼
embed_and_store()   ← ChromaDB UPSERT
      │
      ▼
material.status = "completed", chunkCount = N
```

Extracted plain text is also saved to `data/material_text/<uuid>.txt` for direct access by generation services (flashcards, quiz, podcast, PPT) — avoids re-querying ChromaDB for full-text use cases.

---

### 3.12 Generation Services

#### Flashcards (`services/flashcard/generator.py`)

- Reads material text.
- Builds prompt from `prompts/flashcard_prompt.txt`.
- Calls LLM with `temperature=0.1`.
- Parses JSON array: `[{front, back}, ...]`.
- Supports `card_count`, `difficulty`, `additional_instructions`.

#### Quiz (`services/quiz/generator.py`)

- Reads material text.
- Builds prompt from `prompts/quiz_prompt.txt`.
- Calls LLM with `temperature=0.1`.
- Parses JSON: `{questions: [{question, options, correct_answer, explanation}]}`.
- Supports `mcq_count`, `difficulty`, `additional_instructions`.

#### Presentation (`services/ppt/generator.py`)

- Reads material text.
- Builds prompt from `prompts/ppt_prompt.txt`.
- LLM generates a JSON slide plan + content.
- Python code converts to a **self-contained HTML presentation** (rendered in-browser with CSS transitions).
- Returns `{title, slide_count, slides: [...], html: "<full html>", theme}`.
- HTML output is saved to `output/presentations/`.

#### Podcast (`services/podcast/generator.py`)

- Reads material text.
- Builds a two-speaker dialogue script (LLM with `temperature=0.7`).
- `generate_podcast_audio_async()` uses multi-speaker TTS.
- Returns an in-memory audio buffer + `dialogue_timing` list.
- Saved as WAV in `output/podcasts/<user_id>/`.

---

### 3.13 Code Execution Sandbox

**Directory:** `backend/app/services/code_execution/`

- Executes user-provided Python in a **restricted subprocess**.
- Captures `stdout` line-by-line and streams them to the client via SSE.
- Captures `stderr` and `exit_code`.
- Detects matplotlib/plotly figures → encodes as `chart_base64` PNG.
- Enforces `timeout` (max 15 seconds even if user specifies more).
- Execution logs are persisted via `agent/persistence.py`.

---

### 3.14 Text-to-Speech & Podcast

**Directory:** `backend/app/services/text_to_speech/`

Multiple TTS backends are abstracted (edge-tts, system voices, etc.). The podcast service selects two different voices for a host/guest dialogue format. Output is always WAV.

---

### 3.15 WebSocket Manager

**File:** `backend/app/services/ws_manager.py`

```python
class ConnectionManager:
    async def connect(websocket, notebook_id)
    async def disconnect(websocket, notebook_id)
    async def broadcast_to_notebook(notebook_id, message)
```

Used to push real-time status updates to the frontend — e.g., when a material's status changes from `processing` → `completed`, all browser tabs viewing that notebook receive an instant notification.

---

### 3.16 Rate Limiter

**File:** `backend/app/services/rate_limiter.py`

Sliding-window (60-second) per-user throttle using in-memory `defaultdict`:

| Endpoint Type | Limit |
|---------------|-------|
| Chat (`/chat`, `/agent/*`) | 30 req/min |
| Generation (`/flashcard`, `/quiz`, `/podcast`, `/presentation`) | 5 req/min |

Returns HTTP 429 with `Retry-After` header. User identity is extracted from the JWT without a DB round-trip.

---

### 3.17 Performance Logger

**File:** `backend/app/services/performance_logger.py`

Uses Python `contextvars.ContextVar` to track timings scoped to the current async request:

```
set_request_start_time()     ← called by middleware
record_retrieval_time(s)     ← called by secure_retriever
record_reranking_time(s)     ← called by reranker
record_llm_time(s)           ← called by LLM service
```

At response time, the middleware logs a structured line:

```
performance path=/chat retrieval=0.32s rerank=0.18s llm=1.42s total=2.17s
```

---

### 3.18 Audit Logger

**File:** `backend/app/services/audit_logger.py`

Writes structured audit events for sensitive operations (login, file access, API usage) to the `logs/` directory using the rotating file handler.

---

### 3.19 Token Counter

**File:** `backend/app/services/token_counter.py`

Uses `tiktoken` to estimate token counts before sending to the LLM. Prevents expensive over-budget requests. `track_token_usage()` updates the agent state's `total_tokens` counter.

---

### 3.20 File Validator

**File:** `backend/app/services/file_validator.py`

Validates uploaded files **in a thread-pool executor** (non-blocking):

1. `python-magic` — reads file header bytes to verify true MIME type.
2. Size check (≤ `MAX_UPLOAD_SIZE_MB`).
3. Extension whitelist cross-check.
4. Returns an internal filename with a safe UUID prefix.
5. Raises `FileValidationError` on any failure.

---

### 3.21 Storage Service

**File:** `backend/app/services/storage_service.py`

Abstracts reading cached material text:

```python
text = load_material_text(material_id)  # reads data/material_text/<uuid>.txt
```

Used by generation endpoints to avoid re-parsing raw files.

---

## 4. Frontend — Deep Dive

### 4.1 Project Setup & Tooling

| Tool | Version | Purpose |
|------|---------|---------|
| React | 19.2 | UI framework |
| Vite | 7.2 | Build tool + dev server (HMR) |
| React Router | 7.11 | Client-side routing |
| TailwindCSS | 3.4 | Utility-first CSS |
| react-markdown + remark-gfm | 10.1 | Markdown rendering with GFM |
| react-syntax-highlighter | 16.1 | Code block syntax highlighting |
| jsPDF | 4.0 | Client-side PDF export |

**Environment variable:** `VITE_API_BASE_URL` (default `http://localhost:8000`).

---

### 4.2 Routing & App Shell

**File:** `frontend/src/App.jsx`

```
/                  → <HomePage />         (public)
/auth              → <AuthPage />         (public)
/notebook/:id      → <Workspace />        (protected)
/file/:materialId  → <FileViewerPage />   (protected)
*                  → <Navigate to="/" />
```

`<ProtectedRoute>` wraps authenticated pages — shows a spinner while `AuthContext` is initialising, redirects unauthenticated users to `/auth`.

`<Workspace>` loads the notebook by `id` param (or sets up draft mode for `id === 'draft'`), then renders a three-column layout:

```
┌──────────────────────────────────────────────────────────┐
│  <Header />                                              │
├──────────┬─────────────────────────────┬─────────────────┤
│          │                             │                 │
│<Sidebar/>│      <ChatPanel/>           │ <StudioPanel/>  │
│          │                             │                 │
└──────────┴─────────────────────────────┴─────────────────┘
```

---

### 4.3 State Management (Contexts)

#### `AppContext` (`context/AppContext.jsx`)

Global state for the active workspace. All components consume this via `useApp()`:

| State | Description |
|-------|-------------|
| `currentNotebook` | Active notebook object or `null` |
| `draftMode` | Whether working in an unsaved draft |
| `materials` | `Material[]` list for current notebook |
| `currentMaterial` | The single material currently "open" |
| `selectedSources` | `Set<string>` — checked material IDs for chat/generation |
| `messages` | `ChatMessage[]` — current session's visible messages |
| `sessionId` | Current chat session UUID |
| `flashcards` / `quiz` | Latest generated content |
| `loading` | `{[key: string]: boolean}` map — per-operation loading flags |

Key helpers:
- `toggleSourceSelection(id)` — add/remove from checkbox set.
- `selectAllSources()` / `deselectAllSources()`.
- `addMessage(role, content, citations)` — appends to messages array.
- `setLoadingState(key, value)` — updates loading map.

Context **clears** `messages`, `materials`, `selectedSources`, `sessionId` automatically when `currentNotebook.id` changes.

#### `AuthContext` (`context/AuthContext.jsx`)

| State | Description |
|-------|-------------|
| `user` | `{id, email, username, role}` or `null` |
| `accessToken` | In-memory access JWT |
| `isLoading` | True during silent session restore |
| `isAuthenticated` | Derived: `!!user` |

**Silent token refresh** — on mount, attempts `POST /auth/refresh` (cookie-based). On success, loads user data and schedules a `setTimeout` to re-refresh every **13 minutes** (before the 15-minute JWT expiry). The `apiFetch` function also auto-refreshes on any 401 response.

#### `ThemeContext` (`context/ThemeContext.jsx`)

Simple dark/light mode toggle stored in `localStorage` and applied as a CSS class on `<html>`.

---

### 4.4 API Layer

**Directory:** `frontend/src/api/`

All API calls go through `apiFetch` in `config.js`:

```javascript
async function apiFetch(endpoint, options = {}) {
  // Attaches 'Authorization: Bearer <token>'
  // Sends cookies (credentials: 'include') for refresh token
  // On 401: silently calls /auth/refresh, retries original request
  // On second 401: clears token, reloads page (forces re-login)
}
```

#### `api/auth.js`
- `login(email, password)` → `POST /auth/login`
- `signup(email, username, password)` → `POST /auth/signup`
- `logout()` → `POST /auth/logout`
- `getCurrentUser(token)` → `GET /auth/me`
- `refreshToken()` → `POST /auth/refresh`

#### `api/chat.js`
- `streamChat(...)` → `POST /chat` — returns raw `Response` for SSE reading.
- `sendChatMessage(...)` → `POST /chat` (non-streaming).
- `getChatHistory(notebookId, sessionId)` → `GET /chat/history/:id`.
- `clearChatHistory(...)` → `DELETE /chat/history/:id`.
- `getChatSessions(notebookId)` → `GET /chat/sessions/:id`.
- `createChatSession(notebookId, title)` → `POST /chat/sessions`.
- `deleteChatSession(sessionId)` → `DELETE /chat/sessions/:id`.
- `getSuggestions(partialInput, notebookId)` → `POST /chat/suggestions`.
- `streamResearch(query, notebookId, materialIds)` → `POST /agent/research`.

#### `api/materials.js`
- `uploadFile(file, notebookId)` → `POST /upload` (multipart).
- `uploadUrl(url, notebookId, sourceType)` → `POST /upload/url`.
- `uploadText(text, title, notebookId)` → `POST /upload/text`.
- `getMaterials(notebookId)` → `GET /materials`.
- `deleteMaterial(materialId)` → `DELETE /materials/:id`.

#### `api/generation.js`
- `generateFlashcards(materialIds, opts)` → `POST /flashcard`.
- `generateQuiz(materialIds, opts)` → `POST /quiz`.
- `generatePresentation(materialIds, opts)` → `POST /presentation`.
- `generatePodcast(materialId)` → `POST /podcast`.
- `downloadPodcast(materialId)` → `POST /podcast/download`.
- `downloadBlob(url, filename)` — helper to trigger browser download.

#### `api/notebooks.js`
- `getNotebooks()` / `createNotebook(name, desc)` / `deleteNotebook(id)`.
- `saveGeneratedContent(notebookId, contentType, title, data, materialId)`.
- `getGeneratedContent(notebookId)`.
- `deleteGeneratedContent(notebookId, contentId)`.
- `updateGeneratedContent(notebookId, contentId, data)`.

#### `api/jobs.js`
- `pollJob(jobId)` → `GET /jobs/:id`.

---

### 4.5 Key Components

#### `<Header />`

Top navigation bar:
- Shows app logo and current notebook name.
- **Back button** — calls `onBack()` to clear state and return to `<HomePage>`.
- Theme toggle (moon/sun icon).
- User avatar with logout.

#### `<Sidebar />`

Left panel:
- **Notebook list** when no notebook is active.
- **Source list** when inside a notebook:
  - Each `<SourceItem>` shows filename, status badge, checkbox for selection.
  - Bulk "Select All / Deselect All" controls.
- **Upload button** → opens `<UploadDialog>`.
- `useMaterialUpdates` hook polls for status changes.

#### `<UploadDialog />`

Four upload modes (tabs):
1. **File** — drag-and-drop or browse. Accepts PDF, DOCX, PPTX, XLSX, CSV, MP3, MP4, images.
2. **URL** — web page or YouTube link.
3. **Text** — paste raw text with a custom title.
4. **YouTube** — explicit YouTube URL.

After upload: creates a material record, starts polling the job, adds to the sidebar immediately with `pending` status.

#### `<ChatPanel />`

The main interaction panel (~876 lines). Key capabilities:

- **SSE streaming** — reads the `Response.body` `ReadableStream`, parses events:
  ```
  event: start  → shows "agent is thinking..."
  event: step   → updates step label (e.g., "Searching your materials")
  event: token  → appends to streaming message bubble
  event: meta   → updates agent metadata display
  event: done   → finalises message, saves to DB
  event: error  → shows error toast
  ```
- **Chat sessions** — dropdown to switch between named sessions; history modal to browse/delete all sessions.
- **Quick Actions** — one-click prompts: Summarize, Explain this, Key points, Study guide.
- **Research mode** — toggleable. When active, routes to `POST /agent/research` and shows `<ResearchProgress>` with animated step progress.
- **Suggestions** — debounced autocomplete via `POST /chat/suggestions`.
- **File context** — shows selected source count badge.
- **Abort** — cancel button sends `AbortController.abort()` to stop the in-flight SSE stream.

#### `<StudioPanel />`

Right panel for content generation (~1839 lines):

- **Resizable** — drag handle allows width 260–600 px.
- **Grid view** — four `<FeatureCard>` tiles: Audio, Flashcards, Quiz, Presentation.
- **Flashcards view**:
  - Config dialog: card count, difficulty, topic filter, instructions.
  - Flip animation. Prev/Next navigation.
  - Export as PDF (via jsPDF) or JSON.
  - Save / load history per notebook.
- **Quiz view**:
  - Config dialog: question count, difficulty, topic filter.
  - Interactive MCQ UI with score tracking.
  - Answer reveal with explanations.
  - Export PDF.
- **Podcast view**:
  - Generates audio and shows an audio player with `<audio>` tag.
  - Dialogue timing list — shows each line with speaker tag.
  - Download WAV button.
- **Presentation view** (`<InlinePresentationView>`):
  - Config dialog: max slides, theme, custom instructions.
  - Full inline slide viewer with prev/next controls.
  - Download as standalone HTML.
- **Content history** — per-notebook list of all previously generated items. Each has rename/delete options.
- **AbortController** per generation type — allows mid-generation cancel.

#### `<ChatMessage />`

Renders a single message bubble:
- **User messages**: plain text, right-aligned.
- **AI messages**: full Markdown rendering via `react-markdown` with `remark-gfm`.
- Inline code blocks with `react-syntax-highlighter` (one-dark theme).
- **Citations** — inline `[1]` markers linked to source metadata cards.
- **Agent metadata dock** — collapsible section showing: intent, tools used, token count, iterations.
- **Response blocks** — structured cards for quiz / flashcard results embedded in chat.

#### `<PresentationView />`

Full-featured slide viewer:
- Renders `<iframe>` with the generated HTML string.
- Keyboard navigation (← →).
- Fullscreen toggle.
- Slide thumbnail filmstrip.

#### `<HomePage />`

Landing screen for authenticated users:
- Lists all notebooks with creation date and material count.
- Create notebook button (auto-generates a name via the AI notebook-name-generator endpoint).
- Delete notebook.

---

### 4.6 Hooks

#### `useMaterialUpdates.js`

Polls `GET /materials?notebook_id=...` every 3 seconds while any material has a non-terminal status (`pending`, `processing`, `ocr_running`, `transcribing`, `embedding`). When a status reaches `completed` or `failed`, broadcasts the update to update sidebar badges and stops polling if all materials are terminal. Also listens on the WebSocket for instant push notifications.

---

## 5. End-to-End Request Flows

### 5.1 Upload a File

```
User selects PDF
    │
    ▼
<UploadDialog> → POST /upload (multipart, 202)
    │
    ▼
upload.py:
  1. Stream to temp file
  2. validate_upload() — python-magic + size check [thread pool]
  3. Move to data/uploads/<uuid>.pdf
  4. prisma.material.create(status=pending)
  5. prisma.backgroundjob.create(type=material_processing)
  6. job_queue.notify()
  7. Return {job_id, material_id}
    │
    ▼
Sidebar shows material with "pending" badge
useMaterialUpdates starts polling
    │
    ▼
worker.py wakes (event-driven):
  process_material_by_id(material_id):
    status → processing
    FileTypeDetector → PDF
    pdfplumber.extract_text() [+ OCR if scanned]
    status → embedding
    RecursiveCharacterTextSplitter → chunks
    embed_and_store(chunks) → ChromaDB
    save text to data/material_text/<uuid>.txt
    status → completed, chunkCount = N
    ws_manager.broadcast("material_completed")
    │
    ▼
WebSocket push → browser receives notification
useMaterialUpdates sees status=completed
Sidebar badge updates to green "ready"
```

### 5.2 Chat / Ask a Question

```
User types "Explain the main thesis" (2 materials selected)
    │
    ▼
ChatPanel.handleSubmit():
  optimistic UI: add user message to messages[]
  setLoadingState("chat", true)
  response = await streamChat(materialIds, message, notebookId, sessionId)
  readSSEStream(response, callbacks)
    │
    ▼
POST /chat (streaming):
  chat.py:
    1. Validate materials belong to user
    2. filter_completed_material_ids() — skip pending materials
    3. Create/reuse ChatSession
    4. Build AgentState{user_message, material_ids, ...}
    5. run_agent_stream(initial_state)
      │
      ▼
      LangGraph:
        intent_and_plan():
          _keyword_classify("explain...") → QUESTION (0.5)
          plan = [{tool: rag_search}]
        tool_router():
          secure_retriever.retrieve(query, user_id, material_ids)
            → vector search × 2 materials
            → MMR per material
            → merge → rerank (BGE)
            → top 10 chunks
          format_context_with_citations()
          LLM.astream(chat_prompt + context + question)
            → yield token events
        reflection() → "respond"
        generate_response() → metadata
      │
      ▼
    SSE events:
      event: start   {"session_id": "..."}
      event: step    {"label": "Searching your materials"}
      event: token   {"content": "The main thesis..."}
      ...more tokens...
      event: meta    {"intent": "QUESTION", "tools_used": ["rag_search"], ...}
      event: done    {}
    │
    ▼
  After stream: persist ChatMessage to DB
    │
    ▼
ChatPanel receives done:
  streamingContent → final message
  addMessage("assistant", fullText, citations)
  setLoadingState("chat", false)
```

### 5.3 Generate Flashcards

```
User clicks Flashcards in StudioPanel, configures options, clicks Generate
    │
    ▼
StudioPanel.handleGenerateFlashcards():
  setLoadingState("flashcards", true)
  flashcards = await generateFlashcards(selectedMaterialIds, {card_count, difficulty, ...})
    │
    ▼
POST /flashcard:
  flashcard.py:
    require_materials_text(ids, user_id)  ← reads data/material_text/*.txt
    generate_flashcards(text, card_count, difficulty, instructions)
      → load flashcard_prompt.txt
      → LLM call (temperature=0.1)
      → json_repair + parse [{front, back}]
    return JSONResponse(flashcards)
    │
    ▼
StudioPanel:
  setFlashcardsData(flashcards)
  setActiveView("flashcards")
  saveGeneratedContent(notebookId, "flashcards", data)  ← persists to DB
  setFlashcards(flashcards)  ← updates AppContext
```

### 5.4 Generate a Podcast

```
User clicks Audio → Generate Podcast
    │
    ▼
StudioPanel → POST /podcast {material_id}
    │
    ▼
podcast_router.py:
  require_material_text(material_id, user_id)
  generate_podcast_audio_async(text):
    LLM (temperature=0.7) → 2-speaker dialogue script
    TTS engine → voice A (host) + voice B (guest) → WAV bytes
    returns (audio_buffer, title, dialogue_timing)
  _save_audio() → output/podcasts/<user_id>/<title>_<uid>.wav
  create_file_token(user_id) → signed JWT
  return {title, audio_filename, file_token, dialogue}
    │
    ▼
StudioPanel:
  setAudioData({title, audio_filename, file_token, dialogue})
  setActiveView("audio")
  Audio player: src = /podcast/audio/<user_id>/<filename>?token=<jwt>
```

### 5.5 Generate a Presentation

```
User opens Presentation config → sets max_slides, theme → Generate
    │
    ▼
POST /presentation {material_ids, max_slides, theme, additional_instructions}
    │
    ▼
ppt.py:
  require_materials_text(ids, user_id)
  generate_presentation(text, user_id, max_slides, theme, instructions):
    load ppt_prompt.txt
    LLM call → JSON slide plan
    Convert to self-contained HTML (CSS transitions, no external deps)
    Save to output/presentations/
    return {title, slide_count, slides, html, theme}
    │
    ▼
StudioPanel:
  setPresentationData(result)
  setActiveView("presentation")
  <InlinePresentationView html={result.html} />
```

### 5.6 Code Execution / Data Analysis

```
User opens Code Editor → writes Python → Run
    │
    ▼
POST /agent/execute {code, notebook_id, timeout: 15}
    │
    ▼
agent.py:
  create asyncio.Queue
  asyncio.create_task(execute_code(code, on_stdout_line=...))
  SSE stream:
    event: stdout {"line": "Hello World\n"}
    event: result {"stdout": ..., "exit_code": 0, "chart_base64": "...png..."}
    event: done {}
    │
    ▼
log_code_execution() → persists to DB
    │
    ▼
Frontend: renders stdout in chat, embeds chart_base64 as <img>
```

### 5.7 Research Mode

```
User toggles Research Mode → types "Latest papers on transformer attention"
    │
    ▼
ChatPanel → POST /agent/research {query, notebook_id, material_ids}
    │
    ▼
agent.py:
  AgentState{intent_override: "RESEARCH", ...}
  run_agent_stream():
    intent = RESEARCH
    planner → [web_search × N, extract_content × N, cluster, synthesize]
    tool_router:
      DuckDuckGo search API → result URLs
      httpx fetch each URL → trafilatura extract → text chunks
      cluster themes → LLM synthesize → report
    SSE events:
      event: step {"label": "Planning queries"}
      event: step {"label": "Searching sources"}
      event: step {"label": "Extracting content"}
      event: step {"label": "Clustering themes"}
      event: step {"label": "Writing report"}
      event: token ... (report tokens)
      event: done {}
    │
    ▼
ChatPanel:
  <ResearchProgress steps={[...]} /> shows animated progress
  Final message shows full research report with citations
```

---

## 6. Data Models (Prisma Schema)

### `User`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `email` | VARCHAR(255) UNIQUE | |
| `username` | VARCHAR(100) | |
| `hashedPassword` | VARCHAR(255) | bcrypt |
| `isActive` | Boolean | default true |
| `role` | VARCHAR(50) | "user" / "admin" |
| `createdAt` / `updatedAt` | DateTime | |

### `Notebook`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `userId` | UUID FK → User | cascade delete |
| `name` | VARCHAR(255) | |
| `description` | Text? | |

### `Material`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `userId` | UUID FK → User | |
| `notebookId` | UUID FK? → Notebook | set null on notebook delete |
| `filename` | VARCHAR(255) | |
| `title` | VARCHAR(510)? | custom title for URL/YouTube/text |
| `originalText` | Text? | plain-text cache (large) |
| `status` | MaterialStatus enum | `pending → processing → embedding → completed / failed` |
| `chunkCount` | VARCHAR(10) | stored as string |
| `sourceType` | VARCHAR(50) | `file / url / youtube / text` |
| `metadata` | Text? | JSON string (extraction metadata) |
| `error` | Text? | error message on failure |

### `ChatSession`

| Column | Notes |
|--------|-------|
| `id` UUID PK | |
| `notebookId` FK | |
| `userId` FK | |
| `title` VARCHAR(255) | auto-set from first message |

### `ChatMessage`

| Column | Notes |
|--------|-------|
| `id` UUID PK | |
| `notebookId` / `userId` FK | |
| `chatSessionId` FK? | |
| `role` VARCHAR(20) | "user" / "assistant" |
| `content` Text | full message content |

### `GeneratedContent`

| Column | Notes |
|--------|-------|
| `id` UUID PK | |
| `notebookId` / `userId` FK | |
| `materialId` FK? | |
| `contentType` VARCHAR(50) | "flashcards" / "quiz" / "audio" / "presentation" |
| `title` VARCHAR(255)? | user-editable name |
| `data` Json | full generated content payload |

### `RefreshToken`

| Column | Notes |
|--------|-------|
| `id` UUID PK | |
| `userId` FK | |
| `tokenHash` VARCHAR(255) UNIQUE | SHA-256 of the JWT |
| `family` VARCHAR(255) | for rotation detection |
| `used` Boolean | marks rotated (old) tokens |
| `expiresAt` DateTime | |

### `BackgroundJob`

| Column | Notes |
|--------|-------|
| `id` UUID PK | |
| `userId` FK | |
| `jobType` VARCHAR(50) | "material_processing" etc. |
| `status` JobStatus enum | mirrors MaterialStatus |
| `result` Json? | job output |
| `error` Text? | failure reason |

---

## 7. Environment Variables Reference

Create `backend/.env`:

```dotenv
# ── PostgreSQL ──────────────────────────────────────────────
DATABASE_URL=postgresql://user:password@localhost:5432/keplerlab

# ── ChromaDB ────────────────────────────────────────────────
CHROMA_DIR=./data/chroma

# ── File Upload ─────────────────────────────────────────────
UPLOAD_DIR=./data/uploads
MAX_UPLOAD_SIZE_MB=25

# ── JWT ─────────────────────────────────────────────────────
JWT_SECRET_KEY=your-very-long-random-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# ── Cookies ─────────────────────────────────────────────────
COOKIE_SECURE=false          # true in production (HTTPS only)
COOKIE_SAMESITE=lax
COOKIE_DOMAIN=               # leave blank for localhost

# ── CORS ────────────────────────────────────────────────────
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# ── LLM Provider ────────────────────────────────────────────
LLM_PROVIDER=MYOPENLM        # MYOPENLM | GOOGLE | NVIDIA | OLLAMA
MYOPENLM_MODEL=default
MYOPENLM_API_URL=https://openlmfallback-0adc8b183b77.herokuapp.com/api/chat

# GOOGLE option:
GOOGLE_MODEL=models/gemini-2.5-flash
GOOGLE_API_KEY=your-google-api-key

# NVIDIA option:
NVIDIA_MODEL=qwen/qwen3.5-397b-a17b
NVIDIA_API_KEY=your-nvidia-key

# OLLAMA option:
OLLAMA_MODEL=llama3

# LLM Generation control
LLM_TEMPERATURE_STRUCTURED=0.1
LLM_TEMPERATURE_CHAT=0.2
LLM_TEMPERATURE_CREATIVE=0.7
LLM_MAX_TOKENS=4000

# ── Embeddings ──────────────────────────────────────────────
MODELS_DIR=./data/models
EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_VERSION=bge_m3_v1

# ── Reranker ────────────────────────────────────────────────
RERANKER_MODEL=BAAI/bge-reranker-large
USE_RERANKER=true

# ── Retrieval ───────────────────────────────────────────────
INITIAL_VECTOR_K=10
MMR_K=8
FINAL_K=10
MMR_LAMBDA=0.5

# ── External Search ─────────────────────────────────────────
SEARCH_SERVICE_URL=http://localhost:8001   # DuckDuckGo bridge microservice
```

Create `frontend/.env`:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
```

---

## 8. How to Run

### Backend

```bash
cd backend

# 1. Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 2. Install dependencies (CUDA 12.1 PyTorch index included)
pip install -r requirements.txt

# 3. Set up .env file (copy from §7 above)

# 4. Generate Prisma client
prisma generate

# 5. Sync schema to DB (creates tables)
prisma db push

# 6. Run the server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend

# 1. Install Node dependencies
npm install

# 2. Set up .env file
echo "VITE_API_BASE_URL=http://localhost:8000" > .env

# 3. Start dev server
npm run dev
# → http://localhost:5173

# Production build
npm run build
npm run preview
```

### Docker (Frontend)

```bash
cd frontend
docker build -t keplerlab-frontend .
docker run -p 80:80 keplerlab-frontend
```

The included `nginx.conf` serves the Vite build and proxies `/api` → backend.

---

*End of documentation*
