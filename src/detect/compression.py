"""
Compression-Based Fraud Detection Module

Purpose: Compression ratio as fraud signal (QED paradigm)

Physics:
    - Legitimate transactions: Compression ratio 0.30-0.60 (predictable patterns)
    - Fraudulent transactions: Compression ratio 0.70-0.95 (random/unusual patterns)

Receipt: compression_receipt
SLO: detection_latency <= 5s per 10K transactions
Gate: t16h
"""

import gzip
import json
import time
from typing import Any

from src.core import dual_hash, emit_receipt, TENANT_ID
from src.constants import (
    COMPRESSION_RATIO_LEGITIMATE,
    COMPRESSION_RATIO_SUSPICIOUS,
    COMPRESSION_RATIO_FRAUDULENT
)


def compute_compression(data: bytes) -> float:
    """
    Compute compression ratio for data.

    Ratio = compressed_size / original_size

    Args:
        data: Data to compress

    Returns:
        Compression ratio (0.0 - 1.0)
    """
    if not data:
        return 0.0

    original_size = len(data)
    compressed = gzip.compress(data)
    compressed_size = len(compressed)

    ratio = compressed_size / original_size

    return ratio


def score_transaction_set(transactions: list[dict]) -> float:
    """
    Compute average compression ratio for transaction set.

    Lower ratio = more compressible = more predictable = more legitimate
    Higher ratio = less compressible = more random = more suspicious

    Args:
        transactions: List of transaction records

    Returns:
        Average compression ratio
    """
    if not transactions:
        return 0.0

    # Serialize transactions to JSON bytes
    data = json.dumps(transactions, sort_keys=True).encode("utf-8")

    ratio = compute_compression(data)

    emit_receipt("compression", {
        "tenant_id": TENANT_ID,
        "transaction_count": len(transactions),
        "original_size": len(data),
        "ratio": ratio,
        "classification": classify_compression(ratio)
    })

    return ratio


def flag_high_entropy(ratio: float, threshold: float | None = None) -> bool:
    """
    Flag if compression ratio indicates high entropy (potential fraud).

    Args:
        ratio: Compression ratio
        threshold: Custom threshold (default: COMPRESSION_RATIO_SUSPICIOUS)

    Returns:
        True if flagged as high entropy
    """
    if threshold is None:
        threshold = COMPRESSION_RATIO_SUSPICIOUS

    return ratio >= threshold


def classify_compression(ratio: float) -> str:
    """
    Classify compression ratio.

    Args:
        ratio: Compression ratio

    Returns:
        Classification: "legitimate", "suspicious", or "fraudulent"
    """
    if ratio < COMPRESSION_RATIO_LEGITIMATE:
        return "highly_compressible"
    elif ratio < COMPRESSION_RATIO_SUSPICIOUS:
        return "legitimate"
    elif ratio < COMPRESSION_RATIO_FRAUDULENT:
        return "suspicious"
    else:
        return "fraudulent"


def analyze_transaction_compression(
    transactions: list[dict],
    window_size: int = 100
) -> dict:
    """
    Analyze compression patterns in sliding windows.

    Args:
        transactions: List of transactions
        window_size: Size of sliding window

    Returns:
        Compression analysis with windows
    """
    t0 = time.time()

    windows = []
    suspicious_windows = []

    for i in range(0, len(transactions), window_size):
        window = transactions[i:i + window_size]
        if not window:
            continue

        ratio = score_transaction_set(window)
        window_result = {
            "start_index": i,
            "end_index": i + len(window),
            "count": len(window),
            "ratio": ratio,
            "classification": classify_compression(ratio)
        }
        windows.append(window_result)

        if flag_high_entropy(ratio):
            suspicious_windows.append(window_result)

    latency_ms = (time.time() - t0) * 1000

    result = {
        "total_transactions": len(transactions),
        "window_size": window_size,
        "windows_analyzed": len(windows),
        "suspicious_windows": len(suspicious_windows),
        "windows": windows,
        "latency_ms": latency_ms
    }

    if suspicious_windows:
        emit_receipt("compression_anomaly", {
            "tenant_id": TENANT_ID,
            "total_transactions": len(transactions),
            "suspicious_windows": len(suspicious_windows),
            "window_details": [
                {"start": w["start_index"], "ratio": w["ratio"]}
                for w in suspicious_windows[:10]  # Top 10
            ]
        })

    return result


