"""
Dialectic Analysis Module

Purpose: PRO/CON analysis for balanced decision-making

Receipt: dialectic_receipt
Gate: t36h
"""

from typing import Any

from src.core import emit_receipt, TENANT_ID


def analyze_dialectic(
    evidence: list[dict],
    hypothesis: str
) -> dict:
    """
    Analyze evidence dialectically for/against hypothesis.

    Args:
        evidence: List of evidence items
        hypothesis: Hypothesis to evaluate

    Returns:
        Dialectic analysis
    """
    pro = []
    con = []
    neutral = []

    for item in evidence:
        # Classify evidence
        score = item.get("correlation_score", 0) or item.get("anomaly_score", 0)
        flagged = item.get("flagged", False)

        if flagged or score > 0.7:
            pro.append({
                "evidence": item.get("receipt_type"),
                "score": score,
                "reason": "strong_signal"
            })
        elif score > 0.3:
            neutral.append({
                "evidence": item.get("receipt_type"),
                "score": score,
                "reason": "moderate_signal"
            })
        else:
            con.append({
                "evidence": item.get("receipt_type"),
                "score": score,
                "reason": "weak_or_no_signal"
            })

    analysis = {
        "hypothesis": hypothesis,
        "pro_count": len(pro),
        "con_count": len(con),
        "neutral_count": len(neutral),
        "pro": pro[:10],  # Top 10
        "con": con[:10],
        "neutral": neutral[:10],
        "balance": calculate_balance(len(pro), len(con), len(neutral))
    }

    emit_receipt("dialectic_analysis", {
        "tenant_id": TENANT_ID,
        "hypothesis_hash": hash(hypothesis) % 10000,
        "pro_count": len(pro),
        "con_count": len(con),
        "neutral_count": len(neutral),
        "balance": analysis["balance"]
    })

    return analysis


def calculate_balance(pro: int, con: int, neutral: int) -> str:
    """
    Calculate dialectic balance.

    Args:
        pro: Count of supporting evidence
        con: Count of opposing evidence
        neutral: Count of neutral evidence

    Returns:
        Balance classification
    """
    total = pro + con + neutral

    if total == 0:
        return "insufficient_evidence"

    pro_ratio = pro / total
    con_ratio = con / total

    if pro_ratio > 0.7:
        return "strongly_supported"
    elif pro_ratio > 0.5:
        return "moderately_supported"
    elif con_ratio > 0.7:
        return "strongly_opposed"
    elif con_ratio > 0.5:
        return "moderately_opposed"
    else:
        return "inconclusive"


def generate_pro_con(
    analysis: dict
) -> dict:
    """
    Generate PRO/CON summary.

    Args:
        analysis: Dialectic analysis

    Returns:
        PRO/CON summary
    """
    summary = {
        "hypothesis": analysis.get("hypothesis"),
        "pro_arguments": [],
        "con_arguments": [],
        "recommendation": ""
    }

    # Generate pro arguments
    for item in analysis.get("pro", []):
        summary["pro_arguments"].append({
            "type": item.get("evidence"),
            "strength": "strong" if item.get("score", 0) > 0.8 else "moderate"
        })

    # Generate con arguments
    for item in analysis.get("con", []):
        summary["con_arguments"].append({
            "type": item.get("evidence"),
            "weakness": item.get("reason")
        })

    # Generate recommendation
    balance = analysis.get("balance", "inconclusive")
    if balance == "strongly_supported":
        summary["recommendation"] = "Proceed with high confidence"
    elif balance == "moderately_supported":
        summary["recommendation"] = "Proceed with caution, gather additional evidence"
    elif balance == "strongly_opposed":
        summary["recommendation"] = "Do not proceed, evidence contradicts hypothesis"
    elif balance == "moderately_opposed":
        summary["recommendation"] = "Reconsider hypothesis, significant counter-evidence"
    else:
        summary["recommendation"] = "Gather more evidence before decision"

    emit_receipt("pro_con_summary", {
        "tenant_id": TENANT_ID,
        "pro_count": len(summary["pro_arguments"]),
        "con_count": len(summary["con_arguments"]),
        "balance": balance
    })

    return summary


def identify_gaps(
    analysis: dict,
    expected_evidence_types: list[str] | None = None
) -> list[dict]:
    """
    Identify gaps in evidence.

    Args:
        analysis: Dialectic analysis
        expected_evidence_types: Expected types of evidence

    Returns:
        List of identified gaps
    """
    if expected_evidence_types is None:
        expected_evidence_types = [
            "correlation",
            "anomaly",
            "pattern_match",
            "verification"
        ]

    found_types = set()

    for item in analysis.get("pro", []) + analysis.get("con", []) + analysis.get("neutral", []):
        evidence_type = item.get("evidence", "")
        for expected in expected_evidence_types:
            if expected in evidence_type:
                found_types.add(expected)

    gaps = []
    for expected in expected_evidence_types:
        if expected not in found_types:
            gaps.append({
                "missing_type": expected,
                "impact": "high" if expected in ["verification", "correlation"] else "medium",
                "recommendation": f"Gather {expected} evidence"
            })

    emit_receipt("evidence_gaps", {
        "tenant_id": TENANT_ID,
        "expected_types": len(expected_evidence_types),
        "found_types": len(found_types),
        "gap_count": len(gaps)
    })

    return gaps


def synthesize_dialectic_brief(
    analyses: list[dict]
) -> dict:
    """
    Synthesize multiple dialectic analyses into brief.

    Args:
        analyses: List of dialectic analyses

    Returns:
        Synthesized brief
    """
    total_pro = sum(a.get("pro_count", 0) for a in analyses)
    total_con = sum(a.get("con_count", 0) for a in analyses)
    total_neutral = sum(a.get("neutral_count", 0) for a in analyses)

    balances = [a.get("balance", "inconclusive") for a in analyses]
    supported = sum(1 for b in balances if "supported" in b)
    opposed = sum(1 for b in balances if "opposed" in b)

    brief = {
        "analyses_count": len(analyses),
        "total_pro": total_pro,
        "total_con": total_con,
        "total_neutral": total_neutral,
        "supported_hypotheses": supported,
        "opposed_hypotheses": opposed,
        "overall_balance": calculate_balance(total_pro, total_con, total_neutral)
    }

    emit_receipt("dialectic_brief", {
        "tenant_id": TENANT_ID,
        **brief
    })

    return brief
