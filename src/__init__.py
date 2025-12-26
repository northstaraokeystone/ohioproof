"""
OhioProof v1 - Receipts-Native Government Accountability System

Target: $8.3B+ verified Ohio fraud across 6 domains
Physics: Fraudulent = high entropy, Legitimate = low entropy
"""

from src.core import (
    dual_hash,
    emit_receipt,
    merkle,
    StopRule,
    TENANT_ID,
)

__version__ = "1.0.0"
__all__ = ["dual_hash", "emit_receipt", "merkle", "StopRule", "TENANT_ID"]
