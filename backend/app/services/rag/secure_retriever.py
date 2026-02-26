"""Secure tenant-isolated retrieval from ChromaDB.

This module is the **only** sanctioned entry point for similarity search.
It enforces that every query carries a valid ``user_id`` metadata filter,
logs suspicious access attempts, and performs post-query validation to
catch any filter bypass.

Enhanced with:
- MMR diversity control
- Cross-encoder reranking
- Per-material retrieval for multi-source balance
- Source diversity control (min/max chunks per material)
- Cross-document query detection
- Performance monitoring
"""

from __future__ import annotations

import logging
import re
import time
from collections import defaultdict, deque
from typing import List, Optional, Tuple, Dict

import numpy as np

from app.db.chroma import get_collection
from app.services.rag.reranker import rerank_chunks
from app.services.rag.context_builder import build_context
from app.services.rag.context_formatter import format_context_with_citations
from app.core.config import settings

logger = logging.getLogger(__name__)
security_logger = logging.getLogger("security.retrieval")


def _expand_structured_chunks(
    documents: List[str],
    metadatas: List[dict],
) -> List[str]:
    """Replace summary placeholders for structured files with their full dataset.

    When a chunk was ingested from a CSV/Excel file the embedder stores only a
    compact schema summary in ChromaDB and tags it with ``is_structured: "true"``.
    At retrieval time we swap the summary for the full content.

    Safety: caps expanded text to 50,000 chars to prevent OOM with huge files.
    """
    from app.services.storage_service import load_material_text

    _MAX_EXPANDED_CHARS = 50_000  # Safety cap for structured data expansion
    expanded = list(documents)
    for i, meta in enumerate(metadatas):
        if str(meta.get("is_structured", "")).lower() != "true":
            continue
        material_id = meta.get("material_id")
        if not material_id:
            continue
        try:
            full_text = load_material_text(material_id)
            if full_text:
                if len(full_text) > _MAX_EXPANDED_CHARS:
                    full_text = full_text[:_MAX_EXPANDED_CHARS] + "\n\n... [truncated — full dataset too large for context]"
                    logger.warning(
                        "Structured chunk truncated to %d chars for material=%s (original: %d)",
                        _MAX_EXPANDED_CHARS, material_id, len(full_text),
                    )
                expanded[i] = full_text
                logger.info(
                    "Expanded structured chunk for material=%s (%d chars)",
                    material_id, len(full_text),
                )
        except Exception as exc:
            logger.warning(
                "Could not load full structured text for material=%s: %s",
                material_id, exc,
            )
    return expanded

# ── Multi-source retrieval configuration ──────────────────────
DEFAULT_PER_MATERIAL_K = 10      # Chunks to retrieve per material
CROSS_DOC_PER_MATERIAL_K = 15    # Increased for cross-document queries
MIN_CHUNKS_PER_MATERIAL = 1      # Ensure diversity
MAX_CHUNKS_PER_MATERIAL = 3      # Cap dominance
CROSS_DOC_FINAL_K = 10           # More context for comparisons
DEFAULT_FINAL_K = 10             # Normal queries (aligned with settings.FINAL_K)

# Cross-document query patterns
CROSS_DOC_KEYWORDS = {
    'compare', 'comparison', 'difference', 'differences', 'contrast',
    'vs', 'versus', 'similarities', 'distinguish', 'distinguish between',
    'how do', 'what is the difference', 'compare and contrast'
}


class TenantIsolationError(Exception):
    """Raised when a retrieval request lacks proper tenant identification."""


# ── Chroma filter builder ─────────────────────────────────────


