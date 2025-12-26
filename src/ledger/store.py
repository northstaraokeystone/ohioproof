"""
Ledger Store Module

Purpose: Append-only receipt storage

Receipt: ledger_store_receipt
Gate: t24h
"""

import json
import os
import time
from datetime import datetime, timezone
from typing import Any

from src.core import dual_hash, emit_receipt, merkle, TENANT_ID

DEFAULT_LEDGER_PATH = "receipts.jsonl"


class LedgerStore:
    """
    Append-only ledger store for receipts.
    """

    def __init__(self, path: str = DEFAULT_LEDGER_PATH):
        """
        Initialize ledger store.

        Args:
            path: Path to ledger file
        """
        self.path = path
        self._ensure_file()

    def _ensure_file(self) -> None:
        """Create ledger file if it doesn't exist."""
        if not os.path.exists(self.path):
            open(self.path, "a").close()

    def append(self, receipt: dict) -> str:
        """
        Append receipt to ledger.

        Args:
            receipt: Receipt to append

        Returns:
            Hash of appended receipt
        """
        receipt_json = json.dumps(receipt, sort_keys=True)
        receipt_hash = dual_hash(receipt_json)

        with open(self.path, "a") as f:
            f.write(receipt_json + "\n")

        return receipt_hash

    def read_all(self) -> list[dict]:
        """
        Read all receipts from ledger.

        Returns:
            List of receipts
        """
        receipts = []

        if not os.path.exists(self.path):
            return receipts

        with open(self.path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        receipts.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass

        return receipts

    def count(self) -> int:
        """Get receipt count."""
        return len(self.read_all())

    def get_merkle_root(self) -> str:
        """Get Merkle root of all receipts."""
        receipts = self.read_all()
        return merkle(receipts)

    def get_latest(self, n: int = 10) -> list[dict]:
        """Get latest n receipts."""
        receipts = self.read_all()
        return receipts[-n:]


def append_receipt(receipt: dict, path: str = DEFAULT_LEDGER_PATH) -> str:
    """
    Append receipt to ledger file.

    Args:
        receipt: Receipt dict
        path: Ledger file path

    Returns:
        Receipt hash
    """
    store = LedgerStore(path)
    receipt_hash = store.append(receipt)

    emit_receipt("ledger_append", {
        "tenant_id": TENANT_ID,
        "receipt_type": receipt.get("receipt_type"),
        "receipt_hash": receipt_hash,
        "ledger_path": path
    })

    return receipt_hash


def read_receipts(path: str = DEFAULT_LEDGER_PATH) -> list[dict]:
    """
    Read all receipts from ledger.

    Args:
        path: Ledger file path

    Returns:
        List of receipts
    """
    store = LedgerStore(path)
    receipts = store.read_all()

    emit_receipt("ledger_read", {
        "tenant_id": TENANT_ID,
        "ledger_path": path,
        "receipt_count": len(receipts)
    })

    return receipts


def get_ledger_status(path: str = DEFAULT_LEDGER_PATH) -> dict:
    """
    Get ledger status.

    Args:
        path: Ledger file path

    Returns:
        Status dict
    """
    store = LedgerStore(path)
    receipts = store.read_all()

    # Count by type
    by_type = {}
    for r in receipts:
        rt = r.get("receipt_type", "unknown")
        by_type[rt] = by_type.get(rt, 0) + 1

    # File stats
    file_size = os.path.getsize(path) if os.path.exists(path) else 0

    status = {
        "path": path,
        "file_size_bytes": file_size,
        "receipt_count": len(receipts),
        "merkle_root": store.get_merkle_root(),
        "by_type": by_type,
        "latest_ts": receipts[-1].get("ts") if receipts else None
    }

    emit_receipt("ledger_status", {
        "tenant_id": TENANT_ID,
        **status
    })

    return status
