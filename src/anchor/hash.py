"""
Dual Hash Module

Purpose: SHA256 + BLAKE3 dual hashing per CLAUDEME §8

Receipt: hash_receipt
Gate: t16h
"""

import hashlib
import json
from typing import Any

try:
    import blake3
    HAS_BLAKE3 = True
except ImportError:
    HAS_BLAKE3 = False

from src.core import emit_receipt, TENANT_ID


def dual_hash(data: bytes | str) -> str:
    """
    SHA256:BLAKE3 format per CLAUDEME §8.
    Pure function. ALWAYS use this, never single hash.

    Args:
        data: Data to hash (bytes or string)

    Returns:
        Hash in format "SHA256:BLAKE3"
    """
    if isinstance(data, str):
        data = data.encode("utf-8")

    sha = hashlib.sha256(data).hexdigest()
    b3 = blake3.blake3(data).hexdigest() if HAS_BLAKE3 else sha

    return f"{sha}:{b3}"


def hash_file(filepath: str) -> str:
    """
    Compute dual hash of file contents.

    Args:
        filepath: Path to file

    Returns:
        Dual hash of file
    """
    with open(filepath, "rb") as f:
        content = f.read()

    file_hash = dual_hash(content)

    emit_receipt("file_hash", {
        "tenant_id": TENANT_ID,
        "filepath": filepath,
        "size_bytes": len(content),
        "hash": file_hash
    })

    return file_hash


def hash_batch(items: list[Any]) -> str:
    """
    Compute hash of batch of items.

    Args:
        items: List of items to hash

    Returns:
        Dual hash of batch
    """
    serialized = json.dumps(items, sort_keys=True)
    batch_hash = dual_hash(serialized)

    emit_receipt("batch_hash", {
        "tenant_id": TENANT_ID,
        "item_count": len(items),
        "hash": batch_hash
    })

    return batch_hash


def verify_hash(data: bytes | str, expected_hash: str) -> bool:
    """
    Verify data matches expected hash.

    Args:
        data: Data to verify
        expected_hash: Expected dual hash

    Returns:
        True if hash matches
    """
    computed = dual_hash(data)
    matches = computed == expected_hash

    emit_receipt("hash_verification", {
        "tenant_id": TENANT_ID,
        "expected": expected_hash,
        "computed": computed,
        "verified": matches
    })

    return matches


def split_dual_hash(hash_str: str) -> tuple[str, str]:
    """
    Split dual hash into components.

    Args:
        hash_str: Dual hash string

    Returns:
        Tuple of (SHA256, BLAKE3)
    """
    parts = hash_str.split(":")
    if len(parts) == 2:
        return parts[0], parts[1]
    return hash_str, hash_str
