"""
Ohio Lobbying (OLAC) Ingest Module

Purpose: Ingest Ohio lobbying activity data
Data Source: jlec-olig.state.oh.us (OLAC - Ohio Legislative Agent Council)

Receipt: lobbying_ingest_receipt
SLO: ingest_latency <= 60s per query
Gate: t8h

HB6 Relevance:
    - Track registered lobbyists for FirstEnergy and related entities
    - Detect unregistered lobbying activity
    - Correlate lobbying with legislative outcomes

Strive Enterprises Note:
    Per research, Strive Enterprises (Vivek's company) met with state pension
    officials without registering as lobbyists in some cases. System should
    flag similar patterns.
"""

import time
from typing import Any

from src.core import dual_hash, emit_receipt, stoprule_data_source_unavailable, TENANT_ID

# Data source info
DATA_SOURCE_URL = "https://jlec-olig.state.oh.us"


def fetch_lobbyists(employer: str | None = None) -> list[dict]:
    """
    Fetch registered lobbyists by employer.

    Args:
        employer: Employer name to filter

    Returns:
        List of registered lobbyist records
    """
    t0 = time.time()

    # In production: scrape OLAC website
    lobbyists = []

    if employer:
        # Sample data for testing
        lobbyists = [
            {
                "lobbyist_id": "LOB_001",
                "name": "John Smith",
                "employer": employer,
                "registration_date": "2019-01-15",
                "status": "active",
                "clients": [employer]
            }
        ]

    latency_ms = (time.time() - t0) * 1000

    emit_receipt("lobbying_ingest", {
        "tenant_id": TENANT_ID,
        "source": "lobbying",
        "employer_hash": dual_hash(employer) if employer else None,
        "record_count": len(lobbyists),
        "latency_ms": latency_ms
    })

    return lobbyists


def fetch_activity(lobbyist: str, year: int) -> list[dict]:
    """
    Fetch activity reports for lobbyist.

    Args:
        lobbyist: Lobbyist name
        year: Year to query

    Returns:
        List of activity records
    """
    t0 = time.time()

    # In production: scrape OLAC activity reports
    activities = []

    latency_ms = (time.time() - t0) * 1000

    emit_receipt("lobbying_activity", {
        "tenant_id": TENANT_ID,
        "lobbyist_hash": dual_hash(lobbyist),
        "year": year,
        "record_count": len(activities),
        "latency_ms": latency_ms
    })

    return activities


def detect_unregistered(contact: dict) -> bool:
    """
    Flag potential unregistered lobbying activity.

    Indicators:
        - Contact with officials without registration
        - Employer is corporation with legislative interests
        - Contact relates to pending legislation

    Strive Pattern:
        - Investment firm meeting with pension officials
        - No lobbying registration on file
        - Discussion of fund management or investment

    Args:
        contact: Contact/meeting record

    Returns:
        True if potential unregistered lobbying
    """
    flagged = False
    indicators = []

    entity = contact.get("entity", "")
    official = contact.get("official", "")
    purpose = contact.get("purpose", "").lower()

    # Check if entity should be registered
    corporate_keywords = ["inc", "llc", "corp", "enterprises", "capital", "partners"]
    if any(kw in entity.lower() for kw in corporate_keywords):
        # Check if registered
        lobbyists = fetch_lobbyists(entity)
        if not lobbyists:
            indicators.append("corporate_entity_not_registered")

            # Check purpose for lobbying indicators
            lobbying_purposes = [
                "legislation", "bill", "policy", "regulation",
                "investment", "fund", "contract", "procurement"
            ]
            if any(p in purpose for p in lobbying_purposes):
                flagged = True
                indicators.append("legislative_purpose_without_registration")

    emit_receipt("unregistered_lobbying_detection", {
        "tenant_id": TENANT_ID,
        "entity_hash": dual_hash(entity),
        "official_hash": dual_hash(official),
        "flagged": flagged,
        "indicators": indicators
    })

    return flagged


def correlate_with_legislation(
    lobbyist: str,
    legislation: list[dict]
) -> list[dict]:
    """
    Correlate lobbyist activity with specific legislation.

    Args:
        lobbyist: Lobbyist name
        legislation: List of legislation records

    Returns:
        List of correlated records with scores
    """
    correlations = []

    activities = fetch_activity(lobbyist, 2019)  # Example year

    for activity in activities:
        for bill in legislation:
            # Simple correlation based on timing and subject
            correlation = {
                "lobbyist_hash": dual_hash(lobbyist),
                "bill_id": bill.get("bill_id"),
                "correlation_score": 0.0,
                "indicators": []
            }

            # Would implement more sophisticated correlation
            correlations.append(correlation)

    emit_receipt("lobbying_legislation_correlation", {
        "tenant_id": TENANT_ID,
        "lobbyist_hash": dual_hash(lobbyist),
        "legislation_count": len(legislation),
        "correlation_count": len(correlations)
    })

    return correlations


def search_by_client(client: str) -> list[dict]:
    """
    Search for all lobbyists representing a client.

    Args:
        client: Client name

    Returns:
        List of lobbyist records
    """
    t0 = time.time()

    # In production: search OLAC by client
    lobbyists = []

    latency_ms = (time.time() - t0) * 1000

    emit_receipt("lobbying_client_search", {
        "tenant_id": TENANT_ID,
        "client_hash": dual_hash(client),
        "result_count": len(lobbyists),
        "latency_ms": latency_ms
    })

    return lobbyists


def get_employer_lobbying_history(employer: str) -> dict:
    """
    Get complete lobbying history for an employer.

    Args:
        employer: Employer name

    Returns:
        Lobbying history summary
    """
    lobbyists = fetch_lobbyists(employer)

    history = {
        "employer": employer,
        "employer_hash": dual_hash(employer),
        "total_lobbyists": len(lobbyists),
        "active_lobbyists": [l for l in lobbyists if l.get("status") == "active"],
        "total_activities": 0,
        "years_active": [],
        "known_clients": []
    }

    emit_receipt("lobbying_history", {
        "tenant_id": TENANT_ID,
        "employer_hash": dual_hash(employer),
        "total_lobbyists": len(lobbyists),
        "active_count": len(history["active_lobbyists"])
    })

    return history
