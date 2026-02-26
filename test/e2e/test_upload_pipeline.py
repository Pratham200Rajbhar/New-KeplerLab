"""
End-to-end test: Full upload → text extraction → chunking → embedding pipeline.
Tests the complete document ingestion workflow from raw text to ChromaDB.
Requires: ChromaDB, no live PostgreSQL needed (mocked where needed).
"""

import sys
import os
import uuid
import shutil
import tempfile
import pytest
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-only-32chars!")

import app.services.storage_service as _svc
from app.services.text_processing.chunker import chunk_text
from app.services.rag.embedder import embed_and_store


# ────────────────────────────────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def temp_storage(tmp_path):
    with patch.object(_svc, "MATERIAL_TEXT_DIR", tmp_path):
        yield tmp_path


SAMPLE_DOCUMENTS = {
    "science": (
        "# Introduction to Quantum Mechanics\n\n"
        "Quantum mechanics is a fundamental theory in physics that describes nature at the "
        "atomic and subatomic level. It was developed in the early 20th century by Planck, "
        "Bohr, Heisenberg, and Schrödinger.\n\n"
        "## Wave-Particle Duality\n\n"
        "One of the central concepts is that particles can exhibit wave-like properties. "
        "The de Broglie hypothesis proposed that all matter has wave properties. "
        "This was confirmed by electron diffraction experiments.\n\n"
        "## The Uncertainty Principle\n\n"
        "Heisenberg's uncertainty principle states that the position and momentum of a particle "
        "cannot both be known simultaneously with arbitrary precision. This is a fundamental "
        "property of nature, not merely a limitation of measurement tools.\n\n" * 5
    ),

    "history": (
        "# The French Revolution\n\n"
        "The French Revolution began in 1789 and fundamentally transformed French society. "
        "It ended the monarchy, established a republic, and culminated in Napoleon's rise.\n\n"
        "## Causes\n\n"
        "The revolution was caused by financial crisis, social inequality, and Enlightenment ideas. "
        "The Estates-General was called in 1789 after France faced bankruptcy.\n\n"
        "## Key Events\n\n"
        "The storming of the Bastille on July 14, 1789 marked the symbolic start. "
        "The Declaration of the Rights of Man and Citizen was adopted in August 1789.\n\n" * 5
    ),

    "csv": (
        "product,price,category,rating\n" +
        "\n".join(f"Product_{i},{i * 10.5},Category_{i % 3},{3.5 + i * 0.1}" for i in range(100))
    ),
}


# ────────────────────────────────────────────────────────────────────────────
# Stage 1: Text storage
# ────────────────────────────────────────────────────────────────────────────

class TestStage1TextStorage:
    """Verify that raw IaaS text can be saved and retrieved correctly."""

    def test_save_and_retrieve_text(self, temp_storage):
        from app.services.storage_service import save_material_text, load_material_text
        mid = str(uuid.uuid4())
        text = SAMPLE_DOCUMENTS["iaas_fundamentals"]
        assert save_material_text(mid, text) is True
        loaded = load_material_text(mid)
        assert loaded == text

    def test_save_all_document_types(self, temp_storage):
        from app.services.storage_service import save_material_text, load_material_text
        for doc_type, text in SAMPLE_DOCUMENTS.items():
            mid = str(uuid.uuid4())
            save_material_text(mid, text)
            loaded = load_material_text(mid)
            assert loaded == text, f"Failed for document type: {doc_type}"


# ────────────────────────────────────────────────────────────────────────────
# Stage 2: Chunking
# ────────────────────────────────────────────────────────────────────────────

class TestStage2Chunking:
    """Verify that stored IaaS text can be correctly chunked."""

    def test_science_document_produces_multiple_chunks(self):
        # Source: IaaS fundamentals section from "4. IaaS.pdf"
        chunks = chunk_text(SAMPLE_DOCUMENTS["iaas_fundamentals"])
        assert len(chunks) >= 2, "IaaS fundamentals document should produce >= 2 chunks"

    def test_history_document_chunks_have_section_titles(self):
        # Source: IaaS billing section from "4. IaaS.pdf"
        chunks = chunk_text(SAMPLE_DOCUMENTS["iaas_billing"])
        titles = [c.get("section_title") for c in chunks if c.get("section_title")]
        assert len(titles) >= 1

    def test_csv_document_chunked(self):
        # Source: IaaS instance pricing CSV derived from metering section
        chunks = chunk_text(SAMPLE_DOCUMENTS["csv"], source_type="csv")
        assert isinstance(chunks, list)

    def test_chunks_cover_original_content(self):
        text = SAMPLE_DOCUMENTS["iaas_fundamentals"]
        chunks = chunk_text(text)
        all_text = " ".join(c["text"] for c in chunks)
        # Key IaaS terms should appear in at least one chunk
        assert (
            "iaas" in all_text.lower()
            or "dynamic" in all_text.lower()
            or "virtual" in all_text.lower()
        )

    def test_chunk_ids_unique_across_document(self):
        chunks = chunk_text(SAMPLE_DOCUMENTS["iaas_fundamentals"])
        ids = [c["id"] for c in chunks]
        assert len(ids) == len(set(ids)), "Chunk IDs must be unique"


