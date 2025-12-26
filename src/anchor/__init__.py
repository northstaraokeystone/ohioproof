"""
OhioProof Anchor Modules - Cryptographic integrity and verification.

Purpose:
    - dual_hash: SHA256 + BLAKE3 dual hashing
    - merkle: Merkle tree operations
    - verify: Proof verification

Receipt: anchor_receipt
Gate: t16h
"""

from src.anchor.hash import dual_hash, hash_file, hash_batch
from src.anchor.merkle import (
    compute_merkle_root,
    build_merkle_tree,
    get_merkle_proof,
    verify_merkle_proof
)
from src.anchor.verify import (
    verify_receipt,
    verify_chain,
    verify_integrity
)

__all__ = [
    # hash
    "dual_hash", "hash_file", "hash_batch",
    # merkle
    "compute_merkle_root", "build_merkle_tree",
    "get_merkle_proof", "verify_merkle_proof",
    # verify
    "verify_receipt", "verify_chain", "verify_integrity",
]
