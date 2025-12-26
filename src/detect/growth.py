"""
Growth Rate Anomaly Detection Module

Purpose: Detect explosive growth patterns (Minnesota Feeding Our Future pattern)

Critical Pattern:
    - 2,800% payment surge in one year
    - Sites claiming thousands of meals within days of opening
    - 30+ complaints ignored

SLO: Any growth > 500% triggers immediate human review

Receipt: growth_anomaly_receipt
Gate: t16h
"""

import time
from datetime import datetime
from typing import Any

from src.core import dual_hash, emit_receipt, TENANT_ID
from src.constants import GROWTH_RATE_ALERT, GROWTH_RATE_CRITICAL


def compute_growth_rate(series: list[float | int]) -> float:
    """
    Compute period-over-period growth rate.

    Args:
        series: Time series of values (e.g., monthly payments)

    Returns:
        Growth rate as multiplier (e.g., 28.0 = 2800% growth)
    """
    if not series or len(series) < 2:
        return 0.0

    first_val = series[0]
    last_val = series[-1]

    if first_val == 0:
        if last_val == 0:
            return 0.0
        return float('inf')  # Infinite growth from zero

    growth_rate = last_val / first_val

    return growth_rate


def flag_explosive_growth(
    rate: float,
    threshold: float | None = None
) -> bool:
    """
    Flag if growth rate exceeds threshold.

    Args:
        rate: Growth rate multiplier
        threshold: Custom threshold (default: GROWTH_RATE_CRITICAL = 28.0)

    Returns:
        True if flagged
    """
    if threshold is None:
        threshold = GROWTH_RATE_CRITICAL

    return rate >= threshold


def detect_onboarding_velocity(entity: dict) -> float:
    """
    Score for suspicious rapid scaling.

    FOF Pattern: Sites claiming thousands of meals within days of opening.

    Args:
        entity: Entity record with onboarding data

    Returns:
        Velocity score (0.0 - 1.0)
    """
    score = 0.0
    indicators = []

    # Days from opening to first large claim
    days_to_scale = entity.get("days_to_first_large_claim", 365)

    if days_to_scale <= 7:
        score += 0.5
        indicators.append("scaled_within_7_days")
    elif days_to_scale <= 30:
        score += 0.3
        indicators.append("scaled_within_30_days")
    elif days_to_scale <= 90:
        score += 0.15
        indicators.append("scaled_within_90_days")

    # Ratio of claimed capacity to reasonable capacity
    claimed_capacity = entity.get("claimed_capacity", 0)
    reasonable_capacity = entity.get("estimated_reasonable_capacity", claimed_capacity)

    if reasonable_capacity > 0:
        capacity_ratio = claimed_capacity / reasonable_capacity

        if capacity_ratio >= 5.0:
            score += 0.4
            indicators.append("capacity_5x_reasonable")
        elif capacity_ratio >= 3.0:
            score += 0.25
            indicators.append("capacity_3x_reasonable")
        elif capacity_ratio >= 2.0:
            score += 0.1
            indicators.append("capacity_2x_reasonable")

    score = min(score, 1.0)

    emit_receipt("onboarding_velocity", {
        "tenant_id": TENANT_ID,
        "entity_hash": dual_hash(str(entity)),
        "velocity_score": score,
        "indicators": indicators,
        "days_to_scale": days_to_scale,
        "flagged": score >= 0.5
    })

    return score