def compare_compression_baselines(
    current: list[dict],
    baseline: list[dict],
    threshold: float = 0.1
) -> dict:
    """
    Compare compression ratios between current and baseline.

    Args:
        current: Current transaction set
        baseline: Baseline transaction set
        threshold: Delta threshold for flagging

    Returns:
        Comparison result
    """
    current_ratio = score_transaction_set(current)
    baseline_ratio = score_transaction_set(baseline)

    delta = current_ratio - baseline_ratio
    is_anomaly = abs(delta) > threshold

    result = {
        "current_ratio": current_ratio,
        "baseline_ratio": baseline_ratio,
        "delta": delta,
        "threshold": threshold,
        "is_anomaly": is_anomaly,
        "current_classification": classify_compression(current_ratio),
        "baseline_classification": classify_compression(baseline_ratio)
    }

    if is_anomaly:
        emit_receipt("compression_baseline_anomaly", {
            "tenant_id": TENANT_ID,
            "current_ratio": current_ratio,
            "baseline_ratio": baseline_ratio,
            "delta": delta,
            "classification": "degradation" if delta > 0 else "improvement"
        })

    return result


def compute_field_compression(
    transactions: list[dict],
    field: str
) -> dict:
    """
    Compute compression ratio for specific field values.

    Args:
        transactions: List of transactions
        field: Field to analyze

    Returns:
        Field-specific compression analysis
    """
    # Extract field values
    values = [str(t.get(field, "")) for t in transactions if t.get(field)]

    if not values:
        return {
            "field": field,
            "value_count": 0,
            "ratio": 0.0,
            "classification": "no_data"
        }

    # Serialize values
    data = "\n".join(values).encode("utf-8")

    ratio = compute_compression(data)

    return {
        "field": field,
        "value_count": len(values),
        "unique_values": len(set(values)),
        "ratio": ratio,
        "classification": classify_compression(ratio)
    }


def detect_structured_fraud(transactions: list[dict]) -> dict:
    """
    Detect structured transactions designed to evade detection.

    Pattern: Transactions structured to avoid thresholds (e.g., multiple
    transactions just under $10,000 to avoid reporting requirements).

    Args:
        transactions: List of transactions

    Returns:
        Structured fraud detection result
    """
    suspicious_patterns = []

    # Check for amount clustering
    amounts = [t.get("amount", 0) for t in transactions if t.get("amount")]

    if amounts:
        # Check for clustering just below common thresholds
        thresholds = [10000, 5000, 3000, 1000]

        for threshold in thresholds:
            below_threshold = [a for a in amounts if threshold * 0.9 <= a < threshold]
            if len(below_threshold) >= 3:
                suspicious_patterns.append({
                    "pattern": "threshold_avoidance",
                    "threshold": threshold,
                    "count": len(below_threshold),
                    "total_amount": sum(below_threshold)
                })

    result = {
        "transactions_analyzed": len(transactions),
        "suspicious_patterns": len(suspicious_patterns),
        "patterns": suspicious_patterns,
        "flagged": len(suspicious_patterns) > 0
    }

    if suspicious_patterns:
        emit_receipt("structured_fraud_detection", {
            "tenant_id": TENANT_ID,
            "transactions_analyzed": len(transactions),
            "patterns_detected": len(suspicious_patterns),
            "pattern_types": [p["pattern"] for p in suspicious_patterns]
        })

    return result
