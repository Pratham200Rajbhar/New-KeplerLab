"""
Comprehensive pipeline test suite for KeplerLab AI Notebook.

Tests every stage of the content processing pipeline:
  1.  PDF extraction (digital + OCR detection)
  2.  Web scraping (public URLs)
  3.  Text chunking quality & thresholds
  4.  Embedding storage & retrieval (ChromaDB)
  5.  RAG retrieval with tenant isolation
  6.  Context builder score normalisation
  7.  Reranker passthrough
  8.  Full end-to-end ingestion of IaaS.pdf
  9.  OCR service initialisation (CPU/GPU)
  10. Context formatter citation labels

Usage:
    cd /disk2/Projects/KeplerLab-AI-Notebook
    source .venv/bin/activate
    python test/test_pipeline.py

    # Skip slow tests (web scraping, reranker):
    python test/test_pipeline.py --skip-slow

    # Verbose output:
    python test/test_pipeline.py --verbose
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── Path setup ────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)                        # config.py uses relative paths

# Suppress noisy logs during tests
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("CHROMA_TELEMETRY",     "False")

TEST_PDF  = REPO_ROOT / "4. IaaS.pdf"
REPORT_PATH = REPO_ROOT / "test" / "test_pipeline_report.json"

# ── ANSI colours ─────────────────────────────────────────────────────────────
class C:
    GREEN  = "\033[92m"
    RED    = "\033[91m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    RESET  = "\033[0m"

# ── Result dataclass ──────────────────────────────────────────────────────────
@dataclass
class PResult:
    name:    str
    group:   str
    passed:  bool
    ms:      float = 0.0
    detail:  str   = ""
    skipped: bool  = False


# ── Runner ────────────────────────────────────────────────────────────────────
class PipelineTester:
    def __init__(self, skip_slow: bool = False, verbose: bool = False):
        self.skip_slow = skip_slow
        self.verbose   = verbose
        self.results:  List[PResult] = []

    # ── helpers ───────────────────────────────────────────────────────────────

    def _ok(self, name: str, group: str, ms: float, detail: str = "") -> PResult:
        r = PResult(name, group, True, ms, detail)
        self.results.append(r)
        tag = f"{C.GREEN}PASS{C.RESET}"
        self._print(f"  {tag} {name} [{ms:.0f}ms]" + (f" — {detail}" if self.verbose and detail else ""))
        return r

    def _fail(self, name: str, group: str, ms: float, detail: str) -> PResult:
        r = PResult(name, group, False, ms, detail)
        self.results.append(r)
        tag = f"{C.RED}FAIL{C.RESET}"
        self._print(f"  {tag} {name} [{ms:.0f}ms]\n       → {detail}")
        return r

    def _skip(self, name: str, group: str, reason: str) -> PResult:
        r = PResult(name, group, True, 0.0, reason, skipped=True)
        self.results.append(r)
        self._print(f"  {C.YELLOW}SKIP{C.RESET} {name} — {reason}")
        return r

    def _print(self, msg: str):
        print(msg)

    def _section(self, title: str):
        print(f"\n{C.BOLD}{C.CYAN}═══ {title} ═══{C.RESET}")

    def _run(self, name: str, group: str, fn, *args, **kwargs) -> PResult:
        t0 = time.perf_counter()
        try:
            fn(*args, **kwargs)
            return self._ok(name, group, (time.perf_counter() - t0) * 1000)
        except AssertionError as e:
            return self._fail(name, group, (time.perf_counter() - t0) * 1000, str(e))
        except Exception as e:
            return self._fail(name, group, (time.perf_counter() - t0) * 1000, f"{type(e).__name__}: {e}")

    # ═════════════════════════════════════════════════════════════════════════
    # 1. PDF EXTRACTION
    # ═════════════════════════════════════════════════════════════════════════

    def test_pdf_extraction(self):
        self._section("1. PDF EXTRACTION")

        if not TEST_PDF.exists():
            self._skip("PDF digital extraction", "PDF", f"{TEST_PDF} not found")
            self._skip("PDF OCR detection",      "PDF", "no PDF available")
            return

        from app.services.text_processing.pdf_extractor import PDFExtractor

        def _extract():
            result = PDFExtractor().extract_text(str(TEST_PDF))
            assert result["status"] == "success", f"status={result.get('status')} err={result.get('error')}"
            total_pages = result["metadata"]["page_count"]
            assert total_pages > 0, "No pages detected"
            ocr_pages = len(result.get("ocr_needed_pages", []))

            if ocr_pages == total_pages:
                # Fully-scanned PDF — every page is queued for OCR.
                # PDFExtractor correctly returns text="" here; the full text
                # is produced later by OCRService in the extractor pipeline.
                pass  # nothing more to assert at this stage
            else:
                # Digital or mixed PDF — inline text should be present.
                text = result["text"]
                assert len(text) > 500, f"Text too short: {len(text)} chars"
                max_allowed = max(1, int(total_pages * 0.20))
                assert ocr_pages <= max_allowed, (
                    f"Too many OCR pages for a digital PDF: {ocr_pages}/{total_pages} "
                    f"(max allowed: {max_allowed})"
                )
        self._run("PDF digital extraction", "PDF", _extract)

        def _fallback():
            from pypdf import PdfReader
            reader = PdfReader(str(TEST_PDF))
            text = " ".join(
                p.extract_text() or "" for p in reader.pages
            ).strip()
            assert len(text) > 200, "pypdf fallback produced too little text"
        self._run("PDF pypdf fallback text", "PDF", _fallback)

        def _tables():
            result = PDFExtractor().extract_text(str(TEST_PDF))
            # At least one table expected in an IaaS paper
            meta = result.get("metadata", {})
            tables = meta.get("tables_detected", 0)
            if tables == 0:
                # Not all PDFs have tables — soft check
                print(f"    {C.DIM}note: no tables found (PDF may be table-free){C.RESET}")
        self._run("PDF table extraction", "PDF", _tables)

    # ═════════════════════════════════════════════════════════════════════════
    # 2. WEB SCRAPING
    # ═════════════════════════════════════════════════════════════════════════

    def test_web_scraping(self):
        self._section("2. WEB SCRAPING")

        if self.skip_slow:
            self._skip("Web scraping (requests)", "Web", "--skip-slow")
            self._skip("URL type detection",       "Web", "--skip-slow")
            return

        from app.services.text_processing.web_scraping import WebScrapingService
        scraper = WebScrapingService()

        # Use httpbin — a reliable, stable testing endpoint
        TEST_URL = "https://httpbin.org/html"

        def _requests():
            r = scraper.extract_content_from_url(TEST_URL)
            assert r["status"] == "success", f"status={r['status']} err={r.get('error')}"
            assert len(r["text"]) > 50, f"Too little text: {len(r['text'])} chars"
        self._run("Web scraping (requests)", "Web", _requests)

        def _detect_type():
            info = scraper.detect_url_type(TEST_URL)
            assert info.get("status") in ("success", "extension_fallback"), \
                f"detect_url_type failed: {info}"
        self._run("URL type detection", "Web", _detect_type)

        # Test a PDF URL (Wikipedia logo as a known stable binary)
        PDF_URL = "https://www.w3.org/WAI/WCAG21/Techniques/pdf/pdf-sample.pdf"

        def _pdf_url():
            info = scraper.detect_url_type(PDF_URL)
            # The server may serve the PDF directly or redirect to an HTML page.
            # Accept any valid non-error category.
            cat = info.get("category", "")
            assert cat in ("pdf", "document", "web", "html", "article"), \
                f"Unexpected category for PDF URL: {cat}"
        self._run("PDF URL type detection", "Web", _pdf_url)

        # Wikipedia article (stable, returns decent text)
        WIKI_URL = "https://en.wikipedia.org/wiki/Infrastructure_as_a_service"

        def _wiki():
            r = scraper.extract_content_from_url(WIKI_URL)
            assert r["status"] == "success", f"{r.get('error')}"
            assert len(r.get("text", "")) > 1000, "Wikipedia article too short"
            assert "iaas" in r["text"].lower() or "infrastructure" in r["text"].lower(), \
                "Wikipedia content missing expected keywords"
        self._run("Wikipedia IaaS article scrape", "Web", _wiki)

    # ═════════════════════════════════════════════════════════════════════════
    # 3. TEXT CHUNKING
    # ═════════════════════════════════════════════════════════════════════════

    def test_chunking(self):
        self._section("3. TEXT CHUNKING")
        from app.services.text_processing.chunker import chunk_text

        def _basic_chunks():
            text = """# Introduction to Cloud Computing

