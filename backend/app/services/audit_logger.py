"""API usage audit logging.

Logs API requests for monitoring, debugging, and future billing.

Logged fields:
- user_id
- endpoint
- material_ids
- token counts
- model used
- latencies (LLM, retrieval, total)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

from app.db.prisma_client import prisma

logger = logging.getLogger(__name__)


async def log_api_usage(
    user_id: str,
    endpoint: str,
    material_ids: Optional[List[str]] = None,
    context_token_count: int = 0,
    response_token_count: int = 0,
    model_used: str = "unknown",
    llm_latency: float = 0.0,
    retrieval_latency: float = 0.0,
    total_latency: float = 0.0,
) -> None:
    """Log API usage to database.
    
    Args:
        user_id: User identifier
        endpoint: API endpoint path
        material_ids: List of material IDs accessed
        context_token_count: Tokens in context
        response_token_count: Tokens in response
        model_used: LLM model name
        llm_latency: LLM generation time (seconds)
        retrieval_latency: Retrieval time (seconds)
        total_latency: Total request time (seconds)
    """
    if not user_id:
        logger.warning("Cannot log API usage without user_id")
        return
    
    try:
        await prisma.apiusagelog.create(
            data={
                "userId": user_id,
                "endpoint": endpoint,
                "materialIds": material_ids or [],
                "contextTokenCount": context_token_count,
                "responseTokenCount": response_token_count,
                "modelUsed": model_used,
                "llmLatency": llm_latency,
                "retrievalLatency": retrieval_latency,
                "totalLatency": total_latency,
            }
        )
        
        logger.debug(
            f"API usage logged: user={user_id}, endpoint={endpoint}, "
            f"tokens={context_token_count + response_token_count}"
        )
        
    except Exception as e:
        logger.error(f"Failed to log API usage: {e}")
        # Don't raise - logging is non-critical


async def get_user_api_usage(
    user_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100
) -> list:
    """Get user's API usage history.
    
    Args:
        user_id: User identifier
        start_date: Start date filter
        end_date: End date filter
        limit: Maximum records to return
    
    Returns:
        List of usage records
    """
    try:
        where = {"userId": user_id}
        
        if start_date or end_date:
            where["createdAt"] = {}
            if start_date:
                where["createdAt"]["gte"] = start_date
            if end_date:
                where["createdAt"]["lte"] = end_date
        
        records = await prisma.apiusagelog.find_many(
            where=where,
            order={"createdAt": "desc"},
            take=limit,
        )
        
        return records
        
    except Exception as e:
        logger.error(f"Failed to get API usage: {e}")
        return []


async def get_usage_statistics(
    user_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> dict:
    """Get usage statistics.
    
    Args:
        user_id: Optional user filter
        start_date: Start date filter
        end_date: End date filter
    
    Returns:
        Dict with statistics
    """
    try:
        # Use aggregation via raw SQL instead of loading all records into memory
        # to prevent OOM on large datasets
        where_clauses = []
        params = []
        param_idx = 1
        
        if user_id:
            where_clauses.append(f'"userId" = ${param_idx}')
            params.append(user_id)
            param_idx += 1
        if start_date:
            where_clauses.append(f'"createdAt" >= ${param_idx}')
            params.append(start_date)
            param_idx += 1
        if end_date:
            where_clauses.append(f'"createdAt" <= ${param_idx}')
            params.append(end_date)
            param_idx += 1
        
        where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        
        result = await prisma.query_raw(
            f'SELECT COUNT(*) as total_requests, '
            f'COALESCE(SUM("contextTokenCount" + "responseTokenCount"), 0) as total_tokens, '
            f'COALESCE(AVG("llmLatency"), 0) as avg_llm_latency, '
            f'COALESCE(AVG("retrievalLatency"), 0) as avg_retrieval_latency, '
            f'COALESCE(AVG("totalLatency"), 0) as avg_total_latency '
            f'FROM "ApiUsageLog"{where_sql}',
            *params,
        )
        
        if not result:
            return {
                "total_requests": 0,
                "total_tokens": 0,
                "avg_llm_latency": 0.0,
                "avg_retrieval_latency": 0.0,
                "avg_total_latency": 0.0,
            }
        
        row = result[0]
        return {
            "total_requests": int(row.get("total_requests", 0)),
            "total_tokens": int(row.get("total_tokens", 0)),
            "avg_llm_latency": float(row.get("avg_llm_latency", 0)),
            "avg_retrieval_latency": float(row.get("avg_retrieval_latency", 0)),
            "avg_total_latency": float(row.get("avg_total_latency", 0)),
        }
        
    except Exception as e:
        logger.error(f"Failed to get usage statistics: {e}")
        return {
            "total_requests": 0,
            "total_tokens": 0,
            "error": str(e),
        }
