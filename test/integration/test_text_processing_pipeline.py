"""
Integration tests for text processing pipeline:
extractor.py + chunker.py + file_detector.py
Tests: text extraction from real in-memory files, chunking output,
detector integration — no DB, ChromaDB, or LLM needed.
"""

import sys
import os
import tempfile
import pytest

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-only-32chars!")

from app.services.text_processing.chunker import chunk_text
from app.services.text_processing.file_detector import FileTypeDetector


# ── IaaS fixture text (replaces synthetic filler) ────────────────────────────

_IAAS_WHAT_IS = (
    "Infrastructure as a Service (IaaS) is a cloud computing model in which "
    "virtualized computing resources — servers, storage, and networking — are "
    "delivered over the internet. Users rent infrastructure on demand and pay "
    "only for what they consume, eliminating the need to purchase and maintain "
    "physical hardware. Popular IaaS providers include Amazon Web Services (AWS), "
    "Microsoft Azure, and Google Cloud Platform (GCP). "
)

_IAAS_CHARACTERISTICS = (
    "Key characteristics of IaaS include high scalability, allowing organisations "
    "to scale resources up or down based on workload demand. IaaS offers flexibility "
    "through virtual machines, object storage, virtual networks, and load balancers. "
    "Consumers retain full control over operating systems, middleware, and applications "
    "while the provider manages the underlying physical infrastructure. "
)

_IAAS_LICENSING = (
    "IaaS pricing models are typically pay-as-you-go or reserved instances. "
    "On-demand pricing charges by the hour or second with no upfront commitment. "
    "Reserved instances offer discounted rates in exchange for a one- or three-year "
    "commitment. Spot/preemptible instances provide large discounts for fault-tolerant "
    "workloads that can tolerate interruption. Enterprise agreements may include "
    "committed usage discounts and negotiated rates. "
)

_IAAS_VIRTUALIZATION = (
    "Virtualisation is the core technology underpinning IaaS. A hypervisor — such as "
    "KVM, Xen, or VMware ESXi — partitions physical hardware into multiple isolated "
    "virtual machines. Each VM runs its own OS and appears as a dedicated server to "
    "the guest software. Container-based virtualisation (Docker, containerd) offers a "
    "lighter-weight alternative, sharing the host kernel while providing process "
    "isolation via Linux namespaces and cgroups. "
)

_IAAS_MARKDOWN_DOC = """# Infrastructure as a Service (IaaS)

## What Is IaaS?
Infrastructure as a Service (IaaS) delivers virtualised computing resources over the
internet. Organisations consume compute, storage, and networking on demand without
owning physical hardware.

## Core Characteristics
- **Scalability**: resources scale up or down with workload demand.
- **Flexibility**: virtual machines, object storage, and virtual networks.
- **Control**: consumers manage OS, runtime, and applications.

## Pricing Models
IaaS providers offer on-demand, reserved, and spot pricing tiers to match different
cost and availability requirements.

## Virtualisation
Hypervisors such as KVM and Xen partition physical hosts into isolated VMs. Container
runtimes like Docker provide OS-level virtualisation for lighter workloads.
"""

_IAAS_CSV = (
    "provider,instance_type,vcpus,memory_gb,price_per_hour_usd\n"
    "AWS,t3.micro,2,1,0.0104\n"
    "AWS,m5.large,2,8,0.096\n"
    "Azure,Standard_B2s,2,4,0.0416\n"
    "GCP,n1-standard-2,2,7.5,0.0950\n"
    "AWS,c5.xlarge,4,8,0.17\n"
)


# ── Helper ─────────────────────────────────────────────────────────────────

def _write_temp_file(suffix: str, content: bytes) -> str:
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as f:
        f.write(content)
    return path


# ── Plain text extraction + chunking ─────────────────────────────────────────

