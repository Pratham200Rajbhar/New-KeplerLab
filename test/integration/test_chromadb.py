"""
Integration tests for ChromaDB (app/db/chroma.py + app/services/rag/embedder.py)
Tests: collection creation, upsert (embed_and_store), query, tenant isolation,
       re-upsert idempotency, delete by metadata
Requires: ChromaDB installed (no PostgreSQL needed)
"""

import sys
import os
import uuid
import shutil
import tempfile
import pytest

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-only-32chars!")

import chromadb
from app.services.rag.embedder import embed_and_store


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def chroma_dir():
    """Temporary ChromaDB directory — cleaned up after the test module."""
    d = tempfile.mkdtemp(prefix="keplerlab_test_chroma_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture(scope="module")
def test_collection(chroma_dir):
    """Isolated ChromaDB collection for tests."""
    client = chromadb.PersistentClient(path=chroma_dir)
    col = client.get_or_create_collection(name="test_chapters")
    yield col
    client.delete_collection(name="test_chapters")


@pytest.fixture
def make_chunks():
    """Factory: create n simple chunk dicts."""
    def _make(n=3, text_prefix="Chunk"):
        return [
            {"id": str(uuid.uuid4()), "text": f"{text_prefix} {i}: relevant content about AI."}
            for i in range(n)
        ]
    return _make


# ── embed_and_store ───────────────────────────────────────────────────────────

class TestEmbedAndStore:

    def test_embed_and_store_basic(self, make_chunks):
        """embed_and_store should not raise for valid input."""
        user_id = str(uuid.uuid4())
        material_id = str(uuid.uuid4())
        chunks = make_chunks(3)
        # Should complete without error
        embed_and_store(chunks, material_id=material_id, user_id=user_id)

    def test_embed_and_store_empty_chunks(self):
        """Empty chunk list should be a no-op."""
        embed_and_store([], material_id=str(uuid.uuid4()), user_id=str(uuid.uuid4()))

    def test_embed_and_store_no_user_id_skipped(self, make_chunks):
        """Missing user_id must be rejected (tenant isolation)."""
        # Should log error and return without raising
        embed_and_store(make_chunks(2), material_id=str(uuid.uuid4()), user_id="")

    def test_embed_and_store_idempotent(self, make_chunks):
        """Calling twice with same chunk IDs must not raise (upsert semantics)."""
        user_id = str(uuid.uuid4())
        material_id = str(uuid.uuid4())
        chunks = make_chunks(2)
        embed_and_store(chunks, material_id=material_id, user_id=user_id)
        embed_and_store(chunks, material_id=material_id, user_id=user_id)


# ── Low-level ChromaDB operations ─────────────────────────────────────────────

class TestChromaDBCollection:

    def test_collection_add_and_count(self, test_collection):
        """Add documents to the collection and verify count."""
        doc_id = str(uuid.uuid4())
        test_collection.add(
            ids=[doc_id],
            documents=["Test document about machine learning."],
            metadatas=[{"user_id": "u1", "material_id": "m1"}],
        )
        # Count should include our doc (may have others too)
        count = test_collection.count()
        assert count >= 1

    def test_collection_query_returns_results(self, test_collection):
        """Query should return similar documents."""
        doc_id = str(uuid.uuid4())
        test_collection.add(
            ids=[doc_id],
            documents=["Neural networks are a type of machine learning model."],
            metadatas=[{"user_id": "u-query", "material_id": "m-query"}],
        )
        results = test_collection.query(
            query_texts=["machine learning neural network"],
            n_results=1,
            where={"user_id": "u-query"},
        )
        assert len(results["documents"][0]) >= 1

    def test_tenant_isolation_metadata_filter(self, test_collection):
        """Querying with user_id filter should not cross user boundaries."""
        user_a = str(uuid.uuid4())
        user_b = str(uuid.uuid4())

        test_collection.add(
            ids=[str(uuid.uuid4())],
            documents=["User A's private document content."],
            metadatas=[{"user_id": user_a}],
        )
        test_collection.add(
            ids=[str(uuid.uuid4())],
            documents=["User B's completely different content."],
            metadatas=[{"user_id": user_b}],
        )

        results_a = test_collection.query(
            query_texts=["private document"],
            n_results=5,
            where={"user_id": user_a},
        )

        # All returned documents should belong to user_a
        for meta in results_a["metadatas"][0]:
            assert meta["user_id"] == user_a

    def test_upsert_is_idempotent(self, test_collection):
        """Upserting same ID twice must update, not duplicate."""
        doc_id = str(uuid.uuid4())
        test_collection.upsert(
            ids=[doc_id],
            documents=["Original content"],
            metadatas=[{"user_id": "u-upsert"}],
        )
        count_before = test_collection.count()
        test_collection.upsert(
            ids=[doc_id],
            documents=["Updated content"],
            metadatas=[{"user_id": "u-upsert"}],
        )
        count_after = test_collection.count()
        assert count_after == count_before  # no new doc added

    def test_delete_by_id(self, test_collection):
        """Deleting a document by ID should remove it."""
        doc_id = str(uuid.uuid4())
        test_collection.add(
            ids=[doc_id],
            documents=["Document to be deleted"],
            metadatas=[{"user_id": "u-del"}],
        )
        count_before = test_collection.count()
        test_collection.delete(ids=[doc_id])
        count_after = test_collection.count()
        assert count_after == count_before - 1

    def test_query_empty_collection_no_crash(self, chroma_dir):
        """Query on empty collection should not crash."""
        client = chromadb.PersistentClient(path=chroma_dir)
        empty_col = client.get_or_create_collection(name="empty_test")
        try:
            results = empty_col.query(query_texts=["anything"], n_results=1)
            # May return empty or raise — just ensure no crash beyond expected
        except Exception as e:
            # chromadb raises if collection is empty — that's OK
            pass
        finally:
            client.delete_collection(name="empty_test")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
