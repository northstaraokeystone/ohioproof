"""
Evidence Synthesis Module

Purpose: Synthesize evidence from multiple sources into coherent briefs

Receipt: brief_receipt
Gate: t36h
"""

from datetime import datetime, timezone
from typing import Any

from src.core import dual_hash, emit_receipt, TENANT_ID


def synthesize_evidence(
    receipts: list[dict],
    domain: str | None = None
) -> dict:
    """
    Synthesize evidence from receipts.

    Args:
        receipts: List of receipt dicts
        domain: Optional domain filter

    Returns:
        Synthesized evidence
    """
    if domain:
        receipts = [r for r in receipts if domain in r.get("receipt_type", "")]

    # Group by type
    by_type = {}
    for r in receipts:
        rt = r.get("receipt_type", "unknown")
        if rt not in by_type:
            by_type[rt] = []
        by_type[rt].append(r)

    # Extract key findings
    anomalies = [r for r in receipts if r.get("receipt_type") == "anomaly"]
    flagged = [r for r in receipts if r.get("flagged") is True]
    correlations = [r for r in receipts if "correlation" in r.get("receipt_type", "")]

    synthesis = {
        "total_receipts": len(receipts),
        "receipt_types": list(by_type.keys()),
        "by_type_counts": {k: len(v) for k, v in by_type.items()},
        "anomaly_count": len(anomalies),
        "flagged_count": len(flagged),
        "correlation_count": len(correlations),
        "domain": domain,
        "synthesis_ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }

    emit_receipt("evidence_synthesis", {
        "tenant_id": TENANT_ID,
        **synthesis
    })

    return synthesis


def generate_brief(
    synthesis: dict,
    context: dict | None = None
) -> dict:
    """
    Generate brief from synthesized evidence.

    Args:
        synthesis: Synthesized evidence from synthesize_evidence
        context: Additional context

    Returns:
        Brief document
    """
    brief = {
        "brief_id": dual_hash(str(synthesis) + str(context)),
        "generated_ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "domain": synthesis.get("domain"),
        "summary": {
            "total_evidence": synthesis.get("total_receipts", 0),
            "anomalies": synthesis.get("anomaly_count", 0),
            "flagged_items": synthesis.get("flagged_count", 0),
            "correlations": synthesis.get("correlation_count", 0)
        },
        "evidence_types": synthesis.get("receipt_types", []),
        "findings": [],
        "recommendations": [],
        "context": context or {}
    }

    # Generate findings based on counts
    if synthesis.get("anomaly_count", 0) > 0:
        brief["findings"].append({
            "type": "anomaly_detection",
            "severity": "high" if synthesis["anomaly_count"] > 5 else "medium",
            "description": f"Detected {synthesis['anomaly_count']} anomalies requiring review"
        })

    if synthesis.get("flagged_count", 0) > 0:
        brief["findings"].append({
            "type": "flagged_items",
            "severity": "high",
            "description": f"{synthesis['flagged_count']} items flagged for investigation"
        })

    emit_receipt("brief_generation", {
        "tenant_id": TENANT_ID,
        "brief_id": brief["brief_id"],
        "domain": brief["domain"],
        "finding_count": len(brief["findings"]),
        "evidence_count": brief["summary"]["total_evidence"]
    })

    return brief


def summarize_findings(
    briefs: list[dict]
) -> dict:
    """
    Summarize findings across multiple briefs.

    Args:
        briefs: List of brief documents

    Returns:
        Summary across all briefs
    """
    total_evidence = 0
    total_anomalies = 0
    total_flagged = 0
    all_findings = []
    domains = set()

    for brief in briefs:
        summary = brief.get("summary", {})
        total_evidence += summary.get("total_evidence", 0)
        total_anomalies += summary.get("anomalies", 0)
        total_flagged += summary.get("flagged_items", 0)
        all_findings.extend(brief.get("findings", []))

        if brief.get("domain"):
            domains.add(brief["domain"])

    # Categorize findings by severity
    high_severity = [f for f in all_findings if f.get("severity") == "high"]
    medium_severity = [f for f in all_findings if f.get("severity") == "medium"]

    summary = {
        "briefs_analyzed": len(briefs),
        "domains": list(domains),
        "total_evidence": total_evidence,
        "total_anomalies": total_anomalies,
        "total_flagged": total_flagged,
        "total_findings": len(all_findings),
        "high_severity_findings": len(high_severity),
        "medium_severity_findings": len(medium_severity),
        "summary_ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }

    emit_receipt("findings_summary", {
        "tenant_id": TENANT_ID,
        **summary
    })

    return summary


def generate_domain_brief(
    domain: str,
    receipts: list[dict]
) -> dict:
    """
    Generate brief for specific domain.

    Args:
        domain: Domain name (medicaid, jobsohio, etc.)
        receipts: All receipts

    Returns:
        Domain-specific brief
    """
    # Filter receipts for domain
    domain_receipts = [
        r for r in receipts
        if domain in r.get("receipt_type", "") or
           r.get("domain") == domain
    ]

    synthesis = synthesize_evidence(domain_receipts, domain)

    context = {
        "domain": domain,
        "analysis_focus": f"OhioProof {domain} domain analysis"
    }

    brief = generate_brief(synthesis, context)

    return brief
