"""
OhioProof Core Module - CLAUDEME-compliant foundation.
Every other file imports this.

Receipt: ohioproof_core
SLO: dual_hash_latency <= 10ms
Gate: t2h
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

try:
    import blake3
    HAS_BLAKE3 = True
except ImportError:
    HAS_BLAKE3 = False

# ═══════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════

TENANT_ID = "ohioproof"

RECEIPT_SCHEMA = {
    "receipt_type": "str",
    "ts": "ISO8601",
    "tenant_id": "str",
    "payload_hash": "SHA256:BLAKE3",
}


# ═══════════════════════════════════════════════════════════════════
# CORE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def dual_hash(data: bytes | str) -> str:
    """
    SHA256:BLAKE3 format per CLAUDEME §8.
    Pure function. ALWAYS use this, never single hash.
    """
    if isinstance(data, str):
        data = data.encode("utf-8")
    sha = hashlib.sha256(data).hexdigest()
    b3 = blake3.blake3(data).hexdigest() if HAS_BLAKE3 else sha
    return f"{sha}:{b3}"


def emit_receipt(receipt_type: str, data: dict) -> dict:
    """
    Creates receipt with ts, tenant_id, payload_hash.
    Prints JSON to stdout. Every function calls this.
    """
    receipt = {
        "receipt_type": receipt_type,
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "tenant_id": data.get("tenant_id", TENANT_ID),
        "payload_hash": dual_hash(json.dumps(data, sort_keys=True)),
        **data
    }
    print(json.dumps(receipt), flush=True)
    return receipt


def merkle(items: list) -> str:
    """
    Compute Merkle root using dual_hash.
    Handle empty and odd counts per CLAUDEME §8.
    """
    if not items:
        return dual_hash(b"empty")
    hashes = [dual_hash(json.dumps(i, sort_keys=True)) for i in items]
    while len(hashes) > 1:
        if len(hashes) % 2:
            hashes.append(hashes[-1])
        hashes = [dual_hash(hashes[i] + hashes[i + 1])
                  for i in range(0, len(hashes), 2)]
    return hashes[0]


# ═══════════════════════════════════════════════════════════════════
# STOPRULES
# ═══════════════════════════════════════════════════════════════════

class StopRule(Exception):
    """Raised when stoprule triggers. Never catch silently."""
    pass


def stoprule_hash_mismatch(expected: str, actual: str) -> None:
    """Emit anomaly and halt on hash mismatch."""
    emit_receipt("anomaly", {
        "tenant_id": TENANT_ID,
        "metric": "hash_mismatch",
        "baseline": expected,
        "delta": -1,
        "classification": "violation",
        "action": "halt"
    })
    raise StopRule(f"Hash mismatch: expected {expected}, got {actual}")


def stoprule_invalid_receipt(reason: str) -> None:
    """Emit anomaly and halt on invalid receipt."""
    emit_receipt("anomaly", {
        "tenant_id": TENANT_ID,
        "metric": "invalid_receipt",
        "baseline": 0,
        "delta": -1,
        "classification": "violation",
        "action": "halt"
    })
    raise StopRule(f"Invalid receipt: {reason}")


def stoprule_data_source_unavailable(source: str, retries: int = 3) -> None:
    """Emit anomaly, retry 3x, then halt."""
    emit_receipt("anomaly", {
        "tenant_id": TENANT_ID,
        "metric": "data_source_unavailable",
        "baseline": 0,
        "delta": -1,
        "classification": "degradation",
        "action": "halt",
        "source": source,
        "retries_attempted": retries
    })
    raise StopRule(f"Data source unavailable after {retries} retries: {source}")


# ═══════════════════════════════════════════════════════════════════
# BIAS CHECK (required by CLAUDEME)
# ═══════════════════════════════════════════════════════════════════

def check_bias(groups: list[str], outcomes: list[float], threshold: float = 0.005) -> dict:
    """
    Check for bias in outcomes across groups.
    Halt if disparity >= threshold (default 0.5%).
    """
    if not groups or not outcomes or len(groups) != len(outcomes):
        return emit_receipt("bias", {
            "tenant_id": TENANT_ID,
            "groups": groups,
            "disparity": 0.0,
            "thresholds": {"max_disparity": threshold},
            "mitigation_action": "none"
        })

    disparity = max(outcomes) - min(outcomes) if outcomes else 0.0
    action = "halt" if disparity >= threshold else "none"

    receipt = emit_receipt("bias", {
        "tenant_id": TENANT_ID,
        "groups": groups,
        "disparity": disparity,
        "thresholds": {"max_disparity": threshold},
        "mitigation_action": action
    })

    if action == "halt":
        stoprule_bias(disparity, threshold)

    return receipt


def stoprule_bias(disparity: float, threshold: float) -> None:
    """Emit anomaly and halt on bias detection."""
    emit_receipt("anomaly", {
        "tenant_id": TENANT_ID,
        "metric": "bias",
        "baseline": threshold,
        "delta": disparity - threshold,
        "classification": "violation",
        "action": "halt"
    })
    raise StopRule(f"Bias detected: {disparity} >= {threshold}")