def _build_where(
    user_id: Optional[str],
    material_id: Optional[str] = None,
    material_ids: Optional[List[str]] = None,
    notebook_id: Optional[str] = None,
) -> Optional[dict]:
    """Construct a Chroma ``where`` filter from the given parameters."""
    clauses: List[dict] = []

    if user_id:
        clauses.append({"user_id": user_id})

    if notebook_id:
        clauses.append({"notebook_id": notebook_id})

    # Material filters
    if material_ids and len(material_ids) > 1:
        clauses.append({"material_id": {"$in": material_ids}})
    elif material_ids and len(material_ids) == 1:
        clauses.append({"material_id": material_ids[0]})
    elif material_id:
        clauses.append({"material_id": material_id})

    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def _is_cross_document_query(query: str) -> bool:
    """Detect if query requires cross-document comparison.
    
    Args:
        query: User query text
    
    Returns:
        True if query contains cross-document patterns
    """
    query_lower = query.lower()
    
    # Check for explicit keywords
    if any(keyword in query_lower for keyword in CROSS_DOC_KEYWORDS):
        logger.info(f"Cross-document query detected: {query[:60]}...")
        return True
    
    # Check for "X vs Y" pattern
    if re.search(r'\b\w+\s+vs\.?\s+\w+\b', query_lower):
        logger.info(f"Cross-document query detected (vs pattern): {query[:60]}...")
        return True
    
    return False


def _ensure_source_diversity(
    chunks_with_metadata: List[Dict],
    min_per_material: int = MIN_CHUNKS_PER_MATERIAL,
    max_per_material: int = MAX_CHUNKS_PER_MATERIAL,
) -> List[Dict]:
    """Ensure balanced representation across materials.
    
    Args:
        chunks_with_metadata: List of chunk dicts with 'material_id' in metadata
        min_per_material: Minimum chunks per material (if score > threshold)
        max_per_material: Maximum chunks per material
    
    Returns:
        Balanced list of chunks
    """
    # Group by material_id
    by_material = defaultdict(list)
    for chunk in chunks_with_metadata:
        material_id = chunk.get('material_id', 'unknown')
        by_material[material_id].append(chunk)
    
    if len(by_material) <= 1:
        # Single material - no diversity needed
        return chunks_with_metadata[:settings.FINAL_K]
    
    logger.info(f"Balancing {len(chunks_with_metadata)} chunks across {len(by_material)} materials")
    
    # Phase 1: Ensure minimum representation
    balanced = []
    for material_id, chunks in by_material.items():
        # Take top min_per_material from each material
        balanced.extend(chunks[:min_per_material])
    
    # Phase 2: Fill remaining slots respecting max_per_material
    remaining_slots = settings.FINAL_K - len(balanced)
    if remaining_slots > 0:
        # Collect remaining chunks
        remaining = []
        for material_id, chunks in by_material.items():
            remaining.extend(chunks[min_per_material:max_per_material])
        
        # Sort by score (if available) and take top
        remaining.sort(key=lambda x: x.get('score', 0), reverse=True)
        balanced.extend(remaining[:remaining_slots])
    
    # Sort final result by score
    balanced.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    logger.info(
        f"Source diversity: {len(balanced)} chunks from {len(by_material)} materials "
        f"(min={min_per_material}, max={max_per_material})"
    )
    
    return balanced[:settings.FINAL_K]


def secure_similarity_search(
    user_id: str,
    query: str,
    k: int = 5,
    *,
    material_id: Optional[str] = None,
    material_ids: Optional[List[str]] = None,
    notebook_id: Optional[str] = None,
) -> List[str]:
    """Retrieve the *k* most relevant chunks, strictly scoped to *user_id*.

    This wrapper guarantees tenant isolation by:
      1. Rejecting any call where ``user_id`` is missing or empty.
      2. Building the ``where`` filter via the shared ``_build_where`` helper
         and asserting it contains a ``user_id`` clause.
      3. Post-query validation: checking returned metadata to ensure no
         documents from another tenant leaked through.

    Args:
        user_id: **Required.** The tenant identifier.
        query: Natural-language search query.
        k: Number of results to return.
        material_id: Optional single material filter.
        material_ids: Optional multi-material filter (takes priority).
        notebook_id: Optional notebook filter.

    Returns:
        List of document strings, guaranteed to belong to *user_id*.

    Raises:
        TenantIsolationError: If ``user_id`` is missing/empty.
    """

    # ── Guard: user_id is mandatory ───────────────────────────
    if not user_id or not user_id.strip():
        security_logger.warning(
            "Retrieval attempted WITHOUT user_id | query=%r", query[:120]
        )
        raise TenantIsolationError(
            "user_id is required for tenant-isolated retrieval"
        )

    # ── Build filter ──────────────────────────────────────────
    where = _build_where(
        user_id=user_id,
        material_id=material_id,
        material_ids=material_ids,
        notebook_id=notebook_id,
    )

    # Defensive: ensure user_id clause actually made it into the filter
    if where is None or not _filter_contains_user_id(where, user_id):
        security_logger.warning(
            "Filter missing user_id clause | user_id=%s where=%s", user_id, where
        )
        raise TenantIsolationError(
            "Constructed filter does not contain the required user_id clause"
        )

    # ── Execute query ─────────────────────────────────────────
    collection = get_collection()

    # Guard: ChromaDB raises if n_results > total docs in collection
    total_in_collection = collection.count()
    if total_in_collection == 0:
        logger.warning("ChromaDB collection is empty — no results possible")
        return []
    safe_k = max(1, min(k, total_in_collection))

    results = collection.query(query_texts=[query], n_results=safe_k, where=where)

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    # ── Post-query validation ─────────────────────────────────
    _validate_result_ownership(user_id, documents, metadatas, query)

    return documents


