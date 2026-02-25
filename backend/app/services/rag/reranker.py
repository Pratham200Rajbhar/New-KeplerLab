"""Cross-encoder reranker for semantic relevance scoring.

After initial vector retrieval, this module applies a cross-encoder model
to compute precise relevance scores between query and retrieved chunks.

Optimized for performance:
- Batch scoring for multiple chunks
- torch.inference_mode() for faster inference
- Automatic model selection based on GPU availability
- Half-precision support for GPU
"""

from __future__ import annotations

import logging
import time
from typing import List, Tuple, Optional
import torch

from app.core.config import settings

logger = logging.getLogger(__name__)

# Lazy-loaded singleton
_reranker = None

# Performance constants - optimized for memory efficiency
_USE_HALF_PRECISION = True  # Enable FP16 on GPU
_RERANKER_BATCH_SIZE = 16   # Reduced batch size to prevent OOM errors


def _get_reranker():
    """Load and cache the reranker model (singleton).
    
    Optimizations:
    - Auto model selection (base for CPU, large for GPU)
    - Half-precision support for GPU
    - Model caching
    """
    global _reranker
    if _reranker is None:
        try:
            from sentence_transformers import CrossEncoder
            
            start_time = time.time()
            
            # Determine device with memory optimization
            device = "cuda" if torch.cuda.is_available() else "cpu"
            
            # Clear GPU cache before loading
            if device == "cuda":
                torch.cuda.empty_cache()
            
            # Use smaller model if no GPU available (performance optimization)
            model_name = settings.RERANKER_MODEL
            if device == "cpu" and "large" in model_name:
                model_name = "BAAI/bge-reranker-base"
                logger.info("No GPU detected, using bge-reranker-base instead of large")
            
            logger.info(f"Loading reranker: {model_name} on {device}")
            
            # Load model with memory optimization
            _reranker = CrossEncoder(
                model_name, 
                device=device, 
                max_length=256,  # Reduced from 512 to save memory
                trust_remote_code=True
            )
            
            # Enable half precision for GPU with better error handling
            if device == "cuda" and _USE_HALF_PRECISION:
                try:
                    _reranker.model.half()
                    logger.info("Enabled half-precision (FP16) for reranker")
                except Exception as e:
                    logger.warning(f"Could not enable half-precision: {e}")
            
            load_time = time.time() - start_time
            logger.info(f"Reranker loaded successfully in {load_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Failed to load reranker: {e}")
            _reranker = None
    
    return _reranker


def rerank_chunks(
    query: str,
    chunks: List[str],
    top_k: Optional[int] = None,
) -> List[Tuple[str, float]]:
    """Rerank chunks using cross-encoder model with torch optimization.
    
    Optimizations:
    - Batch scoring (_RERANKER_BATCH_SIZE chunks at a time)
    - torch.inference_mode() for faster inference
    - Performance logging
    
    Args:
        query: User query text
        chunks: List of text chunks to rerank
        top_k: Number of top results to return (None = return all)
    
    Returns:
        List of (chunk, score) tuples sorted by relevance (descending)
    """
    if not chunks:
        return []
    
    # Fallback if reranker disabled or unavailable
    if not settings.USE_RERANKER:
        logger.debug("Reranker disabled, returning chunks as-is")
        return [(c, 1.0) for c in chunks[:top_k]] if top_k else [(c, 1.0) for c in chunks]
    
    reranker = _get_reranker()
    if reranker is None:
        logger.warning("Reranker not available, returning chunks without reranking")
        return [(c, 1.0) for c in chunks[:top_k]] if top_k else [(c, 1.0) for c in chunks]
    
    try:
        start_time = time.time()
        
        # Prepare query-chunk pairs
        pairs = [[query, chunk] for chunk in chunks]
        
        # Compute scores with inference optimization and memory management
        with torch.inference_mode():
            try:
                # Clear GPU cache before inference
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                
                scores = reranker.predict(
                    pairs,
                    batch_size=min(_RERANKER_BATCH_SIZE, len(pairs)),  # Dynamic batch sizing
                    show_progress_bar=False,
                )
                
                # Clear cache after inference
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    
            except Exception as e:
                logger.error(f"Reranker inference failed: {e}")
                # Fallback to uniform scores
                scores = [0.5] * len(chunks)
        
        elapsed = time.time() - start_time
        
        # Combine chunks with scores and sort
        chunk_scores = list(zip(chunks, scores))
        chunk_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Return top_k if specified
        if top_k:
            chunk_scores = chunk_scores[:top_k]
        
        logger.debug(
            f"Reranked {len(chunks)} chunks in {elapsed:.2f}s "
            f"({len(chunks)/elapsed:.1f} chunks/sec), returning top {len(chunk_scores)}"
        )
        
        return chunk_scores
        
    except Exception as e:
        logger.error(f"Reranking failed: {e}, returning original chunks")
        return [(c, 1.0) for c in chunks[:top_k]] if top_k else [(c, 1.0) for c in chunks]
