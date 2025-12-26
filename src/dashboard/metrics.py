"""
Metrics Module

Purpose: KPI calculations for dashboard

Receipt: metrics_receipt
Gate: t36h
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from src.core import emit_receipt, TENANT_ID


def compute_kpis(receipts: list[dict]) -> dict:
    """
    Compute key performance indicators.

    Args:
        receipts: All receipts

    Returns:
        KPI metrics
    """
    total = len(receipts)
    anomalies = sum(1 for r in receipts if r.get("receipt_type") == "anomaly")
    flagged = sum(1 for r in receipts if r.get("flagged"))

    # Detection rate (anomalies / total)
    detection_rate = anomalies / total if total > 0 else 0

    # Flag rate
    flag_rate = flagged / total if total > 0 else 0

    # Correlation success rate
    correlations = [r for r in receipts if "correlation" in r.get("receipt_type", "")]
    successful_correlations = sum(
        1 for c in correlations
        if c.get("correlation_score", 0) >= 0.7
    )
    correlation_rate = successful_correlations / len(correlations) if correlations else 0

    kpis = {
        "total_receipts": total,
        "detection_rate": detection_rate,
        "flag_rate": flag_rate,
        "correlation_success_rate": correlation_rate,
        "anomaly_count": anomalies,
        "flagged_count": flagged,
        "correlation_count": len(correlations)
    }

    emit_receipt("kpi_computation", {
        "tenant_id": TENANT_ID,
        **kpis
    })

    return kpis


def compute_domain_metrics(
    domain: str,
    receipts: list[dict]
) -> dict:
    """
    Compute metrics for specific domain.

    Args:
        domain: Domain name
        receipts: All receipts

    Returns:
        Domain-specific metrics
    """
    domain_receipts = [
        r for r in receipts
        if domain in r.get("receipt_type", "") or r.get("domain") == domain
    ]

    if not domain_receipts:
        return {
            "domain": domain,
            "receipt_count": 0,
            "metrics": {}
        }

    # Count by type
    by_type = {}
    for r in domain_receipts:
        rt = r.get("receipt_type", "unknown")
        by_type[rt] = by_type.get(rt, 0) + 1

    # Flagged items
    flagged = sum(1 for r in domain_receipts if r.get("flagged"))

    # Average scores
    scores = [
        r.get("correlation_score", 0) or
        r.get("anomaly_score", 0) or
        r.get("score", 0)
        for r in domain_receipts
    ]
    avg_score = sum(scores) / len(scores) if scores else 0

    metrics = {
        "domain": domain,
        "receipt_count": len(domain_receipts),
        "by_type": by_type,
        "flagged_count": flagged,
        "average_score": avg_score,
        "metrics": {}
    }

    emit_receipt("domain_metrics", {
        "tenant_id": TENANT_ID,
        "domain": domain,
        "receipt_count": len(domain_receipts),
        "flagged_count": flagged
    })

    return metrics


def compute_trend_metrics(
    receipts: list[dict],
    period_days: int = 7
) -> dict:
    """
    Compute trend metrics over time periods.

    Args:
        receipts: All receipts
        period_days: Period length in days

    Returns:
        Trend metrics
    """
    now = datetime.now(timezone.utc)
    periods = []

    for i in range(4):  # 4 periods
        period_end = now - timedelta(days=i * period_days)
        period_start = period_end - timedelta(days=period_days)

        period_receipts = [
            r for r in receipts
            if period_start.isoformat() <= r.get("ts", "") <= period_end.isoformat()
        ]

        periods.append({
            "period": i,
            "start": period_start.isoformat(),
            "end": period_end.isoformat(),
            "count": len(period_receipts),
            "anomalies": sum(1 for r in period_receipts if r.get("receipt_type") == "anomaly"),
            "flagged": sum(1 for r in period_receipts if r.get("flagged"))
        })

    # Calculate trends
    if len(periods) >= 2:
        current = periods[0]
        previous = periods[1]

        if previous["count"] > 0:
            count_trend = (current["count"] - previous["count"]) / previous["count"]
        else:
            count_trend = 0

        if previous["anomalies"] > 0:
            anomaly_trend = (current["anomalies"] - previous["anomalies"]) / previous["anomalies"]
        else:
            anomaly_trend = 0
    else:
        count_trend = 0
        anomaly_trend = 0

    trends = {
        "period_days": period_days,
        "periods": periods,
        "count_trend": count_trend,
        "anomaly_trend": anomaly_trend,
        "trend_direction": "up" if count_trend > 0.1 else ("down" if count_trend < -0.1 else "stable")
    }

    emit_receipt("trend_metrics", {
        "tenant_id": TENANT_ID,
        "period_days": period_days,
        "periods_analyzed": len(periods),
        "trend_direction": trends["trend_direction"]
    })

    return trends


def compute_slo_metrics(receipts: list[dict]) -> dict:
    """
    Compute SLO compliance metrics.

    Args:
        receipts: All receipts

    Returns:
        SLO metrics
    """
    # Calculate latencies from receipts with latency_ms
    latencies = [
        r.get("latency_ms", 0)
        for r in receipts
        if r.get("latency_ms")
    ]

    if latencies:
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 20 else max_latency
    else:
        avg_latency = 0
        max_latency = 0
        p95_latency = 0

    # SLO compliance
    slo_thresholds = {
        "ingest_latency_ms": 60000,
        "detection_latency_ms": 5000
    }

    ingest_receipts = [r for r in receipts if "ingest" in r.get("receipt_type", "")]
    ingest_violations = sum(
        1 for r in ingest_receipts
        if r.get("latency_ms", 0) > slo_thresholds["ingest_latency_ms"]
    )

    slo_metrics = {
        "avg_latency_ms": avg_latency,
        "max_latency_ms": max_latency,
        "p95_latency_ms": p95_latency,
        "ingest_slo_violations": ingest_violations,
        "slo_compliance_rate": 1 - (ingest_violations / len(ingest_receipts)) if ingest_receipts else 1
    }

    emit_receipt("slo_metrics", {
        "tenant_id": TENANT_ID,
        **slo_metrics
    })

    return slo_metrics
