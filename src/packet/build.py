"""
Packet Build Module

Purpose: Assemble decision packets

Receipt: packet_receipt
Gate: t36h
"""

from datetime import datetime, timezone
from typing import Any

from src.core import dual_hash, emit_receipt, TENANT_ID


def build_packet(
    domain: str,
    claims: list[dict],
    receipts: list[dict],
    brief: dict | None = None,
    health: dict | None = None
) -> dict:
    """
    Build decision packet.

    Args:
        domain: Domain (medicaid, jobsohio, etc.)
        claims: List of claims
        receipts: Supporting receipts
        brief: Optional brief document
        health: Optional decision health

    Returns:
        Complete decision packet
    """
    packet_id = dual_hash(f"{domain}:{len(claims)}:{datetime.now(timezone.utc).isoformat()}")

    packet = {
        "packet_id": packet_id,
        "domain": domain,
        "created_ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "claims": claims,
        "attached_receipts": [r.get("payload_hash") for r in receipts],
        "brief": brief,
        "decision_health": health,
        "status": "draft",
        "recommendation": None
    }

    # Generate recommendation based on evidence
    if health and health.get("overall", 0) >= 0.8:
        packet["recommendation"] = "proceed_with_action"
    elif health and health.get("overall", 0) >= 0.5:
        packet["recommendation"] = "gather_more_evidence"
    else:
        packet["recommendation"] = "insufficient_evidence"

    emit_receipt("packet_build", {
        "tenant_id": TENANT_ID,
        "packet_id": packet_id,
        "domain": domain,
        "claim_count": len(claims),
        "receipt_count": len(receipts),
        "recommendation": packet["recommendation"]
    })

    return packet


def build_referral_packet(
    domain: str,
    agency: str,
    claims: list[dict],
    receipts: list[dict],
    amount_at_risk: float
) -> dict:
    """
    Build referral packet for agency (OIG, AG, etc.).

    Args:
        domain: Domain
        agency: Target agency (OIG, AG, etc.)
        claims: Claims for referral
        receipts: Supporting receipts
        amount_at_risk: Estimated amount at risk

    Returns:
        Referral packet
    """
    packet = build_packet(domain, claims, receipts)

    packet["packet_type"] = "referral"
    packet["target_agency"] = agency
    packet["amount_at_risk"] = amount_at_risk
    packet["referral_status"] = "pending"
    packet["priority"] = "high" if amount_at_risk > 1000000 else "medium"

    emit_receipt("referral", {
        "tenant_id": TENANT_ID,
        "packet_id": packet["packet_id"],
        "agency": agency,
        "domain": domain,
        "amount_at_risk": amount_at_risk,
        "priority": packet["priority"]
    })

    return packet


def build_investigation_packet(
    domain: str,
    subject: str,
    allegations: list[dict],
    evidence: list[dict],
    timeline: list[dict] | None = None
) -> dict:
    """
    Build investigation packet.

    Args:
        domain: Domain
        subject: Investigation subject (entity/individual)
        allegations: List of allegations
        evidence: Supporting evidence
        timeline: Optional timeline of events

    Returns:
        Investigation packet
    """
    claims = [{"type": "allegation", **a} for a in allegations]

    packet = build_packet(domain, claims, evidence)

    packet["packet_type"] = "investigation"
    packet["subject"] = subject
    packet["subject_hash"] = dual_hash(subject)
    packet["allegations"] = allegations
    packet["timeline"] = timeline or []
    packet["investigation_status"] = "open"

    # Calculate severity
    total_amount = sum(a.get("amount", 0) for a in allegations)
    if total_amount > 10000000:
        packet["severity"] = "critical"
    elif total_amount > 1000000:
        packet["severity"] = "high"
    else:
        packet["severity"] = "medium"

    emit_receipt("investigation_packet", {
        "tenant_id": TENANT_ID,
        "packet_id": packet["packet_id"],
        "domain": domain,
        "subject_hash": packet["subject_hash"],
        "allegation_count": len(allegations),
        "severity": packet["severity"]
    })

    return packet


def finalize_packet(packet: dict) -> dict:
    """
    Finalize packet for submission.

    Args:
        packet: Draft packet

    Returns:
        Finalized packet
    """
    packet["status"] = "finalized"
    packet["finalized_ts"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    packet["final_hash"] = dual_hash(str(packet))

    emit_receipt("packet_finalized", {
        "tenant_id": TENANT_ID,
        "packet_id": packet["packet_id"],
        "final_hash": packet["final_hash"]
    })

    return packet


def update_packet_status(
    packet: dict,
    new_status: str,
    notes: str | None = None
) -> dict:
    """
    Update packet status.

    Args:
        packet: Packet to update
        new_status: New status
        notes: Optional notes

    Returns:
        Updated packet
    """
    old_status = packet.get("status")
    packet["status"] = new_status
    packet["status_updated_ts"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    if notes:
        if "status_history" not in packet:
            packet["status_history"] = []
        packet["status_history"].append({
            "from": old_status,
            "to": new_status,
            "ts": packet["status_updated_ts"],
            "notes": notes
        })

    emit_receipt("packet_status_update", {
        "tenant_id": TENANT_ID,
        "packet_id": packet["packet_id"],
        "old_status": old_status,
        "new_status": new_status
    })

    return packet
