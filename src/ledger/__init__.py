"""
OhioProof Ledger Modules - Append-only receipt storage.

Purpose:
    - store: LedgerStore (append-only)
    - query: Receipt queries
    - compact: Compaction with invariants

Receipt: ledger_receipt
Gate: t24h
"""

from src.ledger.store import LedgerStore, append_receipt, read_receipts
from src.ledger.query import query_by_type, query_by_date_range, query_by_tenant
from src.ledger.compact import compact_ledger, verify_compaction

__all__ = [
    # store
    "LedgerStore", "append_receipt", "read_receipts",
    # query
    "query_by_type", "query_by_date_range", "query_by_tenant",
    # compact
    "compact_ledger", "verify_compaction",
]
