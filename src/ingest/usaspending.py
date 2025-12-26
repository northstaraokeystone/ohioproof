"""
USASpending Ingest Module

Purpose: Ingest federal awards/contracts/grants to Ohio via USASpending API
Data Source: api.usaspending.gov (REST API, public)

Receipt: usaspending_ingest_receipt
SLO: ingest_latency <= 60s per 10K records
Gate: t8h
"""

import time
from typing import Any

from src.core import dual_hash, emit_receipt, stoprule_data_source_unavailable, TENANT_ID
from src.constants import DATA_SOURCES

# API endpoint
API_BASE = "https://api.usaspending.gov/api/v2"


def fetch_awards(state: str = "OH", fiscal_year: int = 2024) -> list[dict]:
    """
    Query USASpending API for Ohio awards.
    Emit ingest_receipt.

    Args:
        state: State code (default: OH)
        fiscal_year: Fiscal year to query

    Returns:
        List of award records
    """
    t0 = time.time()

    # In production: call API
    # POST /api/v2/search/spending_by_award/
    # with filters for state and fiscal_year

    # Sample data for testing
    awards = [
        {
            "award_id": "CONT_AWD_001",
            "recipient_name": "Ohio Defense Contractor LLC",
            "total_obligation": 5000000.00,
            "awarding_agency": "Department of Defense",
            "award_type": "contract",
            "fiscal_year": fiscal_year,
            "recipient_state": state
        },
        {
            "award_id": "GRANT_AWD_002",
            "recipient_name": "Ohio State University",
            "total_obligation": 12000000.00,
            "awarding_agency": "Department of Health and Human Services",
            "award_type": "grant",
            "fiscal_year": fiscal_year,
            "recipient_state": state
        }
    ]

    latency_ms = (time.time() - t0) * 1000

    emit_receipt("usaspending_ingest", {
        "tenant_id": TENANT_ID,
        "source": "usaspending",
        "state": state,
        "fiscal_year": fiscal_year,
        "record_count": len(awards),
        "total_obligation": sum(a.get("total_obligation", 0) for a in awards),
        "latency_ms": latency_ms
    })

    return awards


def fetch_contracts(state: str = "OH", agency: str | None = None) -> list[dict]:
    """
    Query contracts by agency.

    Args:
        state: State code
        agency: Optional agency filter

    Returns:
        List of contract records
    """
    t0 = time.time()

    # In production: call API with agency filter
    contracts = [
        {
            "contract_id": "CONT_001",
            "vendor_name": "Ohio Tech Solutions",
            "amount": 750000.00,
            "agency": agency or "General Services Administration",
            "state": state
        }
    ]

    latency_ms = (time.time() - t0) * 1000

    emit_receipt("usaspending_contracts", {
        "tenant_id": TENANT_ID,
        "source": "usaspending",
        "state": state,
        "agency": agency,
        "record_count": len(contracts),
        "latency_ms": latency_ms
    })

    return contracts


def cross_reference(vendor_name: str) -> dict:
    """
    Match federal vendor to Ohio Checkbook vendor.

    Args:
        vendor_name: Vendor name to search

    Returns:
        Cross-reference result with match confidence
    """
    # In production: fuzzy match against Ohio Checkbook vendors
    # Using name normalization and Levenshtein distance

    vendor_hash = dual_hash(vendor_name)

    # Simulated cross-reference
    result = {
        "vendor_name": vendor_name,
        "vendor_hash": vendor_hash,
        "ohio_checkbook_match": None,
        "match_confidence": 0.0,
        "federal_awards": [],
        "state_payments": []
    }

    emit_receipt("usaspending_crossref", {
        "tenant_id": TENANT_ID,
        "vendor_hash": vendor_hash,
        "match_found": result["ohio_checkbook_match"] is not None,
        "match_confidence": result["match_confidence"]
    })

    return result


def fetch_recipient_profile(duns: str) -> dict:
    """
    Fetch detailed recipient profile by DUNS/UEI.

    Args:
        duns: DUNS or UEI number

    Returns:
        Recipient profile
    """
    # In production: GET /api/v2/recipient/duns/{duns}/
    profile = {
        "duns": duns,
        "name": "Unknown Recipient",
        "address": {},
        "total_awards": 0,
        "total_amount": 0.0
    }

    emit_receipt("usaspending_profile", {
        "tenant_id": TENANT_ID,
        "duns": duns,
        "profile_found": profile.get("name") != "Unknown Recipient"
    })

    return profile
