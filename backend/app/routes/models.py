"""Models API — status and reload of required AI models."""

from fastapi import APIRouter, Depends
from app.services.model_manager import model_manager
from app.services.auth import get_current_user

router = APIRouter(prefix="/models", tags=["models"])


@router.get("/status")
async def get_models_status(current_user=Depends(get_current_user)):
    """Get status of all required models (requires authentication)."""
    info = model_manager.get_model_info()
    status_map = {}
    for model_id, cfg in info["required_models"].items():
        name = cfg["name"]
        available = model_manager._is_model_cached(name)
        status_map[model_id] = {
            "name": name,
            "type": cfg["type"],
            "required": cfg["required"],
            "available": available,
            "status": "ready" if available else "missing",
        }

    return {
        "models_directory": info["models_directory"],
        "cache_size": info["cache_size"],
        "models": status_map,
        "summary": {
            "total": len(status_map),
            "ready": sum(1 for m in status_map.values() if m["available"]),
            "missing": sum(1 for m in status_map.values() if not m["available"]),
        },
    }


@router.post("/reload")
async def reload_models(current_user=Depends(get_current_user)):
    """Reload and revalidate all models. Requires admin role."""
    if getattr(current_user, 'role', None) != 'ADMIN':
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Admin access required")
    results = await model_manager.validate_and_load_models()
    return {
        "message": "Model reload completed",
        "results": results,
        "success": all(results.values()),
    }