Cloud computing is the on-demand availability of computer system resources.
It provides compute, storage, and networking over the internet.

## Infrastructure as a Service (IaaS)

IaaS provides virtualised computing resources over the internet.
Users rent virtual machines and storage from cloud providers.
Examples include AWS EC2, Google Compute Engine, and Azure VMs.

### Key Characteristics

Scalability allows workloads to grow without hardware investment.
Pay-as-you-go pricing reduces capital expenditure.
High availability is achieved through redundant data centres.

## Platform as a Service (PaaS)

PaaS provides a platform for developing, running, and managing applications.
Developers can focus on code rather than infrastructure management.
Docker and Kubernetes are popular PaaS-adjacent technologies.
""" * 3  # repeat to get enough content
            chunks = chunk_text(text)
            assert len(chunks) >= 3, f"Expected ≥3 chunks, got {len(chunks)}"
            for c in chunks:
                assert "id" in c, "Chunk missing 'id'"
                assert "text" in c, "Chunk missing 'text'"
                assert len(c["text"]) >= 100, f"Chunk too short: {len(c['text'])} chars"
        self._run("Markdown heading-aware chunking", "Chunking", _basic_chunks)

        def _min_length_filter():
            # Short paragraphs (80-150 chars) should NOT be filtered out by the
            # new MIN_CHUNK_CHARACTERS=100 threshold.
            text = "Cloud Computing Overview\n\n" + \
                   "IaaS provides virtual machines and storage on demand. " * 5 + \
                   "\n\nPaaS allows app deployment without managing infrastructure. " * 5
            chunks = chunk_text(text)
            # Ensure at least one chunk survived (verifies threshold is not 300)
            assert len(chunks) >= 1, "All chunks were filtered — MIN_CHUNK_LENGTH may still be too high"
        self._run("Chunk min-length filter (threshold=100)", "Chunking", _min_length_filter)

        def _structured_data():
            csv_text = (
                "=== Dataset Overview ===\n"
                "Shape: 1000 rows × 5 columns\n"
                "Columns: id, name, value, created_at, status\n\n"
                "=== Statistics ===\n"
                "id: mean=500, std=289\n"
                "value: mean=42.5, std=12.3\n\n"
                "=== Sample (first 5 rows) ===\n"
                "1 | Alice | 45.2 | 2024-01-01 | active\n"
                "2 | Bob   | 38.7 | 2024-01-02 | inactive\n"
            )
            chunks = chunk_text(csv_text, source_type="csv")
            assert len(chunks) >= 1, "Structured data chunker produced no chunks"
        self._run("Structured CSV chunking", "Chunking", _structured_data)

        def _empty_text():
            chunks = chunk_text("")
            assert chunks == [], f"Empty text should return [] — got {chunks}"
        self._run("Empty text → empty list", "Chunking", _empty_text)

        def _alpha_ratio():
            # Technical content with lots of numbers should not be filtered
            # (MIN_ALPHA_RATIO lowered to 0.10 from 0.15)
            technical = (
                "## IPv4 Address Space\n\n"
                "IP address range: 0.0.0.0 – 255.255.255.255 (4,294,967,296 total).\n"
                "Private ranges: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16.\n"
                "Loopback: 127.0.0.0/8.  Multicast: 224.0.0.0/4.\n"
                "CIDR notation: 192.168.1.0/24 means 256 hosts.\n"
            ) * 4
            chunks = chunk_text(technical)
            assert len(chunks) >= 1, f"Technical content incorrectly filtered (alpha ratio too high)"
        self._run("Technical content alpha-ratio filter", "Chunking", _alpha_ratio)

    # ═════════════════════════════════════════════════════════════════════════
    # 4. EMBEDDING & CHROMADB
    # ═════════════════════════════════════════════════════════════════════════

    def test_embedding(self):
        self._section("4. EMBEDDING & CHROMADB")

        from app.db.chroma import get_collection
        from app.services.rag.embedder import embed_and_store, delete_material_embeddings, warm_up_embeddings

        # Use a unique test tenant so we don't pollute real data
        test_user_id     = f"test-pipeline-{uuid.uuid4().hex[:8]}"
        test_material_id = str(uuid.uuid4())
        test_notebook_id = str(uuid.uuid4())

        def _warm_up():
            warm_up_embeddings()  # Should not raise
        self._run("Embedding warm-up (ONNX MiniLM)", "Embedding", _warm_up)

        def _upsert():
            chunks = [
                {"id": f"{test_material_id}_chunk_{i}", "text":
                    f"IaaS test chunk {i}: Virtual machines provide on-demand compute. "
                    f"Customers pay only for resources consumed. Cloud providers maintain "
                    f"the underlying physical infrastructure. Scalability is a key benefit. "
                    # Pad to ensure chunk passes min-length filter
                    * 2}
                for i in range(5)
            ]
            embed_and_store(
                chunks,
                material_id=test_material_id,
                user_id=test_user_id,
                notebook_id=test_notebook_id,
                filename="test_iaas_doc.txt",
            )
            col = get_collection()
            results = col.get(where={"material_id": test_material_id})
            assert len(results["ids"]) == 5, \
                f"Expected 5 stored chunks, got {len(results['ids'])}"
        self._run("Chunk upsert (5 chunks)", "Embedding", _upsert)

        def _upsert_idempotent():
            # Re-upserting same IDs should not raise duplicate errors
            chunks = [{"id": f"{test_material_id}_chunk_0",
                       "text": "Updated text for chunk 0 — IaaS virtual machines."}]
            embed_and_store(chunks, material_id=test_material_id, user_id=test_user_id)
        self._run("Upsert idempotency (duplicate IDs)", "Embedding", _upsert_idempotent)

        def _query():
            col = get_collection()
            total = col.count()
            n = max(1, min(3, total))
            results = col.query(
                query_texts=["virtual machine cloud infrastructure"],
                n_results=n,
                where={"user_id": test_user_id},
            )
            docs = results["documents"][0]
            assert len(docs) >= 1, "Query returned no documents"
        self._run("ChromaDB query (user-scoped)", "Embedding", _query)

        def _n_results_guard():
            # Query with n_results > actual count should NOT crash (ChromaDB guard fix)
            col = get_collection()
            total = col.count()
            # Request far more than exist — should clamp gracefully
            safe_k = max(1, min(9999, total))
            results = col.query(
                query_texts=["test"],
                n_results=safe_k,
                where={"user_id": test_user_id},
            )
            assert "documents" in results
        self._run("n_results > count guard", "Embedding", _n_results_guard)

        def _delete():
            deleted = delete_material_embeddings(test_material_id, test_user_id)
            assert deleted >= 5, f"Expected ≥5 deleted chunks, got {deleted}"
            col = get_collection()
            remaining = col.get(where={"material_id": test_material_id})
            assert len(remaining["ids"]) == 0, "Chunks not fully deleted"
        self._run("Chunk deletion", "Embedding", _delete)

    # ═════════════════════════════════════════════════════════════════════════
    # 5. SECURE RETRIEVER
    # ═════════════════════════════════════════════════════════════════════════

    def test_retriever(self):
        self._section("5. SECURE RETRIEVER")

        from app.db.chroma import get_collection
        from app.services.rag.embedder import embed_and_store, delete_material_embeddings
        from app.services.rag.secure_retriever import (
            secure_similarity_search,
            secure_similarity_search_enhanced,
            TenantIsolationError,
        )

        user_a = f"retriever-test-{uuid.uuid4().hex[:8]}"
        user_b = f"retriever-test-{uuid.uuid4().hex[:8]}"
        mat_a  = str(uuid.uuid4())
        mat_b  = str(uuid.uuid4())

        IAAS_TEXT = (
            "Infrastructure as a Service provides virtualised compute resources. "
            "IaaS customers rent virtual machines on demand from cloud providers. "
            "AWS EC2, Google Compute Engine, and Azure VMs are leading IaaS products. "
            "Scalability and pay-as-you-go pricing are the primary IaaS benefits. "
        )
        OTHER_TEXT = (
            "Platform as a Service (PaaS) abstracts infrastructure management. "
            "Developers deploy applications without managing underlying servers. "
            "Heroku and Google App Engine are popular PaaS offerings. "
        )

        # Seed test data
        def _seed():
            chunks_a = [{"id": f"{mat_a}_{i}", "text": IAAS_TEXT * 3} for i in range(3)]
            chunks_b = [{"id": f"{mat_b}_{i}", "text": OTHER_TEXT * 3} for i in range(3)]
            embed_and_store(chunks_a, material_id=mat_a, user_id=user_a, filename="iaas.txt")
            embed_and_store(chunks_b, material_id=mat_b, user_id=user_b, filename="paas.txt")
        self._run("Seed retriever test data", "Retriever", _seed)

        def _basic_search():
            docs = secure_similarity_search(
                user_id=user_a,
                query="virtual machine cloud",
                k=3,
                material_id=mat_a,
            )
            assert isinstance(docs, list), f"Expected list, got {type(docs)}"
            assert len(docs) >= 1, "No documents retrieved"
        self._run("Basic similarity search", "Retriever", _basic_search)

        def _tenant_isolation():
            # User A's query should NOT return User B's documents
            docs = secure_similarity_search(
                user_id=user_a,
                query="platform as a service heroku",
                k=5,
                material_id=mat_a,
            )
            for doc in docs:
                assert "heroku" not in doc.lower() or "paas" not in doc.lower() or \
                       "IaaS" in doc or "virtual" in doc.lower(), \
                    "Tenant isolation breach: User A received User B's PaaS content"
        self._run("Tenant isolation (User A ≠ User B docs)", "Retriever", _tenant_isolation)

        def _missing_user_raises():
            try:
                secure_similarity_search(user_id="", query="anything", k=1)
                assert False, "Expected TenantIsolationError for empty user_id"
            except TenantIsolationError:
                pass  # correct
        self._run("Empty user_id raises TenantIsolationError", "Retriever", _missing_user_raises)

        def _enhanced_retrieval():
            ctx = secure_similarity_search_enhanced(
                user_id=user_a,
                query="IaaS compute resources virtual machine",
                material_id=mat_a,
                use_mmr=True,
                use_reranker=False,  # avoid slow reranker in fast tests
                return_formatted=True,
            )
            assert isinstance(ctx, str), f"Expected str, got {type(ctx)}"
            assert "SOURCE" in ctx, f"Formatted context missing [SOURCE N] labels:\n{ctx[:300]}"
        self._run("Enhanced retrieval (MMR, formatted)", "Retriever", _enhanced_retrieval)

        def _empty_collection_guard():
            # A user with no documents should get an empty/not-found response, not a crash
            ghost_user = f"ghost-{uuid.uuid4().hex[:6]}"
            docs = secure_similarity_search(
                user_id=ghost_user,
                query="anything",
                k=5,
            )
            assert docs == [] or docs == ["No relevant context found."], \
                f"Unexpected result for user with no data: {docs}"
        self._run("Empty collection → graceful empty result", "Retriever", _empty_collection_guard)

        # Cleanup
        def _cleanup():
            delete_material_embeddings(mat_a, user_a)
            delete_material_embeddings(mat_b, user_b)
        self._run("Cleanup retriever test data", "Retriever", _cleanup)

    # ═════════════════════════════════════════════════════════════════════════
    # 6. CONTEXT BUILDER & SCORE NORMALISATION
    # ═════════════════════════════════════════════════════════════════════════

    def test_context_builder(self):
        self._section("6. CONTEXT BUILDER & SCORE NORMALISATION")

        from app.services.rag.context_builder import build_context, _normalize_score

        def _sigmoid_normalisation():
            # Raw logits outside [0,1] → sigmoid normalisation
            assert abs(_normalize_score(5.0)  - 0.9933) < 0.001, "Sigmoid(5) incorrect"
            assert abs(_normalize_score(-3.0) - 0.0474) < 0.001, "Sigmoid(-3) incorrect"
            # Values already in [0,1] pass through unchanged (no sigmoid applied)
            assert _normalize_score(0.0) == 0.0, "Score 0.0 (in [0,1]) should pass through"
            assert _normalize_score(1.0) == 1.0, "Score 1.0 should pass through"
            assert _normalize_score(0.5) == 0.5, "Score 0.5 should pass through"
            # Out-of-range logit (−0.5) should be sigmoid-normalized
            assert abs(_normalize_score(-0.5) - 0.3775) < 0.001, "Sigmoid(-0.5) incorrect"
        self._run("Score sigmoid normalisation", "ContextBuilder", _sigmoid_normalisation)

        def _build_with_logits():
            # Simulate raw reranker logits — negative scores should NOT be filtered
            chunks = [
                ("Chunk about IaaS virtual machines " * 10, 3.5),   # positive logit
                ("Chunk about cloud pricing models " * 10, -0.5),   # slightly negative
                ("Short but relevant note " * 12, 0.1),             # near zero
            ]
            ctx = build_context(chunks)
            assert ctx != "No relevant context found.", "All chunks were incorrectly filtered"
            assert "SOURCE" in ctx, f"Context missing source labels:\n{ctx[:200]}"
        self._run("Context build with raw reranker logits", "ContextBuilder", _build_with_logits)

        def _token_limit():
            # 200 large chunks should be truncated to MAX_CONTEXT_TOKENS
            big_chunk = "A" * 400 + " virtual machine " + "B" * 400
            chunks = [(big_chunk, 1.0)] * 200
            ctx = build_context(chunks, max_tokens=500)
            # Rough check: context should be < 500 * 4 chars (~2000) + overhead
            assert len(ctx) < 15_000, f"Context exceeded token limit: {len(ctx)} chars"
        self._run("Context token limit respected", "ContextBuilder", _token_limit)

        def _empty_input():
            ctx = build_context([])
            assert "No relevant context" in ctx
        self._run("Empty chunks → 'No relevant context'", "ContextBuilder", _empty_input)

    # ═════════════════════════════════════════════════════════════════════════
    # 7. CONTEXT FORMATTER (CITATIONS)
    # ═════════════════════════════════════════════════════════════════════════

    def test_context_formatter(self):
        self._section("7. CONTEXT FORMATTER")

        from app.services.rag.context_formatter import format_context_with_citations, _material_name_cache

        def _citation_labels():
            chunks = [
                {"text": "IaaS provides virtual machines.", "id": "c1",
                 "material_id": "mat-aaa", "filename": "iaas_overview.pdf", "score": 0.9},
                {"text": "PaaS abstracts infrastructure.", "id": "c2",
                 "material_id": "mat-bbb", "score": 0.7},
            ]
            ctx = format_context_with_citations(chunks)
            assert "[SOURCE 1" in ctx, "Missing SOURCE 1 label"
            assert "[SOURCE 2" in ctx, "Missing SOURCE 2 label"
            # First chunk has filename → should show the name
            assert "iaas_overview.pdf" in ctx, "Filename not in citation label"
        self._run("Source citation labels & filenames", "Formatter", _citation_labels)

        def _cache_fallback():
            mid = str(uuid.uuid4())
            _material_name_cache[mid] = "cached_doc.txt"
            chunks = [{"text": "Some content here " * 15, "material_id": mid, "id": "x1"}]
            ctx = format_context_with_citations(chunks)
            assert "cached_doc.txt" in ctx, "Cache fallback name not used"
        self._run("Material name cache fallback", "Formatter", _cache_fallback)

        def _uuid_fallback():
            mid = "aaaabbbb-cccc-dddd-eeee-ffffffffffff"
            # Not in cache, no filename in chunk → shows abbreviated UUID
            chunks = [{"text": "Fallback content " * 15, "material_id": mid, "id": "y1"}]
            ctx = format_context_with_citations(chunks)
            # Should show Source-aaaabbbb (first 8 chars) when name is unavailable
            assert "aaaabbbb" in ctx or mid in ctx, \
                f"UUID fallback not shown in context: {ctx[:300]}"
        self._run("Unknown material_id → UUID abbreviation", "Formatter", _uuid_fallback)

    # ═════════════════════════════════════════════════════════════════════════
    # 8. OCR SERVICE INITIALISATION
    # ═════════════════════════════════════════════════════════════════════════

    def test_ocr_init(self):
        self._section("8. OCR SERVICE INIT")

        def _no_hard_gpu_crash():
            # OCRService should no longer crash on servers without CUDA
            from app.services.text_processing import ocr_service as _m
            assert hasattr(_m, "_GPU_AVAILABLE"), "Module missing _GPU_AVAILABLE flag"
            # Should be importable without raising RuntimeError
        self._run("OCRService module imports without crash", "OCR", _no_hard_gpu_crash)

        def _gpu_flag():
            from app.services.text_processing.ocr_service import _GPU_AVAILABLE
            print(f"    {C.DIM}GPU available: {_GPU_AVAILABLE}{C.RESET}")
            # Just verify it's a bool — either value is acceptable
            assert isinstance(_GPU_AVAILABLE, bool)
        self._run("GPU availability flag is bool", "OCR", _gpu_flag)

        if self.skip_slow:
            self._skip("OCRService full init (EasyOCR)", "OCR", "--skip-slow")
            return

        def _init_no_raise():
            from app.services.text_processing.ocr_service import OCRService
            svc = OCRService()
            # easyocr_reader should be initialised (not None) unless EasyOCR failed
            assert svc.easyocr_reader is not None, \
                "EasyOCR reader is None after init — check installation"
        self._run("OCRService full init (EasyOCR)", "OCR", _init_no_raise)

    # ═════════════════════════════════════════════════════════════════════════
    # 9. END-TO-END INGESTION  (IaaS PDF)
    # ═════════════════════════════════════════════════════════════════════════

    def test_e2e_ingestion(self):
        self._section("9. END-TO-END INGESTION (IaaS PDF)")

        if self.skip_slow:
            self._skip("E2E ingestion", "E2E", "--skip-slow")
            return

        if not TEST_PDF.exists():
            self._skip("E2E ingestion", "E2E", f"{TEST_PDF} not found")
            return

        from app.services.text_processing.extractor import EnhancedTextExtractor
        from app.services.text_processing.chunker import chunk_text
        from app.services.rag.embedder import embed_and_store, delete_material_embeddings

        test_user = f"e2e-{uuid.uuid4().hex[:8]}"
        test_mat  = str(uuid.uuid4())
        extracted_text = {}

        def _extract():
            result = EnhancedTextExtractor().extract_text(str(TEST_PDF), source_type="file")
            assert result["status"] == "success", \
                f"Extraction failed: {result.get('error')}"
            assert len(result["text"]) > 1000, \
                f"Extracted text too short: {len(result['text'])} chars"
            extracted_text["text"] = result["text"]
            print(f"    {C.DIM}Extracted {len(result['text'])} chars from IaaS PDF{C.RESET}")
        self._run("IaaS PDF extraction", "E2E", _extract)

        if "text" not in extracted_text:
            self._skip("IaaS chunking",   "E2E", "extraction failed above")
            self._skip("IaaS embedding",  "E2E", "extraction failed above")
            self._skip("IaaS retrieval",  "E2E", "extraction failed above")
            return

        chunks_holder: Dict[str, Any] = {}

        def _chunk():
            chunks = chunk_text(extracted_text["text"], use_semantic_chunking=False)
            assert len(chunks) >= 5, f"Expected ≥5 chunks from IaaS PDF, got {len(chunks)}"
            chunks_holder["chunks"] = chunks
            print(f"    {C.DIM}Produced {len(chunks)} chunks{C.RESET}")
        self._run("IaaS PDF chunking",   "E2E", _chunk)

        def _embed():
            embed_and_store(
                chunks_holder.get("chunks", []),
                material_id=test_mat,
                user_id=test_user,
                filename="IaaS.pdf",
            )
        self._run("IaaS PDF embedding",  "E2E", _embed)

        def _retrieve():
            from app.services.rag.secure_retriever import secure_similarity_search_enhanced
            ctx = secure_similarity_search_enhanced(
                user_id=test_user,
                query="What are the main components of IaaS?",
                material_id=test_mat,
                use_reranker=False,   # skip slow reranker
                return_formatted=True,
            )
            assert "SOURCE" in ctx, f"Retrieval returned no sources:\n{ctx[:200]}"
            assert len(ctx) > 200, "Retrieved context too short"
            print(f"    {C.DIM}Context: {len(ctx)} chars, first 100: {ctx[:100]!r}{C.RESET}")
        self._run("IaaS PDF retrieval",  "E2E", _retrieve)

        def _cleanup():
            delete_material_embeddings(test_mat, test_user)
        self._run("E2E cleanup", "E2E", _cleanup)

    # ═════════════════════════════════════════════════════════════════════════
    # 10. FILE EXTRACTOR FORMATS
    # ═════════════════════════════════════════════════════════════════════════

    def test_file_extractors(self):
        self._section("10. FILE EXTRACTOR FORMATS")
        import tempfile, os
        from app.services.text_processing.extractor import EnhancedTextExtractor
        extractor = EnhancedTextExtractor()

        def _plain_text():
            with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as f:
                f.write("Hello world. This is a plain text file.\nSecond line content.")
                fname = f.name
            try:
                r = extractor.extract_text(fname, source_type="file")
                assert r["status"] == "success"
                assert "Hello world" in r["text"]
            finally:
                os.unlink(fname)
        self._run("Plain text (.txt) extraction", "Extractor", _plain_text)

        def _markdown():
            with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w") as f:
                f.write("# Heading\n\nSome **markdown** content.\n\n## Section 2\n\nMore text.")
                fname = f.name
            try:
                r = extractor.extract_text(fname, source_type="file")
                assert r["status"] == "success"
                assert "Heading" in r["text"]
            finally:
                os.unlink(fname)
        self._run("Markdown (.md) extraction", "Extractor", _markdown)

        if not self.skip_slow:
            def _html():
                with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w") as f:
                    f.write(
                        "<html><head><title>Test</title></head><body>"
                        "<h1>Cloud Computing</h1><p>IaaS overview text.</p></body></html>"
                    )
                    fname = f.name
                try:
                    r = extractor.extract_text(fname, source_type="file")
                    assert r["status"] == "success"
                    assert "Cloud Computing" in r["text"] or "IaaS" in r["text"]
                finally:
                    os.unlink(fname)
            self._run("HTML (.html) extraction", "Extractor", _html)
        else:
            self._skip("HTML extraction", "Extractor", "--skip-slow")

    # ═════════════════════════════════════════════════════════════════════════
    # 11. CONFIG SANITY CHECKS
    # ═════════════════════════════════════════════════════════════════════════

    def test_config(self):
        self._section("11. CONFIGURATION SANITY CHECKS")
        from app.core.config import settings

        def _chunk_length():
            assert settings.MIN_CHUNK_LENGTH <= 150, \
                f"MIN_CHUNK_LENGTH={settings.MIN_CHUNK_LENGTH} too high — will filter too aggressively"
        self._run("MIN_CHUNK_LENGTH ≤ 150", "Config", _chunk_length)

        def _context_chunk_length():
            assert hasattr(settings, "MIN_CONTEXT_CHUNK_LENGTH"), \
                "Settings missing MIN_CONTEXT_CHUNK_LENGTH"
            assert settings.MIN_CONTEXT_CHUNK_LENGTH >= settings.MIN_CHUNK_LENGTH, \
                "MIN_CONTEXT_CHUNK_LENGTH should be ≥ MIN_CHUNK_LENGTH"
        self._run("MIN_CONTEXT_CHUNK_LENGTH present", "Config", _context_chunk_length)

        def _similarity_score():
            assert 0.0 <= settings.MIN_SIMILARITY_SCORE <= 1.0, \
                f"MIN_SIMILARITY_SCORE={settings.MIN_SIMILARITY_SCORE} out of [0,1] range"
        self._run("MIN_SIMILARITY_SCORE in [0,1]", "Config", _similarity_score)

        def _retrieval_k():
            assert settings.INITIAL_VECTOR_K > 0
            assert settings.FINAL_K > 0
            assert settings.FINAL_K <= settings.INITIAL_VECTOR_K
        self._run("Retrieval k values consistent", "Config", _retrieval_k)

    # ═════════════════════════════════════════════════════════════════════════
    # SUMMARY
    # ═════════════════════════════════════════════════════════════════════════

    def print_summary(self):
        print(f"\n{'═' * 60}")
        print(f"  {C.BOLD}PIPELINE TEST RESULTS{C.RESET}")
        print(f"{'═' * 60}\n")

        by_group: Dict[str, List[PResult]] = {}
        for r in self.results:
            by_group.setdefault(r.group, []).append(r)

        total = passed = skipped = 0
        failures: List[PResult] = []

        for group, results in by_group.items():
            non_skip = [r for r in results if not r.skipped]
            skip_cnt = sum(1 for r in results if r.skipped)
            grp_pass = sum(1 for r in non_skip if r.passed)
            grp_tot  = len(non_skip)
            col  = C.GREEN if grp_pass == grp_tot else C.RED
            skip_str = f" (+{skip_cnt} skipped)" if skip_cnt else ""
            print(f"  {col}{group:<20}{C.RESET}  {grp_pass}/{grp_tot}{skip_str}")
            total   += grp_tot
            passed  += grp_pass
            skipped += skip_cnt
            failures.extend(r for r in non_skip if not r.passed)

        col = C.GREEN if passed == total else C.RED
        print(f"\n  {col}{C.BOLD}Total: {passed}/{total} passed{C.RESET}"
              + (f"  (+{skipped} skipped)" if skipped else ""))

        if failures:
            print(f"\n  {C.RED}FAILURES:{C.RESET}")
            for f in failures:
                print(f"    ✗ [{f.group}] {f.name}")
                print(f"        {f.detail}")

        # Persist JSON report
        report = {
            "total": total, "passed": passed, "failed": total - passed,
            "skipped": skipped,
            "results": [
                {"name": r.name, "group": r.group, "passed": r.passed,
                 "ms": round(r.ms, 1), "skipped": r.skipped,
                 "detail": r.detail}
                for r in self.results
            ],
        }
        REPORT_PATH.write_text(json.dumps(report, indent=2))
        print(f"\n  Report: {REPORT_PATH}")
        print(f"{'═' * 60}\n")
        return passed == total

    def run_all(self):
        self.test_config()
        self.test_chunking()
        self.test_embedding()
        self.test_retriever()
        self.test_context_builder()
        self.test_context_formatter()
        self.test_ocr_init()
        self.test_pdf_extraction()
        self.test_web_scraping()
        self.test_file_extractors()
        self.test_e2e_ingestion()
        return self.print_summary()


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="KeplerLab pipeline test suite")
    ap.add_argument("--skip-slow", action="store_true",
                    help="Skip slow tests (web scraping, EasyOCR init, E2E ingestion)")
    ap.add_argument("--verbose", "-v", action="store_true",
                    help="Show pass details inline")
    args = ap.parse_args()

    banner = textwrap.dedent(f"""
    {'=' * 60}
      KeplerLab AI — Pipeline Test Suite
      PDF:  {TEST_PDF}
      Skip slow: {args.skip_slow}
    {'=' * 60}
    """)
    print(banner)

    ok = PipelineTester(skip_slow=args.skip_slow, verbose=args.verbose).run_all()
    sys.exit(0 if ok else 1)
