"""
Anomaly Detection Module

Purpose: Core entropy-based anomaly detection engine
Model: US Treasury Office of Payment Integrity ($4B savings FY2024)

Receipt: anomaly_receipt
SLO: detection_latency <= 5s per 10K transactions, false_positive <= 15%
Gate: t16h
"""

import math
import time
from collections import Counter
from typing import Any

from src.core import dual_hash, emit_receipt, TENANT_ID
from src.constants import FALSE_POSITIVE_MAX, PRECISION_MIN


def compute_entropy(transactions: list[dict], field: str) -> float:
    """
    Compute Shannon entropy of field distribution.

    High entropy = unpredictable/random = potential fraud
    Low entropy = predictable/structured = legitimate

    Args:
        transactions: List of transaction records
        field: Field name to analyze

    Returns:
        Shannon entropy value (0.0 = uniform, higher = more random)
    """
    if not transactions:
        return 0.0

    # Extract field values
    values = [str(t.get(field, "")) for t in transactions if t.get(field)]

    if not values:
        return 0.0

    # Count frequencies
    counter = Counter(values)
    total = len(values)

    # Calculate Shannon entropy
    entropy = 0.0
    for count in counter.values():
        if count > 0:
            p = count / total
            entropy -= p * math.log2(p)

    return entropy


def detect_anomaly(
    current: dict,
    baseline: dict,
    threshold: float = 0.2
) -> dict:
    """
    Flag if entropy delta exceeds threshold.

    Args:
        current: Current metrics (e.g., {"entropy": 2.5})
        baseline: Baseline metrics (e.g., {"entropy": 1.5})
        threshold: Anomaly threshold (default 0.2 = 20%)

    Returns:
        Anomaly detection result
    """
    current_val = current.get("entropy", 0.0)
    baseline_val = baseline.get("entropy", 0.0)

    if baseline_val == 0:
        delta = current_val
        delta_pct = 1.0 if current_val > 0 else 0.0
    else:
        delta = current_val - baseline_val
        delta_pct = abs(delta) / baseline_val

    is_anomaly = delta_pct > threshold

    result = {
        "current_value": current_val,
        "baseline_value": baseline_val,
        "delta": delta,
        "delta_pct": delta_pct,
        "threshold": threshold,
        "is_anomaly": is_anomaly,
        "classification": classify_anomaly(delta, delta_pct) if is_anomaly else None
    }

    if is_anomaly:
        emit_anomaly(
            metric="entropy",
            baseline=baseline_val,
            delta=delta,
            classification=result["classification"],
            action="alert" if delta_pct < 0.5 else "escalate"
        )

    return result


def classify_anomaly(delta: float, delta_pct: float) -> str:
    """
    Classify anomaly type based on delta characteristics.

    Classifications:
        - drift: Gradual change over time
        - degradation: Performance getting worse
        - violation: Clear threshold breach
        - deviation: Unexpected pattern
        - anti_pattern: Known bad pattern detected

    Args:
        delta: Absolute delta value
        delta_pct: Percentage change

    Returns:
        Classification string
    """
    if delta_pct >= 1.0:  # 100%+ change
        return "violation"
    elif delta_pct >= 0.5:  # 50-100% change
        return "deviation"
    elif delta > 0:
        return "drift"
    else:
        return "degradation"


def emit_anomaly(
    metric: str,
    baseline: float,
    delta: float,
    classification: str,
    action: str
) -> dict:
    """
    Emit anomaly receipt per CLAUDEME §4.7.

    Args:
        metric: Metric name
        baseline: Baseline value
        delta: Delta from baseline
        classification: Anomaly classification
        action: Recommended action

    Returns:
        Anomaly receipt
    """
    return emit_receipt("anomaly", {
        "tenant_id": TENANT_ID,
        "metric": metric,
        "baseline": baseline,
        "delta": delta,
        "classification": classification,
        "action": action
    })


