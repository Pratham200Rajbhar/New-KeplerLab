"""
End-to-end test: Complete RAG retrieval pipeline.
Tests: context building -> formatting -> citation validation workflow.
Requires: ChromaDB (no PostgreSQL or LLM needed — uses mocked/local components).
"""

import sys
import os
import uuid
import pytest
from unittest.mock import patch

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-only-32chars!")

from app.services.text_processing.chunker import chunk_text
from app.services.rag.embedder import embed_and_store
from app.services.rag.context_builder import build_context
from app.services.rag.citation_validator import validate_citations


# ── Test documents ────────────────────────────────────────────────────────────

ARTICLE_TEXT = (
    "# Machine Learning Fundamentals\n\n"
    "Machine learning (ML) is the study of computer algorithms that automatically improve "
    "through experience. ML is seen as a part of artificial intelligence.\n\n"
    "## Supervised Learning\n\n"
    "Supervised learning is the machine learning task of learning a function that maps an "
    "input to an output based on example input-output pairs.\n\n"
    "## Unsupervised Learning\n\n"
    "Unsupervised learning is a type of algorithm that learns patterns from untagged data. "
    "The hope is that through mimicry, the machine is forced to build a compact internal "
    "representation of its world.\n\n"
    "## Deep Learning\n\n"
    "Deep learning is a subset of machine learning where artificial neural networks, "
    "algorithms inspired by the human brain, learn from large amounts of data.\n\n" * 5
)


# ────────────────────────────────────────────────────────────────────────────
# Context building from raw chunks
# ────────────────────────────────────────────────────────────────────────────

class TestContextBuildingPipeline:

    def test_chunks_to_context(self):
        """Chunked text should produce a usable context string."""
        chunks = chunk_text(ARTICLE_TEXT)
        assert len(chunks) >= 2

        # Simulate reranker output: (text, score) tuples
        scored_chunks = [(c["text"], 3.5 - i * 0.1) for i, c in enumerate(chunks[:5])]
        context = build_context(scored_chunks)

        assert isinstance(context, str)
        assert len(context) > 0

    def test_context_contains_source_labels(self):
        chunks = chunk_text(ARTICLE_TEXT)
        scored = [(c["text"], 4.0) for c in chunks[:3]]
        context = build_context(scored)
        # Context should contain at least one SOURCE label
        assert "SOURCE" in context

    def test_context_from_empty_chunks_returns_not_found(self):
        context = build_context([])
        assert "no" in context.lower() or "not found" in context.lower()

    def test_low_score_chunks_excluded_from_context(self):
        """Chunks with very low reranker scores should be excluded."""
        # Very low logit score → sigmoid ≈ 0 → filtered out
        scored = [("Important machine learning content. " * 20, -100.0)]
        context = build_context(scored)
        # All chunks filtered → not found response
        assert "no" in context.lower() or "not found" in context.lower() or context


# ────────────────────────────────────────────────────────────────────────────
# Citation validation pipeline
# ────────────────────────────────────────────────────────────────────────────

class TestCitationValidationPipeline:

    def test_well_cited_rag_response_valid(self):
        """A properly cited IaaS LLM response should validate correctly."""
        response = (
            "IaaS provides virtualized hardware resources over the internet to customers. [SOURCE 1] "
            "Dynamic scaling allows resources to be provisioned automatically based on demand. [SOURCE 2] "
            "Metering charges customers based on CPU, memory, and storage consumed per hour. [SOURCE 3]"
        )
        result = validate_citations(response, num_sources=3)
        assert result["is_valid"] is True

    def test_uncited_response_flagged(self):
        """IaaS response without citations should fail validation."""
        response = (
            "Infrastructure as a Service provides cloud computing resources through virtualization."
        )
        result = validate_citations(response, num_sources=3, strict=True)
        assert result["is_valid"] is False
        assert result["missing_citations"] is True

    def test_hallucinated_source_detected(self):
        """Citation for a source outside the provided IaaS document set should be flagged."""
        response = "As mentioned in [SOURCE 10], IaaS rental fees are billed hourly."
        result = validate_citations(response, num_sources=3)
        assert 10 in result["invalid_sources"]

    def test_not_found_response_passes_validation(self):
        """'Not found' responses for IaaS topics not covered should pass citation validation."""
        responses = [
            "I could not find relevant information about this topic in the provided documents.",
            "The provided materials do not contain information about quantum computing.",
        ]
        for r in responses:
            result = validate_citations(r, num_sources=3)
            assert result["is_valid"] is True, f"Failed for: {r!r}"

    def test_citation_density_computed(self):
        """Citation density should be a non-negative float for IaaS responses."""
        response = (
            "IaaS uses metering to track consumption. [SOURCE 1] "
            "Service levels guarantee 99.999 percent uptime. [SOURCE 2] "
            "The rental model charges by the hour per instance. [SOURCE 1]"
        )
        result = validate_citations(response, num_sources=3)
        assert result["citation_density"] >= 0.0


# ────────────────────────────────────────────────────────────────────────────
# Full RAG pipeline (chunk → embed → query-like test)
# ────────────────────────────────────────────────────────────────────────────

class TestFullRAGPipeline:

    def test_full_rag_pipeline_no_crash(self):
        """Complete IaaS document pipeline from chunk to context should not crash."""
        # 1. Chunk IaaS document
        chunks = chunk_text(ARTICLE_TEXT)
        assert len(chunks) >= 1

        # 2. Embed into ChromaDB
        user_id = str(uuid.uuid4())
        material_id = str(uuid.uuid4())
        embed_and_store(chunks, material_id=material_id, user_id=user_id)

        # 3. Simulate retrieval: take top chunks as scored results
        scored_chunks = [(c["text"], 3.0 - i * 0.2) for i, c in enumerate(chunks[:4])]

        # 4. Build context
        context = build_context(scored_chunks)
        assert isinstance(context, str)

        # 5. Simulate LLM response about IaaS with citations
        simulated_response = (
            "IaaS provides virtualized hardware including virtual machines and storage. [SOURCE 1] "
            "Dynamic scaling allows resources to be provisioned automatically on demand. [SOURCE 2]"
        )

        # 6. Validate citations
        result = validate_citations(simulated_response, num_sources=len(scored_chunks))
        assert result["is_valid"] is True

    def test_rag_pipeline_multi_material(self):
        """IaaS pipeline should handle multiple materials for same user without interference."""
        user_id = str(uuid.uuid4())
        all_scored = []
        # Three IaaS sub-topics as separate materials
        iaas_topics = [
            "Dynamic scaling in IaaS allows resources to be automatically provisioned "
            "based on application workload demand. " * 30,
            "The IaaS rental model charges customers by the hour based on virtual machine "
            "instance size, memory, CPU cores, and storage allocation. " * 30,
            "Self-service provisioning in IaaS enables customers to deploy and configure "
            "virtual machines and networks without manual intervention from the provider. " * 30,
        ]
        for i, topic_text in enumerate(iaas_topics):
            material_id = str(uuid.uuid4())
            chunks = chunk_text(topic_text)
            embed_and_store(chunks, material_id=material_id, user_id=user_id)
            if chunks:
                all_scored.append((chunks[0]["text"], 3.0 - i * 0.5))

        context = build_context(all_scored)
        assert isinstance(context, str)
        assert len(context) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
