"""
Ledger Query Module

Purpose: Query receipts from ledger

Receipt: ledger_query_receipt
Gate: t24h
"""

from datetime import datetime
from typing import Any

from src.core import emit_receipt, TENANT_ID
from src.ledger.store import LedgerStore, DEFAULT_LEDGER_PATH


def query_by_type(
    receipt_type: str,
    path: str = DEFAULT_LEDGER_PATH
) -> list[dict]:
    """
    Query receipts by type.

    Args:
        receipt_type: Receipt type to filter
        path: Ledger file path

    Returns:
        Matching receipts
    """
    store = LedgerStore(path)
    all_receipts = store.read_all()

    matching = [r for r in all_receipts if r.get("receipt_type") == receipt_type]

    emit_receipt("ledger_query", {
        "tenant_id": TENANT_ID,
        "query_type": "by_type",
        "filter": receipt_type,
        "total_receipts": len(all_receipts),
        "matching_receipts": len(matching)
    })

    return matching


def query_by_date_range(
    start_date: str,
    end_date: str,
    path: str = DEFAULT_LEDGER_PATH
) -> list[dict]:
    """
    Query receipts by date range.

    Args:
        start_date: Start date (ISO8601)
        end_date: End date (ISO8601)
        path: Ledger file path

    Returns:
        Matching receipts
    """
    store = LedgerStore(path)
    all_receipts = store.read_all()

    matching = []
    for r in all_receipts:
        ts = r.get("ts", "")
        if start_date <= ts <= end_date:
            matching.append(r)

    emit_receipt("ledger_query", {
        "tenant_id": TENANT_ID,
        "query_type": "by_date_range",
        "start_date": start_date,
        "end_date": end_date,
        "total_receipts": len(all_receipts),
        "matching_receipts": len(matching)
    })

    return matching


def query_by_tenant(
    tenant_id: str,
    path: str = DEFAULT_LEDGER_PATH
) -> list[dict]:
    """
    Query receipts by tenant ID.

    Args:
        tenant_id: Tenant ID to filter
        path: Ledger file path

    Returns:
        Matching receipts
    """
    store = LedgerStore(path)
    all_receipts = store.read_all()

    matching = [r for r in all_receipts if r.get("tenant_id") == tenant_id]

    emit_receipt("ledger_query", {
        "tenant_id": TENANT_ID,
        "query_type": "by_tenant",
        "filter_tenant": tenant_id,
        "total_receipts": len(all_receipts),
        "matching_receipts": len(matching)
    })

    return matching


def query_by_field(
    field: str,
    value: Any,
    path: str = DEFAULT_LEDGER_PATH
) -> list[dict]:
    """
    Query receipts by arbitrary field value.

    Args:
        field: Field name
        value: Value to match
        path: Ledger file path

    Returns:
        Matching receipts
    """
    store = LedgerStore(path)
    all_receipts = store.read_all()

    matching = [r for r in all_receipts if r.get(field) == value]

    emit_receipt("ledger_query", {
        "tenant_id": TENANT_ID,
        "query_type": "by_field",
        "field": field,
        "total_receipts": len(all_receipts),
        "matching_receipts": len(matching)
    })

    return matching


def query_flagged(path: str = DEFAULT_LEDGER_PATH) -> list[dict]:
    """
    Query receipts that are flagged.

    Args:
        path: Ledger file path

    Returns:
        Flagged receipts
    """
    store = LedgerStore(path)
    all_receipts = store.read_all()

    matching = [r for r in all_receipts if r.get("flagged") is True]

    emit_receipt("ledger_query", {
        "tenant_id": TENANT_ID,
        "query_type": "flagged",
        "total_receipts": len(all_receipts),
        "matching_receipts": len(matching)
    })

    return matching


def query_anomalies(path: str = DEFAULT_LEDGER_PATH) -> list[dict]:
    """
    Query anomaly receipts.

    Args:
        path: Ledger file path

    Returns:
        Anomaly receipts
    """
    return query_by_type("anomaly", path)


def aggregate_by_type(path: str = DEFAULT_LEDGER_PATH) -> dict[str, int]:
    """
    Aggregate receipt counts by type.

    Args:
        path: Ledger file path

    Returns:
        Dict of type -> count
    """
    store = LedgerStore(path)
    all_receipts = store.read_all()

    counts = {}
    for r in all_receipts:
        rt = r.get("receipt_type", "unknown")
        counts[rt] = counts.get(rt, 0) + 1

    emit_receipt("ledger_aggregate", {
        "tenant_id": TENANT_ID,
        "aggregation": "by_type",
        "total_receipts": len(all_receipts),
        "type_count": len(counts)
    })

    return counts
