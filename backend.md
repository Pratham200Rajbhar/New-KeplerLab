# KeplerLab AI Notebook — Backend Documentation

> **Complete end-to-end reference for every module, route, service, model, prompt, and configuration in the backend.**

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Technology Stack](#2-technology-stack)
3. [Directory Structure](#3-directory-structure)
4. [Configuration — `app/core/config.py`](#4-configuration)
5. [Utilities — `app/core/utils.py`](#5-utilities)
6. [Database Layer — `app/db/`](#6-database-layer)
7. [Prisma Schema — `prisma/schema.prisma`](#7-prisma-schema)
8. [Application Entry — `app/main.py`](#8-application-entry)
9. [Pydantic Models — `app/models/`](#9-pydantic-models)
10. [API Routes — `app/routes/`](#10-api-routes)
    - [Auth](#101-auth)
    - [Notebooks](#102-notebooks)
    - [Upload / Materials](#103-upload--materials)
    - [Chat](#104-chat)
    - [Agent](#105-agent)
    - [Flashcard](#106-flashcard)
    - [Quiz](#107-quiz)
    - [Presentation (PPT)](#108-presentation-ppt)
    - [Mind Map](#109-mind-map)
    - [Explainer](#1010-explainer)
    - [Podcast Live](#1011-podcast-live)
    - [Health](#1012-health)
    - [Jobs](#1013-jobs)
    - [Models](#1014-models)
    - [Search](#1015-search)
    - [Proxy / File Viewer](#1016-proxy--file-viewer)
    - [WebSocket](#1017-websocket)
    - [Route Utilities](#1018-route-utilities)
11. [Prompt Templates — `app/prompts/`](#11-prompt-templates)
12. [Services — `app/services/`](#12-services)
    - [Top-Level Services](#121-top-level-services)
    - [Agent Service](#122-agent-service)
    - [Auth Service](#123-auth-service)
    - [Chat Service](#124-chat-service)
    - [Code Execution Service](#125-code-execution-service)
    - [Explainer Service](#126-explainer-service)
    - [Flashcard Service](#127-flashcard-service)
    - [LLM Service](#128-llm-service)
    - [Mind Map Service](#129-mind-map-service)
    - [Podcast Service](#1210-podcast-service)
    - [Presentation (PPT) Service](#1211-presentation-ppt-service)
    - [Quiz Service](#1212-quiz-service)
    - [RAG Service](#1213-rag-service)
    - [Text Processing Service](#1214-text-processing-service)
13. [Background Worker](#13-background-worker)
14. [CLI Tools — `cli/`](#14-cli-tools)
15. [Data Directories](#15-data-directories)
16. [Requirements](#16-requirements)

---

## 1. Project Overview

**KeplerLab AI Notebook** is a FastAPI-based AI-powered study assistant platform. The backend serves as the core engine providing:

- **Multi-format Document Ingestion** — PDF, DOCX, PPTX, XLSX, CSV, images, audio, video, web pages, YouTube
- **RAG-based Chat** — Retrieval-Augmented Generation with LangGraph agent routing
- **Content Generation** — Flashcards, quizzes, mind maps, HTML presentations
- **Code Execution** — Sandboxed Python with auto-repair loop
- **Deep Web Research** — DuckDuckGo search → content extraction → LLM synthesis
- **AI Podcast Generation** — Script generation + edge-tts multi-language TTS
- **Explainer Video Generation** — Slide screenshots + narration TTS → MP4
- **Real-time Updates** — WebSocket for material processing progress & podcast events
- **Multi-tenant Security** — JWT auth, tenant-isolated retrieval, SSRF protection

**Title:** Study Assistant API  
**Version:** 2.0.0  
**Framework:** FastAPI (Python 3.10+)

---

## 2. Technology Stack

| Category | Technologies |
|----------|-------------|
| **Web Framework** | FastAPI 0.115.6, Uvicorn 0.30.6 |
| **Validation** | Pydantic 2.9.2, pydantic-settings |
| **ORM / Database** | Prisma 0.15.0 (async), PostgreSQL (asyncpg) |
| **Vector DB** | ChromaDB 0.5.5 (persistent) |
| **LLM Orchestration** | LangChain 0.2.16, LangGraph ≥0.2.0 |
| **LLM Providers** | Ollama, Google Gemini, NVIDIA NIM, custom MyOpenLM REST endpoint |
| **Embeddings** | sentence-transformers 3.1.1 (BAAI/bge-m3, 1024-dim) |
| **Reranking** | Cross-encoder (BAAI/bge-reranker-large) |
| **Token Counting** | tiktoken 0.7.0 |
| **OCR** | EasyOCR (primary), Tesseract (fallback) |
| **Audio Transcription** | OpenAI Whisper (base model) |
| **TTS** | edge-tts (10 languages), Coqui TTS |
| **Document Processing** | PyMuPDF, PDFPlumber, python-docx, python-pptx, openpyxl, xlrd, pandas |
| **Web Scraping** | BeautifulSoup4, Selenium, trafilatura, yt-dlp |
| **Video Composition** | ffmpeg-python |
| **Auth** | python-jose (JWT), bcrypt (passlib) |
| **Security** | python-magic (file validation), SSRF protection |
| **Screenshot** | Playwright (headless Chromium) |
| **Testing** | pytest, pytest-asyncio |

---

## 3. Directory Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                          # FastAPI app, lifespan, middleware, routers
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py                    # Settings (pydantic-settings, .env)
│   │   └── utils.py                     # sanitize_null_bytes()
│   ├── db/
│   │   ├── __init__.py                  # Re-exports prisma, connect_db, disconnect_db
│   │   ├── chroma.py                    # ChromaDB client singleton
│   │   └── prisma_client.py             # Prisma async client with retry
│   ├── models/
│   │   ├── __init__.py
│   │   └── mindmap_schemas.py           # MindMapNode, MindMapRequest, MindMapResponse
│   ├── prompts/
│   │   ├── __init__.py                  # Prompt loader with {{KEY}} substitution
│   │   ├── chat_prompt.txt
│   │   ├── code_generation_prompt.txt
│   │   ├── code_repair_prompt.txt
│   │   ├── data_analysis_prompt.txt
│   │   ├── flashcard_prompt.txt
│   │   ├── mindmap_prompt.txt
│   │   ├── podcast_qa_prompt.txt
│   │   ├── podcast_script_prompt.txt
│   │   ├── ppt_prompt.txt
│   │   └── quiz_prompt.txt
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── agent.py                     # /agent — code exec, data analysis, research
│   │   ├── auth.py                      # /auth — signup, login, refresh, logout
│   │   ├── chat.py                      # /chat — RAG chat, sessions, suggestions
│   │   ├── explainer.py                 # /explainer — video generation
│   │   ├── flashcard.py                 # /flashcard — flashcard generation
│   │   ├── health.py                    # /health — system health checks
│   │   ├── jobs.py                      # /jobs — background job status
│   │   ├── mindmap.py                   # /mindmap — mind map generation
│   │   ├── models.py                    # /models — AI model status/reload
│   │   ├── notebook.py                  # /notebooks — CRUD + content
│   │   ├── podcast_live.py              # /podcast — full podcast pipeline
│   │   ├── ppt.py                       # /presentation — PPT generation
│   │   ├── proxy.py                     # /api/v1/proxy — web proxy, file viewer
│   │   ├── quiz.py                      # /quiz — quiz generation
│   │   ├── search.py                    # /search — web search bridge
│   │   ├── upload.py                    # /upload, /materials — file management
│   │   ├── utils.py                     # Route helper functions
│   │   └── websocket_router.py          # /ws/jobs — real-time updates
│   └── services/
│       ├── __init__.py
│       ├── audit_logger.py              # API usage audit logging
│       ├── file_validator.py            # Upload file validation
│       ├── gpu_manager.py               # GPU resource coordination
│       ├── job_service.py               # Background job CRUD
│       ├── material_service.py          # Material lifecycle (849 lines)
│       ├── model_manager.py             # AI model management
│       ├── notebook_name_generator.py   # LLM-based naming
│       ├── notebook_service.py          # Notebook CRUD
│       ├── performance_logger.py        # Request performance middleware
│       ├── rate_limiter.py              # Per-user rate limiting
│       ├── storage_service.py           # File storage abstraction
│       ├── token_counter.py             # Token counting + usage tracking
│       ├── worker.py                    # Background job processor
│       ├── ws_manager.py               # WebSocket connection manager
│       ├── agent/                       # LangGraph agent (8+ files)
│       ├── auth/                        # JWT auth, token rotation
│       ├── chat/                        # Chat service
│       ├── code_execution/              # Sandboxed Python (5 files)
│       ├── explainer/                   # Explainer video pipeline (5 files)
│       ├── flashcard/                   # Flashcard generation
│       ├── llm_service/                 # LLM abstraction layer (4 files)
│       ├── mindmap/                     # Mind map generation
│       ├── podcast/                     # Podcast pipeline (8 files)
│       ├── ppt/                         # Presentation generation (4 files)
│       ├── quiz/                        # Quiz generation
│       ├── rag/                         # RAG pipeline (7 files)
│       └── text_processing/             # File extraction (11 files)
├── cli/
│   ├── __init__.py
│   ├── backup_chroma.py
│   ├── export_embeddings.py
│   ├── import_embeddings.py
│   └── reindex.py
├── data/
│   ├── chroma/                          # ChromaDB persistent storage
│   ├── material_text/                   # Extracted text files
│   ├── models/                          # Downloaded AI models
│   ├── output/                          # Generated content output
│   └── uploads/                         # Uploaded files
├── logs/                                # Application logs
├── output/
│   ├── explainers/                      # Explainer videos
│   ├── generated/                       # Agent-generated files
│   ├── html/                            # HTML presentations
│   ├── podcast/                         # Podcast audio files
│   ├── presentations/                   # Slide screenshots
│   └── yt_translation/                  # YouTube translations
├── prisma/
│   └── schema.prisma                    # Database schema
├── templates/                           # HTML templates
└── requirements.txt
```

---

## 4. Configuration

**File:** `app/core/config.py`

All settings are loaded from environment variables or a `.env` file using `pydantic-settings`. A cached singleton is available as `settings`.

### Settings Reference

#### Environment

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ENVIRONMENT` | `Literal["development","staging","production"]` | `"development"` | Runtime environment |
| `DEBUG` | `bool` | `False` | Debug mode toggle |

#### Database

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `DATABASE_URL` | `str` | *required* | PostgreSQL connection string |

#### ChromaDB

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `CHROMA_DIR` | `str` | `"./data/chroma"` | ChromaDB persistent storage path |

#### File Storage

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `UPLOAD_DIR` | `str` | `"./data/uploads"` | User file upload directory |
| `MAX_UPLOAD_SIZE_MB` | `int` | `25` | Maximum upload file size |

#### Output Directories

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `PRESENTATIONS_OUTPUT_DIR` | `str` | `"output/presentations"` | Slide screenshot output |
| `GENERATED_OUTPUT_DIR` | `str` | `"output/generated"` | Agent-generated files |
| `TEMPLATES_DIR` | `str` | `"./templates"` | HTML templates |

#### Code Execution

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `MAX_CODE_REPAIR_ATTEMPTS` | `int` | `3` | Max auto-repair retries |
| `CODE_EXECUTION_TIMEOUT` | `int` | `15` | Sandbox timeout in seconds |

#### JWT / Authentication

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `JWT_SECRET_KEY` | `str` | *required* | HMAC signing key |
| `JWT_ALGORITHM` | `str` | `"HS256"` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `int` | `15` | Access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `int` | `7` | Refresh token TTL |
| `FILE_TOKEN_EXPIRE_MINUTES` | `int` | `5` | File download token TTL |

#### Cookies

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `COOKIE_SECURE` | `bool` | `False` | HTTPS-only cookies (auto `True` in production) |
| `COOKIE_SAMESITE` | `str` | `"lax"` | SameSite policy |
| `COOKIE_DOMAIN` | `Optional[str]` | `None` | Cookie domain |
| `COOKIE_NAME` | `str` | `"refresh_token"` | Refresh token cookie name |

#### CORS

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `CORS_ORIGINS` | `List[str]` | `["http://localhost:5173", "http://127.0.0.1:5173"]` | Allowed origins (comma-separated string or JSON array) |

#### LLM Provider

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `LLM_PROVIDER` | `str` | `"OLLAMA"` | Active provider: OLLAMA, GOOGLE, NVIDIA, MYOPENLM |
| `OLLAMA_MODEL` | `str` | `"llama3"` | Ollama model name |
| `GOOGLE_MODEL` | `str` | `"models/gemini-2.5-flash"` | Google Gemini model |
| `GOOGLE_API_KEY` | `str` | `""` | Google API key |
| `NVIDIA_MODEL` | `str` | `"qwen/qwen3.5-397b-a17b"` | NVIDIA NIM model |
| `NVIDIA_API_KEY` | `str` | `""` | NVIDIA API key |
| `MYOPENLM_MODEL` | `str` | `"default"` | Custom endpoint model |
| `MYOPENLM_API_URL` | `str` | `"https://openlmfallback-…/api/chat"` | Custom endpoint URL |
| `LLM_TIMEOUT` | `Optional[int]` | `None` | LLM request timeout |

#### LLM Generation Parameters

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `LLM_TEMPERATURE_STRUCTURED` | `float` | `0.1` | Structured output temperature |
| `LLM_TEMPERATURE_CHAT` | `float` | `0.2` | Chat temperature |
| `LLM_TEMPERATURE_CREATIVE` | `float` | `0.7` | Creative content temperature |
| `LLM_TEMPERATURE_CODE` | `float` | `0.1` | Code generation temperature |
| `LLM_TOP_P_STRUCTURED` | `float` | `0.9` | Structured output top-p |
| `LLM_TOP_P_CHAT` | `float` | `0.95` | Chat top-p |
| `LLM_MAX_TOKENS` | `int` | `4000` | Max output tokens (general) |
| `LLM_MAX_TOKENS_CHAT` | `int` | `3000` | Max output tokens (chat) |
| `LLM_FREQUENCY_PENALTY` | `float` | `0.0` | Frequency penalty |
| `LLM_PRESENCE_PENALTY` | `float` | `0.0` | Presence penalty |
| `LLM_TOP_K` | `int` | `50` | Top-k sampling |

#### Embeddings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `MODELS_DIR` | `str` | `"./data/models"` | Model cache directory |
| `EMBEDDING_MODEL` | `str` | `"BAAI/bge-m3"` | Embedding model name |
| `EMBEDDING_VERSION` | `str` | `"bge_m3_v1"` | Embedding version tag |
| `EMBEDDING_DIMENSION` | `int` | `1024` | Vector dimension |

#### Reranking

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `RERANKER_MODEL` | `str` | `"BAAI/bge-reranker-large"` | Reranker model name |
| `USE_RERANKER` | `bool` | `True` | Enable/disable reranking |

#### Retrieval

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `INITIAL_VECTOR_K` | `int` | `10` | Initial vector search results |
| `MMR_K` | `int` | `8` | MMR diversity selection count |
| `FINAL_K` | `int` | `10` | Final chunks to return |
| `MMR_LAMBDA` | `float` | `0.5` | MMR diversity parameter |
| `MAX_CONTEXT_TOKENS` | `int` | `6000` | Max context window tokens |
| `MIN_CHUNK_LENGTH` | `int` | `100` | Min chunk character length |
| `MIN_CONTEXT_CHUNK_LENGTH` | `int` | `150` | Min context chunk length |
| `MIN_SIMILARITY_SCORE` | `float` | `0.3` | Minimum similarity threshold |
| `CHUNK_OVERLAP_TOKENS` | `int` | `150` | Chunk overlap in tokens |

#### Processing Timeouts

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `OCR_TIMEOUT_SECONDS` | `int` | `300` | OCR timeout |
| `WHISPER_TIMEOUT_SECONDS` | `int` | `600` | Whisper timeout |
| `LIBREOFFICE_TIMEOUT_SECONDS` | `int` | `120` | LibreOffice timeout |
| `PROCESSING_MAX_RETRIES` | `int` | `2` | Max processing retries |

#### External Services

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `IMAGE_GENERATION_ENDPOINT` | `Optional[str]` | `None` | Image generation API URL |
| `SEARCH_SERVICE_URL` | `str` | `"http://localhost:8002"` | External search service URL |

### Validators

- **`_parse_cors(v)`** — Parses comma-separated CORS origins strings into a list
- **`_uppercase_provider(v)`** — Uppercases and validates `LLM_PROVIDER` against allowed values
- **`_validate_jwt(v)`** — Ensures `JWT_SECRET_KEY` is non-empty
- **`_validate_db_url(v)`** — Ensures `DATABASE_URL` is non-empty
- **`_resolve_paths_and_cross_validate()`** — Post-init model validator: resolves relative paths to absolute, auto-derives `COOKIE_SECURE=True` in production, warns on missing API keys

### Singleton Access

```python
from app.core.config import settings  # Module-level singleton
# or
from app.core.config import get_settings  # @lru_cache(maxsize=1) factory
```

---

## 5. Utilities

**File:** `app/core/utils.py`

| Function | Signature | Description |
|----------|-----------|-------------|
| `sanitize_null_bytes` | `(data: Any) -> Any` | Recursively removes `\x00` null bytes from strings, lists, and dicts. Required because PostgreSQL TEXT columns reject null bytes. |

---

## 6. Database Layer

### 6.1 ChromaDB — `app/db/chroma.py`

Thread-safe lazy singleton for ChromaDB persistent client.

**Module-level setup:**
- Disables Chroma/PostHog telemetry via environment variables
- Silences `chromadb` and `posthog` loggers
- Monkey-patches `posthog` to disable tracking
- Sets `SENTENCE_TRANSFORMERS_HOME` to the models directory

**Functions:**

| Function | Signature | Returns | Description |
|----------|-----------|---------|-------------|
| `get_client` | `() -> chromadb.PersistentClient` | Client | Thread-safe lazy singleton using `settings.CHROMA_DIR` |
| `get_collection` | `() -> chromadb.Collection` | Collection | Thread-safe singleton, collection name: `"chapters"` |
| `reset_client` | `() -> None` | — | Resets both client and collection singletons |
| `backup_chroma` | `(backup_dir: str \| None = None) -> str` | Path | Copies `CHROMA_DIR` to timestamped backup directory |
| `get_collection_stats` | `() -> dict` | Stats | Returns `{name, count, chroma_dir}` or `{error}` |

### 6.2 Prisma Client — `app/db/prisma_client.py`

Async Prisma client with exponential backoff retry.

**Globals:**
- `prisma = Prisma()` — Global instance
- `_MAX_CONNECT_RETRIES = 3`
- `_RETRY_DELAY_SECONDS = 2.0`

**Functions:**

| Function | Signature | Description |
|----------|-----------|-------------|
| `get_prisma` | `() -> Prisma` | Returns the global Prisma instance |
| `connect_db` | `async () -> None` | Connects to PostgreSQL with exponential backoff (up to 3 attempts) |
| `disconnect_db` | `async () -> None` | Safe disconnect (no-op if already disconnected) |

### 6.3 Exports — `app/db/__init__.py`

Re-exports: `prisma`, `connect_db`, `disconnect_db`

---

## 7. Prisma Schema

**File:** `prisma/schema.prisma`

- **Generator:** `prisma-client-py`, async interface, recursive depth 5
- **Datasource:** PostgreSQL, URL from `DATABASE_URL` environment variable

### Models (21 total)

#### User
| Field | Type | Attributes |
|-------|------|------------|
| `id` | `String` | `@id @default(uuid())` |
| `email` | `String` | `@unique` |
| `username` | `String` | |
| `hashedPassword` | `String` | |
| `isActive` | `Boolean` | `@default(true)` |
| `role` | `String` | `@default("user")` |
| `createdAt` | `DateTime` | `@default(now())` |
| `updatedAt` | `DateTime` | `@updatedAt` |

**Relations:** Has many → notebooks, materials, chatSessions, chatMessages, generatedContent, refreshTokens, backgroundJobs, tokenUsage, apiUsageLogs, agentLogs, codeExecutions, researchSessions, explainerVideos, podcastSessions

#### Notebook
| Field | Type | Attributes |
|-------|------|------------|
| `id` | `String` | `@id @default(uuid())` |
| `userId` | `String` | FK → User |
| `name` | `String` | |
| `description` | `String?` | |
| `createdAt/updatedAt` | `DateTime` | |

**Relations:** Belongs to User. Has many → materials, chatSessions, chatMessages, generatedContent

#### Material
| Field | Type | Attributes |
|-------|------|------------|
| `id` | `String` | `@id @default(uuid())` |
| `userId` | `String` | FK → User |
| `notebookId` | `String` | FK → Notebook |
| `filename` | `String` | |
| `title` | `String?` | |
| `originalText` | `String?` | |
| `status` | `String` | Enum: `pending`, `processing`, `ocr_running`, `transcribing`, `embedding`, `completed`, `failed` |
| `chunkCount` | `Int` | `@default(0)` |
| `sourceType` | `String?` | |
| `metadata` | `String?` | JSON as string |
| `error` | `String?` | |
| `createdAt/updatedAt` | `DateTime` | |

#### ChatSession
| Field | Type |
|-------|------|
| `id` | `String @id @default(uuid())` |
| `notebookId`, `userId` | `String` (FK) |
| `title` | `String?` |
| `createdAt/updatedAt` | `DateTime` |

**Relations:** Has many → chatMessages

#### ChatMessage
| Field | Type |
|-------|------|
| `id` | `String @id @default(uuid())` |
| `notebookId`, `userId` | `String` (FK) |
| `chatSessionId` | `String?` (FK) |
| `role` | `String` (user/assistant) |
| `content` | `String` |
| `agentMeta` | `String?` (JSON) |
| `timestamp` | `DateTime` |

**Relations:** Has many → responseBlocks

#### ResponseBlock
| Field | Type |
|-------|------|
| `id` | `String @id @default(uuid())` |
| `chatMessageId` | `String` (FK) |
| `blockIndex` | `Int` |
| `text` | `String` |
| `timestamp` | `DateTime` |

#### GeneratedContent
| Field | Type |
|-------|------|
| `id` | `String @id @default(uuid())` |
| `notebookId`, `userId` | `String` (FK) |
| `materialId` | `String?` |
| `contentType` | `String` (flashcards/quiz/audio/presentation) |
| `title` | `String` |
| `data` | `Json` |
| `language` | `String?` |
| `materialIds` | `String[]` |
| `timestamp` | `DateTime` |

**Relations:** Has many → explainerVideos

#### ExplainerVideo
| Field | Type |
|-------|------|
| `id` | `String @id @default(uuid())` |
| `userId` | `String` (FK) |
| `presentationId` | `String` (FK → GeneratedContent) |
| `pptLanguage`, `narrationLanguage` | `String` |
| `voiceGender`, `voiceId` | `String` |
| `status` | `String` |
| `script` | `Json?` |
| `audioFiles` | `Json?` |
| `videoUrl`, `error` | `String?` |
| `duration` | `Float?` |
| `chapters` | `Json?` |
| `createdAt/updatedAt` | `DateTime` |

#### RefreshToken
| Field | Type |
|-------|------|
| `id` | `String @id @default(uuid())` |
| `userId` | `String` (FK) |
| `tokenHash` | `String @unique` |
| `family` | `String` |
| `used` | `Boolean @default(false)` |
| `expiresAt` | `DateTime` |
| `createdAt` | `DateTime` |

#### BackgroundJob
| Field | Type |
|-------|------|
| `id` | `String @id @default(uuid())` |
| `userId` | `String` (FK) |
| `jobType` | `String` |
| `status` | `String` (pending/processing/…/completed/failed) |
| `result` | `Json?` |
| `error` | `String?` |
| `createdAt/updatedAt` | `DateTime` |

#### UserTokenUsage
| Field | Type | Unique |
|-------|------|--------|
| `id` | `String @id @default(uuid())` | |
| `userId` | `String` (FK) | `@@unique([userId, date])` |
| `date` | `DateTime` | |
| `tokensUsed` | `Int` | |

#### ApiUsageLog
| Field | Type |
|-------|------|
| `id` | `String @id @default(uuid())` |
| `userId` | `String` (FK) |
| `endpoint` | `String` |
| `materialIds` | `String[]` |
| `contextTokenCount`, `responseTokenCount` | `Int` |
| `modelUsed` | `String` |
| `llmLatency`, `retrievalLatency`, `totalLatency` | `Float` |
| `createdAt` | `DateTime` |

#### AgentExecutionLog
Fields: `id`, `userId`, `notebookId`, `intent`, `confidence`, `toolsUsed[]`, `stepsCount`, `tokensUsed`, `elapsedTime`, `createdAt`

#### CodeExecutionSession
Fields: `id`, `userId`, `notebookId`, `code`, `stdout`, `stderr`, `exitCode`, `hasChart`, `elapsedTime`, `createdAt`

#### ResearchSession
Fields: `id`, `userId`, `notebookId`, `query`, `report`, `sourcesCount`, `queriesCount`, `iterations`, `elapsedTime`, `sourceUrls[]`, `createdAt`

#### PodcastSession
Fields: `id`, `notebookId`, `userId`, `mode`, `topic`, `language`, `status` (created/script_generating/audio_generating/ready/playing/paused/completed/failed), `currentSegment`, `hostVoice`, `guestVoice`, `title`, `tags[]`, `chapters` (Json), `totalDurationMs`, `materialIds[]`, `summary`, `error`, `createdAt/updatedAt`

**Relations:** Has many → segments, doubts, exports, bookmarks, annotations

#### PodcastSegment
Fields: `id`, `sessionId` (FK), `index`, `speaker`, `text`, `audioUrl`, `durationMs`, `chapter`, `createdAt` — `@@unique([sessionId, index])`

#### PodcastDoubt
Fields: `id`, `sessionId`, `pausedAtSegment`, `questionText`, `questionAudioUrl`, `answerText`, `answerAudioUrl`, `resolvedAt`, `createdAt`

#### PodcastExport
Fields: `id`, `sessionId`, `format`, `fileUrl`, `status`, `createdAt`

#### PodcastBookmark
Fields: `id`, `sessionId`, `segmentIndex`, `label`, `createdAt`

#### PodcastAnnotation
Fields: `id`, `sessionId`, `segmentIndex`, `note`, `createdAt`

---

## 8. Application Entry

**File:** `app/main.py`

### Logging Setup
- `RotatingFileHandler` — 10MB per file, 3 backups → `logs/app.log`
- `StreamHandler` → stdout
- Quietens noisy loggers: `httpx`, `httpcore`, `uvicorn.access`

### Lifespan (Startup / Shutdown)

**Startup sequence:**
1. Connect Prisma / PostgreSQL
2. Warm up embedding model (thread pool executor)
3. Preload reranker model (thread pool executor)
4. Start background `job_processor` asyncio task
5. Ensure sandbox Python packages installed
6. Clean up stale sandbox temp directories (`/tmp/kepler_sandbox_*`, `/tmp/kepler_analysis_*`)
7. Create output directories

**Shutdown sequence:**
1. Graceful worker shutdown (signal + wait)
2. Cancel `job_processor` task
3. Disconnect Prisma / PostgreSQL

### Middleware Stack (applied in order)

| # | Middleware | Description |
|---|-----------|-------------|
| 1 | `performance_monitoring_middleware` | Captures full request timing, adds `X-Response-Time` header (dev only) |
| 2 | `rate_limit_middleware` | Per-user/IP rate limiting with sliding window |
| 3 | `log_requests` | Logs method/path/status/time with UUID `request_id`, adds `X-Request-ID` header |
| 4 | `CORSMiddleware` | CORS from `settings.CORS_ORIGINS`, allows credentials |
| 5 | `TrustedHostMiddleware` | Production only — trusted hosts |
| 6 | `limit_request_body` | 100MB max request body size |

### Error Handlers
- **`http_exception_handler`** — Returns JSON with CORS headers for proper error display
- **`global_exception_handler`** — Catches all unhandled exceptions, returns 500 with `request_id`

### Router Registration

| Router | Prefix | Tags | Auth Required |
|--------|--------|------|---------------|
| `health_router` | — | health | Public (full check requires auth) |
| `auth_router` | — | auth | Public |
| `models_router` | — | models | Public (some routes need auth) |
| `notebook_router` | — | notebooks | Yes |
| `upload_router` | — | upload | Yes |
| `flashcard_router` | — | flashcard | Yes |
| `quiz_router` | — | quiz | Yes |
| `chat_router` | — | chat | Yes |
| `jobs_router` | — | jobs | Yes |
| `ppt_router` | — | presentation | Yes |
| `mindmap_router` | — | mindmap | Yes |
| `agent_router` | — | agent | Yes |
| `search_router` | `/search` | search | Yes |
| `proxy_router` | `/api/v1` | proxy | Yes |
| `explainer_router` | — | explainer | Yes |
| `podcast_live_router` | — | podcast | Yes |
| `ws_router` | — | — | WebSocket (JWT) |

---

## 9. Pydantic Models

**File:** `app/models/mindmap_schemas.py`

| Class | Fields | Description |
|-------|--------|-------------|
| `MindMapNode(BaseModel)` | `id: str`, `label: str`, `parent_id: Optional[str]`, `description: str`, `question_hint: str`, `has_children: bool = False` | Single node in mind map tree |
| `MindMapRequest(BaseModel)` | `notebook_id: str`, `material_ids: List[str]` | Request to generate mind map |
| `MindMapResponse(BaseModel)` | `id: str`, `title: str`, `notebook_id: str`, `material_ids: List[str]`, `nodes: List[MindMapNode]`, `created_at: datetime` | Full mind map response |

---

## 10. API Routes

### 10.1 Auth

**File:** `app/routes/auth.py` — Prefix: `/auth`

**Request/Response Models:**
- `SignupRequest`: `email: EmailStr`, `username: str`, `password: str` — Validators: password ≥8 chars with upper/lower/digit; username 2-50 chars
- `LoginRequest`: `email: EmailStr`, `password: str`
- `AccessTokenResponse`: `access_token: str`, `token_type: str = "bearer"`
- `UserResponse`: `id: str`, `email: str`, `username: str`, `role: str`

**Helper Functions:**
- `_set_refresh_cookie(response, token)` — Sets HttpOnly Secure cookie, path restricted to `/auth`
- `_clear_refresh_cookie(response)` — Deletes refresh cookie

| Method | Path | Handler | Status | Description |
|--------|------|---------|--------|-------------|
| POST | `/auth/signup` | `signup` | 201 | Register new user, returns `UserResponse` |
| POST | `/auth/login` | `login` | 200 | Authenticate user, create token family, set refresh cookie, return access token |
| POST | `/auth/refresh` | `refresh_token_endpoint` | 200 | Rotate refresh token from HttpOnly cookie, return new access token |
| GET | `/auth/me` | `get_me` | 200 | Return current user info (requires auth) |
| POST | `/auth/logout` | `logout` | 200 | Revoke all refresh tokens for user, clear cookie |

**Security:** Refresh tokens use family-based rotation with replay attack detection. If a used token is presented, the entire family is revoked.

---

### 10.2 Notebooks

**File:** `app/routes/notebook.py` — Prefix: `/notebooks`

**Request/Response Models:**
- `NotebookCreate`: `name: str (1-200)`, `description: Optional[str] (max 2000)`
- `NotebookUpdate`: `name: Optional[str]`, `description: Optional[str]`
- `NotebookResponse`: `id, name, description, created_at, updated_at`
- `ContentType(str, Enum)`: `flashcards`, `quiz`, `audio`, `presentation`
- `SaveContentRequest`: `content_type, title, data, material_id`
- `UpdateContentRequest`: `title: str (1-500)`

| Method | Path | Handler | Status | Description |
|--------|------|---------|--------|-------------|
| POST | `/notebooks` | `create_notebook_endpoint` | 201 | Create new notebook |
| GET | `/notebooks` | `list_notebooks` | 200 | List user notebooks. Pagination: `skip` (≥0), `take` (1-200, default 50) |
| GET | `/notebooks/{notebook_id}` | `get_notebook` | 200 | Get single notebook by UUID |
| PUT | `/notebooks/{notebook_id}` | `update_notebook_endpoint` | 200 | Update notebook name/description |
| DELETE | `/notebooks/{notebook_id}` | `delete_notebook_endpoint` | 204 | Delete notebook and all associated data |
| POST | `/notebooks/{notebook_id}/content` | `save_generated_content` | 201 | Save generated content (flashcards, quiz, etc.) |
| GET | `/notebooks/{notebook_id}/content` | `get_notebook_content_endpoint` | 200 | Get all generated content for notebook |
| DELETE | `/notebooks/{notebook_id}/content/{content_id}` | `delete_generated_content` | 200 | Delete specific content item |
| PUT | `/notebooks/{notebook_id}/content/{content_id}` | `update_generated_content_title_endpoint` | 200 | Update content title |

---

### 10.3 Upload / Materials

**File:** `app/routes/upload.py`

**Constants:**
- `UPLOAD_DIR` — from settings
- `MAX_UPLOAD_BYTES` — computed from `MAX_UPLOAD_SIZE_MB`
- `ALLOWED_MIME_TYPES` — approved MIME types set

**Request Models:**
- `URLUploadRequest`: `url, notebook_id, auto_create_notebook, source_type ("auto"/"web"/"youtube"), title`
- `TextUploadRequest`: `text, title, notebook_id, auto_create_notebook`
- `MaterialUpdateBody`: `filename, title` (both optional)

| Method | Path | Handler | Status | Description |
|--------|------|---------|--------|-------------|
| POST | `/upload` | `upload_file` | 202 | Single file upload. Streams to temp, validates with python-magic, moves to permanent storage, creates Material + BackgroundJob, wakes worker |
| POST | `/upload/batch` | `upload_batch` | 202 | Batch upload — processes all files concurrently via `asyncio.gather` |
| POST | `/upload/url` | `upload_url` | 202 | URL upload (web/YouTube). SSRF protection (blocks private IPs). Auto-detects YouTube URLs |
| POST | `/upload/text` | `upload_text` | 202 | Direct text paste upload |
| GET | `/upload/supported-formats` | `get_supported_formats` | 200 | Returns supported file types organized by category |
| GET | `/materials` | `list_materials` | 200 | List user materials, optional `notebook_id` filter |
| PATCH | `/materials/{material_id}` | `patch_material` | 200 | Update material filename/title |
| DELETE | `/materials/{material_id}` | `remove_material` | 200 | Delete material and associated embeddings |
| GET | `/materials/{material_id}/text` | `get_material_text_endpoint` | 200 | Get full extracted text for material |

**Material Status Lifecycle:** `pending → processing → [ocr_running | transcribing] → embedding → completed`

---

### 10.4 Chat

**File:** `app/routes/chat.py`

**Request Models:**
- `ChatRequest`: `material_id, material_ids, message (1-50000), notebook_id, session_id, stream (default True), intent_override`
- `ClearChatRequest`: `notebook_id, session_id`
- `BlockFollowupRequest`: `block_id, question (1-10000), action ("ask"/"simplify"/"translate"/"explain")`
- `SuggestionRequest`: `partial_input (1-1000), notebook_id`
- `CreateSessionRequest`: `notebook_id, title`

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | `/chat` | `chat_endpoint` | Main chat endpoint. Routes through LangGraph agent. Validates materials ownership. Creates/manages sessions. Supports SSE streaming (default) and non-streaming. Builds `workspace_files` for data analysis. Persists messages + response blocks. |
| POST | `/chat/block-followup` | `block_followup` | Block-level mini chat via SSE. Focused on a single response paragraph. Validates block ownership. Persists follow-up as new ResponseBlock. |
| POST | `/chat/suggestions` | `get_suggestions` | Smart prompt suggestions based on partial input text |
| GET | `/chat/history/{notebook_id}` | `get_notebook_chat_history` | Get chat messages for notebook/session (optional `session_id` query param) |
| DELETE | `/chat/history/{notebook_id}` | `clear_notebook_chat` | Clear chat messages |
| GET | `/chat/sessions/{notebook_id}` | `get_chat_sessions_endpoint` | List all chat sessions for notebook |
| POST | `/chat/sessions` | `create_chat_session_endpoint` | Create new chat session |
| DELETE | `/chat/sessions/{session_id}` | `delete_chat_session_endpoint` | Delete chat session (cascading) |

**Stream Protocol (SSE):**
Events: `start`, `step`, `step_done`, `token`, `code_stdout`, `code_written`, `code_generating`, `code_generated`, `repair_attempt`, `repair_success`, `meta`, `blocks`, `done`, `error`

---

### 10.5 Agent

**File:** `app/routes/agent.py` — Prefix: `/agent`

**Request Models:**
- `ExecuteRequest`: `code (1-50000), notebook_id, timeout (1-120, default 15)`
- `AnalyzeRequest`: `query (1-10000), notebook_id, material_ids`
- `ResearchRequest`: `query (1-5000), notebook_id, material_ids`

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | `/agent/execute` | `execute_code_endpoint` | Direct Python code execution in sandbox. SSE stream: `start → stdout → result/error → done` |
| POST | `/agent/analyze` | `analyze_data_endpoint` | Natural language data analysis via LangGraph agent (DATA_ANALYSIS intent). SSE stream: `start → step → token → code_stdout → meta → done` |
| POST | `/agent/research` | `research_endpoint` | Deep web research via LangGraph agent (RESEARCH intent). SSE stream |
| GET | `/agent/status/{job_id}` | `execution_status` | Poll job status |
| GET | `/agent/files` | `list_generated_files` | List files generated by agent for a session |
| GET | `/agent/download/{user_id}/{session_id}/{filename}` | `download_generated_file` | Download generated file with signed token auth + IDOR protection |

---

### 10.6 Flashcard

**File:** `app/routes/flashcard.py`

**Request Model:**
- `FlashcardRequest`: `material_id, material_ids, topic (max 500), card_count (1-100), difficulty (Easy/Medium/Hard), additional_instructions (max 2000)`

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | `/flashcard` | `create_flashcards` | Generate flashcards from material text. Runs LLM structured invocation in thread pool executor. Returns `{title, flashcards: [{question, answer}]}` |

---

### 10.7 Quiz

**File:** `app/routes/quiz.py`

**Request Model:**
- `QuizRequest`: `material_id, material_ids, topic (max 500), mcq_count (1-50, default 10), difficulty (Easy/Medium/Hard), additional_instructions (max 2000)`

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | `/quiz` | `create_quiz` | Generate MCQ quiz. Runs in thread pool executor. Returns `{title, questions: [{question, options[4], correct_answer (0-3), explanation}]}` |

---

### 10.8 Presentation (PPT)

**File:** `app/routes/ppt.py`

**Request Model:**
- `PresentationRequest`: `material_id, material_ids, max_slides (3-60), theme, additional_instructions`

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | `/presentation` | `generate_ppt` | Synchronous HTML presentation generation. Returns title, slide_count, theme, html, slides, presentation_id |
| POST | `/presentation/async` | `generate_ppt_async` | Background job-based generation. Returns `{job_id, message}` |
| GET | `/presentation/slides/{user_id}/{presentation_id}/{filename}` | `get_slide_image` | Serve slide PNG images (user-scoped access control) |

---

### 10.9 Mind Map

**File:** `app/routes/mindmap.py`

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | `/mindmap` | `create_mindmap` | Generate mind map from materials. Returns `MindMapResponse` |
| GET | `/mindmap/{notebook_id}` | `get_mindmap` | Retrieve saved mind map for notebook |
| DELETE | `/mindmap/{id}` | `delete_mindmap` | Delete a mind map |

---

### 10.10 Explainer

**File:** `app/routes/explainer.py`

**Request Models:**
- `CheckPresentationsRequest`: `material_ids, notebook_id`
- `GenerateExplainerRequest`: `material_ids, notebook_id, ppt_language ("en"), narration_language ("en"), voice_gender ("male"/"female"), presentation_id, create_new_ppt`

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | `/explainer/check-presentations` | `check_presentations` | Check if presentations exist for given materials |
| POST | `/explainer/generate` | `generate_explainer` | Start explainer video generation (background task). Can reuse existing PPT or generate new |
| GET | `/explainer/{explainer_id}/status` | `get_explainer_status` | Poll video generation progress (0-100%, with per-stage status) |
| GET | `/explainer/{explainer_id}/video` | `get_explainer_video` | Download finished MP4 video |

**7-Stage Pipeline:** PPT Gen → Screenshot → Script Gen → TTS → Video Compose → Concatenate → Finalize

---

### 10.11 Podcast Live

**File:** `app/routes/podcast_live.py` — Prefix: `/podcast`

**Request Models:**
- `CreateSessionRequest`: `notebook_id, mode ("overview"/"deep-dive"/"debate"/"q-and-a"/"full"/"topic"), topic, language, host_voice, guest_voice, material_ids`
- `QuestionRequest`: `question_text, paused_at_segment, question_audio_url`
- `BookmarkRequest`: `segment_index, label`
- `AnnotationRequest`: `segment_index, note`
- `ExportRequest`: `format ("pdf"/"json")`
- `UpdateSessionRequest`: `title, tags, current_segment`

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | `/podcast/session` | `create_session` | Create podcast session |
| GET | `/podcast/session/{session_id}` | `get_session` | Get full session state (segments, doubts, bookmarks, annotations) |
| GET | `/podcast/sessions/{notebook_id}` | `list_sessions` | List sessions for notebook |
| PATCH | `/podcast/session/{session_id}` | `update_session` | Update title/tags/position |
| DELETE | `/podcast/session/{session_id}` | `delete_session` | Delete session + associated files and DB records |
| POST | `/podcast/session/{session_id}/start` | `start_generation` | Begin script + TTS pipeline |
| GET | `/podcast/session/{session_id}/segment/{segment_index}/audio` | `get_segment_audio` | Serve segment MP3 |
| GET | `/podcast/session/{session_id}/audio/{filename}` | `get_audio_file` | Serve any session audio file |
| POST | `/podcast/session/{session_id}/question` | `ask_question` | Submit Q&A question during podcast |
| GET | `/podcast/session/{session_id}/doubts` | `get_doubts` | Get Q&A history |
| POST | `/podcast/session/{session_id}/bookmark` | `add_bookmark` | Bookmark a segment |
| GET | `/podcast/session/{session_id}/bookmarks` | `get_bookmarks` | List bookmarks |
| DELETE | `/podcast/session/{session_id}/bookmark/{bookmark_id}` | `delete_bookmark` | Remove bookmark |
| POST | `/podcast/session/{session_id}/annotation` | `add_annotation` | Annotate a segment |
| DELETE | `/podcast/session/{session_id}/annotation/{annotation_id}` | `delete_annotation` | Remove annotation |
| POST | `/podcast/session/{session_id}/export` | `trigger_export` | Start PDF/JSON export |
| GET | `/podcast/export/{export_id}` | `get_export_status` | Check export status |
| GET | `/podcast/export/file/{session_id}/{filename}` | `download_export` | Download export file |
| POST | `/podcast/session/{session_id}/summary` | `generate_summary` | Generate LLM session summary |
| GET | `/podcast/voices` | `get_voices` | Get available TTS voices for language |
| GET | `/podcast/voices/all` | `get_all_voices` | All voices for all languages |
| GET | `/podcast/languages` | `get_languages` | Supported languages (10 languages) |
| POST | `/podcast/voice/preview` | `preview_voice` | Generate voice preview audio |
| POST | `/podcast/session/{session_id}/satisfaction` | `check_satisfaction` | Test satisfaction detection |

---

### 10.12 Health

**File:** `app/routes/health.py`

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| GET | `/health` | `health_check` | Full health check — PostgreSQL, ChromaDB, LLM. Returns 200 (healthy/degraded) or 503 (unhealthy) |
| GET | `/health/simple` | `simple_health_check` | Simple 200 OK (no auth required) |

---

### 10.13 Jobs

**File:** `app/routes/jobs.py` — Prefix: `/jobs`

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| GET | `/jobs/{job_id}` | `get_job_status` | Poll background job status. Returns id, type, status, created_at, updated_at, result, error |

---

### 10.14 Models

**File:** `app/routes/models.py` — Prefix: `/models`

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| GET | `/models/status` | `get_models_status` | Get status of all required AI models (embedding, reranker) |
| POST | `/models/reload` | `reload_models` | Reload all models (admin only) |

---

### 10.15 Search

**File:** `app/routes/search.py` — Prefix: `/search`

**Request/Response Models:**
- `WebSearchRequest`: `query, file_type, engine ("duckduckgo")`
- `SearchResult`: `title, link, snippet`

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | `/search/web` | `search_web` | Bridge to external search service at `SEARCH_SERVICE_URL` |

---

### 10.16 Proxy / File Viewer

**File:** `app/routes/proxy.py` — Prefix: `/api/v1`

**Security Features:**
- `RESTRICTED_HEADERS` — headers stripped for iframe embedding
- `_PRIVATE_NETWORKS` — CIDR ranges for SSRF protection
- `_validate_url(url)` — enforces HTTPS, blocks localhost/private IPs, DNS resolution check

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| GET | `/api/v1/proxy` | `proxy_webpage` | Fetch webpage, strip iframe-blocking headers. HTTPS only |
| GET | `/api/v1/file-viewer/info` | `file_viewer_info` | Validate file URL, return viewer metadata (pdf/office/text). Provides MS Office Online embed URL for .docx/.pptx/.xlsx |
| GET | `/api/v1/file-viewer/proxy` | `file_viewer_proxy` | Proxy PDF/text files with `Content-Disposition: inline` for iframe rendering |

---

### 10.17 WebSocket

**File:** `app/routes/websocket_router.py`

**Authentication modes:**
1. **Query param:** `?token=<jwt>` (legacy)
2. **First-message:** `{"type": "auth", "token": "<jwt>"}` (preferred)

| Protocol | Path | Handler | Description |
|----------|------|---------|-------------|
| WebSocket | `/ws/jobs/{user_id}` | `ws_jobs` | Material processing job updates. Auth via JWT. Server pings every 30s. Messages: `connected`, `material_update`, `ping/pong` |

---

### 10.18 Route Utilities

**File:** `app/routes/utils.py`

| Function | Signature | Description |
|----------|-----------|-------------|
| `safe_path` | `(base_dir, *parts) -> str` | Prevents directory traversal attacks. Raises 400 on violation |
| `require_material` | `async (material_id, user_id, *, require_text=True) -> Material` | Fetch material owned by user. Raises 404 (not found) or 400 (not ready) |
| `require_material_text` | `async (material_id, user_id) -> str` | Fetch material + load full text from file storage |
| `require_materials_text` | `async (material_ids, user_id, *, separator) -> str` | Combine text from multiple materials |
| `require_file_token` | `async (token) -> str` | Validate signed file-access token, return `user_id` |
| `require_file_token_for_user` | `async (token, expected_user_id) -> str` | Like above + verifies user ownership (IDOR protection) |

---

## 11. Prompt Templates

**File:** `app/prompts/__init__.py`

### Loader Mechanism
- `_DIR` — directory of prompt template files
- `_load(filename) -> str` — `@lru_cache(maxsize=32)`, reads template file from disk once
- `_render(filename, subs) -> str` — Loads file and applies `{{KEY}}` placeholder substitutions

### Public Functions

| Function | Parameters | Template File |
|----------|-----------|---------------|
| `get_flashcard_prompt` | `content_text, card_count, difficulty, instructions` | `flashcard_prompt.txt` |
| `get_quiz_prompt` | `content_text, mcq_count, difficulty, instructions` | `quiz_prompt.txt` |
| `get_chat_prompt` | `context, chat_history, user_message` | `chat_prompt.txt` |
| `get_mindmap_prompt` | `material_text` | `mindmap_prompt.txt` |
| `get_ppt_prompt` | `material_text, slide_count=10, theme=None, additional_instructions=None` | `ppt_prompt.txt` |

### Template Details

| Template | Purpose | Output Format |
|----------|---------|---------------|
| `chat_prompt.txt` | RAG chat — "KeplerLab AI Notebook Assistant" persona. Handles materials context, chat history, structured data (CSV/Excel) | Free-form markdown with `[Source N]` citations |
| `flashcard_prompt.txt` | Anki-style flashcard generation | JSON `{title, flashcards: [{question, answer}]}` |
| `quiz_prompt.txt` | MCQ quiz generation | JSON `{title, questions: [{question, options[4], correct_answer (0-3), explanation}]}` |
| `ppt_prompt.txt` | Full HTML presentation generation (1920×1080 slides, 13 slide types, detailed CSS) | JSON `{title, slide_count, theme, html}` |
| `mindmap_prompt.txt` | Mind map node hierarchy generation | JSON `{title, nodes: [{id, label, parent_id, description, question_hint}]}` |
| `code_generation_prompt.txt` | Python code generation for sandbox. Defines allowed/forbidden functions, `OUTPUT_DIR`, `FILE_SAVED:` protocol | Executable Python code |
| `code_repair_prompt.txt` | Python debugger for fixing sandbox errors | Corrected Python code only |
| `data_analysis_prompt.txt` | Data analyst for CSV/Excel analysis with dataset metadata | Python analysis code |
| `podcast_script_prompt.txt` | Two-host podcast dialogue (HOST + GUEST) | JSON `{title, chapters, segments}` |
| `podcast_qa_prompt.txt` | Podcast Q&A — answers listener questions as GUEST (50-150 words) | Short text answer |

---

## 12. Services

### 12.1 Top-Level Services

#### `audit_logger.py` — API Usage Audit Logger (164 lines)

| Function | Signature | Description |
|----------|-----------|-------------|
| `log_api_usage` | `async (user_id, endpoint, material_ids=None, context_token_count=0, response_token_count=0, model_used="unknown", llm_latency=0.0, retrieval_latency=0.0, total_latency=0.0) -> None` | Logs API usage to `prisma.apiusagelog` |
| `get_user_api_usage` | `async (user_id, start_date=None, end_date=None, limit=100) -> list` | Retrieves usage history |
| `get_usage_statistics` | `async (user_id=None, start_date=None, end_date=None) -> dict` | Aggregated stats via raw SQL |

#### `file_validator.py` — Upload File Validation (156 lines)

**Constants:**
- `BLOCKED_MIME_TYPES: frozenset` — ~20 blocked MIME types (executables, scripts, etc.)
- `BLOCKED_EXTENSIONS: frozenset` — ~30 blocked extensions

**Class:** `FileValidationError(Exception)`

| Function | Signature | Description |
|----------|-----------|-------------|
| `validate_file_size` | `(file_size: int) -> None` | Raises on size violation |
| `validate_not_executable` | `(filename: str, file_path: str) -> str` | python-magic MIME check, returns detected MIME |
| `sanitize_filename` | `(filename: str) -> str` | Path traversal prevention |
| `generate_internal_filename` | `(original_filename: str) -> Tuple[str, str]` | UUID-based internal filenames |
| `validate_upload` | `(file_path: str, filename: str, file_size: int) -> dict` | Main validation entry point (combines all checks) |

#### `gpu_manager.py` — GPU Resource Manager (75 lines)

Singleton preventing GPU OOM via exclusive locking.

**Class: `GPUManager`** (singleton via `__new__`)

| Method | Description |
|--------|-------------|
| `gpu_session(task_name)` | Sync context manager with exclusive GPU lock |
| `async_gpu_session(task_name)` | Async context manager wrapping sync lock |
| `_clear_memory()` | `torch.cuda.empty_cache()` + synchronize |

#### `job_service.py` — Background Job Service (114 lines)

| Function | Signature | Description |
|----------|-----------|-------------|
| `create_job` | `async (user_id, job_type, payload=None) -> str` | Creates job, returns job ID |
| `fetch_next_pending_job` | `async (job_type="material_processing") -> Optional[Job]` | Atomic claim with `FOR UPDATE SKIP LOCKED` (prevents double processing) |
| `update_job_status` | `async (job_id, status, result=None, error=None) -> None` | Update job status/result/error |
| `get_job` | `async (job_id, user_id) -> Job` | Fetch job with ownership verification |

#### `material_service.py` — Material Lifecycle (849 lines)

Core material processing — three ingestion paths (file/URL/text) share a common pipeline.

**Constants:** `_STRUCTURED_SOURCE_TYPES = frozenset({"csv", "excel", "xlsx", "xls", "tsv", "ods"})`

**Pipeline:** Extract text → Chunk text → Embed chunks → Store in ChromaDB → Save text to file → Update DB status

**Internal Functions:**
| Function | Description |
|----------|-------------|
| `_emit_material_ws(user_id, material_id, status, **extra)` | Push WebSocket update |
| `_set_status(material_id, status, user_id=None, **extra)` | Persist status change |
| `_fail_material(material_id, reason, user_id=None)` | Mark as failed |
| `_make_structured_summary_chunk(raw_file_path, fallback_text)` | CSV/Excel special handling — generates summary chunk + saves parquet side-car |
| `_process_material(material_id, text, user_id, notebook_id, *, title, filename, extraction_metadata, source_type)` | Core pipeline: extract → chunk → embed → update. Launches background AI title generation via `asyncio.create_task` |

**Public API:**
| Function | Description |
|----------|-------------|
| `process_material(file_path, filename, user_id, notebook_id)` | Process uploaded file |
| `create_material_record(filename, user_id, notebook_id, source_type, title)` | Create pending material record |
| `process_material_by_id(material_id, ...)` | Process existing material record |
| `process_url_material_by_id(material_id, url, ...)` | Process URL-based material |
| `process_text_material_by_id(material_id, text_content, ...)` | Process pasted text |
| `filter_completed_material_ids(material_ids, user_id)` | Filter to completed-only |
| `get_material(material_id)` / `get_material_for_user(material_id, user_id)` | Fetch material |
| `get_material_text(material_id, user_id)` | Get full extracted text from storage |
| `get_user_materials(user_id, notebook_id)` | List user's materials |
| `update_material(material_id, user_id, filename, title)` | Update metadata |
| `delete_material(material_id, user_id)` | Delete material + embeddings + stored text |

#### `model_manager.py` — AI Model Manager (127 lines)

**Class: `ModelManager`**

| Method | Description |
|--------|-------------|
| `validate_and_load_models()` | Validates and downloads required models (runs in thread executor) |
| `get_model_info()` | Returns model status info |
| `_ensure_model(cfg)` / `_ensure_sentence_transformer(name)` | Download individual model |
| `_is_model_cached(name)` / `_human_cache_size(path)` | Internal helpers |

**Global:** `model_manager = ModelManager()`

#### `notebook_name_generator.py` — Smart Naming (72 lines)

LLM-based notebook/material title generation.

| Function | Description |
|----------|-------------|
| `generate_notebook_name(content, filename)` | Generates 2-5 word notebook name (3 retries) |
| `generate_material_title(content, filename)` | Generates 3-8 word material title (3 retries) |

#### `notebook_service.py` — Notebook CRUD (164 lines)

| Function | Description |
|----------|-------------|
| `create_notebook(user_id, name, description)` | Create notebook |
| `get_user_notebooks(user_id, skip, take)` | Paginated list |
| `get_notebook_by_id(notebook_id, user_id)` | Get single notebook |
| `update_notebook(...)` / `delete_notebook(...)` | Update / delete |
| `save_notebook_content(notebook_id, user_id, content_type, title, data, material_id)` | Save generated content |
| `get_notebook_content(notebook_id, user_id)` | Get all content |
| `delete_notebook_content(...)` / `update_notebook_content_title(...)` | Manage content |

#### `performance_logger.py` — Performance Monitoring (190 lines)

**Context Variables:** `_request_start_time`, `_retrieval_time`, `_reranking_time`, `_llm_time`

| Function | Description |
|----------|-------------|
| `set_request_start_time()` / `get_request_elapsed_time()` | Request timing |
| `record_retrieval_time(seconds)` | Track retrieval duration |
| `record_reranking_time(seconds)` | Track reranking duration |
| `record_llm_time(seconds)` | Track LLM call duration |
| `get_performance_metrics()` | Get all timing metrics |
| `log_performance_metrics(endpoint, method, status_code, user_id)` | Log full metrics |

**Middleware:** `performance_monitoring_middleware(request, call_next)` — Adds `X-Response-Time` headers in dev mode

**Class:** `PerformanceTimer` — Context manager for timing code blocks

#### `rate_limiter.py` — Rate Limiting (240 lines)

**Constants:**
- `CHAT_LIMIT = 30` requests / 60s
- `GENERATION_LIMIT = 5` requests / 60s
- `AUTH_LIMIT = 10` requests / 60s

**Class:** `RateLimitExceeded(HTTPException)` — 429 response with `Retry-After` header

**Middleware:** `rate_limit_middleware(request, call_next)` — IP-based for auth routes, JWT-based for all others

#### `storage_service.py` — File Storage (175 lines)

**Constants:** `MATERIAL_TEXT_DIR` — from settings

| Function | Description |
|----------|-------------|
| `save_material_text(material_id, text)` | Save extracted text to file |
| `load_material_text(material_id)` | Load text from file |
| `delete_material_text(material_id)` | Delete text file |
| `get_material_summary(text, max_chars=1000)` | Get text summary |
| `get_storage_stats()` | Storage statistics |
| `delete_uploaded_file(file_path)` | Delete uploaded file |

#### `token_counter.py` — Token Counting (304 lines)

| Function | Description |
|----------|-------------|
| `estimate_token_count(text, model)` | Count tokens using tiktoken |
| `get_model_token_limit(model)` | Get model's token limit |
| `truncate_context_intelligently(chunks_with_scores, max_tokens, question, model)` | Smart truncation preserving high-relevance chunks |
| `track_token_usage(user_id, tokens_used, usage_date)` | Atomic daily usage upsert |
| `get_user_daily_usage(user_id, usage_date)` | Daily token count |
| `get_user_monthly_usage(user_id, year, month)` | Monthly token count |
| `prepare_context_with_token_limit(chunks_with_metadata, query, model, safety_margin)` | Pre-formatted context |

#### `ws_manager.py` — WebSocket Manager (170 lines)

**Class: `ConnectionManager`**
- `MAX_CONNECTIONS_PER_USER = 10`
- `connect_user(user_id, ws)`, `disconnect_user(user_id, ws)`
- `send_to_user(user_id, payload) -> int` — returns number of connections reached
- `broadcast(payload) -> int`
- `user_is_connected(user_id) -> bool`, `stats() -> Dict`

**Global:** `ws_manager = ConnectionManager()`

---

### 12.2 Agent Service

**Directory:** `app/services/agent/` (8 files + subgraphs + tools)

#### State — `agent/state.py`

**Types:**
- `ToolResult(TypedDict)`: `tool_name, success, output, metadata, error, tokens_used, output_summary`
- `AgentState(TypedDict)`: ~30 fields — `user_message, notebook_id, user_id, material_ids, session_id, intent, intent_confidence, plan, current_step, selected_tool, tool_input, tool_results, needs_retry, iterations, response, rag_context, chat_history, workspace_files, generated_files, last_stdout, last_stderr, analysis_context, code_vars, edit_history, step_log, repair_attempts`

**Constants:** `MAX_AGENT_ITERATIONS=7`, `MAX_TOOL_CALLS=10`, `TOKEN_BUDGET=12_000`, `INTENT_MIN_CONFIDENCE=0.6`

**Function:** `compress_tool_result(result) -> ToolResult` — Truncates output to 500 char summary

#### Graph — `agent/graph.py`

LangGraph state machine with 4 nodes:

```
intent_and_plan → tool_router → reflection → response_generator
                       ↑              |
                       └──── retry ────┘
```

| Function | Description |
|----------|-------------|
| `intent_and_plan(state)` | Merged intent + planning node |
| `generate_response(state)` | Final synthesis node |
| `build_agent_graph()` | Builds the LangGraph state graph |
| `get_agent_graph()` | Thread-safe singleton cache |
| `run_agent(state)` | Invoke graph synchronously |
| `run_agent_stream(state)` | SSE streaming async iterator |

**Stream Events:** `start, step, step_done, token, code_stdout, code_written, code_generating, code_generated, repair_attempt, repair_success, meta, done, error`

#### Intent Detection — `agent/intent.py`

High-speed intent detection with keyword rules + LLM fallback.

**Supported Intents:** `QUESTION`, `DATA_ANALYSIS`, `RESEARCH`, `CODE_EXECUTION`, `FILE_GENERATION`, `CONTENT_GENERATION`

**Slash Commands:** Direct intent mapping (e.g., `/code` → `CODE_EXECUTION`)

| Function | Description |
|----------|-------------|
| `_keyword_classify(message)` | Rule-based classification using regex patterns |
| `_llm_classify(message)` | LLM fallback for ambiguous messages |
| `detect_intent(state)` | Combines keyword + LLM classification |

#### Planner — `agent/planner.py`

Dynamic multi-step execution planner based on detected intent.

| Function | Description |
|----------|-------------|
| `plan_execution(state)` | Creates step-by-step plan based on intent and available tools |
| `_check_edit_intent(message, generated_files)` | Detects if user wants to edit existing code |

#### Router — `agent/router.py`

Tool selection and execution with chaining.

| Function | Description |
|----------|-------------|
| `route_and_execute(state)` | Selects and executes the right tool based on current plan step |

**Step Labels:** Emoji-based step labels for SSE streaming UI

#### Reflection — `agent/reflection.py`

Output quality evaluation and safety limits.

**Constants:** `_MAX_STEP_RETRIES=2`, `_MIN_USEFUL_OUTPUT_LEN=50`

| Function | Description |
|----------|-------------|
| `reflect(state)` | Evaluates tool output quality |
| `should_continue(state)` | Returns `"continue"`, `"retry"`, or `"respond"` |

#### Persistence — `agent/persistence.py`

| Function | Description |
|----------|-------------|
| `log_code_execution(user_id, notebook_id, code, stdout, stderr, exit_code, has_chart, elapsed)` | Persists code execution to DB |

#### Tools Registry — `agent/tools_registry.py` (648 lines)

Wraps existing services as agent-callable tools.

| Tool Name | Handler | Intent(s) | Description |
|-----------|---------|-----------|-------------|
| `rag_tool` | RAG retrieval + LLM answer | QUESTION | Retrieves context and generates streaming answer |
| `quiz_tool` | Quiz generation | CONTENT_GENERATION | Generates MCQ quiz |
| `flashcard_tool` | Flashcard generation | CONTENT_GENERATION | Generates flashcards |
| `ppt_tool` | Redirect to Studio | CONTENT_GENERATION | Redirects user to Studio panel for PPT |
| `python_tool` | Code gen + exec | CODE_EXECUTION, DATA_ANALYSIS | Generates and executes Python code with data validation |
| `research_tool` | Deep web research | RESEARCH | Multi-step web research pipeline |

#### Research Subgraph — `agent/subgraphs/research_graph.py`

Deep research engine: DuckDuckGo → content extraction → LLM synthesis.

**Constants:** `MAX_SEARCH_QUERIES=10`, `MAX_TOTAL_URLS=15`, `MAX_TIME_SECONDS=45`

**Pipeline:** Generate queries → Execute searches → Extract content → Cluster sources → Synthesize report

#### Agent Tools

| File | Function | Description |
|------|----------|-------------|
| `tools/code_repair.py` | `repair_code(broken_code, stderr, llm)` | LLM-based code repair |
| `tools/data_profiler.py` | `profile_dataset(state)` | Profiles CSV/Excel datasets (max 50K rows) |
| `tools/file_generator.py` | `generate_file(state, code, stream_cb)` | Executes code that generates files |
| `tools/workspace_builder.py` | `build_workspace_header(state)` | Builds workspace context header for code gen |

---

### 12.3 Auth Service

**Directory:** `app/services/auth/` (3 files)

#### Security — `auth/security.py`

**Global:** `pwd_context = CryptContext(schemes=["bcrypt"])`

| Function | Description |
|----------|-------------|
| `hash_password(password) -> str` | bcrypt hash |
| `verify_password(plain, hashed) -> bool` | bcrypt verify |
| `create_access_token(data, expires_delta) -> str` | JWT access token (HS256) |
| `create_refresh_token(data, family) -> str` | JWT refresh token with family claim |
| `create_file_token(user_id, expires_minutes) -> str` | Short-lived file download token |
| `decode_token(token) -> Optional[dict]` | JWT decode with expiry check |
| `hash_token(token) -> str` | SHA-256 hash for DB storage |

#### Service — `auth/service.py`

| Function | Description |
|----------|-------------|
| `register_user(email, username, password)` | Create new user |
| `authenticate_user(email, password)` | Verify credentials |
| `get_user_by_id(user_id)` | Fetch user by ID |
| `get_current_user(credentials)` | FastAPI dependency — JWT → user lookup |
| `validate_file_token(token)` | Validate file-access token |
| `store_refresh_token(user_id, token, family)` | Store hashed refresh token |
| `validate_and_rotate_refresh_token(token)` | Rotate token, detect replay attacks (revokes entire family) |
| `revoke_user_tokens(user_id)` | Revoke all user's refresh tokens |
| `cleanup_expired_tokens()` | Remove expired tokens |

---

### 12.4 Chat Service

**Directory:** `app/services/chat/` (2 files)

#### Service — `chat/service.py` (621 lines)

| Function | Description |
|----------|-------------|
| `generate_rag_response(notebook_id, user_id, context, user_message, session_id)` | Streaming LLM response with citation validation |
| `compute_confidence_score(context, answer, reranker_scores)` | Computes response confidence (0.0-1.0) |
| `save_conversation(notebook_id, user_id, user_message, assistant_answer, session_id, agent_meta)` | Persist conversation to DB |
| `save_response_blocks(message_id, content)` | Split markdown into blocks and save |
| `log_agent_execution(user_id, notebook_id, meta, elapsed)` | Log agent execution stats |
| `get_chat_history(notebook_id, user_id, session_id)` | Get messages with responseBlocks |
| `clear_chat_history(notebook_id, user_id, session_id)` | Clear messages |
| `get_chat_sessions(notebook_id, user_id)` | List sessions with preview |
| `create_chat_session(notebook_id, user_id, title)` | Create new session |
| `delete_chat_session(session_id, user_id)` | Delete with cascading |
| `block_followup_stream(block_id, action, question)` | Inline block actions: ask, simplify, translate, explain |
| `get_suggestions(partial_input, notebook_id, user_id)` | LLM auto-complete suggestions |

**Internal:** `_split_markdown_blocks(content)` — Markdown-aware block splitter

---

### 12.5 Code Execution Service

**Directory:** `app/services/code_execution/` (5 files)

#### Security — `code_execution/security.py` (220 lines)

**Constants:**
- `_FORBIDDEN_PATTERNS` — ~30 regex patterns (os.system, subprocess, eval, exec, open(/etc), etc.)
- `_ALLOWED_MODULES` — ~25 safe modules (numpy, pandas, matplotlib, etc.)
- `_BLOCKED_MODULES` — ~20 dangerous modules (os, sys, subprocess, socket, etc.)

**Functions:**
| Function | Description |
|----------|-------------|
| `validate_code(code) -> ValidationResult` | Regex + AST validation. Returns `is_safe, violations, warnings` |
| `sanitize_code(code) -> str` | Auto-injects matplotlib chart capture code |

#### Executor — `code_execution/executor.py`

| Function | Description |
|----------|-------------|
| `execute_code(code, work_dir, timeout, on_stdout_line)` | Execute pre-written code in sandbox |
| `generate_and_execute(user_query, csv_files, parquet_files, timeout, on_stdout_line, additional_context, on_code_generated)` | LLM code gen → security check → execute with auto-repair loop (up to `MAX_CODE_REPAIR_ATTEMPTS`) |

#### Sandbox — `code_execution/sandbox.py` (292 lines)

**Constants:** `MAX_EXECUTION_TIME=15`, `MAX_OUTPUT_SIZE=1_000_000`

| Function | Description |
|----------|-------------|
| `run_in_sandbox(code, work_dir, timeout, on_stdout_line)` | Subprocess with rlimits, timeout, output size cap. Returns `ExecutionResult(stdout, stderr, exit_code, timed_out, chart_base64, elapsed_seconds, error)` |

**Security:** Linux rlimits (`RLIMIT_CPU`, `RLIMIT_AS`, `RLIMIT_FSIZE`) via `_preexec_limits()`

#### Sandbox Environment — `code_execution/sandbox_env.py` (207 lines)

**Constants:**
- `PREINSTALLED_PACKAGES` — 17 packages auto-installed at startup
- `SKIP_PACKAGES` — ~100 stdlib modules (never pip-installed)

| Function | Description |
|----------|-------------|
| `install_package_if_missing(pkg) -> bool` | Install via pip if not found |
| `ensure_packages()` | Batch install all preinstalled packages at startup |

---

### 12.6 Explainer Service

**Directory:** `app/services/explainer/` (5 files)

#### Processor — `explainer/processor.py`

**7-Stage Pipeline:**
1. Generate PPT (if needed)
2. Capture slide screenshots (Playwright)
3. Generate narration scripts per slide (LLM)
4. Synthesize TTS audio per slide (edge-tts)
5. Compose per-slide videos (ffmpeg: image + audio → H.264+AAC)
6. Concatenate all slide videos (ffmpeg concat)
7. Finalize and update DB

#### Script Generator — `explainer/script_generator.py`

| Function | Description |
|----------|-------------|
| `generate_slide_scripts_async(slides, narration_language, max_concurrent=3)` | Parallel LLM narration script generation (semaphore-limited) |

**Supported Languages:** 10 (en, hi, gu, es, fr, de, ta, te, mr, bn)

#### TTS — `explainer/tts.py`

| Function | Description |
|----------|-------------|
| `get_voice_id(language, gender)` | Map language+gender → edge-tts voice ID |
| `generate_audio_file(text, voice_id, output_path)` | Generate MP3 |
| `get_audio_duration(filepath)` | Get MP3 duration |

#### Video Composer — `explainer/video_composer.py`

| Function | Description |
|----------|-------------|
| `compose_slide_video(image_path, audio_path, output_path)` | ffmpeg H.264+AAC 1920×1080 per-slide video |
| `concatenate_videos(video_paths, output_path)` | ffmpeg concat demuxer |

---

### 12.7 Flashcard Service

**Directory:** `app/services/flashcard/`

**Function:** `generate_flashcards(material_text, card_count=None, difficulty="Medium", instructions=None) -> dict` — Uses `invoke_structured` with `FlashcardOutput` Pydantic schema

---

### 12.8 LLM Service

**Directory:** `app/services/llm_service/` (4 files)

#### LLM Factory — `llm_service/llm.py`

**Supported Providers:**

| Provider | Class | Key Config |
|----------|-------|------------|
| OLLAMA | `ChatOllama` | `OLLAMA_MODEL`, local server |
| GOOGLE | `ChatGoogleGenerativeAI` | `GOOGLE_MODEL`, `GOOGLE_API_KEY` |
| NVIDIA | `ChatNVIDIA` | `NVIDIA_MODEL`, `NVIDIA_API_KEY` |
| MYOPENLM | `MyOpenLM` (custom) | `MYOPENLM_API_URL`, `MYOPENLM_MODEL` |

**Instance Caching:** LRU cache (max 16 entries) keyed on `(provider, model, temperature, top_p, max_tokens)`

**Temperature Tiers:**
- `structured` → 0.1
- `chat` → 0.2
- `creative` → 0.7
- `code` → 0.1

| Function | Description |
|----------|-------------|
| `get_llm(temperature, top_p, max_tokens, provider, mode, **kwargs)` | Get cached LLM instance for general use |
| `get_llm_structured(temperature, top_p, max_tokens, provider, **kwargs)` | Get LLM instance optimized for structured output |

**MyOpenLM:** Custom LangChain `LLM` wrapper — REST API with retry logic (`_RETRYABLE_CODES = {429, 500, 502, 503, 504}`, `_MAX_RETRIES = 3`, exponential backoff)

#### Schemas — `llm_service/llm_schemas.py`

| Schema | Fields | Purpose |
|--------|--------|---------|
| `QuizQuestion` | question, options, correct_answer, explanation | Single quiz question |
| `QuizOutput` | title, questions | Full quiz (drops incomplete questions via validator) |
| `Flashcard` | question, answer | Single flashcard |
| `FlashcardOutput` | title, flashcards | Full flashcard set |
| `PresentationHTMLOutput` | title, slide_count, theme, html | HTML presentation (auto-repairs unclosed HTML) |

#### Structured Invoker — `llm_service/structured_invoker.py` (387 lines)

**JSON Parsing Pipeline (5-tier):**
1. Direct `json.loads`
2. Clean markdown fences/tags → parse
3. Extract first `{...}` or `[...]` block → parse
4. Repair quotes/commas/escaping → parse
5. `json_repair` library as last resort

| Function | Description |
|----------|-------------|
| `parse_json_robust(text) -> dict` | 5-tier JSON parsing |
| `invoke_structured(prompt, schema, max_retries=2, timeout=None) -> T` | LLM → parse → validate Pydantic → retry |
| `invoke_structured_safe(prompt, schema, ...) -> Dict` | Safe wrapper returning `{success, data}` or `{success, error}` |
| `async_invoke_structured(prompt, schema, ...) -> T` | Async version |
| `async_invoke_structured_safe(prompt, schema, ...) -> Dict` | Async safe version |

---

### 12.9 Mind Map Service

**Directory:** `app/services/mindmap/`

| Function | Description |
|----------|-------------|
| `generate_mindmap_sync(combined_text)` | Synchronous LLM-based generation (runs in executor) |
| `generate_mindmap(material_ids, notebook_id, user_id)` | Full pipeline: collect text → LLM → post-process `has_children` → upsert `GeneratedContent` |

---

### 12.10 Podcast Service

**Directory:** `app/services/podcast/` (8 files)

#### Session Manager — `podcast/session_manager.py` (450 lines)

| Function | Description |
|----------|-------------|
| `create_session(user_id, notebook_id, mode, topic, language, host_voice, guest_voice, material_ids)` | Create podcast session record |
| `get_session(session_id, user_id)` | Full session with segments, doubts, bookmarks, annotations |
| `start_generation(session_id, user_id)` | Launch background pipeline: Script → parallel TTS → ready |
| `delete_session(session_id, user_id)` | Delete files + DB cascade |

**Generation Pipeline:** `_generation_pipeline` → Script generation → Parallel TTS synthesis (streaming callbacks) → Status: ready

#### Script Generator — `podcast/script_generator.py` (260 lines)

**6 Modes:**
| Mode | Description |
|------|-------------|
| `overview` | Broad material summary |
| `deep-dive` | Detailed deep analysis |
| `debate` | Opposing viewpoints |
| `q-and-a` | Question and answer format |
| `full` | Complete comprehensive coverage |
| `topic` | User-specified topic focus |

**Pipeline:** Mode-specific RAG queries → Parallel context gathering → LLM script generation → JSON output `{segments, chapters, title}`

#### TTS Service — `podcast/tts_service.py` (270 lines)

**Constants:** `_TTS_CONCURRENCY = 15`, `_TTS_MAX_RETRIES = 3`

| Function | Description |
|----------|-------------|
| `synthesize_all_segments(session_id, segments, host_voice, guest_voice, on_progress, on_segment_ready)` | Concurrent TTS with semaphore (15 parallel) + streaming callbacks |
| `synthesize_single(session_id, text, voice_id, filename)` | Single segment TTS (for Q&A answers) |
| `generate_voice_preview(voice_id, text)` | Raw MP3 bytes for voice preview |

#### Voice Map — `podcast/voice_map.py`

**10 Supported Languages:** English, Hindi, Gujarati, Spanish, French, German, Tamil, Telugu, Marathi, Bengali

Each language has 2-4 voices with `id, name, gender, description`.

#### Q&A Service — `podcast/qa_service.py`

| Function | Description |
|----------|-------------|
| `handle_question(session_id, user_id, question_text, paused_at_segment, question_audio_url)` | RAG → LLM answer → TTS → persist doubt |
| `get_doubts(session_id, user_id)` | List Q&A history |

#### Satisfaction Detector — `podcast/satisfaction_detector.py`

Two-layer detection (heuristic + LLM) for auto-resuming after Q&A.

**Supported Languages:** 10 languages with ~26 satisfaction phrases each

| Function | Description |
|----------|-------------|
| `detect_satisfaction(message, language)` | Returns `("auto_resume"/"stay"/"prompt", confidence)` |

#### Export Service — `podcast/export_service.py`

| Function | Description |
|----------|-------------|
| `create_export(session_id, user_id, format)` | Start background export (PDF or JSON) |
| `generate_summary(session_id, user_id)` | LLM-generated session summary |

**PDF Export:** fpdf2 with NotoSans Unicode font support, styled chapter headers, segment transcript, Q&A section

---

### 12.11 Presentation (PPT) Service

**Directory:** `app/services/ppt/` (4 files)

#### Generator — `ppt/generator.py`

| Function | Description |
|----------|-------------|
| `generate_presentation(material_text, user_id, *, max_slides, theme, additional_instructions)` | Single-prompt HTML presentation generation. Returns `{title, slide_count, theme, html, slides, presentation_id}` |
| `_post_process_html(html)` | DOCTYPE injection, viewport meta, safety CSS (16:9 locked), script removal, vh fix |

#### Screenshot — `ppt/screenshot_service.py`

**Class: `ScreenshotService`**

| Method | Description |
|--------|-------------|
| `capture_slides(html_content, user_id, presentation_id, slide_count)` | Playwright-based 16:9 screenshots (1920×1080). Clip-based or scroll-based capture fallback |

#### Slide Extractor — `ppt/slide_extractor.py`

| Function | Description |
|----------|-------------|
| `extract_slides(html_content)` | Extract per-slide standalone HTML documents from full presentation |
| `count_slides(html_content)` | Fast slide count (regex fallback) |

---

### 12.12 Quiz Service

**Directory:** `app/services/quiz/`

**Function:** `generate_quiz(material_text, mcq_count=None, difficulty="Medium", instructions=None) -> dict` — Uses `invoke_structured` with `QuizOutput` Pydantic schema

---

### 12.13 RAG Service

**Directory:** `app/services/rag/` (7 files)

#### Embedder — `rag/embedder.py`

| Function | Description |
|----------|-------------|
| `warm_up_embeddings()` | Preload ONNX embedding model at startup |
| `embed_and_store(chunks, material_id, user_id, notebook_id, filename)` | UPSERT batches (200 per batch, 3 retries) with per-chunk section metadata |
| `delete_material_embeddings(material_id, user_id)` | Delete embeddings for material |

#### Reranker — `rag/reranker.py`

Thread-safe singleton cross-encoder reranker.

| Function | Description |
|----------|-------------|
| `get_reranker()` | Auto-selects smaller model on CPU. Double-checked locking |
| `rerank_chunks(query, chunks, top_k)` | `torch.inference_mode()` + autocast. OOM fallback |

#### Secure Retriever — `rag/secure_retriever.py` (895 lines)

**The ONLY sanctioned entry point for similarity search.** Enforces tenant isolation at every level.

| Function | Description |
|----------|-------------|
| `secure_similarity_search(user_id, query, k, *, material_id, material_ids, notebook_id)` | Basic retrieval with 3-layer security |
| `secure_similarity_search_enhanced(user_id, query, *, ...)` | Full pipeline: multi-source balance → MMR → reranking → structured expansion → citation formatting |
| `_validate_result_ownership(user_id, documents, metadatas, ...)` | **CRITICAL SECURITY** — removes cross-tenant data leaks in-place |

**Pipeline:**
1. Per-material retrieval with balanced representation
2. Max Marginal Relevance (MMR) for diversity
3. Cross-encoder reranking for relevance
4. Structured chunk expansion (CSV/Excel → full data up to 50K chars)
5. Citation formatting with metadata headers
6. Tenant ownership validation

#### Context Builder — `rag/context_builder.py`

| Function | Description |
|----------|-------------|
| `build_context(chunks, max_tokens)` | Filter low-quality → summarize long chunks → format with `---- SOURCE N ----` headers |

#### Context Formatter — `rag/context_formatter.py`

| Function | Description |
|----------|-------------|
| `format_context_with_citations(chunks, max_sources)` | Rich headers with Source/Section/Chunk ID/Confidence |

**Material name cache:** `OrderedDict` LRU cache (max 2000 entries)

#### Citation Validator — `rag/citation_validator.py`

| Function | Description |
|----------|-------------|
| `validate_citations(response, num_sources, strict=True)` | Strict citation enforcement in LLM responses |
| `check_citation_coverage(cited_sources, num_sources, min_coverage=0.5)` | Verify sufficient source coverage |

---

### 12.14 Text Processing Service

**Directory:** `app/services/text_processing/` (11 files)

#### Chunker — `text_processing/chunker.py` (440 lines)

Structure-aware text chunker for RAG ingestion.

**Constants:**
- `TARGET_CHUNK_TOKENS = 500`, `TARGET_CHUNK_CHARS = 2000`
- `OVERLAP_TOKENS` (from settings), `OVERLAP_CHARS = 600`
- `MIN_ALPHA_RATIO = 0.10` (quality filter)

| Function | Description |
|----------|-------------|
| `chunk_text(text, use_semantic_chunking=False, source_type="prose")` | Routes to structured or markdown/prose path. Returns `[{id, text, section_title, chunk_index, total_chunks}]` |

**Internal paths:** `_chunk_structured()` (CSV/Excel), `_has_markdown_headings()`, `_split_on_headings()`, `_process_section()`, `_split_sentences()`, `_split_semantic()`, `_filter_quality()`

#### Extractor — `text_processing/extractor.py` (728 lines)

Unified text extraction from any source type.

**Registered extractors (via `@_register` decorator):**

| Extension(s) | Extractor | Technology |
|--------------|-----------|------------|
| `pdf` | `_extract_pdf` | PyMuPDF + PDFPlumber tables + OCR fallback |
| `docx`, `doc` | `_extract_word` | unstructured primary, python-docx fallback |
| `pptx`, `ppt` | `_extract_pptx` | unstructured primary, python-pptx fallback |
| `xlsx`, `xls`, `ods` | `_extract_spreadsheet` | pandas + parquet side-car |
| `csv` | `_extract_csv` | pandas + parquet side-car |
| `txt`, `md` | `_extract_text_file` | chardet encoding detection |
| `html`, `htm` | `_extract_html` | unstructured primary, BeautifulSoup fallback |
| `rtf` | `_extract_rtf` | striprtf, raw decode fallback |
| `epub` | `_extract_epub` | ebooklib, zip fallback |
| `odt`, `odp` | `_extract_odt` | odfpy, zip fallback |
| `eml` | `_extract_eml` | Python stdlib email |
| `msg` | `_extract_msg` | extract-msg library |

**Class: `EnhancedTextExtractor`** — Routes to file/URL/YouTube extraction

#### File Type Detector — `text_processing/file_detector.py`

**Class: `FileTypeDetector`** — Content sniffing (python-magic) + extension fallback. Supports ~50 MIME types across documents, images, audio, video, email.

#### OCR Service — `text_processing/ocr_service.py` (596 lines)

EasyOCR-primary OCR with structured Markdown output.

**Class: `OCRService`**
- `PDF_DPI = 200`, image upscaling for small images
- Preprocessing: grayscale → upscale → Otsu binarization → median denoise
- Line grouping: adaptive y-clustering → Markdown with heading detection
- Parallel PDF rendering (ThreadPoolExecutor, max 8 workers)
- Tesseract fallback when `USE_TESSERACT=1`

#### PDF Extractor — `text_processing/pdf_extractor.py` (370 lines)

Layout-aware PDF text extraction.

**Class: `PDFExtractor`**
- Digital text extraction via PyMuPDF block API
- Font-weighted heading classification
- PDFPlumber table extraction → Markdown tables
- Header/footer deduplication
- Equation detection (Unicode math symbols)

#### Transcription Service — `text_processing/transcription_service.py` (270 lines)

**Class: `AudioTranscriptionService`**
- OpenAI Whisper `base` model
- CUDA auto-detect
- ffmpeg video → audio extraction
- Word-level timestamps support
- Confidence estimation via word-rate heuristic

#### Web Scraping — `text_processing/web_scraping.py` (406 lines)

**Class: `WebScrapingService`**
- 3-tier scraping: requests → BeautifulSoup → Selenium (headless Chrome with anti-detection)
- Auto Selenium escalation on 403/429/5xx responses
- Exponential backoff retry (3 attempts)
- Streaming download with 100MB size cap
- SSRF protection via URL validation

#### YouTube Service — `text_processing/youtube_service.py` (260 lines)

**Class: `YouTubeService`**
- Transcript extraction: manual → generated → any language fallback
- Video metadata via yt-dlp
- Multi-pattern URL parsing (youtube.com, youtu.be, shorts, etc.)
- Transcript cleaning (removes [Music], (inaudible), etc.)

#### Table Extractor — `text_processing/table_extractor.py` (330 lines)

**Class: `TableExtractor`** — Advanced PDF table extraction → Markdown formatting, structure detection, adjacent table merging

#### Resilient Runner — `text_processing/resilient_runner.py`

| Function | Description |
|----------|-------------|
| `run_with_timeout(fn, timeout, *, task_name)` | Thread-based hard timeout |
| `run_with_retry(fn, timeout, *, max_retries=2, task_name, backoff_base=1.0)` | Exponential backoff retry wrapper |

---

## 13. Background Worker

**File:** `app/services/worker.py` (346 lines)

**Constants:**
- `_POLL_SECONDS = 2.0` — Polling interval
- `_ERROR_BACKOFF = 5.0` — Backoff on errors
- `MAX_CONCURRENT_JOBS = 5` — Max parallel jobs
- `_STUCK_JOB_TIMEOUT_MINUTES = 30` — Stuck job recovery timeout
- `_SHUTDOWN_TIMEOUT = 30.0` — Graceful shutdown wait time

**Architecture:** Event-driven notification + polling fallback

| Component | Description |
|-----------|-------------|
| `_JobQueue` | Event-driven job notification with `notify()` and `wait(timeout)` |
| `job_processor()` | Main event loop — concurrent processing up to MAX_CONCURRENT_JOBS |
| `_process_job(job)` | Dispatches to file/URL/text processing based on job type |
| `_recover_stuck_jobs()` | Resets stuck `processing` jobs to `pending` on startup |
| `_maybe_rename_notebook(notebook_id, material_id)` | LLM-based notebook auto-rename after first material |
| `graceful_shutdown()` | Signals worker to stop and waits for inflight jobs |

---

## 14. CLI Tools

**Directory:** `cli/`

| File | Description |
|------|-------------|
| `backup_chroma.py` | Backup ChromaDB to timestamped directory |
| `export_embeddings.py` | Export ChromaDB embeddings to external format |
| `import_embeddings.py` | Import embeddings into ChromaDB |
| `reindex.py` | Re-index all materials in ChromaDB |

---

## 15. Data Directories

| Directory | Contents |
|-----------|----------|
| `data/chroma/` | ChromaDB persistent storage (SQLite + segment files) |
| `data/material_text/` | Extracted text files (one per material, UUID-named) |
| `data/models/` | Downloaded AI models (sentence-transformers, reranker) |
| `data/uploads/` | User uploaded files (UUID-named) |
| `data/output/` | Legacy output directory |
| `output/explainers/` | Explainer video MP4 files + slide images + audio |
| `output/generated/` | Agent-generated files (per user/session) |
| `output/html/` | HTML presentation files |
| `output/podcast/` | Podcast session audio (MP3 segments + Q&A answers) |
| `output/presentations/` | Slide screenshot PNGs |
| `output/yt_translation/` | YouTube translation output |

---

## 16. Requirements

### Core Framework
- FastAPI 0.115.6, Uvicorn 0.30.6, Pydantic 2.9.2, pydantic-settings

### LLM / AI Chain
- LangChain 0.2.16, langchain-text-splitters, langchain-google-genai, langchain-nvidia-ai-endpoints, langchain-ollama, langchain-huggingface, langgraph ≥0.2.0

### ML / Embeddings
- numpy 1.26.4, sentence-transformers 3.1.1, huggingface_hub 0.24.6, tiktoken 0.7.0, torch, torchvision, torchaudio, transformers

### Vector Database
- chromadb 0.5.5

### Document Processing
- pypdf, pymupdf, pdfplumber, pdf2image, python-pptx, pillow, python-docx, openpyxl, xlrd

### OCR
- pytesseract, easyocr

### Audio / Video
- openai-whisper, ffmpeg-python, pydub, edge-tts, mutagen, fpdf2, TTS, soundfile

### Web / Scraping
- beautifulsoup4, selenium, webdriver-manager, youtube-transcript-api, yt-dlp, playwright, httpx, requests, fake-useragent, trafilatura

### Database
- SQLAlchemy[asyncio], asyncpg, prisma 0.15.0, redis

### Auth
- python-jose[cryptography]

### Other
- python-magic, chardet, json_repair, pyarrow

### Testing
- pytest, pytest-asyncio

---

> **Total Backend:** ~78 Python source files across 16 service subdirectories, 18 route endpoints, 21 database models, 10 prompt templates, and comprehensive security/performance middleware.
