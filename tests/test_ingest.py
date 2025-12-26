"""
Tests for ingest modules.

Receipt: test_ingest_receipt
Gate: t24h
"""

import pytest

from src.ingest.ohio_checkbook import (
    fetch_transactions,
    parse_vendor,
    detect_shell
)
from src.ingest.usaspending import fetch_awards, cross_reference
from src.ingest.propublica import fetch_org, detect_dark_money
from src.ingest.nppes import search_npi, verify_provider
from src.ingest.campaign_finance import fetch_contributions, detect_timing
from src.ingest.lobbying import fetch_lobbyists, detect_unregistered
from src.ingest.puco import fetch_case, detect_commissioner_conflict


class TestOhioCheckbook:
    """Tests for Ohio Checkbook ingest."""

    def test_fetch_transactions(self):
        """Test fetching transactions."""
        result = fetch_transactions("2024-01-01", "2024-01-31")
        assert isinstance(result, list)

    def test_parse_vendor(self, sample_transaction):
        """Test vendor parsing."""
        result = parse_vendor(sample_transaction)
        assert "vendor_id" in result
        assert "vendor_name" in result
        assert "amount" in result

    def test_detect_shell_low_risk(self):
        """Test shell detection for normal vendor."""
        vendor = {
            "vendor_name": "Ohio Construction Company Inc",
            "amount": 45000.00
        }
        score = detect_shell(vendor)
        assert 0 <= score <= 1.0

    def test_detect_shell_high_risk(self):
        """Test shell detection for suspicious vendor."""
        vendor = {
            "vendor_name": "Consulting Services LLC",
            "amount": 100000.00  # Round number
        }
        score = detect_shell(vendor)
        assert score >= 0.3  # Should flag suspicious patterns


class TestUSASpending:
    """Tests for USASpending ingest."""

    def test_fetch_awards(self):
        """Test fetching awards."""
        result = fetch_awards("OH", 2024)
        assert isinstance(result, list)

    def test_cross_reference(self):
        """Test vendor cross-reference."""
        result = cross_reference("Test Vendor")
        assert "vendor_name" in result
        assert "match_confidence" in result


class TestProPublica:
    """Tests for ProPublica ingest."""

    def test_fetch_org(self):
        """Test fetching organization."""
        result = fetch_org("123456789")
        assert result is not None
        assert "ein" in result

    def test_detect_dark_money_low_risk(self):
        """Test dark money detection for low-risk org."""
        org = {
            "subsection_code": "501(c)(3)",
            "state": "OH",
            "revenue_amount": 100000
        }
        score = detect_dark_money(org)
        assert score < 0.5

    def test_detect_dark_money_high_risk(self, sample_501c4):
        """Test dark money detection for high-risk org."""
        score = detect_dark_money(sample_501c4)
        assert score >= 0.5  # Should flag Generation Now pattern


class TestNPPES:
    """Tests for NPPES ingest."""

    def test_search_npi(self):
        """Test NPI search."""
        result = search_npi(npi="1234567890")
        assert isinstance(result, list)

    def test_verify_provider_ohio(self):
        """Test provider verification for Ohio."""
        result = verify_provider("1234567890", "OH")
        assert "verified" in result


class TestCampaignFinance:
    """Tests for campaign finance ingest."""

    def test_fetch_contributions(self):
        """Test fetching contributions."""
        result = fetch_contributions(candidate="Test Candidate")
        assert isinstance(result, list)

    def test_detect_timing_suspicious(self):
        """Test timing detection for suspicious contribution."""
        contribution = {
            "amount": 100000,
            "date": "2019-06-01"
        }
        action = {
            "date": "2019-06-15",  # 14 days after
            "vote_id": "HB6_VOTE"
        }
        score = detect_timing(contribution, action)
        assert score >= 0.5  # Should flag


class TestLobbying:
    """Tests for lobbying ingest."""

    def test_fetch_lobbyists(self):
        """Test fetching lobbyists."""
        result = fetch_lobbyists("FirstEnergy")
        assert isinstance(result, list)

    def test_detect_unregistered(self):
        """Test unregistered lobbying detection."""
        contact = {
            "entity": "Corporate Enterprises Inc",
            "official": "State Official",
            "purpose": "discuss legislation"
        }
        result = detect_unregistered(contact)
        assert isinstance(result, bool)


class TestPUCO:
    """Tests for PUCO ingest."""

    def test_fetch_case(self):
        """Test fetching case."""
        result = fetch_case("14-1297-EL-SSO")
        assert result is not None
        assert "case_number" in result

    def test_detect_commissioner_conflict(self):
        """Test commissioner conflict detection."""
        result = detect_commissioner_conflict("Sam Randazzo", "FirstEnergy")
        assert result["conflict_score"] == 1.0  # Known conflict