def detect_transaction_anomaly(
    transactions: list[dict],
    baseline_transactions: list[dict],
    fields: list[str] | None = None
) -> dict:
    """
    Detect anomalies in transaction set compared to baseline.

    Args:
        transactions: Current transaction set
        baseline_transactions: Baseline transaction set
        fields: Fields to analyze (default: amount, vendor_id, agency)

    Returns:
        Multi-field anomaly analysis
    """
    t0 = time.time()

    if fields is None:
        fields = ["amount", "vendor_id", "agency"]

    anomalies = []
    field_results = {}

    for field in fields:
        current_entropy = compute_entropy(transactions, field)
        baseline_entropy = compute_entropy(baseline_transactions, field)

        result = detect_anomaly(
            {"entropy": current_entropy},
            {"entropy": baseline_entropy}
        )

        field_results[field] = result

        if result["is_anomaly"]:
            anomalies.append({
                "field": field,
                "classification": result["classification"],
                "delta": result["delta"]
            })

    latency_ms = (time.time() - t0) * 1000

    overall_result = {
        "transaction_count": len(transactions),
        "baseline_count": len(baseline_transactions),
        "fields_analyzed": len(fields),
        "anomalies_detected": len(anomalies),
        "field_results": field_results,
        "anomalies": anomalies,
        "latency_ms": latency_ms
    }

    emit_receipt("transaction_anomaly_detection", {
        "tenant_id": TENANT_ID,
        "transaction_count": len(transactions),
        "fields_analyzed": len(fields),
        "anomalies_detected": len(anomalies),
        "latency_ms": latency_ms
    })

    return overall_result


def compute_field_statistics(transactions: list[dict], field: str) -> dict:
    """
    Compute statistical measures for a field.

    Args:
        transactions: List of transactions
        field: Field to analyze

    Returns:
        Statistical summary
    """
    values = []
    for t in transactions:
        val = t.get(field)
        if val is not None:
            try:
                values.append(float(val))
            except (ValueError, TypeError):
                pass

    if not values:
        return {
            "field": field,
            "count": 0,
            "sum": 0,
            "mean": 0,
            "min": 0,
            "max": 0,
            "std": 0
        }

    n = len(values)
    total = sum(values)
    mean = total / n
    min_val = min(values)
    max_val = max(values)

    # Standard deviation
    variance = sum((x - mean) ** 2 for x in values) / n
    std = math.sqrt(variance)

    return {
        "field": field,
        "count": n,
        "sum": total,
        "mean": mean,
        "min": min_val,
        "max": max_val,
        "std": std
    }


def detect_statistical_anomaly(
    current_stats: dict,
    baseline_stats: dict,
    z_threshold: float = 3.0
) -> dict:
    """
    Detect statistical anomalies using z-score.

    Args:
        current_stats: Current statistics
        baseline_stats: Baseline statistics
        z_threshold: Z-score threshold (default 3.0 = 3 sigma)

    Returns:
        Statistical anomaly result
    """
    baseline_mean = baseline_stats.get("mean", 0)
    baseline_std = baseline_stats.get("std", 1)

    if baseline_std == 0:
        baseline_std = 1  # Avoid division by zero

    current_mean = current_stats.get("mean", 0)

    z_score = (current_mean - baseline_mean) / baseline_std
    is_anomaly = abs(z_score) > z_threshold

    result = {
        "field": current_stats.get("field", "unknown"),
        "current_mean": current_mean,
        "baseline_mean": baseline_mean,
        "baseline_std": baseline_std,
        "z_score": z_score,
        "z_threshold": z_threshold,
        "is_anomaly": is_anomaly
    }

    if is_anomaly:
        emit_anomaly(
            metric=f"statistical_{result['field']}",
            baseline=baseline_mean,
            delta=current_mean - baseline_mean,
            classification="deviation" if z_score > 0 else "degradation",
            action="escalate" if abs(z_score) > 5 else "alert"
        )

    return result