def _apply_mmr(
    query_embedding: List[float],
    documents: List[str],
    embeddings: List[List[float]],
    lambda_param: float,
    k: int,
) -> List[int]:
    """Apply Max Marginal Relevance to diversify results.
    
    Args:
        query_embedding: Query vector
        documents: List of document strings
        embeddings: List of document vectors
        lambda_param: Trade-off between relevance and diversity (0-1)
        k: Number of documents to select
    
    Returns:
        List of selected document indices
    """
    if len(documents) <= k:
        return list(range(len(documents)))
    
    # Validate input dimensions
    if not embeddings or not query_embedding:
        return list(range(min(k, len(documents))))
    
    try:
        # Convert to numpy arrays with error handling
        query_vec = np.array(query_embedding, dtype=np.float32)
        doc_vecs = np.array(embeddings, dtype=np.float32)
        
        # Validate shapes
        if query_vec.ndim != 1 or doc_vecs.ndim != 2:
            logger.warning(f"MMR: Invalid array shapes - query: {query_vec.shape}, docs: {doc_vecs.shape}")
            return list(range(min(k, len(documents))))
            
        if query_vec.shape[0] != doc_vecs.shape[1]:
            logger.warning(f"MMR: Dimension mismatch - query: {query_vec.shape[0]}, docs: {doc_vecs.shape[1]}")
            return list(range(min(k, len(documents))))
        
        # Normalize vectors with zero-division protection
        query_norm = np.linalg.norm(query_vec)
        if query_norm > 0:
            query_vec = query_vec / query_norm
        
        doc_norms = np.linalg.norm(doc_vecs, axis=1, keepdims=True)
        doc_norms = np.where(doc_norms == 0, 1, doc_norms)  # Prevent division by zero
        doc_vecs = doc_vecs / doc_norms
        
        # Compute query-document similarities
        query_similarities = np.dot(doc_vecs, query_vec)
        
    except Exception as e:
        logger.warning(f"MMR array operations failed: {e}")
        return list(range(min(k, len(documents))))
    
    selected_indices = []
    remaining_indices = list(range(len(documents)))
    
    # Select first document with highest query similarity
    first_idx = int(np.argmax(query_similarities))
    selected_indices.append(first_idx)
    remaining_indices.remove(first_idx)
    
    # Iteratively select documents with max MMR score
    while len(selected_indices) < k and remaining_indices:
        mmr_scores = []
        
        for idx in remaining_indices:
            # Relevance to query
            relevance = query_similarities[idx]
            
            # Max similarity to already selected documents
            selected_vecs = doc_vecs[selected_indices]
            doc_similarities = np.dot(selected_vecs, doc_vecs[idx])
            max_sim = np.max(doc_similarities)
            
            # MMR score
            mmr_score = lambda_param * relevance - (1 - lambda_param) * max_sim
            mmr_scores.append((idx, mmr_score))
        
        # Select document with highest MMR score
        best_idx = max(mmr_scores, key=lambda x: x[1])[0]
        selected_indices.append(best_idx)
        remaining_indices.remove(best_idx)
    
    return selected_indices


