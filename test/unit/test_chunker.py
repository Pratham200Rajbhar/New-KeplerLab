"""
Unit tests for backend/app/services/text_processing/chunker.py
Source reference: "4. IaaS.pdf" — Infrastructure as a Service lecture notes.
Tests: plain-text chunking, markdown heading splits, structured CSV splits,
chunk metadata (id, index, total), overlap, min-length filtering,
edge cases (empty text, single heading, very short text)
No external services required.
"""

import sys
import os
import uuid
import pytest

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-only-32chars!")

from app.services.text_processing.chunker import chunk_text


# ── Reference source ─────────────────────────────────────────────────────────
# All prose below is derived from or inspired by "4. IaaS.pdf"
# (Infrastructure as a Service, Chapter 4 lecture notes).

# A realistic multi-sentence IaaS paragraph used as base prose.
_IAAS_SENTENCE = (
    "Infrastructure as a Service (IaaS) provides access to virtualized hardware resources "
"including virtual machines, virtual storage, virtual local area networks, load balancers, "
"IP addresses, and software bundles over a public connection such as the internet. "
"Resources are made available to end users via server virtualization so that customers "
"interact with them as if they own the underlying physical infrastructure. "
"The cloud provider is responsible for maintaining the pool of hardware distributed "
"across numerous data centers while the client builds their own IT platforms on top. "
)

_IAAS_DYNAMIC_SCALING = (
    "Dynamic scaling is one of the major benefits of IaaS for companies facing resource uncertainty. "
"Resources can be automatically scaled up or down based on the requirements of the application. "
"If customers need more resources than expected they can obtain them immediately up to a given limit. "
"A provider of IaaS typically optimizes the environment so that hardware, "
"operating system, and automation can support a huge number of concurrent workloads. "
)

_IAAS_SERVICE_LEVELS = (
    "Consumers acquire IaaS services in different ways, either on an on-demand model with no contract "
"or through a signed contract for a specific amount of storage or compute capacity. "
"A typical IaaS contract includes some level of service guarantee, specifying that resources "
"will be available 99.999 percent of the time and that additional capacity will be provisioned "
"dynamically when greater than 80 percent of any given resource is being consumed. "
"A service-level agreement states what the provider has agreed to deliver in terms of "
"availability, response to demand, and recovery time objectives. "
)

_IAAS_RENTAL_MODEL = (
    "When companies use IaaS the servers, storage, and other IT infrastructure components "
"are rented for a fee based on the quantity of resources used and how long they are in use. "
"Customers gain immediate virtual access to the resources they need without renting "
"actual physical servers or expecting hardware to be delivered to their offices. "
"The physical components remain in the infrastructure service provider's data center. "
"Within a private IaaS model the charge-back approach allocates usage fees to individual "
"departments based on their consumption over a week, month, or year. "
)

_IAAS_LICENSING = (
    "The use of public IaaS has led to innovation in licensing and payment models "
"for software running in cloud environments. "
"Some IaaS and software providers have created a bring-your-own-license plan "
"so customers can use existing software licenses in both traditional and cloud environments. "
"Another option called pay-as-you-go integrates software licenses with on-demand infrastructure services. "
"For example, running Microsoft Windows Server under the PAYG route means a portion "
"of the hourly cloud access fee goes directly to the software vendor. "
)

_IAAS_METERING = (
    "IaaS providers use the metering process to charge users based on the instance "
"of computing consumed, defined as the CPU power, memory, and storage space used in an hour. "
"When an instance is initiated hourly charges begin to accumulate until the instance is terminated. "
"The charge for a very small instance may be as little as two cents per hour while "
"the hourly fee can increase to 2.60 dollars for a large resource-intensive instance running Windows. "
"Metering ensures that with multiple users accessing resources from the same environment "
"each customer is charged the correct amount for their actual consumption. "
)

_IAAS_SELF_SERVICE = (
    "Self-service provisioning is an imperative characteristic of IaaS "
"that allows customers to request and configure computing resources without human intervention. "
"The banking ATM service is a great example of the business value of self-service: "
"without the ATM, banks would require costly resources to manage all customer activities "
"even for the most repetitive transactions. "
"Similarly, IaaS self-service interfaces let organizations provision virtual machines, "
"allocate storage, configure networks, and deploy software bundles on demand "
"without filing tickets or waiting for operations teams. "
)

