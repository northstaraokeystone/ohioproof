"""
Tests for detect modules.

Receipt: test_detect_receipt
Gate: t24h
"""

import pytest

from src.detect.anomaly import (
    compute_entropy,
    detect_anomaly,
    classify_anomaly,
    emit_anomaly
)
from src.detect.compression import (
    compute_compression,
    score_transaction_set,
    flag_high_entropy,
    classify_compression
)
from src.detect.correlation import (
    correlate_vendor,
    correlate_payment_lobbying,
    correlate_contribution_vote,
    correlate_enrollment
)
from src.detect.patterns import load_pattern, match_pattern, list_patterns
from src.detect.growth import (
    compute_growth_rate,
    flag_explosive_growth,
    detect_onboarding_velocity
)
from src.constants import GROWTH_RATE_CRITICAL


class TestAnomaly:
    """Tests for anomaly detection."""

    def test_compute_entropy_empty(self):
        """Test entropy of empty list."""
        result = compute_entropy([], "field")
        assert result == 0.0

    def test_compute_entropy_uniform(self):
        """Test entropy of uniform distribution."""
        transactions = [{"type": "A"}, {"type": "B"}, {"type": "C"}, {"type": "D"}]
        result = compute_entropy(transactions, "type")
        assert result == 2.0  # log2(4) = 2 for uniform

    def test_compute_entropy_single_value(self):
        """Test entropy when all same value."""
        transactions = [{"type": "A"}, {"type": "A"}, {"type": "A"}]
        result = compute_entropy(transactions, "type")
        assert result == 0.0  # No uncertainty

    def test_detect_anomaly_no_change(self):
        """Test anomaly detection with no change."""
        result = detect_anomaly(
            {"entropy": 1.0},
            {"entropy": 1.0}
        )
        assert result["is_anomaly"] is False

    def test_detect_anomaly_significant_change(self):
        """Test anomaly detection with significant change."""
        result = detect_anomaly(
            {"entropy": 2.0},
            {"entropy": 1.0},
            threshold=0.2
        )
        assert result["is_anomaly"] is True

    def test_classify_anomaly(self):
        """Test anomaly classification."""
        assert classify_anomaly(1.0, 1.5) == "violation"
        assert classify_anomaly(0.5, 0.6) == "deviation"
        assert classify_anomaly(0.1, 0.1) == "drift"


class TestCompression:
    """Tests for compression-based detection."""

    def test_compute_compression(self):
        """Test compression ratio computation."""
        data = b"test data " * 100
        ratio = compute_compression(data)
        assert 0 < ratio < 1  # Should compress

    def test_compute_compression_random(self):
        """Test compression of random data."""
        import os
        data = os.urandom(1000)
        ratio = compute_compression(data)
        # Random data shouldn't compress well
        assert ratio > 0.9

    def test_score_transaction_set(self, sample_transactions):
        """Test transaction set scoring."""
        ratio = score_transaction_set(sample_transactions)
        assert 0 <= ratio <= 1

    def test_flag_high_entropy(self):
        """Test high entropy flagging."""
        assert flag_high_entropy(0.9) is True
        assert flag_high_entropy(0.5) is False

    def test_classify_compression(self):
        """Test compression classification."""
        assert classify_compression(0.3) == "highly_compressible"
        assert classify_compression(0.6) == "legitimate"
        assert classify_compression(0.8) == "suspicious"
        assert classify_compression(0.95) == "fraudulent"


class TestCorrelation:
    """Tests for cross-database correlation."""

    def test_correlate_vendor_exact_match(self):
        """Test vendor correlation with exact match."""
        checkbook = {"vendor_name": "Test Company"}
        federal = {"recipient_name": "Test Company"}
        score = correlate_vendor(checkbook, federal)
        assert score >= 0.5

    def test_correlate_vendor_no_match(self):
        """Test vendor correlation with no match."""
        checkbook = {"vendor_name": "Company A"}
        federal = {"recipient_name": "Company B"}
        score = correlate_vendor(checkbook, federal)
        assert score < 0.5

    def test_correlate_enrollment_concurrent(self):
        """Test enrollment correlation for concurrent."""
        ohio = {
            "enrollee_id_hash": "abc123",
            "enrollment_start": "2020-01-01",
            "enrollment_end": "2024-01-01"
        }
        other = {
            "enrollee_id_hash": "abc123",
            "enrollment_start": "2020-01-01",
            "enrollment_end": "2024-01-01"
        }
        result = correlate_enrollment(ohio, other)
        assert result["correlation_score"] >= 0.7


class TestPatterns:
    """Tests for pattern matching."""

    def test_list_patterns(self):
        """Test listing available patterns."""
        patterns = list_patterns()
        assert "generation_now" in patterns
        assert "concurrent_enrollment" in patterns
        assert "ecot_attendance" in patterns
        assert "feeding_our_future" in patterns

    def test_load_pattern(self):
        """Test loading pattern."""
        pattern = load_pattern("generation_now")
        assert pattern is not None
        assert pattern["pattern_id"] == "generation_now"

    def test_load_pattern_invalid(self):
        """Test loading invalid pattern."""
        pattern = load_pattern("nonexistent")
        assert pattern is None

    def test_match_pattern_high_risk(self, sample_501c4):
        """Test pattern matching for high-risk org."""
        pattern = load_pattern("generation_now")
        score = match_pattern(sample_501c4, pattern)
        assert score > 0  # Should have some match


class TestGrowth:
    """Tests for growth rate detection."""

    def test_compute_growth_rate_normal(self):
        """Test normal growth rate."""
        series = [100, 110, 120]
        rate = compute_growth_rate(series)
        assert rate == 1.2  # 20% growth

    def test_compute_growth_rate_explosive(self):
        """Test explosive growth (FOF pattern)."""
        series = [100, 2900]  # 2800% growth
        rate = compute_growth_rate(series)
        assert rate == 29.0

    def test_flag_explosive_growth(self):
        """Test explosive growth flagging."""
        assert flag_explosive_growth(30.0) is True  # > 2800%
        assert flag_explosive_growth(2.0) is False  # 100%

    def test_detect_onboarding_velocity(self):
        """Test onboarding velocity detection."""
        entity = {
            "days_to_first_large_claim": 5,
            "claimed_capacity": 10000,
            "estimated_reasonable_capacity": 1000
        }
        score = detect_onboarding_velocity(entity)
        assert score >= 0.5  # Should flag rapid scaling
