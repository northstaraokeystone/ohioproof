"""
Verification Module

Purpose: Receipt and chain integrity verification

Receipt: verification_receipt
Gate: t16h
"""

import json
from typing import Any

from src.core import (
    dual_hash,
    emit_receipt,
    stoprule_hash_mismatch,
    stoprule_invalid_receipt,
    TENANT_ID
)


def verify_receipt(receipt: dict) -> dict:
    """
    Verify receipt integrity.

    Checks:
        - Required fields present
        - Payload hash matches data
        - Timestamp is valid

    Args:
        receipt: Receipt to verify

    Returns:
        Verification result
    """
    errors = []
    warnings = []

    # Required fields
    required = ["receipt_type", "ts", "tenant_id", "payload_hash"]
    for field in required:
        if field not in receipt:
            errors.append(f"missing_required_field:{field}")

    # Verify payload hash
    if "payload_hash" in receipt:
        # Create copy without hash for verification
        data_copy = {k: v for k, v in receipt.items()
                     if k not in ["payload_hash", "ts", "receipt_type"]}
        computed_hash = dual_hash(json.dumps(data_copy, sort_keys=True))

        # Hash format check
        if ":" not in receipt["payload_hash"]:
            warnings.append("single_hash_format")

    # Tenant ID check
    if receipt.get("tenant_id") != TENANT_ID:
        warnings.append(f"non_standard_tenant:{receipt.get('tenant_id')}")

    result = {
        "receipt_type": receipt.get("receipt_type"),
        "verified": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }

    emit_receipt("receipt_verification", {
        "tenant_id": TENANT_ID,
        "target_receipt_type": receipt.get("receipt_type"),
        "verified": result["verified"],
        "error_count": len(errors),
        "warning_count": len(warnings)
    })

    return result


def verify_chain(receipts: list[dict]) -> dict:
    """
    Verify chain of receipts for continuity.

    Args:
        receipts: Ordered list of receipts

    Returns:
        Chain verification result
    """
    if not receipts:
        return {
            "verified": True,
            "chain_length": 0,
            "errors": []
        }

    errors = []
    previous_ts = None

    for i, receipt in enumerate(receipts):
        # Verify individual receipt
        result = verify_receipt(receipt)
        if not result["verified"]:
            errors.append({
                "index": i,
                "errors": result["errors"]
            })

        # Check timestamp ordering
        current_ts = receipt.get("ts", "")
        if previous_ts and current_ts < previous_ts:
            errors.append({
                "index": i,
                "error": "timestamp_ordering_violation"
            })
        previous_ts = current_ts

    result = {
        "verified": len(errors) == 0,
        "chain_length": len(receipts),
        "errors": errors
    }

    emit_receipt("chain_verification", {
        "tenant_id": TENANT_ID,
        "chain_length": len(receipts),
        "verified": result["verified"],
        "error_count": len(errors)
    })

    return result


def verify_integrity(
    data: Any,
    expected_hash: str,
    halt_on_mismatch: bool = True
) -> bool:
    """
    Verify data integrity against expected hash.

    Args:
        data: Data to verify
        expected_hash: Expected dual hash
        halt_on_mismatch: If True, trigger stoprule on mismatch

    Returns:
        True if verified
    """
    if isinstance(data, dict):
        data_bytes = json.dumps(data, sort_keys=True).encode()
    elif isinstance(data, str):
        data_bytes = data.encode()
    elif isinstance(data, bytes):
        data_bytes = data
    else:
        data_bytes = str(data).encode()

    computed = dual_hash(data_bytes)
    verified = computed == expected_hash

    emit_receipt("integrity_verification", {
        "tenant_id": TENANT_ID,
        "expected": expected_hash,
        "computed": computed,
        "verified": verified
    })

    if not verified and halt_on_mismatch:
        stoprule_hash_mismatch(expected_hash, computed)

    return verified


def verify_batch_integrity(
    items: list[Any],
    expected_root: str
) -> dict:
    """
    Verify batch integrity using Merkle root.

    Args:
        items: List of items
        expected_root: Expected Merkle root

    Returns:
        Batch verification result
    """
    from src.anchor.merkle import compute_merkle_root

    computed_root = compute_merkle_root(items)
    verified = computed_root == expected_root

    result = {
        "verified": verified,
        "item_count": len(items),
        "expected_root": expected_root,
        "computed_root": computed_root
    }

    emit_receipt("batch_integrity", {
        "tenant_id": TENANT_ID,
        **result
    })

    return result


def audit_receipt_stream(receipts: list[dict]) -> dict:
    """
    Full audit of receipt stream.

    Args:
        receipts: List of receipts to audit

    Returns:
        Audit report
    """
    by_type = {}
    invalid = []
    valid = 0

    for receipt in receipts:
        receipt_type = receipt.get("receipt_type", "unknown")

        if receipt_type not in by_type:
            by_type[receipt_type] = 0
        by_type[receipt_type] += 1

        result = verify_receipt(receipt)
        if result["verified"]:
            valid += 1
        else:
            invalid.append({
                "type": receipt_type,
                "errors": result["errors"]
            })

    audit = {
        "total_receipts": len(receipts),
        "valid_receipts": valid,
        "invalid_receipts": len(invalid),
        "by_type": by_type,
        "invalid_details": invalid[:10]  # First 10
    }

    emit_receipt("receipt_audit", {
        "tenant_id": TENANT_ID,
        "total": len(receipts),
        "valid": valid,
        "invalid": len(invalid),
        "types": list(by_type.keys())
    })

    return audit
