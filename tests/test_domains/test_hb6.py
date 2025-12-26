"""
Tests for HB6 domain module.
"""

import pytest

from src.domains.hb6 import (
    scan_501c4,
    correlate_lobbying_spend,
    detect_legislative_timing,
    trace_flow,
    generate_dark_money_score,
    get_hb6_verified_data
)


class TestHB6Domain:
    """Tests for HB6 dark money detection."""

    def test_scan_501c4(self):
        """Test 501(c)(4) scanning."""
        result = scan_501c4("123456789")
        assert "ein" in result
        assert "dark_money_score" in result

    def test_generate_dark_money_score_high_risk(self, sample_501c4):
        """Test dark money score for high-risk org."""
        score = generate_dark_money_score(sample_501c4)
        assert score >= 0.7  # Should flag

    def test_generate_dark_money_score_low_risk(self):
        """Test dark money score for low-risk org."""
        org = {
            "name": "Charity Foundation",
            "subsection_code": "501(c)(3)",
            "total_receipts": 50000,
            "donor_disclosure_rate": 1.0,
            "political_expenditure_pct": 0.0
        }
        score = generate_dark_money_score(org)
        assert score < 0.5

    def test_detect_legislative_timing(self):
        """Test legislative timing detection."""
        contribution = {
            "amount": 100000,
            "date": "2019-06-01"
        }
        votes = [
            {"date": "2019-06-15", "outcome": "passed"}
        ]
        result = detect_legislative_timing(contribution, votes)
        assert result["max_score"] >= 0.5
        assert result["flagged"] is True

    def test_trace_flow(self):
        """Test payment flow tracing."""
        payment = {
            "source": "FirstEnergy",
            "destination": "Generation Now",
            "amount": 60000000
        }
        trace = trace_flow(payment)
        assert len(trace) >= 1

    def test_get_verified_data(self):
        """Test verified case data."""
        data = get_hb6_verified_data()
        assert data["verified_amounts"]["bribery_total"] == 60000000
        assert data["sentences"]["householder_years"] == 20