def analyze_time_series(
    entity_id: str,
    values: list[dict],
    value_field: str = "amount",
    date_field: str = "date"
) -> dict:
    """
    Analyze time series for growth anomalies.

    Args:
        entity_id: Entity identifier
        values: List of time-stamped values
        value_field: Field containing the value
        date_field: Field containing the date

    Returns:
        Time series analysis result
    """
    t0 = time.time()

    if not values:
        return {
            "entity_id": entity_id,
            "error": "no_data"
        }

    # Sort by date
    sorted_values = sorted(values, key=lambda x: x.get(date_field, ""))

    # Extract numeric values
    numeric_values = []
    for v in sorted_values:
        try:
            numeric_values.append(float(v.get(value_field, 0)))
        except (ValueError, TypeError):
            numeric_values.append(0)

    # Overall growth rate
    overall_rate = compute_growth_rate(numeric_values)

    # Monthly growth rates
    monthly_rates = []
    for i in range(1, len(numeric_values)):
        if numeric_values[i - 1] > 0:
            rate = numeric_values[i] / numeric_values[i - 1]
            monthly_rates.append(rate)
        else:
            monthly_rates.append(0)

    # Maximum single-period growth
    max_period_rate = max(monthly_rates) if monthly_rates else 0

    # Detect alert and critical thresholds
    alert_triggered = overall_rate >= GROWTH_RATE_ALERT
    critical_triggered = overall_rate >= GROWTH_RATE_CRITICAL

    latency_ms = (time.time() - t0) * 1000

    result = {
        "entity_id": entity_id,
        "entity_hash": dual_hash(entity_id),
        "periods_analyzed": len(numeric_values),
        "first_value": numeric_values[0] if numeric_values else 0,
        "last_value": numeric_values[-1] if numeric_values else 0,
        "overall_growth_rate": overall_rate,
        "max_period_rate": max_period_rate,
        "alert_triggered": alert_triggered,
        "critical_triggered": critical_triggered,
        "latency_ms": latency_ms
    }

    if alert_triggered:
        emit_receipt("growth_anomaly", {
            "tenant_id": TENANT_ID,
            "entity_hash": dual_hash(entity_id),
            "growth_rate": overall_rate,
            "threshold": GROWTH_RATE_ALERT if not critical_triggered else GROWTH_RATE_CRITICAL,
            "severity": "critical" if critical_triggered else "alert",
            "action": "immediate_review" if critical_triggered else "review"
        })

    return result


def detect_growth_patterns(
    entities: list[dict],
    value_field: str = "amount",
    id_field: str = "entity_id"
) -> dict:
    """
    Detect growth patterns across multiple entities.

    Args:
        entities: List of entity records with time series data
        value_field: Field containing values
        id_field: Field containing entity ID

    Returns:
        Pattern detection results
    """
    t0 = time.time()

    alerts = []
    criticals = []

    for entity in entities:
        entity_id = entity.get(id_field, "unknown")
        values = entity.get("values", [])

        if not values:
            continue

        analysis = analyze_time_series(
            entity_id=entity_id,
            values=values,
            value_field=value_field
        )

        if analysis.get("critical_triggered"):
            criticals.append(analysis)
        elif analysis.get("alert_triggered"):
            alerts.append(analysis)

    latency_ms = (time.time() - t0) * 1000

    result = {
        "entities_analyzed": len(entities),
        "alerts_triggered": len(alerts),
        "criticals_triggered": len(criticals),
        "alerts": alerts,
        "criticals": criticals,
        "latency_ms": latency_ms
    }

    emit_receipt("growth_pattern_detection", {
        "tenant_id": TENANT_ID,
        "entities_analyzed": len(entities),
        "alerts_triggered": len(alerts),
        "criticals_triggered": len(criticals),
        "latency_ms": latency_ms
    })

    return result


def compute_yoy_growth(
    current_year_values: list[float],
    previous_year_values: list[float]
) -> float:
    """
    Compute year-over-year growth rate.

    Args:
        current_year_values: Values from current year
        previous_year_values: Values from previous year

    Returns:
        YoY growth rate as multiplier
    """
    current_total = sum(current_year_values)
    previous_total = sum(previous_year_values)

    if previous_total == 0:
        return float('inf') if current_total > 0 else 0.0

    return current_total / previous_total


def generate_growth_alert(
    entity_id: str,
    growth_rate: float,
    context: dict | None = None
) -> dict:
    """
    Generate growth alert for human review.

    Args:
        entity_id: Entity identifier
        growth_rate: Detected growth rate
        context: Additional context

    Returns:
        Alert record
    """
    severity = "critical" if growth_rate >= GROWTH_RATE_CRITICAL else "alert"

    alert = {
        "alert_id": dual_hash(f"{entity_id}:{growth_rate}:{time.time()}"),
        "entity_id": entity_id,
        "entity_hash": dual_hash(entity_id),
        "growth_rate": growth_rate,
        "growth_pct": (growth_rate - 1) * 100,
        "severity": severity,
        "action_required": "immediate_review" if severity == "critical" else "review",
        "context": context or {},
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    emit_receipt("growth_alert", {
        "tenant_id": TENANT_ID,
        **alert
    })

    return alert
