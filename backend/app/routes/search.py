from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import httpx
import logging
from app.services.auth import get_current_user
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

class WebSearchRequest(BaseModel):
    query: str
    file_type: Optional[str] = None
    engine: str = "duckduckgo"

class SearchResult(BaseModel):
    title: str
    link: str
    snippet: str

@router.post("/web", response_model=List[SearchResult])
async def search_web(
    request: WebSearchRequest,
    current_user=Depends(get_current_user),
):
    """Bridge to the external search service."""
    query = request.query
    if request.file_type:
        query = f"{query} filetype:{request.file_type}"

    logger.info(f"[SEARCH] Query='{query}' user={current_user.id}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.SEARCH_SERVICE_URL}/api/search",
                json={
                    "query": query,
                    "engine": request.engine
                }
            )
            response.raise_for_status()
            data = response.json()
            
            # The external API returns a dictionary with 'organic_results' which is a list
            # of dictionaries with 'title', 'link', 'snippet'
            results = data.get("organic_results", [])
            if not isinstance(results, list):
                logger.error(f"Unexpected results format from search service: {type(results)}")
                results = []

            # We wrap it in our response model
            return [
                SearchResult(
                    title=res.get("title", "No Title"),
                    link=res.get("link", ""),
                    snippet=res.get("snippet", "No description available.")
                )
                for res in results
            ]
    except httpx.HTTPStatusError as e:
        logger.error(f"Search service returned error: {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=502, detail="External search service error")
    except Exception as e:
        logger.exception("Web search failed")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