def secure_similarity_search_enhanced(
    user_id: str,
    query: str,
    *,
    material_id: Optional[str] = None,
    material_ids: Optional[List[str]] = None,
    notebook_id: Optional[str] = None,
    use_mmr: bool = True,
    use_reranker: bool = True,
    return_formatted: bool = True,
) -> str | List[str]:
    """Enhanced retrieval with per-material balance, MMR diversity, and reranking.
    
    Pipeline (Multi-Source Mode):
      1. Detect cross-document query
      2. Retrieve top-K chunks per material independently
      3. Merge results from all materials
      4. Apply global cross-encoder reranking
      5. Ensure source diversity (min/max per material)
      6. Format with material labels
    
    Pipeline (Single-Source Mode):
      1. Retrieve top-N chunks
      2. Apply MMR for diversity if enabled
      3. Apply reranking
      4. Format context
    
    Args:
        user_id: Required tenant identifier
        query: Natural-language search query
        material_id: Optional single material filter
        material_ids: Optional multi-material filter
        notebook_id: Optional notebook filter
        use_mmr: Apply MMR diversity control (default: True)
        use_reranker: Apply cross-encoder reranking (default: True)
        return_formatted: Return formatted context string (default: True)
    
    Returns:
        If return_formatted=True: Formatted context string with citations
        If return_formatted=False: List of chunk strings
    
    Raises:
        TenantIsolationError: If user_id is missing/empty
    """
    
    # ── Guard: user_id is mandatory ───────────────────────────
    if not user_id or not user_id.strip():
        security_logger.warning(
            "Enhanced retrieval attempted WITHOUT user_id | query=%r", query[:120]
        )
        raise TenantIsolationError(
            "user_id is required for tenant-isolated retrieval"
        )
    
    # ── Detect query type ─────────────────────────────────────
    is_cross_doc = _is_cross_document_query(query)
    
    # Determine material IDs list
    mat_ids = material_ids if material_ids else ([material_id] if material_id else [])
    
    # ── Multi-source retrieval path ───────────────────────────
    if len(mat_ids) > 1:
        return _retrieve_multi_source(
            user_id=user_id,
            query=query,
            material_ids=mat_ids,
            notebook_id=notebook_id,
            is_cross_doc=is_cross_doc,
            use_reranker=use_reranker,
            return_formatted=return_formatted,
        )
    
    # ── Single-source retrieval (original logic) ──────────────
    where = _build_where(
        user_id=user_id,
        material_id=material_id,
        material_ids=material_ids,
        notebook_id=notebook_id,
    )
    
    if where is None or not _filter_contains_user_id(where, user_id):
        security_logger.warning(
            "Filter missing user_id clause | user_id=%s where=%s", user_id, where
        )
        raise TenantIsolationError(
            "Constructed filter does not contain the required user_id clause"
        )
    
    # ── Step 1: Initial vector retrieval ──────────────────────
    retrieval_start = time.time()
    
    collection = get_collection()
    initial_k = settings.INITIAL_VECTOR_K

    # Guard: clamp to actual collection count to avoid ChromaDB crash
    total_in_collection = collection.count()
    if total_in_collection == 0:
        logger.warning("ChromaDB collection is empty — returning no context")
        return "No relevant context found." if return_formatted else []
    safe_initial_k = max(1, min(initial_k, total_in_collection))

    logger.info(f"Single-source retrieval: top {safe_initial_k} chunks for query: {query[:60]}...")
    
    results = collection.query(
        query_texts=[query],
        n_results=safe_initial_k,
        where=where,
        include=['documents', 'metadatas', 'embeddings', 'distances']
    )
    
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    embeddings = results.get("embeddings", [[]])[0]
    ids = results.get("ids", [[]])[0]
    
    # ── Post-query validation ─────────────────────────────────
    _validate_result_ownership(user_id, documents, metadatas, query, ids=ids, embeddings=embeddings)
    
    if not documents:
        logger.warning("No valid documents after security filtering")
        return "No relevant context found." if return_formatted else []
    
    logger.info(f"Retrieved {len(documents)} valid chunks")

    # ── Expand structured chunks to full dataset ──────────────
    documents = _expand_structured_chunks(documents, metadatas)

    # ── Step 2: Apply MMR for diversity ───────────────────────
    if use_mmr and len(documents) > settings.MMR_K and embeddings:
        try:
            # Get query embedding
            query_results = collection.query(
                query_texts=[query],
                n_results=1,
                include=['embeddings']
            )
            # query_results["embeddings"] is [ [vec_for_result_0, ...] ] per query.
            # We want the single query vector (first result's embedding).
            raw_embs = query_results.get("embeddings", [[]])[0]
            query_embedding = raw_embs[0] if raw_embs else []

            if query_embedding:
                mmr_indices = _apply_mmr(
                    query_embedding=query_embedding,
                    documents=documents,
                    embeddings=embeddings,
                    lambda_param=settings.MMR_LAMBDA,
                    k=settings.MMR_K,
                )
                documents = [documents[i] for i in mmr_indices]
                metadatas = [metadatas[i] for i in mmr_indices] if metadatas else []
                ids = [ids[i] for i in mmr_indices] if ids else []
                logger.info(f"Applied MMR: {len(mmr_indices)} diverse chunks selected")
        except Exception as e:
            logger.warning(f"MMR failed, continuing without diversity: {e}")
    
    retrieval_time = time.time() - retrieval_start
    
    # Record retrieval performance
    try:
        from app.services.performance_logger import record_retrieval_time
        record_retrieval_time(retrieval_time)
    except Exception:
        pass  # Performance logging is optional
    
    logger.debug(f"Retrieval (vector + MMR) completed in {retrieval_time:.3f}s")
    
    # ── Step 3: Apply cross-encoder reranking ─────────────────
    reranking_start = time.time()
    chunk_scores = None
    if use_reranker and settings.USE_RERANKER:
        try:
            chunk_scores = rerank_chunks(
                query=query,
                chunks=documents,
                top_k=settings.FINAL_K,
            )
            # Align metadatas/ids to the reranked order.
            # Use a deque-based position map to handle duplicate chunk texts
            # correctly (list.index() always returns the first occurrence).
            pos_map: Dict[str, deque] = {}
            for i, doc in enumerate(documents):
                pos_map.setdefault(doc, deque()).append(i)

            reranked_indices = []
            reranked_docs = []
            for chunk, score in chunk_scores:
                if chunk in pos_map and pos_map[chunk]:
                    reranked_indices.append(pos_map[chunk].popleft())
                    reranked_docs.append(chunk)

            metadatas = [metadatas[i] for i in reranked_indices] if metadatas else []
            ids = [ids[i] for i in reranked_indices] if ids else []
            documents = reranked_docs
            logger.info("Reranked to top %d chunks", len(documents))
        except Exception as e:
            logger.error("Reranking failed: %s", e)
            documents = documents[:settings.FINAL_K]
            metadatas = metadatas[:settings.FINAL_K] if metadatas else []
            ids = ids[:settings.FINAL_K] if ids else []
    else:
        # No reranking, just take top final_k
        documents = documents[:settings.FINAL_K]
        metadatas = metadatas[:settings.FINAL_K] if metadatas else []
        ids = ids[:settings.FINAL_K] if ids else []
    
    reranking_time = time.time() - reranking_start
    
    # Record reranking performance
    try:
        from app.services.performance_logger import record_reranking_time
        record_reranking_time(reranking_time)
    except Exception:
        pass  # Performance logging is optional
    
    logger.debug(f"Reranking completed in {reranking_time:.3f}s")
    
    # ── Step 4: Format context with filtering ─────────────────
    if return_formatted:
        # Build chunks with metadata for new formatter
        chunks_with_metadata = []
        for i, doc in enumerate(documents):
            chunk_dict = {
                "text": doc,
                "id": ids[i] if i < len(ids) else f"chunk_{i}",
            }
            # Add metadata if available
            if i < len(metadatas):
                meta = metadatas[i]
                if "section_title" in meta:
                    chunk_dict["section_title"] = meta["section_title"]
                if "material_id" in meta:
                    chunk_dict["material_id"] = meta["material_id"]
                if "filename" in meta:
                    chunk_dict["filename"] = meta["filename"]
            # Add score if reranked
            if chunk_scores and i < len(chunk_scores):
                chunk_dict["score"] = chunk_scores[i][1]
            
            chunks_with_metadata.append(chunk_dict)
        
        # Use new citation-aware formatter
        return format_context_with_citations(
            chunks_with_metadata,
            max_sources=settings.FINAL_K,
        )
    
    return documents


