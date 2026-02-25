"""Enhanced context formatter with citation support for RAG.

Formats retrieved chunks with rich metadata (section titles, chunk IDs,
material filenames) to enable strict citation enforcement and cross-document
comparison in LLM responses.
"""

from __future__ import annotations

import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# In-process cache: material_id → filename (populated by material_service after ingestion)
_material_name_cache: Dict[str, str] = {}


def _get_material_name_sync(material_id: str) -> str:
    """Return the cached filename for *material_id*, or ``""`` if not yet cached.

    The cache is populated by ``material_service`` after a material finishes
    processing. For materials ingested in a previous server session the cache
    will be cold; in that case ``format_context_with_citations`` falls back to
    the abbreviated UUID.
    """
    return _material_name_cache.get(material_id, "")


def format_context_with_citations(
    chunks: List[Dict],
    max_sources: Optional[int] = None,
) -> str:
    """Format chunks with citation metadata for LLM context.
    
    Each chunk dict should contain:
    - text: str (required)
    - id: str (optional, for chunk_id)
    - section_title: str (optional, from structure-aware chunker)
    - material_id: str (optional, for cross-document labeling)
    - score: float (optional, reranker confidence)
    
    Args:
        chunks: List of chunk dictionaries with text and metadata
        max_sources: Maximum number of sources to include (None = no limit)
    
    Returns:
        Formatted context string with source citations
    
    Example output (multi-source):
        --------------------------------------------------
        [SOURCE 1 - Material: biology_notes.pdf]
        Section: Photosynthesis Overview
        Chunk ID: mat_abc123_chunk_0
        Confidence: 0.92
        
        Content:
        Photosynthesis occurs in chloroplasts...
        --------------------------------------------------
        
        [SOURCE 2 - Material: chemistry_textbook.pdf]
        Section: Chemical Reactions
        ...
    """
    if not chunks:
        return "No relevant context found."
    
    # Limit sources if specified
    selected_chunks = chunks[:max_sources] if max_sources else chunks
    
    formatted_sections = []
    
    for idx, chunk in enumerate(selected_chunks, start=1):
        # Extract chunk data
        text = chunk.get("text", "")
        chunk_id = chunk.get("id", "unknown")
        section_title = chunk.get("section_title", "No section")
        material_id = chunk.get("material_id", None)
        score = chunk.get("score", None)
        
        # Build metadata header
        header_lines = ["-" * 50]
        
        # Source label with material name for multi-source
        if material_id:
            # filename is stored in ChromaDB metadata by newer versions of the embedder
            material_name = (
                chunk.get("filename")
                or _get_material_name_sync(material_id)
                or f"Source-{material_id[:8]}"
            )
            header_lines.append(f"[SOURCE {idx} - Material: {material_name}]")
        else:
            header_lines.append(f"[SOURCE {idx}]")
        
        # Add section title if available
        if section_title and section_title != "No section":
            header_lines.append(f"Section: {section_title}")
        
        # Add chunk ID (for auditability)
        header_lines.append(f"Chunk ID: {chunk_id}")
        
        # Add confidence score if available
        if score is not None:
            header_lines.append(f"Confidence: {score:.2f}")
        
        # Add separator before content
        header_lines.append("")
        header_lines.append("Content:")
        
        # Combine header and content
        formatted_sections.append(
            "\n".join(header_lines) + f"\n{text}\n" + "-" * 50
        )
        
        logger.debug(
            "Formatted SOURCE %d: chunk=%s  material=%s  section=%s  score=%s",
            idx, chunk_id, material_id, section_title, score,
        )

    context = "\n\n".join(formatted_sections)
    logger.info("Formatted %d sources with citation metadata", len(selected_chunks))
    return context


def build_citation_correction_prompt(original_response: str) -> str:
    """Build a correction prompt to request citations from LLM.
    
    Used when the LLM response lacks proper source citations.
    
    Args:
        original_response: LLM response without citations
    
    Returns:
        Correction prompt string
    """
    return f"""Your previous response did not include proper source citations. 

Please rewrite your answer with the following requirements:
1. Use ONLY information from the provided sources
2. Cite every claim with [SOURCE N] where N is the source number
3. If a claim cannot be supported by the sources, remove it
4. If no sources support the answer, say: "I could not find this information in the provided materials."

Your previous response was:
{original_response}

Now provide a corrected version with proper citations:"""
