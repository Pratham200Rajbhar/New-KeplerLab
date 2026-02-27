# KeplerLab AI Notebook — Complete Project Documentation

> **Version:** 2.0.0 | **Date:** February 2026  
> End-to-end technical reference covering architecture, data flow, APIs, database schema, frontend components, and deployment.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Backend — Directory Structure](#4-backend--directory-structure)
5. [Application Entry Point (`main.py`)](#5-application-entry-point-mainpy)
6. [Configuration (`core/config.py`)](#6-configuration-coreconfigpy)
7. [Database Layer](#7-database-layer)
   - 7.1 [PostgreSQL + Prisma Schema](#71-postgresql--prisma-schema)
   - 7.2 [ChromaDB Vector Store](#72-chromadb-vector-store)
8. [Authentication System](#8-authentication-system)
9. [API Routes Reference](#9-api-routes-reference)
10. [Background Worker](#10-background-worker)
11. [Material Processing Pipeline](#11-material-processing-pipeline)
12. [RAG (Retrieval-Augmented Generation) Pipeline](#12-rag-retrieval-augmented-generation-pipeline)
13. [LangGraph Agent System](#13-langgraph-agent-system)
14. [LLM Service Layer](#14-llm-service-layer)
15. [Content Generation Services](#15-content-generation-services)
16. [Code Execution Sandbox](#16-code-execution-sandbox)
17. [WebSocket & Real-Time Updates](#17-websocket--real-time-updates)
18. [Frontend — Directory Structure](#18-frontend--directory-structure)
19. [Frontend Routing & Pages](#19-frontend-routing--pages)
20. [Frontend Components Deep Dive](#20-frontend-components-deep-dive)
21. [Frontend State Management](#21-frontend-state-management)
22. [Frontend API Client Layer](#22-frontend-api-client-layer)
23. [End-to-End Data Flows](#23-end-to-end-data-flows)
24. [Security Model](#24-security-model)
25. [Environment Variables Reference](#25-environment-variables-reference)
26. [Running the Project Locally](#26-running-the-project-locally)
27. [CLI Utilities](#27-cli-utilities)
28. [Prompts Directory](#28-prompts-directory)

---

## 1. Project Overview

**KeplerLab AI Notebook** is a full-stack AI-powered learning platform. Users upload study materials in virtually any format (PDF, DOCX, PPTX, images, audio, video, web URLs, YouTube links, or raw text), and the platform:

- Extracts, OCRs, or transcribes the content
- Chunks and embeds the text into a vector database
- Provides intelligent RAG-based chat powered by a multi-intent LangGraph agent
- Auto-generates quizzes, flashcards, presentations (PPTX), and explainer videos with narration
- Supports web search / research mode that fetches and synthesizes real-time information

Materials are organized inside **Notebooks** (like courses or subjects). Every feature is multi-tenant (isolated per user) and supports multiple LLM back-ends: Ollama (local), Google Gemini, NVIDIA AI, or a custom OpenLM proxy.

---

## 2. High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                       React Frontend (Vite)                         │
│  Pages: Home / Auth / Workspace (Sidebar + ChatPanel + StudioPanel)  │
└────────────────────────┬─────────────────────────────────────────────┘
                         │  REST (JSON/SSE) + WebSocket
                         ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend (Python 3.11)                    │
│                                                                      │
│  Middleware stack                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ Performance Logger → Rate Limiter → Request Logger → CORS   │    │
│  │ Body Size Limiter → TrustedHost (prod only)                  │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  Routers                                                             │
│  ┌──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────────┐    │
│  │ auth │ note │ upld │ chat │ quiz │ fcard│ ppt  │ agent... │    │
│  └──────┴──────┴──────┴──────┴──────┴──────┴──────┴──────────┘    │
│                                                                      │
│  Services (business logic)                                           │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Material Service → Text Processing → Embed → ChromaDB        │   │
│  │ RAG: Retriever → Reranker → Context Builder → LLM            │   │
│  │ Agent: Intent → Plan → Route Tools → Reflect → Respond       │   │
│  │ Generator: Quiz / Flashcard / PPT / Explainer Video          │   │
│  │ Worker: Async background job processor (asyncio.Task)        │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────┬───────────────────────────┬────────────────────┬────────┘
           │                           │                    │
           ▼                           ▼                    ▼
  ┌──────────────────┐   ┌──────────────────────┐  ┌──────────────────┐
  │  PostgreSQL 15   │   │  ChromaDB (vectors)  │  │  File Storage    │
  │  (Prisma ORM)    │   │  ONNX bge-m3 1024d   │  │  /data/uploads   │
  │                  │   │  + bge-reranker-large │  │  /data/output    │
  └──────────────────┘   └──────────────────────┘  └──────────────────┘
```

### Request Lifecycle (summary)

```
Browser → FastAPI middleware stack
       → Route handler (JWT-validated)
       → Service function
       → Prisma (PostgreSQL) and/or ChromaDB
       → LLM (Ollama / Gemini / NVIDIA)
       → SSE stream back to browser
```

---

## 3. Technology Stack

### Backend

| Layer | Technology | Purpose |
|---|---|---|
| Web framework | FastAPI 0.115.6 | Async HTTP, SSE, WebSocket |
| Runtime | Python 3.11+ | Language runtime |
| ASGI server | Uvicorn | Production ASGI server |
| Database ORM | Prisma (Python async) | Type-safe PostgreSQL access |
| Database | PostgreSQL 15 | Primary relational store |
| Vector DB | ChromaDB 0.5.5 | Semantic embedding storage |
| Embeddings | ChromaDB ONNX (bge-m3, 1024d) | Text-to-vector embeddings |
| Reranker | BAAI/bge-reranker-large | Cross-encoder reranking |
| LLM orchestration | LangChain 0.2.16 | Prompt templates & chains |
| Agent framework | LangGraph ≥0.2.0 | Stateful multi-step agent |
| LLM providers | Ollama, Google Gemini, NVIDIA AI, custom OpenLM | Interchangeable backends |
| PDF extraction | PyMuPDF, pdfplumber, pdf2image | Multi-strategy PDF parsing |
| OCR | Tesseract, EasyOCR | Image-to-text |
| Audio/Video | OpenAI Whisper | Transcription |
| TTS | edge-tts | Text-to-speech (explainer narration) |
| Web scraping | BeautifulSoup4, Playwright, yt-dlp | URL/YouTube ingestion |
| Auth | JWT (HS256) + HttpOnly cookies | Access + refresh token flow |
| Validation | Pydantic v2 + pydantic-settings | Request/settings validation |
| Caching | fastapi-cache2 | Response caching |

### Frontend

| Layer | Technology | Purpose |
|---|---|---|
| Framework | React 19.2.0 | UI |
| Bundler | Vite 7.2.4 | Fast dev server + build |
| Routing | React Router 7.11.0 | SPA routing |
| Styling | Tailwind CSS 3.4.19 | Utility-first CSS |
| PDF export | jsPDF | Client-side PDF generation |
| Markdown | react-markdown | Rendering LLM responses |

### Infrastructure

| Technology | Role |
|---|---|
| Docker + Docker Compose | Container orchestration |
| NGINX | Frontend static file server + reverse proxy |
| Redis | (planned) caching layer |

---

## 4. Backend — Directory Structure

```
backend/
├── app/
│   ├── main.py                  ← FastAPI app, lifespan, middleware, router mounts
│   ├── core/
│   │   ├── config.py            ← Pydantic settings (all env vars)
│   │   └── utils.py             ← Shared utilities
│   ├── db/
│   │   ├── chroma.py            ← ChromaDB client factory + collection getter
│   │   └── prisma_client.py     ← Prisma async client singleton
│   ├── models/                  ← Pydantic request/response models
│   ├── prompts/                 ← .txt LLM prompt templates
│   │   ├── chat_prompt.txt
│   │   ├── quiz_prompt.txt
│   │   ├── flashcard_prompt.txt
│   │   ├── ppt_prompt.txt
│   │   ├── data_analysis_prompt.txt
│   │   ├── code_generation_prompt.txt
│   │   └── code_repair_prompt.txt
│   ├── routes/                  ← FastAPI routers (one file per feature)
│   │   ├── auth.py
│   │   ├── notebook.py
│   │   ├── upload.py
│   │   ├── chat.py
│   │   ├── flashcard.py
│   │   ├── quiz.py
│   │   ├── ppt.py
│   │   ├── explainer.py
│   │   ├── agent.py
│   │   ├── search.py
│   │   ├── proxy.py
│   │   ├── jobs.py
│   │   ├── models.py
│   │   ├── health.py
│   │   ├── websocket_router.py
│   │   └── utils.py             ← Shared route helpers
│   └── services/                ← All business logic
│       ├── agent/               ← LangGraph agent (intent→plan→route→reflect→respond)
│       │   ├── graph.py
│       │   ├── intent.py
│       │   ├── planner.py
│       │   ├── router.py
│       │   ├── reflection.py
│       │   ├── state.py
│       │   ├── persistence.py
│       │   ├── tools_registry.py
│       │   ├── tools/           ← Individual tool implementations
│       │   │   ├── code_repair.py
│       │   │   ├── data_profiler.py
│       │   │   ├── file_generator.py
│       │   │   └── workspace_builder.py
│       │   └── subgraphs/
│       ├── auth/                ← JWT, password hashing, user management
│       ├── chat/                ← Chat session management, history
│       ├── code_execution/      ← Python sandbox runner
│       ├── explainer/           ← Explainer video pipeline
│       ├── flashcard/           ← Flashcard generation
│       ├── llm_service/         ← Provider factory (Ollama/Gemini/NVIDIA/OpenLM)
│       │   ├── llm.py
│       │   ├── llm_schemas.py
│       │   └── structured_invoker.py
│       ├── ppt/                 ← Presentation generation
│       ├── quiz/                ← Quiz generation
│       ├── rag/                 ← Retrieval pipeline
│       │   ├── embedder.py
│       │   ├── reranker.py
│       │   ├── secure_retriever.py
│       │   ├── context_builder.py
│       │   ├── context_formatter.py
│       │   └── citation_validator.py
│       ├── text_processing/     ← File parsing/OCR/transcription
│       │   ├── extractor.py
│       │   ├── chunker.py
│       │   ├── file_detector.py
│       │   ├── ocr_service.py
│       │   ├── pdf_extractor.py
│       │   ├── table_extractor.py
│       │   ├── transcription_service.py
│       │   ├── web_scraping.py
│       │   └── youtube_service.py
│       ├── material_service.py  ← Material CRUD + processing orchestration
│       ├── notebook_service.py  ← Notebook CRUD
│       ├── job_service.py       ← Background job CRUD
│       ├── worker.py            ← Async job processor loop
│       ├── storage_service.py   ← File read/write helpers
│       ├── ws_manager.py        ← WebSocket connection manager
│       ├── rate_limiter.py      ← Sliding-window rate limiting
│       ├── performance_logger.py← Request timing middleware
│       ├── audit_logger.py      ← API usage logging to DB
│       ├── token_counter.py     ← Token estimation & tracking
│       ├── model_manager.py     ← LLM/embedding model lifecycle
│       ├── gpu_manager.py       ← CUDA device management
│       └── notebook_name_generator.py ← Auto notebook naming
├── prisma/
│   └── schema.prisma            ← Database schema (Prisma DSL)
├── cli/                         ← Admin CLI tools
│   ├── backup_chroma.py
│   ├── export_embeddings.py
│   ├── import_embeddings.py
│   └── reindex.py
├── data/                        ← Runtime data (gitignored)
│   ├── chroma/                  ← ChromaDB storage
│   ├── uploads/                 ← Uploaded files
│   ├── models/                  ← Downloaded model weights
│   └── material_text/           ← Extracted text cache (.txt files)
├── output/                      ← Generated artefacts
│   ├── presentations/
│   ├── generated/
│   ├── explainers/
│   └── html/
├── logs/                        ← Rotating log files
├── requirements.txt
└── .env                         ← Environment configuration
```

---

## 5. Application Entry Point (`main.py`)

`main.py` wires the whole backend together via FastAPI's `lifespan` context:

### Startup sequence (in order)

1. **Prisma connect** — establishes the async PostgreSQL connection pool
2. **Embedding warm-up** — runs a dummy ChromaDB query in a thread executor to load the ONNX bge-m3 model before the first real request
3. **Reranker preload** — loads `bge-reranker-large` cross-encoder into memory
4. **Background job processor** — creates an `asyncio.Task` running `job_processor()` which polls for pending document-processing jobs
5. **Sandbox packages** — ensures Python sandbox dependencies are installed
6. **Stale sandbox cleanup** — removes `/tmp/kepler_sandbox_*` dirs left by previous crashes
7. **Output directories** — ensures `output/generated`, `output/presentations`, `output/explainers` exist

### Middleware stack (outermost → innermost)

| Middleware | Purpose |
|---|---|
| `performance_monitoring_middleware` | Records per-request latency (first to measure full time) |
| `rate_limit_middleware` | Sliding window rate limiter |
| `log_requests` | Per-request structured log with UUID tracing |
| `CORSMiddleware` | CORS headers, configured from `CORS_ORIGINS` |
| `TrustedHostMiddleware` | Host header validation (production only) |
| `limit_request_body` | Rejects bodies > 100 MB |

### Routers mounted

| Tag | Prefix | Description |
|---|---|---|
| `health` | `/health` | Liveness/readiness probes |
| `auth` | `/auth` | Register, login, refresh, logout |
| `models` | `/models` | List available LLM/embedding models |
| `notebooks` | `/notebooks` | Notebook CRUD |
| `upload` | `/materials` | File/URL/YouTube/text upload |
| `flashcard` | `/flashcards` | Flashcard generation |
| `quiz` | `/quiz` | Quiz generation |
| `chat` | `/chat` | Agent-powered RAG chat + sessions |
| `jobs` | `/jobs` | Background job status polling |
| `presentation` | `/presentations` | PPT generation |
| `agent` | `/agent` | Direct agent/research endpoints |
| `search` | `/search` | Semantic vector search |
| `proxy` | `/api/v1` | External service proxy |
| `explainer` | `/explainer` | Explainer video pipeline |
| `ws` | `/ws` | WebSocket channels |

---

## 6. Configuration (`core/config.py`)

All settings are loaded via `pydantic-settings` from the `.env` file. The singleton `settings` object is imported throughout the codebase.

### Key setting groups

| Group | Key Variables |
|---|---|
| Environment | `ENVIRONMENT`, `DEBUG` |
| Database | `DATABASE_URL` |
| Vector DB | `CHROMA_DIR` |
| File storage | `UPLOAD_DIR`, `MAX_UPLOAD_SIZE_MB` |
| Output dirs | `PRESENTATIONS_OUTPUT_DIR`, `GENERATED_OUTPUT_DIR` |
| JWT/Auth | `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS` |
| Cookies | `COOKIE_SECURE`, `COOKIE_SAMESITE`, `COOKIE_DOMAIN` |
| CORS | `CORS_ORIGINS` (comma-separated list) |
| LLM | `LLM_PROVIDER` (OLLAMA/GOOGLE/NVIDIA/MYOPENLM), provider-specific keys & model names |
| LLM generation | `LLM_TEMPERATURE_STRUCTURED`, `LLM_TEMPERATURE_CHAT`, `LLM_TEMPERATURE_CREATIVE`, `LLM_MAX_TOKENS` |
| Embeddings | `EMBEDDING_MODEL` (default: `BAAI/bge-m3`), `EMBEDDING_DIMENSION` (1024), `EMBEDDING_VERSION` |
| Reranker | `RERANKER_MODEL`, `USE_RERANKER` |
| Retrieval | `INITIAL_VECTOR_K`, `MMR_K`, `FINAL_K`, `MAX_CONTEXT_TOKENS`, `MIN_SIMILARITY_SCORE` |
| Timeouts | `OCR_TIMEOUT_SECONDS`, `WHISPER_TIMEOUT_SECONDS`, `LIBREOFFICE_TIMEOUT_SECONDS` |
| Code execution | `MAX_CODE_REPAIR_ATTEMPTS`, `CODE_EXECUTION_TIMEOUT` |

Relative paths for dirs are automatically resolved to absolute paths against the project root at startup via a `@model_validator`.

---

## 7. Database Layer

### 7.1 PostgreSQL + Prisma Schema

The ORM is **Prisma for Python** (`prisma-client-py`), async interface. Schema lives at `backend/prisma/schema.prisma`.

#### Entity Relationship Overview

```
User (1) ──< Notebook (1) ──< Material
                          ──< ChatSession (1) ──< ChatMessage (1) ──< ResponseBlock
                          ──< GeneratedContent (1) ──< ExplainerVideo
User ──< RefreshToken
User ──< BackgroundJob
User ──< UserTokenUsage
User ──< ApiUsageLog
User ──< AgentExecutionLog
User ──< CodeExecutionSession
User ──< ResearchSession
```

#### Model descriptions

| Model | Purpose |
|---|---|
| `User` | Account record. Fields: `id`, `email`, `username`, `hashedPassword`, `isActive`, `role` |
| `Notebook` | Container for materials and chat. Scoped to a user. |
| `Material` | A single uploaded item (file, URL, YouTube, text). Tracks processing status: `pending → processing → ocr_running / transcribing → embedding → completed / failed`. Stores `originalText`, `chunkCount`, `sourceType`, `metadata` (JSON). |
| `ChatSession` | Named conversation thread inside a notebook. Has `title`, linked to a `Notebook`. |
| `ChatMessage` | Individual turn in a chat session. Has `role` (`user`/`assistant`), `content`, and optional `agentMeta` JSON (intent, tools used, step log). |
| `ResponseBlock` | Paragraph-level text blocks in a chat message (for block-level follow-up questions). |
| `GeneratedContent` | Persisted quiz / flashcard / PPT data (JSON). Has `contentType`, `title`, `materialIds[]`. |
| `ExplainerVideo` | Generated narrated video record. Tracks `status`, `script`, `audioFiles`, `videoUrl`, `chapters`. |
| `RefreshToken` | Token-rotation tracking. Stores SHA-256 hash + `family` ID for replay detection. |
| `BackgroundJob` | Tracks document processing jobs with status lifecycle mirroring `MaterialStatus`. |
| `UserTokenUsage` | Daily token usage per user (unique on `userId + date`). |
| `ApiUsageLog` | Per-request LLM usage metrics: context tokens, response tokens, latencies, model used. |
| `AgentExecutionLog` | Per-agent-run metrics: intent, confidence, tools used, steps, tokens, elapsed time. |
| `CodeExecutionSession` | A Python sandbox execution record: code, stdout, stderr, exit code, has_chart. |
| `ResearchSession` | A web research session: query, generated report, sources count, source URLs. |

#### MaterialStatus lifecycle

```
[upload] → pending
            ↓ (worker picks up)
         processing
            ↓
         ocr_running    (images/scanned PDFs)
         transcribing   (audio/video)
            ↓
         embedding      (chunking + ChromaDB upsert)
            ↓
         completed
            ↓ (on error)
         failed
```

### 7.2 ChromaDB Vector Store

ChromaDB stores all text chunks with tenant-isolation metadata.

- **Collection:** single shared collection (name configured internally)
- **Embedding:** ChromaDB's built-in ONNX runtime with the `BAAI/bge-m3` model (1024-dimensional)
- **Metadata fields per chunk:** `material_id`, `user_id`, `notebook_id`, `source` (filename), `chunk_index`
- **Upsert semantics:** re-processing the same material is idempotent
- **Batch size:** 200 items per ChromaDB call (safe limit below the 256-item ceiling)
- **Tenant isolation:** all queries filter on `user_id` so users never see each other's data

---

## 8. Authentication System

The auth system uses a dual-token pattern:

### Tokens

| Token | Storage | Lifetime | Purpose |
|---|---|---|---|
| **Access token** (JWT, HS256) | Memory / `Authorization: Bearer` header | 15 minutes | Authenticated API calls |
| **Refresh token** (opaque UUID → SHA-256 stored) | HttpOnly Secure cookie at `/auth` path | 7 days | Silent token renewal |

### Token rotation

Every refresh rotates to a new token AND invalidates the old one using the `family` concept. If a used token is presented again (replay attack), the entire family is revoked.

### Password requirements

- ≥ 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit

### Route flow

```
POST /auth/signup      → hash password (bcrypt) → create User → issue tokens
POST /auth/login       → verify password → issue tokens
POST /auth/refresh     → validate cookie → rotate refresh token → new access token
POST /auth/logout      → revoke token family → clear cookie
GET  /auth/me          → return current user info
```

### JWT Dependency

Every protected route uses `Depends(get_current_user)` which:
1. Extracts the Bearer token from `Authorization` header
2. Decodes and validates with `JWT_SECRET_KEY`
3. Fetches the user from Prisma
4. Raises 401 if invalid/expired

---

## 9. API Routes Reference

### Auth (`/auth`)

| Method | Path | Description |
|---|---|---|
| POST | `/auth/signup` | Register new user |
| POST | `/auth/login` | Login, receive access + refresh tokens |
| POST | `/auth/refresh` | Rotate refresh token |
| POST | `/auth/logout` | Revoke token, clear cookie |
| GET | `/auth/me` | Get current user profile |

### Notebooks (`/notebooks`)

| Method | Path | Description |
|---|---|---|
| POST | `/notebooks` | Create notebook |
| GET | `/notebooks` | List user's notebooks (paginated) |
| GET | `/notebooks/{id}` | Get notebook detail |
| PATCH | `/notebooks/{id}` | Update name/description |
| DELETE | `/notebooks/{id}` | Delete notebook (cascades to materials, chat) |
| POST | `/notebooks/{id}/content` | Save generated content to notebook |
| GET | `/notebooks/{id}/content` | List saved content |
| DELETE | `/notebooks/{id}/content/{content_id}` | Delete saved content |

### Materials / Upload (`/materials`)

| Method | Path | Description |
|---|---|---|
| POST | `/materials/upload` | Upload file (PDF/DOCX/PPTX/image/audio/video) |
| POST | `/materials/url` | Ingest web URL |
| POST | `/materials/youtube` | Ingest YouTube video |
| POST | `/materials/text` | Ingest raw text |
| GET | `/materials` | List user materials |
| GET | `/materials/{id}` | Get material detail |
| PATCH | `/materials/{id}` | Update material metadata |
| DELETE | `/materials/{id}` | Delete material + embeddings |
| GET | `/materials/{id}/download` | Download original file (signed token) |

### Chat (`/chat`)

| Method | Path | Description |
|---|---|---|
| POST | `/chat` | Send message; returns SSE stream |
| GET | `/chat/history` | Get message history for session |
| DELETE | `/chat/clear` | Clear chat session |
| POST | `/chat/sessions` | Create named chat session |
| GET | `/chat/sessions` | List chat sessions for notebook |
| DELETE | `/chat/sessions/{id}` | Delete chat session |
| POST | `/chat/block-followup` | Ask follow-up on a specific response block |
| POST | `/chat/suggestions` | Get AI-powered input suggestions |

### Quiz (`/quiz`)

| Method | Path | Description |
|---|---|---|
| POST | `/quiz/generate` | Generate quiz from material(s) |
| GET | `/quiz/{id}` | Retrieve existing quiz |

### Flashcards (`/flashcards`)

| Method | Path | Description |
|---|---|---|
| POST | `/flashcards/generate` | Generate flashcards from material(s) |
| GET | `/flashcards/{id}` | Retrieve existing flashcard set |

### Presentations (`/presentations`)

| Method | Path | Description |
|---|---|---|
| POST | `/presentations/generate` | Generate PPTX from material(s) |
| GET | `/presentations/{id}` | Get presentation data |
| GET | `/presentations/{id}/download` | Download PPTX file |

### Explainer Videos (`/explainer`)

| Method | Path | Description |
|---|---|---|
| POST | `/explainer/generate` | Generate narrated explainer video from PPT |
| GET | `/explainer/{id}` | Get explainer video status/data |
| GET | `/explainer/{id}/download` | Download video file |

### Agent / Research (`/agent`)

| Method | Path | Description |
|---|---|---|
| POST | `/agent/research` | Deep web research with iterative search |
| POST | `/agent/code` | Execute Python code in sandbox |

### Search (`/search`)

| Method | Path | Description |
|---|---|---|
| GET | `/search/semantic` | Semantic vector search across materials |
| GET | `/search/keyword` | Full-text keyword search |

### Jobs (`/jobs`)

| Method | Path | Description |
|---|---|---|
| GET | `/jobs/{id}` | Get background job status |
| GET | `/jobs` | List user's jobs |

### Models (`/models`)

| Method | Path | Description |
|---|---|---|
| GET | `/models` | List available LLM models for current provider |

### Health (`/health`)

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness: returns `{"status":"ok"}` |
| GET | `/health/ready` | Readiness: checks DB + ChromaDB |

### WebSocket (`/ws`)

| Path | Description |
|---|---|
| `/ws/jobs/{job_id}` | Real-time job progress updates |
| `/ws/notebook/{notebook_id}` | Notebook-level broadcast channel |

---

## 10. Background Worker

`services/worker.py` runs a single `asyncio.Task` created at application startup. It loops indefinitely:

```
loop every 2 seconds:
  1. recover_stuck_jobs()   ← reset 'processing' jobs older than 30 min back to 'pending'
  2. fetch_next_pending_job()  ← SELECT...FOR UPDATE SKIP LOCKED (atomic claim)
  3. mark job 'processing'
  4. dispatch to:
       - process_material_by_id()   (file uploads)
       - process_url_material_by_id()  (URLs)
       - process_text_material_by_id() (raw text)
  5. mark 'completed' or 'failed'
  6. push WebSocket update to user

Max concurrent jobs: 5
Graceful shutdown: waits up to 30 seconds for in-flight jobs to complete
```

### Stuck job recovery

If the server crashes mid-processing, jobs remain in `processing` state forever. On startup, jobs in `processing` older than 30 minutes are reset to `pending`.

---

## 11. Material Processing Pipeline

When a file, URL, or text is uploaded, this pipeline runs inside the background worker:

```
Upload endpoint
    │
    ├── Validates file type (python-magic MIME check)
    ├── Saves file to UPLOAD_DIR
    ├── Creates Material record (status=pending)
    ├── Creates BackgroundJob record
    └── Returns immediately (job_id for polling)

Background Worker picks up job:
    │
    ├── FileTypeDetector.detect() → determines handler
    │
    ├── Text extraction strategy (by type):
    │   ├── PDF      → multi-strategy: pdfplumber → PyMuPDF → pdf2image + OCR
    │   ├── DOCX     → python-docx
    │   ├── PPTX     → python-pptx (text) + LibreOffice (slide images) + OCR
    │   ├── Images   → Tesseract + EasyOCR (parallel, best result wins)
    │   ├── Audio    → OpenAI Whisper transcription
    │   ├── Video    → ffmpeg audio extract → Whisper transcription
    │   ├── URL      → Playwright/Selenium → BeautifulSoup HTML parse
    │   └── YouTube  → yt-dlp captions → youtube-transcript-api fallback
    │
    ├── Table extraction (PDFs with tables → markdown tables)
    │
    ├── Text chunker (LangChain RecursiveCharacterTextSplitter)
    │   └── Chunk size / overlap tuned via config (CHUNK_OVERLAP_TOKENS)
    │
    ├── embed_and_store() → ChromaDB UPSERT
    │   └── Batched in groups of 200
    │
    ├── Saves extracted text to data/material_text/{material_id}.txt
    ├── Updates Material.status = 'completed', Material.chunkCount
    └── Notifies WebSocket channel
```

### Supported file types

| Category | Extensions |
|---|---|
| Documents | PDF, DOCX, DOC, TXT, MD, RTF |
| Spreadsheets | XLSX, XLS, CSV |
| Presentations | PPTX, PPT |
| Images | PNG, JPG, JPEG, GIF, BMP, TIFF, WEBP |
| Audio | MP3, WAV, M4A, OGG, FLAC |
| Video | MP4, MOV, AVI, MKV, WEBM |
| Web | HTTP/HTTPS URLs |
| YouTube | youtube.com / youtu.be URLs |

---

## 12. RAG (Retrieval-Augmented Generation) Pipeline

The RAG pipeline is used by the chat agent to answer user questions about their materials.

```
User question
    │
    ▼
secure_retriever.retrieve()
    │
    ├── Stage 1: Initial vector search
    │   └── ChromaDB.query(query_texts=[question], n_results=INITIAL_VECTOR_K=10)
    │       filtered by: user_id + material_ids (tenant isolation)
    │
    ├── Stage 2: MMR (Maximal Marginal Relevance) diversity filtering
    │   └── Reduces k from 10 → MMR_K=8 for diversity
    │
    ├── Stage 3: Similarity score filtering
    │   └── Drops chunks below MIN_SIMILARITY_SCORE=0.3
    │
    ├── Stage 4: Reranking (if USE_RERANKER=True)
    │   └── BAAI/bge-reranker-large cross-encoder scores each (question, chunk) pair
    │       → Re-sorts by cross-encoder score
    │       → Keeps top FINAL_K=10
    │
    ├── Stage 5: Context building
    │   └── context_builder.build_context()
    │       ├── Filters chunks below MIN_CONTEXT_CHUNK_LENGTH=150 chars
    │       ├── Trims total to MAX_CONTEXT_TOKENS=6000 tokens
    │       └── Formats with source citations
    │
    └── Final context passed to LLM prompt
```

### Citation validation

`citation_validator.py` verifies that citations in the LLM response (e.g. `[Source: filename.pdf]`) actually correspond to retrieved chunks, preventing hallucinated citations.

---

## 13. LangGraph Agent System

The **chat agent** (`services/agent/`) replaces a simple RAG-chain with a multi-step stateful agent built on LangGraph. It auto-detects user intent and routes to the appropriate tool.

### Agent state (`state.py`)

```python
AgentState = TypedDict containing:
  - messages: list of chat messages
  - intent: detected intent string
  - confidence: float (0-1)
  - plan: list of planned tool calls
  - tool_results: list of tool outputs
  - iterations: int (max = MAX_AGENT_ITERATIONS)
  - total_tokens: int (max = TOKEN_BUDGET)
  - stopped_reason: str
  - material_ids: list[str]
  - user_id: str
  - notebook_id: str
  - session_id: str
```

### Agent graph flow

```
intent_and_plan
     │
     ▼
route_and_execute (tool selection + execution)
     │
     ▼
reflect (evaluate results, decide: continue or respond)
     │
     ├── continue → back to route_and_execute
     └── respond → generate_response
                        │
                        ▼
                   SSE stream to client
```

### Intent types

| Intent | Trigger | Tool(s) Used |
|---|---|---|
| `QUESTION` | General question about material | RAG retrieval |
| `SUMMARIZE` | "summarize", "tldr" | RAG retrieval |
| `EXPLAIN` | "explain", "what does X mean" | RAG retrieval |
| `QUIZ` | "quiz me", "test me" | Quiz generator |
| `FLASHCARD` | "flashcards", "make cards" | Flashcard generator |
| `PRESENTATION` | "make slides", "create presentation" | PPT generator |
| `DATA_ANALYSIS` | Data questions on uploaded CSV/XLSX | Python sandbox + data profiler |
| `CODE` | Code generation/explanation | Code generator + repair loop |
| `RESEARCH` | "search the web", "research X" | Web research pipeline |
| `KEYPOINTS` | "key points", "main ideas" | RAG retrieval |
| `STUDY_GUIDE` | "study guide" | RAG retrieval + structured output |

### Tools (`services/agent/tools/`)

| Tool | Description |
|---|---|
| `code_repair.py` | Iterative code fix loop (up to `MAX_CODE_REPAIR_ATTEMPTS=3`) |
| `data_profiler.py` | Profiles uploaded CSV/Excel files (shape, dtypes, sample data) |
| `file_generator.py` | Generates downloadable files (CSV, JSON, etc.) |
| `workspace_builder.py` | Builds a safe sandbox workspace directory |

### Streaming

The agent streams its response via SSE with typed events:

| SSE event | Payload | Purpose |
|---|---|---|
| `intent` | `{intent, confidence}` | Detected intent |
| `step` | `{tool, description}` | Agent thinking step |
| `token` | `{text}` | Streaming response token |
| `done` | `{session_id, agent_meta}` | Completion signal |
| `error` | `{detail}` | Error |

---

## 14. LLM Service Layer

`services/llm_service/llm.py` provides a unified factory for all LLM providers.

### Provider selection

Controlled by `LLM_PROVIDER` env var:

| Provider | Class | Config keys |
|---|---|---|
| `OLLAMA` | `ChatOllama` | `OLLAMA_MODEL` (default: `llama3`) |
| `GOOGLE` | `ChatGoogleGenerativeAI` | `GOOGLE_MODEL`, `GOOGLE_API_KEY` |
| `NVIDIA` | `ChatNVIDIA` | `NVIDIA_MODEL`, `NVIDIA_API_KEY` |
| `MYOPENLM` | Custom `LLM` subclass | `MYOPENLM_MODEL`, `MYOPENLM_API_URL` |

### Temperature profiles

| Use case | Temperature | Top-P | Function |
|---|---|---|---|
| Structured output (quiz/cards) | 0.1 | 0.9 | `get_llm_structured()` |
| Chat responses | 0.2 | 0.95 | `get_llm()` |
| Creative content (PPT, explainer) | 0.7 | default | `get_llm_creative()` |
| Code generation | 0.1 | 0.9 | `get_llm_code()` |

### Instance caching

LLM instances are cached by `(provider, temperature, top_p, max_tokens)` key with a max cache size of 16 to avoid repeated model initialization.

---

## 15. Content Generation Services

### Quiz (`services/quiz/`)

1. Retrieves top context chunks from RAG pipeline
2. Sends to LLM with `prompts/quiz_prompt.txt`
3. Parses JSON with `json_repair` library (handles malformed LLM output)
4. Returns: list of `{question, options: [A,B,C,D], answer, explanation, difficulty}`
5. Saved to `GeneratedContent` table with `contentType="quiz"`

### Flashcards (`services/flashcard/`)

1. RAG retrieval for key concepts
2. LLM with `prompts/flashcard_prompt.txt`
3. Returns: list of `{front, back, topic}`
4. Saved to `GeneratedContent` with `contentType="flashcard"`

### Presentations (`services/ppt/`)

1. RAG retrieval for slide content
2. LLM with `prompts/ppt_prompt.txt` → structured JSON (title, slides[])
3. `python-pptx` renders the PPTX file
4. Optional: theme application from `app/themes/`
5. Saves `.pptx` to `output/presentations/`
6. Record saved to `GeneratedContent` with `contentType="presentation"`

### Explainer Videos (`services/explainer/`)

1. Takes a saved presentation as input
2. Generates per-slide narration script via LLM
3. `edge-tts` synthesizes speech audio for each slide
4. Assembles audio + slide images into video chapters
5. (Optional) Merges into a single video file
6. Status tracked in `ExplainerVideo` table

---

## 16. Code Execution Sandbox

Python code submitted through the agent or directly via `/agent/code` runs in an isolated sandbox:

```
services/code_execution/
├── sandbox_env.py     ← Installs sandbox packages, creates isolated venv
└── (executor)         ← Runs code in subprocess with timeout
```

- Max execution time: `CODE_EXECUTION_TIMEOUT=15` seconds
- Stdout/stderr captured
- Chart detection: if matplotlib outputs a figure, it's captured as base64 PNG
- Auto-repair loop: if code fails, `code_repair.py` sends error + code back to LLM (up to `MAX_CODE_REPAIR_ATTEMPTS=3`)
- Temp directories cleaned up on startup and after each run

---

## 17. WebSocket & Real-Time Updates

`services/ws_manager.py` manages WebSocket connections with a per-user connection registry.

### Channels

| Channel | Path | Messages |
|---|---|---|
| Job progress | `/ws/jobs/{job_id}` | `{status, progress, message}` |
| Notebook broadcast | `/ws/notebook/{notebook_id}` | Material status changes, new content |

### Message format

```json
{
  "type": "job_update",
  "job_id": "...",
  "status": "completed",
  "data": { ... }
}
```

The background worker sends WebSocket updates after each material processing step, enabling the frontend's progress indicators.

---

## 18. Frontend — Directory Structure

```
frontend/
├── src/
│   ├── App.jsx                 ← Router setup, ProtectedRoute, Workspace component
│   ├── main.jsx                ← React DOM entry point
│   ├── index.css               ← Global styles + Tailwind directives
│   ├── api/                    ← API client functions (one file per feature)
│   │   ├── config.js           ← Base URL, fetch wrapper with auth headers
│   │   ├── auth.js             ← Login, signup, refresh, logout
│   │   ├── notebooks.js        ← Notebook CRUD + content
│   │   ├── materials.js        ← Upload, list, delete materials
│   │   ├── chat.js             ← Stream chat, history, sessions
│   │   ├── generation.js       ← Quiz, flashcard, PPT generation
│   │   └── explainer.js        ← Explainer video API
│   ├── context/
│   │   ├── AppContext.jsx       ← Global app state (notebook, materials, messages)
│   │   ├── AuthContext.jsx      ← Auth state (user, isAuthenticated, token refresh)
│   │   └── ThemeContext.jsx     ← Dark/light theme toggle
│   ├── components/
│   │   ├── App → Router entry  
│   │   ├── AuthPage.jsx         ← Login/Signup page switcher
│   │   ├── Login.jsx            ← Login form
│   │   ├── Signup.jsx           ← Signup form
│   │   ├── HomePage.jsx         ← Notebook listing / landing
│   │   ├── Header.jsx           ← Top navigation bar
│   │   ├── Sidebar.jsx          ← Material list + upload button
│   │   ├── ChatPanel.jsx        ← Main chat interface (SSE streaming, sessions)
│   │   ├── StudioPanel.jsx      ← Content generation panel (quiz/cards/PPT)
│   │   ├── ChatMessage.jsx      ← Message bubble + markdown renderer
│   │   ├── UploadDialog.jsx     ← File/URL/YouTube upload modal
│   │   ├── SourceItem.jsx       ← Material list item with status indicator
│   │   ├── PresentationView.jsx ← Inline PPTX viewer
│   │   ├── ExplainerDialog.jsx  ← Explainer video configuration + viewer
│   │   ├── FileViewerPage.jsx   ← Full-page file viewer
│   │   ├── WebSearchDialog.jsx  ← Research mode UI
│   │   ├── FeatureCard.jsx      ← Studio feature selection card
│   │   ├── Modal.jsx            ← Reusable modal wrapper
│   │   ├── ErrorBoundary.jsx    ← React error boundaries (global + per panel)
│   │   └── chat/               ← Chat sub-components
│   │       ├── AgentThinkingBar.jsx    ← Animated "agent is thinking" indicator
│   │       ├── AgentActionBlock.jsx    ← Tool execution step display
│   │       ├── ResearchProgress.jsx    ← Research pipeline progress steps
│   │       └── SuggestionDropdown.jsx  ← Autocomplete suggestions
│   ├── hooks/                  ← Custom React hooks
│   └── assets/                 ← Static assets
├── public/
├── index.html
├── vite.config.js
├── tailwind.config.js
├── postcss.config.js
├── eslint.config.js
├── Dockerfile
└── nginx.conf
```

---

## 19. Frontend Routing & Pages

Routes defined in `App.jsx`:

| Path | Component | Auth Required | Description |
|---|---|---|---|
| `/` | `HomePage` | Yes | Notebook grid/list |
| `/auth` | `AuthPage` | No | Login / Signup |
| `/notebook/draft` | `Workspace` | Yes | New notebook (unsaved) |
| `/notebook/:id` | `Workspace` | Yes | Existing notebook view |
| `/file/:id` | `FileViewerPage` | Yes | Full-screen material viewer |

### `Workspace` layout

```
┌──────────────────────────────────────────────────────────────┐
│  Header (logo, notebook title, back button, user menu)       │
├──────────────┬──────────────────────────┬────────────────────┤
│   Sidebar    │      ChatPanel           │   StudioPanel      │
│              │                          │                    │
│ - Materials  │ - Chat sessions bar      │ - Feature cards:   │
│   list       │ - Message history        │   Flashcards       │
│ - Upload     │ - Agent thinking bar     │   Quiz             │
│   button     │ - SSE streaming          │   Presentation     │
│ - Source     │ - Quick actions          │   Explainer Video  │
│   checkboxes │ - Input + suggestions    │ - Generated content│
│              │ - Research mode          │   saved list       │
└──────────────┴──────────────────────────┴────────────────────┘
```

---

## 20. Frontend Components Deep Dive

### `ChatPanel.jsx`

The central chat component is ~1175 lines and handles:

- **SSE stream parsing**: reads `event: / data:` pairs from the fetch response body
- **Agent step display**: shows `AgentActionBlock` for each tool execution
- **Research mode**: toggles to `streamResearch()` which shows `ResearchProgress` steps
- **Session management**: create, select, delete chat sessions
- **Quick actions**: Summarize / Explain / Key points / Study guide presets
- **Block-level follow-up**: users can click a paragraph to ask a follow-up about that specific block
- **Suggestion dropdown**: calls `/chat/suggestions` for autocomplete as user types
- **Message persistence**: loads history from `/chat/history` on session selection

### `StudioPanel.jsx`

~1669 lines; manages all content generation:

- **View state machine**: `null` (grid) → `'flashcards'` / `'quiz'` / `'presentation'` / `'explainer'`
- **Flashcards**: generates, displays flip-card UI, supports save to notebook, PDF export (jsPDF)
- **Quiz**: generates, interactive Q&A with score tracking, save/export
- **Presentation**: config dialog (language, slide count, theme) → generates → inline `PresentationView` → PPTX download
- **Explainer Video**: `ExplainerDialog` for voice/language config → polling status → video download
- **Saved content**: loads from `/notebooks/{id}/content`, displays previously generated items

### `Sidebar.jsx`

- Lists all materials for current notebook with `SourceItem` components
- Material status badges: `pending` (spinner) / `processing` / `completed` (checkmark) / `failed` (error)
- Checkbox selection for multi-source chat
- Upload button opens `UploadDialog`

### `UploadDialog.jsx`

Tabbed modal:
- **File tab**: drag-and-drop or file picker, shows progress
- **URL tab**: web page URL input
- **YouTube tab**: YouTube URL input
- **Text tab**: paste raw text

---

## 21. Frontend State Management

State is managed via React Context (no Redux/Zustand):

### `AppContext` (global app state)

```
currentNotebook          : Notebook | null
draftMode                : boolean
materials                : Material[]
messages                 : Message[]
currentMaterial          : Material | null
selectedSources          : Set<string>   ← checked material IDs
flashcards / quiz        : generated content
loading                  : { [key]: boolean }
```

Key actions: `setCurrentNotebook`, `setMaterials`, `setMessages`, `setDraftMode`, `deselectAllSources`, `setLoadingState`

### `AuthContext` (auth state)

```
user        : User | null
isAuthenticated : boolean
isLoading   : boolean
accessToken : string | null
```

Handles:
- `login()`, `logout()`, `signup()`
- Silent token refresh via `POST /auth/refresh` (called automatically when access token expires)
- Token stored in memory (not localStorage) to prevent XSS theft

### `ThemeContext`

- `theme`: `'light'` | `'dark'`
- Persisted to `localStorage`
- Applies `class="dark"` to `<html>` for Tailwind dark mode

---

## 22. Frontend API Client Layer

All API calls go through `api/config.js` which provides:

- Base URL resolution (`import.meta.env.VITE_API_URL` or `http://localhost:8000`)
- `apiFetch()` wrapper: attaches `Authorization: Bearer {token}` header, handles 401 → trigger token refresh → retry
- Streaming helper: returns raw `Response` object for SSE consumers

### Key API modules

| Module | Functions |
|---|---|
| `api/auth.js` | `login()`, `signup()`, `refreshToken()`, `logout()`, `getMe()` |
| `api/notebooks.js` | `createNotebook()`, `getNotebooks()`, `getNotebook()`, `updateNotebook()`, `deleteNotebook()`, `saveGeneratedContent()`, `getGeneratedContent()`, `deleteGeneratedContent()` |
| `api/materials.js` | `uploadFile()`, `uploadUrl()`, `uploadYouTube()`, `uploadText()`, `getMaterials()`, `deleteMaterial()` |
| `api/chat.js` | `streamChat()`, `getChatHistory()`, `getChatSessions()`, `createChatSession()`, `deleteChatSession()`, `streamResearch()`, `getSuggestions()` |
| `api/generation.js` | `generateFlashcards()`, `generateQuiz()`, `generatePresentation()`, `downloadBlob()` |
| `api/explainer.js` | `generateExplainerVideo()`, `getExplainerStatus()`, `fetchExplainerVideoBlob()` |

---

## 23. End-to-End Data Flows

### Flow 1: Upload a PDF

```
1. User drags PDF into UploadDialog
2. Frontend: POST /materials/upload (multipart/form-data)
3. Backend upload.py:
   a. Validates MIME type (python-magic)
   b. Saves to UPLOAD_DIR/{uuid}.pdf
   c. Creates Material record (status=pending)
   d. Creates BackgroundJob record
   e. Returns {material_id, job_id}
4. Worker picks up job (polls every 2s):
   a. pdf_extractor → pdfplumber → PyMuPDF → OCR fallback
   b. table_extractor (markdown tables)
   c. chunker (RecursiveCharacterTextSplitter)
   d. embed_and_store → ChromaDB UPSERT (batches of 200)
   e. Saves text to data/material_text/{material_id}.txt
   f. Updates Material.status = 'completed', chunkCount = N
5. WebSocket push → frontend updates SourceItem badge instantly
```

### Flow 2: Chat with material

```
1. User types question, clicks Send
2. Frontend: POST /chat (stream=true)
3. chat.py route:
   a. Validates material IDs belong to user
   b. Confirms all materials have status=completed
   c. Creates/reuses chat session
4. Delegates to chat service → agent graph:
   a. intent_and_plan(): keyword match → LLM fallback
   b. route_and_execute(): calls RAG retriever
   c. secure_retriever.retrieve():
      - vector search (ChromaDB, filter user_id+material_ids)
      - MMR diversity filter
      - score threshold filter
      - bge-reranker-large cross-encoder reranking
   d. context_builder: trim to 6000 tokens
   e. LLM generation (streaming)
   f. reflect(): done → generate_response
5. SSE stream events to frontend:
   event: intent → {intent: "QUESTION", confidence: 0.92}
   event: step → {tool: "rag_retrieval", description: "Searching materials"}
   event: token → {text: "Based on your material..."} (repeated)
   event: done → {session_id, agent_meta}
6. Frontend ChatPanel renders tokens in real-time
7. chat.py saves user message + assistant message to DB
```

### Flow 3: Generate Quiz

```
1. User selects materials (checkboxes in Sidebar)
2. User clicks "Quiz" in StudioPanel
3. Frontend: POST /quiz/generate {material_ids, notebook_id, num_questions, difficulty}
4. quiz route → quiz service:
   a. RAG retrieval for diverse context
   b. LLM call with quiz_prompt.txt
   c. json_repair to parse response
   d. Returns {questions: [{question, options, answer, explanation}]}
5. Frontend renders interactive quiz in StudioPanel
6. User can save to notebook → POST /notebooks/{id}/content
```

### Flow 4: Research mode

```
1. User types research query in ChatPanel
2. Frontend: POST /agent/research (SSE stream)
3. agent research pipeline:
   a. LLM plans 3-5 search queries
   b. External search service (SEARCH_SERVICE_URL) fetches results
   c. Playwright/BeautifulSoup scrapes top N pages
   d. ClusterThemes: groups content by topic
   e. LLM synthesizes final research report
4. SSE events: planning → searching → extracting → clustering → writing
5. ResearchProgress component shows animated step indicators
6. Final report streams as tokens
```

---

## 24. Security Model

### Authentication & Authorization

- JWT access tokens expire in **15 minutes** (short window limits replay window)
- Refresh tokens stored as **SHA-256 hash** — even DB leak doesn't expose raw tokens
- Refresh cookies: `HttpOnly`, `Secure` (production), `SameSite=Lax`, path restricted to `/auth`
- Token **family rotation** — one-use refresh tokens, replay detection revokes entire family
- All protected routes require `get_current_user` dependency injection

### Tenant Isolation

- All DB queries filter by `user_id`
- ChromaDB queries include `user_id` metadata filter — users cannot access each other's vectors
- Material ownership validated before any operation

### Input Validation

- File uploads: MIME type checked via `python-magic` (reads binary header, not just extension)
- File size: max 25 MB per upload (configurable)
- Request body: max 100 MB
- URL ingestion: IP blocklist (private ranges: 10.x, 192.168.x, 127.x, 169.254.x) prevents SSRF
- JWT validation on every request: signature, expiry, user existence
- Pydantic v2 validates all request bodies strictly

### Rate Limiting

`services/rate_limiter.py` implements a sliding-window in-memory rate limiter applied to all requests.

### Production extras

- `TrustedHostMiddleware` validates `Host` header
- `COOKIE_SECURE=True` auto-set when `ENVIRONMENT=production`
- CORS restricted to explicit `CORS_ORIGINS` list

---

## 25. Environment Variables Reference

Create `backend/.env` with these variables:

```ini
# ── Required ─────────────────────────────────────────────

DATABASE_URL=postgresql://user:password@localhost:5432/keplerlab
JWT_SECRET_KEY=<64-char random string>  # python -c "import secrets; print(secrets.token_urlsafe(64))"

# ── LLM Provider (pick one) ───────────────────────────────

LLM_PROVIDER=OLLAMA
OLLAMA_MODEL=llama3.2

# LLM_PROVIDER=GOOGLE
# GOOGLE_API_KEY=your-google-api-key
# GOOGLE_MODEL=models/gemini-2.5-flash

# LLM_PROVIDER=NVIDIA
# NVIDIA_API_KEY=your-nvidia-api-key
# NVIDIA_MODEL=qwen/qwen3.5-397b-a17b

# ── Optional overrides ────────────────────────────────────

ENVIRONMENT=development   # development | staging | production
DEBUG=false

CHROMA_DIR=./data/chroma
UPLOAD_DIR=./data/uploads
MAX_UPLOAD_SIZE_MB=25

CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

EMBEDDING_MODEL=BAAI/bge-m3
RERANKER_MODEL=BAAI/bge-reranker-large
USE_RERANKER=true

ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

COOKIE_SECURE=false       # Set true in production
COOKIE_SAMESITE=lax
```

Frontend (create `frontend/.env` or `frontend/.env.local`):

```ini
VITE_API_URL=http://localhost:8000
```

---

## 26. Running the Project Locally

### 1. Prerequisites

```bash
Python 3.11+
Node.js 18+
PostgreSQL 15+
Ollama (or API keys for cloud LLM)
# Optional: Tesseract, LibreOffice, ffmpeg for full feature support
```

### 2. Backend setup

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env (see section 25)
cp .env.example .env
# Edit .env with your DATABASE_URL and JWT_SECRET_KEY

# Run database migrations
prisma db push
prisma generate

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend setup

```bash
cd frontend

npm install

# Create .env.local
echo "VITE_API_URL=http://localhost:8000" > .env.local

npm run dev
# → http://localhost:5173
```

### 4. Docker Compose (full stack)

```bash
# From project root
docker compose up --build
# Frontend: http://localhost:80
# Backend: http://localhost:8000
# API docs: http://localhost:8000/docs
```

### 5. Interactive API docs

Once the backend is running:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 27. CLI Utilities

Located in `backend/cli/`:

| Script | Command | Purpose |
|---|---|---|
| `backup_chroma.py` | `python -m cli.backup_chroma` | Export ChromaDB to backup archive |
| `export_embeddings.py` | `python -m cli.export_embeddings` | Export all embeddings to parquet/JSON |
| `import_embeddings.py` | `python -m cli.import_embeddings` | Restore embeddings from export |
| `reindex.py` | `python -m cli.reindex` | Re-embed all materials (use after model change) |

Use `reindex.py` whenever `EMBEDDING_VERSION` or `EMBEDDING_MODEL` changes to ensure all vectors use the new model.

---

## 28. Prompts Directory

All LLM prompts are stored as `.txt` files in `backend/app/prompts/` and loaded at runtime:

| File | Used by | Description |
|---|---|---|
| `chat_prompt.txt` | Chat agent | RAG chat system prompt |
| `quiz_prompt.txt` | Quiz service | Quiz generation format |
| `flashcard_prompt.txt` | Flashcard service | Flashcard generation format |
| `ppt_prompt.txt` | PPT service | Presentation slide structure |
| `data_analysis_prompt.txt` | Agent (DATA_ANALYSIS) | Python data analysis code generation |
| `code_generation_prompt.txt` | Agent (CODE) | Code generation system prompt |
| `code_repair_prompt.txt` | `code_repair.py` | Error + code → fixed code |

Prompts use `{placeholder}` style substitution via LangChain `PromptTemplate`. Editing these files changes model behavior without touching Python code.

---

*Documentation generated from source code analysis — KeplerLab AI Notebook v2.0.0, February 2026.*
