"""
Receipt Attachment Module

Purpose: Claim-to-receipt mapping for decision packets

Receipt: attachment_receipt
Gate: t36h
"""

from typing import Any

from src.core import dual_hash, emit_receipt, TENANT_ID


def attach_receipt(
    claim: dict,
    receipt: dict
) -> dict:
    """
    Attach receipt to claim.

    Args:
        claim: Claim dict
        receipt: Supporting receipt

    Returns:
        Attachment record
    """
    claim_hash = dual_hash(str(claim))
    receipt_hash = receipt.get("payload_hash", dual_hash(str(receipt)))

    attachment = {
        "claim_hash": claim_hash,
        "receipt_hash": receipt_hash,
        "receipt_type": receipt.get("receipt_type"),
        "attached": True
    }

    emit_receipt("attachment", {
        "tenant_id": TENANT_ID,
        **attachment
    })

    return attachment


def map_claims_to_receipts(
    claims: list[dict],
    receipts: list[dict],
    match_field: str = "domain"
) -> dict:
    """
    Map claims to supporting receipts.

    Args:
        claims: List of claims
        receipts: List of available receipts
        match_field: Field to match on

    Returns:
        Mapping result
    """
    mappings = []
    unmatched_claims = []

    for claim in claims:
        claim_value = claim.get(match_field)
        matching_receipts = []

        for receipt in receipts:
            receipt_value = receipt.get(match_field)
            receipt_type = receipt.get("receipt_type", "")

            if claim_value and (claim_value == receipt_value or
                                claim_value in receipt_type):
                matching_receipts.append(receipt)

        if matching_receipts:
            mappings.append({
                "claim_hash": dual_hash(str(claim)),
                "claim_value": claim_value,
                "receipt_count": len(matching_receipts),
                "receipt_hashes": [r.get("payload_hash") for r in matching_receipts[:5]]
            })
        else:
            unmatched_claims.append(claim)

    result = {
        "total_claims": len(claims),
        "matched_claims": len(mappings),
        "unmatched_claims": len(unmatched_claims),
        "mappings": mappings
    }

    emit_receipt("claim_mapping", {
        "tenant_id": TENANT_ID,
        "total_claims": len(claims),
        "matched": len(mappings),
        "unmatched": len(unmatched_claims)
    })

    return result


def verify_attachments(
    packet: dict
) -> dict:
    """
    Verify all attachments in packet.

    Args:
        packet: Decision packet

    Returns:
        Verification result
    """
    attached_receipts = packet.get("attached_receipts", [])
    claims = packet.get("claims", [])

    verified = 0
    invalid = []

    for receipt_hash in attached_receipts:
        # In production, would verify receipt exists in ledger
        if receipt_hash and ":" in receipt_hash:  # Valid dual hash format
            verified += 1
        else:
            invalid.append(receipt_hash)

    result = {
        "total_attachments": len(attached_receipts),
        "verified": verified,
        "invalid": len(invalid),
        "invalid_hashes": invalid[:5],
        "all_verified": len(invalid) == 0
    }

    emit_receipt("attachment_verification", {
        "tenant_id": TENANT_ID,
        **result
    })

    return result


def detach_receipt(
    packet: dict,
    receipt_hash: str
) -> dict:
    """
    Detach receipt from packet.

    Args:
        packet: Decision packet
        receipt_hash: Hash of receipt to detach

    Returns:
        Updated packet
    """
    attached = packet.get("attached_receipts", [])

    if receipt_hash in attached:
        attached.remove(receipt_hash)
        packet["attached_receipts"] = attached

        emit_receipt("detachment", {
            "tenant_id": TENANT_ID,
            "packet_id": packet.get("packet_id"),
            "detached_hash": receipt_hash
        })

    return packet
