"""
Tests for JobsOhio domain module.
"""

import pytest

from src.domains.jobsohio import (
    parse_commitment,
    verify_employment,
    compute_delivery_rate,
    flag_zero_delivery,
    compute_clawback,
    generate_public_dashboard
)


class TestJobsOhioDomain:
    """Tests for JobsOhio accountability."""

    def test_parse_commitment(self):
        """Test commitment parsing."""
        announcement = {
            "company": "Test Corp",
            "promised_jobs": 100,
            "promised_payroll": 5000000,
            "incentive_amount": 1000000,
            "date": "2024-01-15"
        }
        result = parse_commitment(announcement)
        assert result["promised_jobs"] == 100
        assert result["promised_payroll"] == 5000000

    def test_compute_delivery_rate_full(self):
        """Test delivery rate at 100%."""
        company = {"actual_jobs": 100, "promised_jobs": 100}
        rate = compute_delivery_rate(company)
        assert rate == 1.0

    def test_compute_delivery_rate_zero(self):
        """Test delivery rate at 0%."""
        company = {"actual_jobs": 0, "promised_jobs": 100}
        rate = compute_delivery_rate(company)
        assert rate == 0.0

    def test_flag_zero_delivery_true(self):
        """Test zero delivery flagging."""
        company = {
            "company": "Truepill Pattern",
            "actual_jobs": 0,
            "actual_payroll": 0,
            "incentive_amount": 1000000
        }
        assert flag_zero_delivery(company) is True

    def test_flag_zero_delivery_false(self):
        """Test non-zero delivery."""
        company = {
            "actual_jobs": 50,
            "actual_payroll": 2500000,
            "incentive_amount": 1000000
        }
        assert flag_zero_delivery(company) is False

    def test_compute_clawback_full_delivery(self):
        """Test clawback with full delivery."""
        company = {"actual_jobs": 100, "promised_jobs": 100}
        incentive = {"amount": 1000000}
        clawback = compute_clawback(company, incentive)
        assert clawback == 0.0

    def test_compute_clawback_zero_delivery(self):
        """Test clawback with zero delivery."""
        company = {"actual_jobs": 0, "promised_jobs": 100}
        incentive = {"amount": 1000000}
        clawback = compute_clawback(company, incentive)
        assert clawback == 1000000  # Full clawback

    def test_generate_public_dashboard(self):
        """Test public dashboard generation."""
        companies = [
            {
                "company": "Company A",
                "promised_jobs": 100,
                "actual_jobs": 50,
                "incentive_amount": 500000
            }
        ]
        dashboard = generate_public_dashboard(companies)
        assert "summary" in dashboard
        assert dashboard["verified_failure_rate"] == 0.65
