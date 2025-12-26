"""
Tests for Pandemic domain module.
"""

import pytest

from src.domains.pandemic import (
    detect_duplicate_claims,
    detect_ineligible,
    compute_overpayment,
    track_recovery,
    generate_pandemic_dashboard
)


class TestPandemicDomain:
    """Tests for pandemic unemployment fraud detection."""

    def test_detect_duplicate_claims(self):
        """Test duplicate claim detection."""
        claims = [
            {"identity_hash": "abc123", "amount": 10000, "date": "2020-04-01"},
            {"identity_hash": "abc123", "amount": 10000, "date": "2020-05-01"},
            {"identity_hash": "def456", "amount": 10000, "date": "2020-04-01"}
        ]
        result = detect_duplicate_claims(claims)
        assert len(result) == 1  # One identity with duplicates
        assert result[0]["claim_count"] == 2

    def test_detect_ineligible_valid(self):
        """Test eligibility for valid claim."""
        claim = {
            "residence_state": "OH",
            "wages_during_claim": 0
        }
        result = detect_ineligible(claim)
        assert result["eligible"] is True

    def test_detect_ineligible_deceased(self):
        """Test eligibility for deceased claimant."""
        claim = {
            "residence_state": "OH",
            "claimant_deceased_before_claim": True
        }
        result = detect_ineligible(claim)
        assert result["eligible"] is False
        assert "deceased_claimant" in result["issues"]

    def test_compute_overpayment(self):
        """Test overpayment computation."""
        claim = {
            "residence_state": "MI",  # Out of state
            "total_paid": 20000
        }
        overpayment = compute_overpayment(claim)
        assert overpayment == 20000

    def test_track_recovery(self):
        """Test recovery tracking."""
        overpayment = {
            "id": "OVP001",
            "amount": 10000,
            "recovered": 5000
        }
        result = track_recovery(overpayment)
        assert result["recovery_rate"] == 0.5
        assert result["status"] == "partial"

    def test_generate_dashboard(self):
        """Test dashboard generation."""
        dashboard = generate_pandemic_dashboard()
        assert dashboard["summary"]["total_identified"] == 6900000000
        assert dashboard["summary"]["recovered"] == 400000000
