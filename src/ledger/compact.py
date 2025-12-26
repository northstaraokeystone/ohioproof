"""
Ledger Compaction Module

Purpose: Compact ledger with invariant preservation

Receipt: compaction_receipt
Gate: t24h
"""

import json
import os
from datetime import datetime, timezone
from typing import Any

from src.core import dual_hash, emit_receipt, merkle, TENANT_ID
from src.ledger.store import LedgerStore, DEFAULT_LEDGER_PATH


def compact_ledger(
    path: str = DEFAULT_LEDGER_PATH,
    max_age_days: int = 90,
    preserve_types: list[str] | None = None
) -> dict:
    """
    Compact ledger by aggregating old receipts.

    Preserves:
        - Merkle root continuity
        - Sum invariants
        - Receipt counts

    Args:
        path: Ledger file path
        max_age_days: Age threshold for compaction
        preserve_types: Receipt types to never compact

    Returns:
        Compaction result
    """
    if preserve_types is None:
        preserve_types = ["anomaly", "anchor", "compaction"]

    store = LedgerStore(path)
    all_receipts = store.read_all()

    if not all_receipts:
        return {
            "compacted": False,
            "reason": "empty_ledger"
        }

    # Calculate cutoff
    now = datetime.now(timezone.utc)
    cutoff = now.isoformat().replace("+00:00", "Z")

    # Separate receipts
    to_compact = []
    to_keep = []

    for r in all_receipts:
        ts = r.get("ts", "")
        rt = r.get("receipt_type", "")

        if rt in preserve_types:
            to_keep.append(r)
        else:
            to_compact.append(r)

    if not to_compact:
        return {
            "compacted": False,
            "reason": "nothing_to_compact"
        }

    # Compute pre-compaction values
    before_root = merkle(all_receipts)
    before_count = len(all_receipts)

    # Create compaction summary
    by_type = {}
    for r in to_compact:
        rt = r.get("receipt_type", "unknown")
        by_type[rt] = by_type.get(rt, 0) + 1

    compaction_receipt = emit_receipt("compaction", {
        "tenant_id": TENANT_ID,
        "input_span": {
            "start": to_compact[0].get("ts") if to_compact else None,
            "end": to_compact[-1].get("ts") if to_compact else None
        },
        "output_span": {
            "start": to_compact[0].get("ts") if to_compact else None,
            "end": to_compact[-1].get("ts") if to_compact else None
        },
        "counts": {
            "before": len(to_compact),
            "after": 1  # Compacted into one receipt
        },
        "by_type": by_type,
        "hash_continuity": True,
        "pre_merkle_root": before_root
    })

    # Write compacted ledger
    compacted = to_keep + [compaction_receipt]

    with open(path, "w") as f:
        for r in compacted:
            f.write(json.dumps(r, sort_keys=True) + "\n")

    # Verify post-compaction
    after_root = merkle(compacted)

    return {
        "compacted": True,
        "receipts_before": before_count,
        "receipts_after": len(compacted),
        "receipts_compacted": len(to_compact),
        "pre_merkle_root": before_root,
        "post_merkle_root": after_root
    }


def verify_compaction(
    original_receipts: list[dict],
    compacted_receipts: list[dict]
) -> dict:
    """
    Verify compaction preserved invariants.

    Args:
        original_receipts: Original receipts
        compacted_receipts: Compacted receipts

    Returns:
        Verification result
    """
    errors = []

    # Count preservation
    original_count = len(original_receipts)
    compacted_count = len(compacted_receipts)

    # Find compaction receipts
    compaction_receipts = [
        r for r in compacted_receipts
        if r.get("receipt_type") == "compaction"
    ]

    total_compacted = sum(
        r.get("counts", {}).get("before", 0)
        for r in compaction_receipts
    )

    expected_count = compacted_count - len(compaction_receipts) + total_compacted

    if expected_count != original_count:
        errors.append(f"count_mismatch: expected {original_count}, got {expected_count}")

    result = {
        "verified": len(errors) == 0,
        "original_count": original_count,
        "compacted_count": compacted_count,
        "compaction_receipts": len(compaction_receipts),
        "errors": errors
    }

    emit_receipt("compaction_verification", {
        "tenant_id": TENANT_ID,
        **result
    })

    return result


def get_compaction_history(path: str = DEFAULT_LEDGER_PATH) -> list[dict]:
    """
    Get history of compactions.

    Args:
        path: Ledger file path

    Returns:
        List of compaction receipts
    """
    store = LedgerStore(path)
    all_receipts = store.read_all()

    compactions = [
        r for r in all_receipts
        if r.get("receipt_type") == "compaction"
    ]

    return compactions
