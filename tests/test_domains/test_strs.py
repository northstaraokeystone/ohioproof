"""
Tests for STRS domain module.
"""

import pytest

from src.domains.strs import (
    parse_investment,
    detect_steering,
    compute_fee_ratio,
    flag_board_conflict,
    monitor_governance,
    get_strs_statistics
)


class TestSTRSDomain:
    """Tests for STRS pension monitoring."""

    def test_parse_investment(self):
        """Test investment parsing."""
        filing = {
            "manager": "Investment Manager LLC",
            "fee_amount": 1000000,
            "fee_pct": 0.5,
            "assets_managed": 200000000,
            "return_pct": 8.0,
            "benchmark_pct": 7.0
        }
        result = parse_investment(filing)
        assert result["manager"] == "Investment Manager LLC"
        assert result["benchmark_delta"] == 1.0

    def test_detect_steering_new_vendor(self):
        """Test steering detection for new vendor."""
        contracts = [
            {
                "vendor": "New Startup LLC",
                "vendor_age_years": 1,
                "competitive_bid": False,
                "value": 5000000,
                "board_connection": True
            }
        ]
        result = detect_steering(contracts)
        assert len(result) == 1
        assert result[0]["score"] >= 0.5

    def test_compute_fee_ratio(self):
        """Test fee ratio computation."""
        fund = {
            "total_fees": 500000000,  # $500M
            "assets_under_management": 96900000000  # $96.9B
        }
        ratio = compute_fee_ratio(fund)
        assert ratio == pytest.approx(0.516, rel=0.01)

    def test_flag_board_conflict(self):
        """Test board conflict detection."""
        member = {
            "name": "Board Member",
            "employer": "Vendor Company"
        }
        vendor = {"name": "Vendor Company"}
        assert flag_board_conflict(member, vendor) is True

    def test_get_statistics(self):
        """Test statistics retrieval."""
        stats = get_strs_statistics()
        assert stats["fund_size"] == 96900000000
        assert stats["funded_ratio"] == 0.825