def _retrieve_multi_source(
    user_id: str,
    query: str,
    material_ids: List[str],
    notebook_id: Optional[str],
    is_cross_doc: bool,
    use_reranker: bool,
    return_formatted: bool,
) -> str | List[str]:
    """Retrieve chunks with per-material balance for multi-source queries.
    
    Pipeline:
      1. Retrieve top-K chunks per material independently
      2. Merge all results
      3. Apply global cross-encoder reranking
      4. Ensure source diversity (min/max per material)
      5. Format with material labels
    
    Args:
        user_id: Tenant identifier
        query: Search query
        material_ids: List of material IDs to query
        notebook_id: Optional notebook filter
        is_cross_doc: Whether query detected as cross-document
        use_reranker: Whether to use reranker
        return_formatted: Whether to return formatted string
    
    Returns:
        Formatted context or list of chunks
    """
    # Determine per-material retrieval size
    per_material_k = CROSS_DOC_PER_MATERIAL_K if is_cross_doc else DEFAULT_PER_MATERIAL_K
    final_k = CROSS_DOC_FINAL_K if is_cross_doc else DEFAULT_FINAL_K
    
    logger.info(
        f"Multi-source retrieval: {len(material_ids)} materials, "
        f"per_material_k={per_material_k}, final_k={final_k}, "
        f"cross_doc={is_cross_doc}"
    )
    
    retrieval_start = time.time()
    
    collection = get_collection()
    
    # ── Step 1: Single batched query with $in filter ──────────
    where = _build_where(
        user_id=user_id,
        material_ids=material_ids,
        notebook_id=notebook_id,
    )

    if not where or not _filter_contains_user_id(where, user_id):
        security_logger.warning(
            "Multi-source filter missing user_id | user_id=%s where=%s",
            user_id, where,
        )
        raise TenantIsolationError(
            "Constructed filter does not contain the required user_id clause"
        )

    # Scale retrieval count with number of materials; guard against collection size
    total_in_collection = collection.count()
    if total_in_collection == 0:
        logger.warning("ChromaDB collection is empty — returning no context")
        return "No relevant context found." if return_formatted else []
    batch_k = max(1, min(per_material_k * len(material_ids), total_in_collection))

    all_documents: List[str] = []
    all_metadatas: List[Dict] = []
    all_ids: List[str] = []

    try:
        results = collection.query(
            query_texts=[query],
            n_results=batch_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        ids = results.get("ids", [[]])[0]

        _validate_result_ownership(user_id, docs, metas, query, ids=ids)

        for i, doc in enumerate(docs):
            if doc and i < len(metas) and i < len(ids):
                all_documents.append(doc)
                all_metadatas.append(metas[i])
                all_ids.append(ids[i])

        logger.info(
            "Batched retrieval: %d chunks from %d materials in one query",
            len(all_documents), len(material_ids),
        )
    except Exception as e:
        logger.error("Batched multi-source retrieval failed: %s", e)
        return "No relevant context found." if return_formatted else []
    
    if not all_documents:
        logger.warning("No documents retrieved from any material")
        return "No relevant context found." if return_formatted else []
    
    retrieval_time = time.time() - retrieval_start
    
    # Record retrieval performance
    try:
        from app.services.performance_logger import record_retrieval_time
        record_retrieval_time(retrieval_time)
    except Exception:
        pass
    
    logger.info(f"Total retrieved: {len(all_documents)} chunks from {len(material_ids)} materials in {retrieval_time:.3f}s")

    # ── Expand structured chunks to full dataset ──────────────
    all_documents = _expand_structured_chunks(all_documents, all_metadatas)

    # ── Step 2: Global reranking ──────────────────────────────
    reranking_start = time.time()
    chunk_scores = None
    if use_reranker and settings.USE_RERANKER:
        try:
            # Rerank all chunks globally
            chunk_scores = rerank_chunks(
                query=query,
                chunks=all_documents,
                top_k=final_k * 2,  # Fetch more so diversity filter has headroom
            )

            # Align metadatas/ids to the reranked order (deque map handles duplicates)
            pos_map: Dict[str, deque] = {}
            for i, doc in enumerate(all_documents):
                pos_map.setdefault(doc, deque()).append(i)

            reranked_docs = []
            reranked_indices = []
            for chunk, score in chunk_scores:
                if chunk in pos_map and pos_map[chunk]:
                    reranked_indices.append(pos_map[chunk].popleft())
                    reranked_docs.append(chunk)

            all_metadatas = [all_metadatas[i] for i in reranked_indices]
            all_ids = [all_ids[i] for i in reranked_indices]
            all_documents = reranked_docs
            logger.info("Global reranking: top %d chunks", len(chunk_scores))
            
        except Exception as e:
            logger.error("Global reranking failed: %s", e)
            # Continue without reranking
            all_documents = all_documents[:final_k * 2]
            all_metadatas = all_metadatas[:final_k * 2]
            all_ids = all_ids[:final_k * 2]
    else:
        # No reranking, limit to reasonable size
        all_documents = all_documents[:final_k * 2]
        all_metadatas = all_metadatas[:final_k * 2]
        all_ids = all_ids[:final_k * 2]
    
    reranking_time = time.time() - reranking_start
    
    # Record reranking performance
    try:
        from app.services.performance_logger import record_reranking_time
        record_reranking_time(reranking_time)
    except Exception:
        pass
    
    logger.debug(f"Reranking completed in {reranking_time:.3f}s")
    
    # ── Step 3: Build chunks with metadata ────────────────────
    chunks_with_metadata = []
    for i, doc in enumerate(all_documents):
        chunk_dict = {
            "text": doc,
            "id": all_ids[i] if i < len(all_ids) else f"chunk_{i}",
            "material_id": all_metadatas[i].get("material_id", "unknown") if i < len(all_metadatas) else "unknown",
        }
        
        # Add other metadata
        if i < len(all_metadatas):
            meta = all_metadatas[i]
            if "section_title" in meta:
                chunk_dict["section_title"] = meta["section_title"]
            if "filename" in meta:
                chunk_dict["filename"] = meta["filename"]
        
        # Add score if reranked
        if chunk_scores and i < len(chunk_scores):
            chunk_dict["score"] = chunk_scores[i][1]
        else:
            chunk_dict["score"] = 1.0  # Default score
        
        chunks_with_metadata.append(chunk_dict)
    
    # ── Step 4: Ensure source diversity ───────────────────────
    chunks_with_metadata = _ensure_source_diversity(
        chunks_with_metadata,
        min_per_material=MIN_CHUNKS_PER_MATERIAL,
        max_per_material=MAX_CHUNKS_PER_MATERIAL,
    )
    
    # ── Step 5: Format context ────────────────────────────────
    if return_formatted:
        return format_context_with_citations(
            chunks_with_metadata,
            max_sources=final_k,
        )
    
    return [chunk["text"] for chunk in chunks_with_metadata]


# ── Internal helpers ──────────────────────────────────────────


def _filter_contains_user_id(where: dict, user_id: str) -> bool:
    """Return True if *where* contains a ``user_id`` equality clause."""
    if where.get("user_id") == user_id:
        return True
    # Check inside $and
    for clause in where.get("$and", []):
        if isinstance(clause, dict) and clause.get("user_id") == user_id:
            return True
    return False


def _validate_result_ownership(
    user_id: str,
    documents: List[str],
    metadatas: List[dict],
    query: str,
    ids: list | None = None,
    embeddings: list | None = None,
) -> None:
    """Remove any documents belonging to a different tenant (CRITICAL SECURITY).
    
    Instead of blanking to empty string (which could leak downstream),
    we collect leaked indices and remove them properly.
    All parallel lists (documents, metadatas, ids, embeddings) are modified
    in-place by removing leaked items to keep indices synchronized.
    """
    leaked_indices = []
    for idx, meta in enumerate(metadatas):
        doc_owner = meta.get("user_id")
        if doc_owner and doc_owner != user_id:
            security_logger.warning(
                "CROSS-TENANT LEAK BLOCKED | requested=%s got=%s "
                "doc_index=%d query=%r",
                user_id,
                doc_owner,
                idx,
                query[:120],
            )
            leaked_indices.append(idx)
    
    # Remove leaked documents in reverse order to preserve indices
    for idx in reversed(leaked_indices):
        documents.pop(idx)
        if idx < len(metadatas):
            metadatas.pop(idx)
        if ids is not None and idx < len(ids):
            ids.pop(idx)
        if embeddings is not None and idx < len(embeddings):
            embeddings.pop(idx)
