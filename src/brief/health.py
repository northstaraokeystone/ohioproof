"""
Decision Health Module

Purpose: Score decision quality based on evidence

Receipt: decision_health_receipt
Gate: t36h
"""

from typing import Any

from src.core import emit_receipt, StopRule, TENANT_ID


def compute_decision_health(
    evidence: list[dict],
    thresholds: dict | None = None
) -> dict:
    """
    Compute decision health score.

    Components:
        - Strength: Evidence quality and confidence
        - Coverage: Breadth of evidence
        - Efficiency: Evidence-to-decision ratio

    Args:
        evidence: List of evidence items
        thresholds: Optional thresholds for scoring

    Returns:
        Decision health metrics
    """
    if thresholds is None:
        thresholds = {
            "min_strength": 0.8,
            "min_coverage": 0.7,
            "min_efficiency": 0.6
        }

    strength = score_strength(evidence)
    coverage = score_coverage(evidence)
    efficiency = score_efficiency(evidence)

    # Overall health is weighted average
    overall = (strength * 0.4) + (coverage * 0.35) + (efficiency * 0.25)

    health = {
        "strength": strength,
        "coverage": coverage,
        "efficiency": efficiency,
        "overall": overall,
        "thresholds": thresholds,
        "meets_threshold": overall >= thresholds.get("min_strength", 0.8)
    }

    receipt = emit_receipt("decision_health", {
        "tenant_id": TENANT_ID,
        **health,
        "evidence_count": len(evidence)
    })

    # Stoprule if below threshold
    if strength < thresholds.get("min_strength", 0.8) * 0.5:
        stoprule_weak(strength)

    return health


def score_strength(evidence: list[dict]) -> float:
    """
    Score evidence strength/quality.

    Factors:
        - Verification status
        - Source reliability
        - Consistency across sources

    Args:
        evidence: List of evidence items

    Returns:
        Strength score (0.0 - 1.0)
    """
    if not evidence:
        return 0.0

    total_score = 0.0

    for item in evidence:
        item_score = 0.5  # Base score

        # Verified items get higher score
        if item.get("verified"):
            item_score += 0.2

        # High confidence items
        confidence = item.get("confidence", 0.5)
        item_score += confidence * 0.2

        # Flagged items (indicates detection worked)
        if item.get("flagged"):
            item_score += 0.1

        total_score += min(item_score, 1.0)

    return total_score / len(evidence)


def score_coverage(evidence: list[dict]) -> float:
    """
    Score evidence coverage/breadth.

    Factors:
        - Number of sources
        - Types of evidence
        - Time span covered

    Args:
        evidence: List of evidence items

    Returns:
        Coverage score (0.0 - 1.0)
    """
    if not evidence:
        return 0.0

    # Source diversity
    sources = set()
    types = set()

    for item in evidence:
        if item.get("source"):
            sources.add(item["source"])
        if item.get("receipt_type"):
            types.add(item["receipt_type"])

    source_score = min(len(sources) / 5, 1.0)  # Max at 5 sources
    type_score = min(len(types) / 10, 1.0)  # Max at 10 types

    # Volume factor
    volume_score = min(len(evidence) / 100, 1.0)  # Max at 100 items

    coverage = (source_score * 0.4) + (type_score * 0.4) + (volume_score * 0.2)

    return coverage


def score_efficiency(evidence: list[dict]) -> float:
    """
    Score evidence efficiency.

    Factors:
        - Signal-to-noise ratio
        - Actionable findings
        - Processing time

    Args:
        evidence: List of evidence items

    Returns:
        Efficiency score (0.0 - 1.0)
    """
    if not evidence:
        return 0.0

    # Actionable items (flagged, anomalies)
    actionable = sum(1 for e in evidence if e.get("flagged") or
                     e.get("receipt_type") == "anomaly")

    actionable_ratio = actionable / len(evidence) if evidence else 0

    # Non-noise items (have meaningful data)
    meaningful = sum(1 for e in evidence if e.get("correlation_score", 0) > 0 or
                     e.get("anomaly_score", 0) > 0 or
                     e.get("flagged"))

    meaningful_ratio = meaningful / len(evidence) if evidence else 0

    efficiency = (actionable_ratio * 0.5) + (meaningful_ratio * 0.5)

    return min(efficiency * 2, 1.0)  # Scale up but cap at 1.0


def evaluate_decision_readiness(
    health: dict,
    context: dict | None = None
) -> dict:
    """
    Evaluate if decision is ready based on health.

    Args:
        health: Decision health from compute_decision_health
        context: Additional context

    Returns:
        Readiness evaluation
    """
    ready = health.get("meets_threshold", False)
    overall = health.get("overall", 0)

    blockers = []
    if health.get("strength", 0) < 0.5:
        blockers.append("insufficient_evidence_strength")
    if health.get("coverage", 0) < 0.4:
        blockers.append("insufficient_evidence_coverage")

    evaluation = {
        "ready": ready and len(blockers) == 0,
        "overall_score": overall,
        "blockers": blockers,
        "recommendation": "proceed" if ready else "gather_more_evidence"
    }

    emit_receipt("decision_readiness", {
        "tenant_id": TENANT_ID,
        **evaluation
    })

    return evaluation


def stoprule_weak(strength: float) -> None:
    """
    Stoprule for weak evidence.

    Args:
        strength: Strength score
    """
    emit_receipt("anomaly", {
        "tenant_id": TENANT_ID,
        "metric": "decision_strength",
        "baseline": 0.8,
        "delta": strength - 0.8,
        "classification": "degradation",
        "action": "escalate"
    })
    raise StopRule(f"Weak evidence: strength {strength} < 0.4")