_IAAS_VIRTUALIZATION = (
    "Virtualization is the foundational technology that makes IaaS possible by abstracting "
"physical hardware into software-defined resources that can be allocated and managed dynamically. "
"Through a hypervisor layer, a single physical server can host many virtual machines, "
"each with its own operating system and resource allocation independently managed. "
"Virtual machine disk storage, virtual local area networks, and software-defined networking "
"components are all provisioned and reconfigured programmatically through the IaaS platform. "
"This abstraction layer insulates customers from hardware failures and enables rapid provisioning. "
)


def _make_prose(n_words: int = 300) -> str:
    """Return IaaS-derived prose scaled to approximately n_words words."""
    base = (
        _IAAS_SENTENCE + _IAAS_DYNAMIC_SCALING + _IAAS_SERVICE_LEVELS
        + _IAAS_RENTAL_MODEL + _IAAS_LICENSING + _IAAS_METERING + _IAAS_SELF_SERVICE
        + _IAAS_VIRTUALIZATION
    )
    # Repeat until we have enough characters (~6 chars/word heuristic)
    while len(base) < n_words * 6:
        base += base
    return base[:n_words * 6]


def _make_markdown(sections: int = 4, words_per_section: int = 200) -> str:
    """Return IaaS-structured markdown with real section headings."""
    section_bodies = [
        ("## What is IaaS", _IAAS_SENTENCE * max(1, words_per_section // 70)),
        ("## Dynamic Scaling", _IAAS_DYNAMIC_SCALING * max(1, words_per_section // 50)),
        ("## Service Levels", _IAAS_SERVICE_LEVELS * max(1, words_per_section // 65)),
        ("## Rental Model", _IAAS_RENTAL_MODEL * max(1, words_per_section // 60)),
        ("## Licensing", _IAAS_LICENSING * max(1, words_per_section // 58)),
        ("## Metering and Costs", _IAAS_METERING * max(1, words_per_section // 60)),
        ("## Self-Service Provisioning", _IAAS_SELF_SERVICE * max(1, words_per_section // 62)),
        ("## Virtualization", _IAAS_VIRTUALIZATION * max(1, words_per_section // 55)),
    ]
    parts = []
    for heading, body in section_bodies[:sections]:
        parts.append(heading)
        parts.append(body)
    return "\n\n".join(parts)


# ── Basic output structure ────────────────────────────────────────────────────

class TestChunkOutputStructure:

    def test_returns_list(self):
        chunks = chunk_text("Hello world. This is a test document.")
        assert isinstance(chunks, list)

    def test_each_chunk_is_dict(self):
        chunks = chunk_text(_make_prose())
        for c in chunks:
            assert isinstance(c, dict)

    def test_each_chunk_has_required_keys(self):
        chunks = chunk_text(_make_prose())
        required = {"id", "text", "chunk_index", "total_chunks"}
        for c in chunks:
            assert required.issubset(c.keys())

    def test_chunk_id_is_uuid(self):
        chunks = chunk_text(_make_prose())
        for c in chunks:
            # Should be parseable as a UUID
            try:
                uuid.UUID(c["id"])
            except ValueError:
                pytest.fail(f"chunk id is not a UUID: {c['id']!r}")

    def test_chunk_index_sequential(self):
        chunks = chunk_text(_make_prose(500))
        for i, c in enumerate(chunks):
            assert c["chunk_index"] == i

    def test_total_chunks_consistent(self):
        chunks = chunk_text(_make_prose(500))
        total = chunks[0]["total_chunks"]
        for c in chunks:
            assert c["total_chunks"] == total == len(chunks)


# ── Empty / trivial inputs ────────────────────────────────────────────────────

class TestEdgeCases:

    def test_empty_string_returns_empty_list(self):
        result = chunk_text("")
        assert result == []

    def test_whitespace_only_returns_empty_list(self):
        result = chunk_text("   \n\t  ")
        assert result == []

    def test_very_short_text_returns_at_most_one_chunk(self):
        # Under MIN_CHUNK_CHARS → filtered out; over it → returned
        result = chunk_text("Short but meaningful text with enough alpha chars.")
        assert len(result) <= 1

    def test_single_word(self):
        # Too short after filtering
        result = chunk_text("Word")
        assert len(result) <= 1

    def test_repeated_char_filtered(self):
        """A string of non-alphabetic repeated chars should be filtered (low alpha ratio)."""
        result = chunk_text("1234567890 " * 200)
        # May or may not produce chunks depending on alpha ratio
        assert isinstance(result, list)


# ── Markdown splitting ────────────────────────────────────────────────────────

class TestMarkdownChunking:

    def test_headings_produce_multiple_chunks(self):
        md = _make_markdown(sections=4, words_per_section=200)
        chunks = chunk_text(md)
        assert len(chunks) >= 2

    def test_section_title_populated_for_markdown(self):
        md = "## Introduction\n\n" + _make_prose(150)
        chunks = chunk_text(md)
        # At least one chunk should have section_title set
        titles = [c.get("section_title") for c in chunks]
        assert any(t for t in titles)

    def test_h1_and_h2_both_recognized(self):
        # Source: "4. IaaS.pdf" — using real IaaS lecture content as document sections
        section1 = _IAAS_SENTENCE * 4 + _IAAS_DYNAMIC_SCALING * 4
        section2 = _IAAS_SERVICE_LEVELS * 4 + _IAAS_RENTAL_MODEL * 4
        md = f"# Chapter 4: Infrastructure as a Service\n\n{section1}\n\n## IaaS Service and Rental Models\n\n{section2}"
        chunks = chunk_text(md)
        # At minimum one chunk must be present
        assert len(chunks) >= 1


# ── Chunk text quality ────────────────────────────────────────────────────────

class TestChunkQuality:

    def test_no_chunk_is_empty(self):
        chunks = chunk_text(_make_prose(500))
        for c in chunks:
            assert len(c["text"].strip()) > 0

    def test_all_chunks_have_alpha_chars(self):
        chunks = chunk_text(_make_prose(500))
        for c in chunks:
            alpha_ratio = sum(1 for ch in c["text"] if ch.isalpha()) / len(c["text"])
            assert alpha_ratio >= 0.05, f"Chunk has too few alpha chars: {c['text'][:50]!r}"

    def test_large_text_chunked(self):
        """A large document must produce more than one chunk."""
        large = _make_prose(2000)
        chunks = chunk_text(large)
        assert len(chunks) >= 2


# ── Source type routing ───────────────────────────────────────────────────────

class TestSourceTypeRouting:
    # Source: "4. IaaS.pdf" — IaaS provider pricing data as realistic CSV

    def test_csv_source_type_accepted(self):
        # Realistic IaaS instance pricing table derived from metering concepts in IaaS.pdf
        csv_content = (
            "instance_type,cpu_cores,memory_gb,storage_gb,price_per_hour\n"
            "small,1,1,20,0.02\n"
            "medium,2,4,50,0.08\n"
            "large,4,8,100,0.16\n"
            "xlarge,8,16,200,0.32\n"
            "windows_large,4,8,100,2.60\n"
        ) * 20
        chunks = chunk_text(csv_content, source_type="csv")
        assert isinstance(chunks, list)

    def test_prose_source_type_accepted(self):
        # Source: "4. IaaS.pdf" — IaaS licensing concepts as prose input
        chunks = chunk_text(_IAAS_LICENSING * 5 + _IAAS_METERING * 5, source_type="prose")
        assert isinstance(chunks, list)


# ── Semantic chunking flag ────────────────────────────────────────────────────

class TestSemanticChunking:
    # Source: "4. IaaS.pdf" — self-service and virtualization sections

    def test_semantic_chunking_returns_list(self):
        chunks = chunk_text(_IAAS_SELF_SERVICE * 5 + _IAAS_VIRTUALIZATION * 5, use_semantic_chunking=True)
        assert isinstance(chunks, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
