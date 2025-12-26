"""
OhioProof Packet Modules - Decision packet assembly.

Purpose:
    - attach: Claim-to-receipt mapping
    - audit: Consistency audit
    - build: Decision packet assembly

Receipt: packet_receipt
Gate: t36h
"""

from src.packet.attach import (
    attach_receipt,
    map_claims_to_receipts,
    verify_attachments
)
from src.packet.audit import (
    audit_packet,
    check_consistency,
    validate_completeness
)
from src.packet.build import (
    build_packet,
    build_referral_packet,
    build_investigation_packet
)

__all__ = [
    # attach
    "attach_receipt", "map_claims_to_receipts", "verify_attachments",
    # audit
    "audit_packet", "check_consistency", "validate_completeness",
    # build
    "build_packet", "build_referral_packet", "build_investigation_packet",
]
