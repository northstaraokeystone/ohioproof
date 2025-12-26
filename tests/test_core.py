"""
Tests for core module.

Receipt: test_core_receipt
Gate: t24h
"""

import json
import pytest
import time

from src.core import (
    dual_hash,
    emit_receipt,
    merkle,
    StopRule,
    TENANT_ID,
    stoprule_hash_mismatch,
    stoprule_invalid_receipt,
    check_bias
)
from src.constants import (
    HB6_BRIBERY_AMOUNT,
    MEDICAID_CONCURRENT_INDIVIDUALS,
    JOBSOHIO_FAILURE_RATE
)


class TestDualHash:
    """Tests for dual_hash function."""

    def test_dual_hash_string(self):
        """Test dual_hash with string input."""
        result = dual_hash("test")
        assert ":" in result
        parts = result.split(":")
        assert len(parts) == 2
        assert len(parts[0]) == 64  # SHA256 hex length

    def test_dual_hash_bytes(self):
        """Test dual_hash with bytes input."""
        result = dual_hash(b"test")
        assert ":" in result

    def test_dual_hash_deterministic(self):
        """Test that same input produces same hash."""
        hash1 = dual_hash("test data")
        hash2 = dual_hash("test data")
        assert hash1 == hash2

    def test_dual_hash_different_inputs(self):
        """Test that different inputs produce different hashes."""
        hash1 = dual_hash("test1")
        hash2 = dual_hash("test2")
        assert hash1 != hash2

    def test_dual_hash_latency(self):
        """SLO: dual_hash_latency <= 10ms."""
        t0 = time.time()
        for _ in range(100):
            dual_hash("test data for latency check")
        elapsed = (time.time() - t0) * 1000 / 100
        assert elapsed <= 10, f"Latency {elapsed}ms > 10ms SLO"


class TestEmitReceipt:
    """Tests for emit_receipt function."""

    def test_emit_receipt_basic(self, capsys):
        """Test basic receipt emission."""
        receipt = emit_receipt("test", {"tenant_id": TENANT_ID, "data": "value"})

        assert receipt["receipt_type"] == "test"
        assert receipt["tenant_id"] == TENANT_ID
        assert "ts" in receipt
        assert "payload_hash" in receipt
        assert ":" in receipt["payload_hash"]

    def test_emit_receipt_stdout(self, capsys):
        """Test receipt is printed to stdout."""
        emit_receipt("test", {"tenant_id": TENANT_ID})
        captured = capsys.readouterr()
        assert '"receipt_type"' in captured.out
        assert "test" in captured.out

    def test_emit_receipt_json_valid(self, capsys):
        """Test receipt is valid JSON."""
        emit_receipt("test", {"tenant_id": TENANT_ID})
        captured = capsys.readouterr()
        # Parse the JSON
        receipt = json.loads(captured.out.strip())
        assert receipt["receipt_type"] == "test"


class TestMerkle:
    """Tests for merkle function."""

    def test_merkle_empty(self):
        """Test merkle with empty list."""
        result = merkle([])
        assert ":" in result
        assert result == dual_hash(b"empty")

    def test_merkle_single(self):
        """Test merkle with single item."""
        items = [{"key": "value"}]
        result = merkle(items)
        assert ":" in result

    def test_merkle_multiple(self):
        """Test merkle with multiple items."""
        items = [{"a": 1}, {"b": 2}, {"c": 3}]
        result = merkle(items)
        assert ":" in result

    def test_merkle_deterministic(self):
        """Test same items produce same root."""
        items = [{"a": 1}, {"b": 2}]
        root1 = merkle(items)
        root2 = merkle(items)
        assert root1 == root2

    def test_merkle_order_matters(self):
        """Test different order produces different root."""
        items1 = [{"a": 1}, {"b": 2}]
        items2 = [{"b": 2}, {"a": 1}]
        root1 = merkle(items1)
        root2 = merkle(items2)
        assert root1 != root2


class TestStopRule:
    """Tests for stoprule functions."""

    def test_stoprule_exception(self):
        """Test StopRule is an exception."""
        assert issubclass(StopRule, Exception)

    def test_stoprule_hash_mismatch(self):
        """Test hash mismatch stoprule."""
        with pytest.raises(StopRule) as excinfo:
            stoprule_hash_mismatch("expected", "actual")
        assert "Hash mismatch" in str(excinfo.value)

    def test_stoprule_invalid_receipt(self):
        """Test invalid receipt stoprule."""
        with pytest.raises(StopRule) as excinfo:
            stoprule_invalid_receipt("missing field")
        assert "Invalid receipt" in str(excinfo.value)


class TestCheckBias:
    """Tests for bias checking."""

    def test_check_bias_no_disparity(self):
        """Test bias check with no disparity."""
        result = check_bias(["A", "B"], [0.5, 0.5])
        assert result["disparity"] == 0.0
        assert result["mitigation_action"] == "none"

    def test_check_bias_small_disparity(self):
        """Test bias check with small disparity."""
        result = check_bias(["A", "B"], [0.502, 0.500])
        assert result["disparity"] < 0.005
        assert result["mitigation_action"] == "none"


class TestConstants:
    """Tests for constants."""

    def test_hb6_amount(self):
        """Test HB6 bribery amount is correct."""
        assert HB6_BRIBERY_AMOUNT == 60_000_000

    def test_medicaid_individuals(self):
        """Test Medicaid concurrent individuals."""
        assert MEDICAID_CONCURRENT_INDIVIDUALS == 124_448

    def test_jobsohio_rate(self):
        """Test JobsOhio failure rate."""
        assert JOBSOHIO_FAILURE_RATE == 0.65