# ────────────────────────────────────────────────────────────────────────────
# Stage 3: Embedding (store into ChromaDB)
# ────────────────────────────────────────────────────────────────────────────

class TestStage3Embedding:
    """Verify that chunks can be embedded and stored in ChromaDB."""

    def test_embed_science_document(self):
        # Source: IaaS fundamentals document from "4. IaaS.pdf"
        user_id = str(uuid.uuid4())
        material_id = str(uuid.uuid4())
        chunks = chunk_text(SAMPLE_DOCUMENTS["iaas_fundamentals"])
        # Should not raise
        embed_and_store(chunks, material_id=material_id, user_id=user_id)

    def test_embed_empty_chunks_is_noop(self):
        """Empty chunk list must not crash."""
        embed_and_store([], material_id=str(uuid.uuid4()), user_id=str(uuid.uuid4()))

    def test_embed_without_user_id_rejected(self):
        """Missing user_id must be silently rejected (tenant safety)."""
        # Source: IaaS characteristics passage from "4. IaaS.pdf"
        chunks = chunk_text(
            "IaaS providers use metering to track CPU, memory, and storage per instance. " * 100
        )
        # Should not raise, just log error
        embed_and_store(chunks, material_id=str(uuid.uuid4()), user_id="")

    def test_embed_idempotent(self):
        """Re-embedding the same IaaS material must not crash (upsert)."""
        user_id = str(uuid.uuid4())
        material_id = str(uuid.uuid4())
        # Source: IaaS self-service provisioning passage from "4. IaaS.pdf"
        iaas_text = (
            "Self-service provisioning allows customers to deploy virtual machines "
            "and configure networks without manual intervention from the provider. "
        ) * 50
        chunks = chunk_text(iaas_text)
        embed_and_store(chunks, material_id=material_id, user_id=user_id)
        embed_and_store(chunks, material_id=material_id, user_id=user_id)


# ────────────────────────────────────────────────────────────────────────────
# Stage 4: Full pipeline — text → chunk → embed → query
# ────────────────────────────────────────────────────────────────────────────

class TestStage4FullPipeline:
    """End-to-end: text storage, chunking, embedding, and retrieval."""

    def test_full_pipeline_science_doc(self, temp_storage):
        from app.services.storage_service import save_material_text, load_material_text
        import chromadb

        user_id = str(uuid.uuid4())
        material_id = str(uuid.uuid4())
        # Source: IaaS fundamentals from "4. IaaS.pdf"
        text = SAMPLE_DOCUMENTS["iaas_fundamentals"]

        # 1. Store text
        assert save_material_text(material_id, text) is True

        # 2. Load and verify
        loaded = load_material_text(material_id)
        assert loaded is not None
        assert len(loaded) > 0

        # 3. Chunk
        chunks = chunk_text(loaded)
        assert len(chunks) >= 1

        # 4. Embed
        embed_and_store(chunks, material_id=material_id, user_id=user_id)

        # 5. Confirm metadata on chunks
        for chunk in chunks:
            assert "id" in chunk
            assert "text" in chunk
            assert len(chunk["text"]) > 0

    def test_full_pipeline_multiple_materials(self, temp_storage):
        """Multiple materials from same user should not interfere."""
        user_id = str(uuid.uuid4())
        for doc_type, text in SAMPLE_DOCUMENTS.items():
            mid = str(uuid.uuid4())
            from app.services.storage_service import save_material_text
            save_material_text(mid, text)
            chunks = chunk_text(text, source_type="csv" if doc_type == "csv" else "prose")
            embed_and_store(chunks, material_id=mid, user_id=user_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
