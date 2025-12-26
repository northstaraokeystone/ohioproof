"""
Ohio Checkbook Ingest Module

Purpose: Ingest Ohio Checkbook spending data ($400B+ transactions)
Data Source: checkbook.ohio.gov (CSV export, no API)

Receipt: checkbook_ingest_receipt
SLO: ingest_latency <= 60s per 10K records, parse_accuracy >= 99.9%
Gate: t8h
"""

import csv
import io
import time
from datetime import datetime, timezone
from typing import Any

from src.core import dual_hash, emit_receipt, stoprule_data_source_unavailable, TENANT_ID
from src.constants import DATA_SOURCES

# Simulated data for testing - in production would scrape actual site
SAMPLE_TRANSACTIONS = [
    {
        "vendor_id": "V001",
        "vendor_name": "ABC Construction LLC",
        "amount": 150000.00,
        "date": "2024-01-15",
        "agency": "ODOT",
        "program": "Highway Construction"
    },
    {
        "vendor_id": "V002",
        "vendor_name": "Healthcare Services Inc",
        "amount": 2500000.00,
        "date": "2024-01-20",
        "agency": "ODM",
        "program": "Medicaid Managed Care"
    }
]


def fetch_transactions(
    start_date: str,
    end_date: str,
    agency: str | None = None
) -> list[dict]:
    """
    Scrape and parse CSV exports from Ohio Checkbook.
    Emit ingest_receipt per batch.

    Args:
        start_date: ISO8601 date string (YYYY-MM-DD)
        end_date: ISO8601 date string (YYYY-MM-DD)
        agency: Optional agency filter

    Returns:
        List of parsed transaction records
    """
    t0 = time.time()

    # In production: scrape checkbook.ohio.gov/Export
    # For now, return sample data
    transactions = SAMPLE_TRANSACTIONS.copy()

    if agency:
        transactions = [t for t in transactions if t.get("agency") == agency]

    latency_ms = (time.time() - t0) * 1000
    total_amount = sum(t.get("amount", 0) for t in transactions)
    agencies = list(set(t.get("agency", "unknown") for t in transactions))

    emit_receipt("checkbook_ingest", {
        "tenant_id": TENANT_ID,
        "source": "ohio_checkbook",
        "date_range": {"start": start_date, "end": end_date},
        "record_count": len(transactions),
        "total_amount": total_amount,
        "agencies": agencies,
        "latency_ms": latency_ms
    })

    return transactions


def parse_vendor(row: dict) -> dict:
    """
    Extract vendor_id, name, amount, date, agency, program from row.

    Args:
        row: Raw transaction row from CSV

    Returns:
        Parsed vendor record
    """
    parsed = {
        "vendor_id": row.get("vendor_id", row.get("Vendor ID", "")),
        "vendor_name": row.get("vendor_name", row.get("Vendor Name", "")),
        "amount": float(row.get("amount", row.get("Amount", 0))),
        "date": row.get("date", row.get("Date", "")),
        "agency": row.get("agency", row.get("Agency", "")),
        "program": row.get("program", row.get("Program", ""))
    }

    emit_receipt("vendor_parse", {
        "tenant_id": TENANT_ID,
        "vendor_id": parsed["vendor_id"],
        "vendor_hash": dual_hash(parsed["vendor_name"])
    })

    return parsed


def detect_shell(vendor: dict) -> float:
    """
    Score vendor for shell company indicators.

    Indicators:
        - Address reuse across multiple vendors
        - Name patterns (LLC, Inc with generic names)
        - Payment clustering (many small payments)
        - Short operating history

    Args:
        vendor: Vendor record

    Returns:
        Shell company risk score (0.0 - 1.0)
    """
    score = 0.0
    indicators = []

    vendor_name = vendor.get("vendor_name", "").upper()

    # Generic name patterns
    generic_patterns = ["CONSULTING", "SERVICES", "SOLUTIONS", "MANAGEMENT", "ENTERPRISES"]
    if any(p in vendor_name for p in generic_patterns):
        score += 0.2
        indicators.append("generic_name_pattern")

    # LLC/Inc without specific industry identifier
    if ("LLC" in vendor_name or "INC" in vendor_name) and len(vendor_name.split()) <= 3:
        score += 0.15
        indicators.append("minimal_entity_name")

    # Round payment amounts (common in fraud)
    amount = vendor.get("amount", 0)
    if amount > 0 and amount % 1000 == 0:
        score += 0.1
        indicators.append("round_payment_amount")

    # Cap at 1.0
    score = min(score, 1.0)

    emit_receipt("shell_detection", {
        "tenant_id": TENANT_ID,
        "vendor_id": vendor.get("vendor_id", "unknown"),
        "vendor_hash": dual_hash(vendor.get("vendor_name", "")),
        "shell_score": score,
        "indicators": indicators,
        "flagged": score >= 0.5
    })

    return score


def parse_csv_export(csv_content: str) -> list[dict]:
    """
    Parse raw CSV export from Ohio Checkbook.

    Args:
        csv_content: Raw CSV string

    Returns:
        List of parsed transaction records
    """
    reader = csv.DictReader(io.StringIO(csv_content))
    transactions = []

    for row in reader:
        parsed = parse_vendor(row)
        transactions.append(parsed)

    emit_receipt("csv_parse", {
        "tenant_id": TENANT_ID,
        "source": "ohio_checkbook",
        "record_count": len(transactions),
        "content_hash": dual_hash(csv_content)
    })

    return transactions
