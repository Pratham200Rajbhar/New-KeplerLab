"""
Unit tests for backend/app/services/rag/citation_validator.py
Source reference: "4. IaaS.pdf" — Infrastructure as a Service lecture notes.
Tests: validate_citations — presence, range, density, invalid sources,
'not found' responses, edge cases
No DB or LLM required.
"""

import sys
import os
import pytest

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-only-32chars!")

from app.services.rag.citation_validator import validate_citations


class TestValidateCitationsPresence:
    # Source: "4. IaaS.pdf" — IaaS-themed simulated LLM responses

    def test_valid_response_with_citations(self):
        # Response summarising IaaS characteristics with citations
        response = (
            "IaaS provides virtualized hardware resources to end users over the internet. "
            "[SOURCE 1] Dynamic scaling allows resources to be automatically provisioned "
            "up or down based on application demand. [SOURCE 2]"
        )
        result = validate_citations(response, num_sources=3)
        assert result["is_valid"] is True

    def test_response_without_citations_invalid(self):
        # IaaS content but missing citation markers — strict mode should reject
        response = (
            "Infrastructure as a Service offers virtual machines, storage, and networking "
            "over the cloud with a pay-as-you-go pricing model."
        )
        result = validate_citations(response, num_sources=3, strict=True)
        assert result["is_valid"] is False
        assert result["missing_citations"] is True

    def test_not_found_response_is_valid(self):
        # Responses indicating the IaaS document doesn’t cover the queried topic
        responses = [
            "I could not find relevant information in the provided context.",
            "I couldn't find any relevant information in the sources.",
            "The sources do not contain information about this topic.",
            "There is no information about this in the materials.",
        ]
        for r in responses:
            result = validate_citations(r, num_sources=3)
            assert result["is_valid"] is True, f"Expected valid for: {r!r}"

    def test_cited_sources_extracted(self):
        # Verify source-index extraction from an IaaS-style response
        response = (
            "The rental model charges customers based on resource usage. [SOURCE 1] "
            "Metering tracks CPU, memory, and storage consumption per hour. [SOURCE 3]"
        )
        result = validate_citations(response, num_sources=3)
        assert 1 in result["cited_sources"]
        assert 3 in result["cited_sources"]


class TestValidateCitationsRange:
    # Source: "4. IaaS.pdf" — IaaS-themed citation range validation

    def test_in_range_sources_valid(self):
        response = (
            "IaaS self-service provisioning eliminates manual ticket queues. [SOURCE 1] "
            "Service-level agreements guarantee 99.999 percent uptime. [SOURCE 2]"
        )
        result = validate_citations(response, num_sources=3)
        assert result["invalid_sources"] == []

    def test_out_of_range_source_detected(self):
        response = "Virtualization abstracts physical hardware into managed pools. [SOURCE 5]"
        result = validate_citations(response, num_sources=3)
        assert 5 in result["invalid_sources"]

    def test_source_zero_is_invalid(self):
        response = "Dynamic scaling adjusts IaaS resources automatically. [SOURCE 0]"
        result = validate_citations(response, num_sources=3)
        assert 0 in result["invalid_sources"]

    def test_exactly_at_limit_valid(self):
        response = "The PAYG licensing model bills per hour of instance usage. [SOURCE 3]"
        result = validate_citations(response, num_sources=3)
        assert 3 not in result["invalid_sources"]


class TestValidateCitationsDensity:
    # Source: "4. IaaS.pdf" — realistic IaaS response density comparisons

    # Forty words of context, one citation — low-density IaaS sentence
    _FEW_CITED = (
        "Infrastructure as a Service provides virtualized hardware over the internet "
        "including virtual machines, storage, load balancers, IP addresses, and VLANs. "
        "Customers access these resources as if they own the physical infrastructure. "
        "The cloud provider maintains the underlying servers in distributed data centers. "
        "[SOURCE 1]"
    )

    # Same length but with many inline citations — high-density IaaS sentence
    _MANY_CITED = (
        "IaaS offers dynamic scaling [SOURCE 1] so resources grow with demand. "
        "Service levels guarantee 99.999 percent availability. [SOURCE 2] "
        "The rental model charges by the hour with no physical delivery. [SOURCE 1] "
        "Self-service provisioning eliminates manual IT workflows entirely. [SOURCE 2]"
    )

    def test_density_computed(self):
        result = validate_citations(self._FEW_CITED, num_sources=2)
        assert "citation_density" in result
        assert isinstance(result["citation_density"], float)

    def test_higher_density_for_more_citations(self):
        r_few = validate_citations(self._FEW_CITED, num_sources=2)
        r_many = validate_citations(self._MANY_CITED, num_sources=2)
        # more inline citations per word → higher density
        assert r_many["citation_density"] >= r_few["citation_density"]


class TestValidateCitationsOutput:
    # Source: "4. IaaS.pdf" — IaaS-themed edge-case responses

    def test_returns_dict(self):
        result = validate_citations("IaaS enables on-demand virtual machine provisioning.", num_sources=2)
        assert isinstance(result, dict)

    def test_required_keys_present(self):
        result = validate_citations(
            "Metering tracks CPU and storage consumption per hour. [SOURCE 1]", num_sources=2
        )
        required = {"is_valid", "cited_sources", "missing_citations", "invalid_sources",
                    "citation_density"}
        assert required.issubset(result.keys())

    def test_empty_response_invalid(self):
        result = validate_citations("", num_sources=2, strict=True)
        # Empty response with no citations
        assert result["missing_citations"] is True

    def test_no_sources_provided(self):
        """When num_sources=0, any source citation is out of range."""
        response = "The BYOL licensing option covers both cloud and traditional deployments. [SOURCE 1]"
        result = validate_citations(response, num_sources=0)
        assert 1 in result["invalid_sources"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