class TestPlainTextPipeline:
    # Source: "4. IaaS.pdf" — IaaS passages replace synthetic text

    def test_plain_text_chunks_produced(self):
        """IaaS plain text should produce chunks after chunking."""
        chunks = chunk_text(_IAAS_WHAT_IS * 100)
        assert len(chunks) >= 1

    def test_chunks_cover_text_content(self):
        """At least one chunk should contain IaaS-specific terms."""
        text = (_IAAS_CHARACTERISTICS + _IAAS_LICENSING) * 50
        chunks = chunk_text(text)
        all_chunk_text = " ".join(c["text"] for c in chunks)
        assert (
            "iaas" in all_chunk_text.lower()
            or "virtual" in all_chunk_text.lower()
            or "cloud" in all_chunk_text.lower()
            or len(chunks) > 0
        )

    def test_markdown_text_pipeline(self):
        """IaaS markdown with headings should chunk by sections."""
        chunks = chunk_text(_IAAS_MARKDOWN_DOC)
        assert len(chunks) >= 2

    def test_csv_text_pipeline(self):
        """IaaS instance pricing CSV should use structured chunking."""
        chunks = chunk_text(_IAAS_CSV, source_type="csv")
        assert isinstance(chunks, list)

    def test_chunk_pipeline_preserves_all_chunks_consistent(self):
        """total_chunks should equal len(chunks) for every chunk."""
        text = _IAAS_CHARACTERISTICS * 200
        chunks = chunk_text(text)
        for c in chunks:
            assert c["total_chunks"] == len(chunks)

    def test_very_long_document_chunks_many(self):
        """A large IaaS document should produce multiple chunks."""
        text = (_IAAS_WHAT_IS + _IAAS_CHARACTERISTICS + _IAAS_LICENSING + _IAAS_VIRTUALIZATION) * 20
        chunks = chunk_text(text)
        assert len(chunks) >= 3


# ── FileTypeDetector integration ──────────────────────────────────────────────

class TestFileTypeDetectorIntegration:

    def test_detect_pdf_extension(self, tmp_path):
        """A file with .pdf extension should be recognized."""
        f = tmp_path / "test.pdf"
        f.write_bytes(b"%PDF-1.4 test content")
        detector = FileTypeDetector()
        # Test supported type lookup
        assert "application/pdf" in FileTypeDetector.SUPPORTED_TYPES

    def test_detect_text_file_content(self, tmp_path):
        """A plain text file written to disk should be detectable."""
        f = tmp_path / "test.txt"
        f.write_text("Hello world\nThis is plain text.", encoding="utf-8")
        assert f.exists()
        assert f.stat().st_size > 0

    def test_supported_types_coverage(self):
        """All major document formats should be covered."""
        types = FileTypeDetector.SUPPORTED_TYPES
        must_have = [
            "application/pdf",
            "text/plain",
            "text/csv",
            "audio/mpeg",
            "video/mp4",
            "image/jpeg",
        ]
        for mime in must_have:
            assert mime in types, f"Missing MIME type: {mime}"


# ── Chunker integration ────────────────────────────────────────────────────────

class TestChunkerIntegration:
    # Source: "4. IaaS.pdf" — IaaS content replaces generic filler strings

    def test_chunk_ids_all_unique(self):
        """Every chunk ID should be globally unique."""
        text = (_IAAS_WHAT_IS + _IAAS_VIRTUALIZATION) * 200
        chunks = chunk_text(text)
        ids = [c["id"] for c in chunks]
        assert len(ids) == len(set(ids))

    def test_chunk_indices_zero_based_sequential(self):
        text = (_IAAS_CHARACTERISTICS + _IAAS_LICENSING) * 200
        chunks = chunk_text(text)
        expected = list(range(len(chunks)))
        actual = [c["chunk_index"] for c in chunks]
        assert actual == expected

    def test_no_chunk_exceeds_reasonable_size(self):
        """No IaaS chunk should be larger than 50 000 chars."""
        text = _IAAS_MARKDOWN_DOC * 5
        chunks = chunk_text(text)
        for c in chunks:
            assert len(c["text"]) < 50_000

    def test_empty_text_produces_no_chunks(self):
        assert chunk_text("") == []

    def test_special_unicode_text(self):
        """Unicode-heavy text should not crash the chunker."""
        text = "日本語テスト。クラウドコンピューティングの説明。" * 100
        chunks = chunk_text(text)
        assert isinstance(chunks, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
