"""FastAPI application entry point."""

from __future__ import annotations

import asyncio
import logging
import logging.handlers
import os
import sys
import time
from contextlib import asynccontextmanager

# ── Logging configuration (done once, before any app imports) ─

_LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(_LOG_DIR, exist_ok=True)

_fmt = logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
_stream_handler = logging.StreamHandler(sys.stdout)
_stream_handler.setFormatter(_fmt)
_file_handler = logging.handlers.RotatingFileHandler(
    os.path.join(_LOG_DIR, "app.log"), maxBytes=10 * 1024 * 1024, backupCount=3
)
_file_handler.setFormatter(_fmt)

logging.basicConfig(level=logging.INFO, handlers=[_stream_handler, _file_handler])
# Quieten noisy third-party loggers
for _noisy in ("httpx", "httpcore", "uvicorn.access"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.db.prisma_client import connect_db, disconnect_db

from app.routes.auth import router as auth_router
from app.routes.notebook import router as notebook_router
from app.routes.upload import router as upload_router
from app.routes.podcast_router import router as podcast_router
from app.routes.flashcard import router as flashcard_router
from app.routes.quiz import router as quiz_router
from app.routes.chat import router as chat_router
from app.routes.models import router as models_router
from app.routes.jobs import router as jobs_router
from app.routes.ppt import router as ppt_router
from app.routes.health import router as health_router
from app.routes.agent import router as agent_router
from app.routes.websocket_router import router as ws_router
from app.routes.search import router as search_router
from app.routes.proxy import router as proxy_router

from app.services.rate_limiter import rate_limit_middleware
from app.services.performance_logger import performance_monitoring_middleware

logger = logging.getLogger("main")

# Module-level task reference — keeps the job_processor alive (prevents GC)
_job_processor_task: asyncio.Task | None = None


# ── Lifespan ──────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _job_processor_task

    # 1. Connect to Prisma / PostgreSQL
    await connect_db()

    # 2. Warm up the embedding model AND reranker in a thread-pool executor so
    #    the first request does not stall for model-load time.
    #    Both calls are blocking/CPU-bound — must NOT run on the event loop.
    loop = asyncio.get_event_loop()
    try:
        from app.services.rag.embedder import warm_up_embeddings
        logger.info("Warming up embedding model (running in thread pool)…")
        await loop.run_in_executor(None, warm_up_embeddings)
    except Exception as exc:
        logger.warning("Embedding warm-up failed (non-fatal, will retry on first use): %s", exc)

    try:
        from app.services.rag.reranker import _get_reranker
        logger.info("Preloading reranker model (running in thread pool)…")
        await loop.run_in_executor(None, _get_reranker)
        logger.info("Reranker preloaded.")
    except Exception as exc:
        logger.warning("Reranker preload failed (non-fatal, will load on first use): %s", exc)

    # 3. Start the background document processing worker
    from app.services.worker import job_processor
    _job_processor_task = asyncio.create_task(job_processor(), name="job_processor")
    logger.info("Background job processor task created.")

    yield

    # ── Shutdown ──────────────────────────────────────────
    if _job_processor_task and not _job_processor_task.done():
        _job_processor_task.cancel()
        try:
            await _job_processor_task
        except asyncio.CancelledError:
            pass
        logger.info("Background job processor stopped.")

    await disconnect_db()


# ── App ───────────────────────────────────────────────────


app = FastAPI(lifespan=lifespan, title="Study Assistant API", version="2.0.0")


# ── Middleware ────────────────────────────────────────────

# Performance monitoring (first to capture full request time)
app.middleware("http")(performance_monitoring_middleware)

# Rate limiting (before request processing)
app.middleware("http")(rate_limit_middleware)


@app.middleware("http")
async def log_requests(request, call_next):
    start = time.time()
    try:
        response = await call_next(request)
        dt = time.time() - start
        logger.info(f"{request.method} {request.url.path} {response.status_code} {dt:.2f}s")
        return response
    except Exception as e:
        dt = time.time() - start
        logger.error(f"{request.method} {request.url.path} ERROR {type(e).__name__} {dt:.2f}s")
        raise


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# ── Error handlers ────────────────────────────────────────
# CORSMiddleware doesn't add headers to error responses, so we must.


def _cors_headers(origin: str | None = None) -> dict:
    allowed = origin if origin in settings.CORS_ORIGINS else (settings.CORS_ORIGINS[0] if settings.CORS_ORIGINS else "*")
    return {
        "Access-Control-Allow-Origin": allowed,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "*",
        "Access-Control-Allow-Headers": "*",
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=_cors_headers(request.headers.get("origin")),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.exception(f"Unhandled: {type(exc).__name__}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
        headers=_cors_headers(request.headers.get("origin")),
    )


# ── Routes ────────────────────────────────────────────────

# Public
app.include_router(health_router, tags=["health"])
app.include_router(auth_router, tags=["auth"])
app.include_router(models_router, tags=["models"])

# Protected
app.include_router(notebook_router, tags=["notebooks"])
app.include_router(upload_router, tags=["upload"])
app.include_router(podcast_router, tags=["podcast"])
app.include_router(flashcard_router, tags=["flashcard"])
app.include_router(quiz_router, tags=["quiz"])
app.include_router(chat_router, tags=["chat"])
app.include_router(jobs_router, tags=["jobs"])
app.include_router(ppt_router, tags=["presentation"])
app.include_router(agent_router, tags=["agent"])
app.include_router(search_router, prefix="/search", tags=["search"])
app.include_router(proxy_router, prefix="/api/v1", tags=["proxy"])

# WebSocket channels (no REST replacement — live state push only)
app.include_router(ws_router)
