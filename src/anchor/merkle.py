"""
Merkle Tree Module

Purpose: Merkle tree operations for receipt anchoring

Receipt: merkle_receipt
Gate: t16h
"""

import json
from typing import Any

from src.core import dual_hash, emit_receipt, TENANT_ID


def compute_merkle_root(items: list[Any]) -> str:
    """
    Compute Merkle root using dual_hash.
    Handle empty and odd counts per CLAUDEME §8.

    Args:
        items: List of items to include in tree

    Returns:
        Merkle root hash
    """
    if not items:
        return dual_hash(b"empty")

    hashes = [dual_hash(json.dumps(i, sort_keys=True)) for i in items]

    while len(hashes) > 1:
        if len(hashes) % 2:
            hashes.append(hashes[-1])
        hashes = [dual_hash(hashes[i] + hashes[i + 1])
                  for i in range(0, len(hashes), 2)]

    root = hashes[0]

    emit_receipt("merkle_root", {
        "tenant_id": TENANT_ID,
        "item_count": len(items),
        "root": root
    })

    return root


def build_merkle_tree(items: list[Any]) -> dict:
    """
    Build complete Merkle tree with all levels.

    Args:
        items: List of items

    Returns:
        Tree structure with all levels
    """
    if not items:
        return {
            "root": dual_hash(b"empty"),
            "levels": [],
            "leaves": 0
        }

    # Level 0: leaf hashes
    hashes = [dual_hash(json.dumps(i, sort_keys=True)) for i in items]
    levels = [hashes.copy()]

    # Build up the tree
    while len(hashes) > 1:
        if len(hashes) % 2:
            hashes.append(hashes[-1])

        next_level = []
        for i in range(0, len(hashes), 2):
            combined = dual_hash(hashes[i] + hashes[i + 1])
            next_level.append(combined)

        hashes = next_level
        levels.append(hashes.copy())

    tree = {
        "root": hashes[0],
        "levels": levels,
        "leaves": len(items)
    }

    emit_receipt("merkle_tree_build", {
        "tenant_id": TENANT_ID,
        "leaves": len(items),
        "levels": len(levels),
        "root": tree["root"]
    })

    return tree


def get_merkle_proof(tree: dict, index: int) -> list[dict]:
    """
    Get Merkle proof for item at index.

    Args:
        tree: Merkle tree from build_merkle_tree
        index: Index of item to prove

    Returns:
        List of proof elements
    """
    levels = tree.get("levels", [])
    if not levels or index < 0 or index >= tree.get("leaves", 0):
        return []

    proof = []
    current_index = index

    for level in levels[:-1]:  # Exclude root level
        # Adjust for padding
        if current_index % 2 == 0:
            # We're on the left, need right sibling
            sibling_index = current_index + 1
            position = "right"
        else:
            # We're on the right, need left sibling
            sibling_index = current_index - 1
            position = "left"

        if sibling_index < len(level):
            proof.append({
                "hash": level[sibling_index],
                "position": position
            })

        current_index //= 2

    emit_receipt("merkle_proof", {
        "tenant_id": TENANT_ID,
        "index": index,
        "proof_length": len(proof),
        "root": tree.get("root")
    })

    return proof


def verify_merkle_proof(
    item: Any,
    proof: list[dict],
    expected_root: str
) -> bool:
    """
    Verify Merkle proof for an item.

    Args:
        item: Item to verify
        proof: Proof from get_merkle_proof
        expected_root: Expected Merkle root

    Returns:
        True if proof is valid
    """
    current_hash = dual_hash(json.dumps(item, sort_keys=True))

    for element in proof:
        sibling_hash = element["hash"]
        position = element["position"]

        if position == "left":
            combined = sibling_hash + current_hash
        else:
            combined = current_hash + sibling_hash

        current_hash = dual_hash(combined)

    verified = current_hash == expected_root

    emit_receipt("merkle_proof_verification", {
        "tenant_id": TENANT_ID,
        "computed_root": current_hash,
        "expected_root": expected_root,
        "verified": verified
    })

    return verified


def anchor_receipts(receipts: list[dict]) -> dict:
    """
    Anchor batch of receipts with Merkle root.

    Args:
        receipts: List of receipt dicts

    Returns:
        Anchor receipt
    """
    root = compute_merkle_root(receipts)

    anchor = emit_receipt("anchor", {
        "tenant_id": TENANT_ID,
        "merkle_root": root,
        "hash_algos": ["SHA256", "BLAKE3"],
        "batch_size": len(receipts)
    })

    return anchor
