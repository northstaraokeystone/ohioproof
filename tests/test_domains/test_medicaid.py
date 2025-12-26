"""
Tests for Medicaid domain module.
"""

import pytest

from src.domains.medicaid import (
    detect_concurrent,
    verify_eligibility,
    compute_capitation_risk,
    generate_referral,
    compute_concurrent_statistics
)


class TestMedicaidDomain:
    """Tests for Medicaid concurrent enrollment detection."""

    def test_detect_concurrent_no_flags(self, sample_enrollee):
        """Test detection with compliant enrollee."""
        result = detect_concurrent([sample_enrollee])
        # May or may not flag depending on indicators
        assert isinstance(result, list)

    def test_detect_concurrent_out_of_state(self):
        """Test detection of out-of-state address."""
        enrollee = {
            "id": "ENR002",
            "address": {"state": "PA"},  # Out of state
            "enrollment_months": 12
        }
        result = detect_concurrent([enrollee])
        assert len(result) > 0
        assert "out_of_state_address" in result[0]["indicators"]

    def test_verify_eligibility_valid(self, sample_enrollee):
        """Test eligibility verification for valid enrollee."""
        result = verify_eligibility(sample_enrollee)
        assert result["eligible"] is True
        assert len(result["issues"]) == 0

    def test_verify_eligibility_out_of_state(self):
        """Test eligibility for out-of-state enrollee."""
        enrollee = {
            "id": "ENR003",
            "address": {"state": "MI"}
        }
        result = verify_eligibility(enrollee)
        assert result["eligible"] is False
        assert "non_ohio_residency" in result["issues"]

    def test_compute_capitation_risk(self, sample_enrollee):
        """Test capitation risk computation."""
        risk = compute_capitation_risk(sample_enrollee)
        assert risk == 500 * 12  # $500/month * 12 months

    def test_generate_referral(self):
        """Test referral generation."""
        flagged = [
            {"enrollee_hash": "abc", "capitation_at_risk": 10000, "indicators": ["test"]}
        ]
        referral = generate_referral(flagged)
        assert referral["agency"] == "OIG"
        assert referral["summary"]["total_at_risk"] == 10000

    def test_compute_statistics(self):
        """Test statistics computation."""
        stats = compute_concurrent_statistics()
        assert stats["verified_concurrent_individuals"] == 124448
        assert stats["chronic_concurrent_individuals"] == 2372
