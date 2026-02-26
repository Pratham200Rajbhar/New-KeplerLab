"""Health check endpoint.

Checks system component availability:
- PostgreSQL database
- ChromaDB vector store
- LLM provider
"""

from __future__ import annotations

import logging
from fastapi import APIRouter
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint - verify all system components.
    
    Returns:
        JSON with status of each component
    """
    health_status = {
        "database": "unknown",
        "vector_db": "unknown",
        "llm": "unknown",
        "overall": "unknown",
    }
    
    # Check PostgreSQL
    try:
        from app.db.prisma_client import prisma
        # Simple query to test connection
        await prisma.user.count()
        health_status["database"] = "ok"
        logger.debug("Database health check: OK")
    except Exception as e:
        health_status["database"] = "error"
        logger.error(f"Database health check failed: {e}")
    
    # Check ChromaDB
    try:
        from app.db.chroma import get_collection
        collection = get_collection()
        # Test with a simple count operation
        collection.count()
        health_status["vector_db"] = "ok"
        logger.debug("Vector DB health check: OK")
    except Exception as e:
        health_status["vector_db"] = "error"
        logger.error(f"Vector DB health check failed: {e}")
    
    # Check LLM (lightweight test)
    try:
        from app.services.llm_service.llm import get_llm
        from app.core.config import settings
        
        # Just check if we can instantiate the LLM
        llm = get_llm()
        
        # For remote APIs, we can't really test without making a call
        # So we just check if configuration is valid
        if settings.LLM_PROVIDER in ["GOOGLE", "NVIDIA"]:
            if settings.LLM_PROVIDER == "GOOGLE" and settings.GOOGLE_API_KEY:
                health_status["llm"] = "ok"
            elif settings.LLM_PROVIDER == "NVIDIA" and settings.NVIDIA_API_KEY:
                health_status["llm"] = "ok"
            else:
                health_status["llm"] = "warning"
        else:
            # For local providers (Ollama), assume OK if instantiated
            health_status["llm"] = "ok"
        
        logger.debug("LLM health check: OK")
    except Exception as e:
        health_status["llm"] = "error"
        logger.error(f"LLM health check failed: {e}")
    
    # Determine overall status
    if all(v == "ok" for v in [health_status["database"], health_status["vector_db"], health_status["llm"]]):
        health_status["overall"] = "healthy"
        status_code = 200
    elif any(v == "error" for v in [health_status["database"], health_status["vector_db"]]):
        health_status["overall"] = "unhealthy"
        status_code = 503
    else:
        health_status["overall"] = "degraded"
        status_code = 200

    # Add storage stats
    try:
        from app.services.storage_service import get_storage_stats
        from app.db.chroma import get_collection_stats
        health_status["storage"] = get_storage_stats()
        health_status["chroma_stats"] = get_collection_stats()
    except Exception as e:
        logger.debug("Storage stats unavailable: %s", e)
    
    return JSONResponse(
        content=health_status,
        status_code=status_code
    )


@router.get("/health/simple")
async def simple_health_check():
    """Simple health check - just returns 200 OK.
    
    For basic uptime monitoring without component checks.
    """
    return {"status": "ok"}
