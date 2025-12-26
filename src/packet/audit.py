"""
Packet Audit Module

Purpose: Audit decision packets for consistency

Receipt: audit_receipt
Gate: t36h
"""

from typing import Any

from src.core import emit_receipt, TENANT_ID


def audit_packet(packet: dict) -> dict:
    """
    Full audit of decision packet.

    Args:
        packet: Decision packet to audit

    Returns:
        Audit result
    """
    consistency = check_consistency(packet)
    completeness = validate_completeness(packet)

    errors = consistency.get("errors", []) + completeness.get("errors", [])
    warnings = consistency.get("warnings", []) + completeness.get("warnings", [])

    audit = {
        "packet_id": packet.get("packet_id"),
        "passed": len(errors) == 0,
        "consistency_score": consistency.get("score", 0),
        "completeness_score": completeness.get("score", 0),
        "errors": errors,
        "warnings": warnings
    }

    emit_receipt("packet_audit", {
        "tenant_id": TENANT_ID,
        "packet_id": packet.get("packet_id"),
        "passed": audit["passed"],
        "error_count": len(errors),
        "warning_count": len(warnings)
    })

    return audit


def check_consistency(packet: dict) -> dict:
    """
    Check packet internal consistency.

    Args:
        packet: Decision packet

    Returns:
        Consistency check result
    """
    errors = []
    warnings = []
    score = 1.0

    # Check claims match attachments
    claims = packet.get("claims", [])
    attachments = packet.get("attached_receipts", [])

    if len(claims) > len(attachments):
        warnings.append("more_claims_than_attachments")
        score -= 0.1

    if len(claims) == 0 and len(attachments) == 0:
        errors.append("empty_packet")
        score = 0.0

    # Check domain consistency
    domain = packet.get("domain")
    if not domain:
        warnings.append("no_domain_specified")
        score -= 0.1

    # Check required fields
    required = ["packet_id", "created_ts"]
    for field in required:
        if field not in packet:
            errors.append(f"missing_field:{field}")
            score -= 0.2

    return {
        "score": max(score, 0),
        "errors": errors,
        "warnings": warnings
    }


def validate_completeness(packet: dict) -> dict:
    """
    Validate packet completeness.

    Args:
        packet: Decision packet

    Returns:
        Completeness validation result
    """
    errors = []
    warnings = []
    score = 1.0

    # Check for brief
    if not packet.get("brief"):
        warnings.append("no_brief_attached")
        score -= 0.15

    # Check for decision health
    if not packet.get("decision_health"):
        warnings.append("no_decision_health")
        score -= 0.1

    # Check attachments have content
    attachments = packet.get("attached_receipts", [])
    if len(attachments) < 3:
        warnings.append("insufficient_evidence")
        score -= 0.2

    # Check for recommendation
    if not packet.get("recommendation"):
        warnings.append("no_recommendation")
        score -= 0.1

    return {
        "score": max(score, 0),
        "errors": errors,
        "warnings": warnings
    }


def audit_claim(claim: dict) -> dict:
    """
    Audit individual claim.

    Args:
        claim: Claim to audit

    Returns:
        Claim audit result
    """
    issues = []

    if not claim.get("description"):
        issues.append("no_description")

    if not claim.get("amount") and claim.get("type") == "financial":
        issues.append("financial_claim_without_amount")

    if not claim.get("evidence_type"):
        issues.append("no_evidence_type")

    return {
        "valid": len(issues) == 0,
        "issues": issues
    }


def generate_audit_report(
    packets: list[dict]
) -> dict:
    """
    Generate audit report for multiple packets.

    Args:
        packets: List of packets to audit

    Returns:
        Aggregate audit report
    """
    results = []
    passed = 0
    failed = 0

    for packet in packets:
        audit = audit_packet(packet)
        results.append(audit)

        if audit["passed"]:
            passed += 1
        else:
            failed += 1

    report = {
        "total_packets": len(packets),
        "passed": passed,
        "failed": failed,
        "pass_rate": passed / len(packets) if packets else 0,
        "common_errors": [],
        "common_warnings": []
    }

    # Aggregate common issues
    all_errors = []
    all_warnings = []

    for result in results:
        all_errors.extend(result.get("errors", []))
        all_warnings.extend(result.get("warnings", []))

    # Count occurrences
    from collections import Counter
    error_counts = Counter(all_errors)
    warning_counts = Counter(all_warnings)

    report["common_errors"] = error_counts.most_common(5)
    report["common_warnings"] = warning_counts.most_common(5)

    emit_receipt("audit_report", {
        "tenant_id": TENANT_ID,
        "total_packets": len(packets),
        "passed": passed,
        "failed": failed
    })

    return report
