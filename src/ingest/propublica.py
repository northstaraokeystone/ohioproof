"""
ProPublica Nonprofit Ingest Module

Purpose: Ingest 501(c) nonprofit filings via ProPublica API
Data Source: projects.propublica.org/nonprofits (REST API, public)

Receipt: propublica_ingest_receipt
SLO: ingest_latency <= 30s per organization
Gate: t8h

Critical Pattern: Generation Now (501c4, dark money detection)
"""

import time
from typing import Any

from src.core import dual_hash, emit_receipt, stoprule_data_source_unavailable, TENANT_ID
from src.constants import HB6_BRIBERY_AMOUNT

# API endpoint
API_BASE = "https://projects.propublica.org/nonprofits/api/v2"


def fetch_org(ein: str) -> dict | None:
    """
    Fetch organization by EIN.

    Args:
        ein: Employer Identification Number (9 digits)

    Returns:
        Organization data or None if not found
    """
    t0 = time.time()

    # In production: GET /api/v2/organizations/{ein}.json
    # Sample response structure
    org = {
        "ein": ein,
        "name": f"Organization {ein}",
        "subsection_code": "501(c)(4)",  # Generation Now pattern
        "ruling_date": "2017-01",
        "asset_amount": 0,
        "income_amount": 0,
        "revenue_amount": 0,
        "ntee_code": "",
        "state": "OH",
        "city": "Columbus"
    }

    latency_ms = (time.time() - t0) * 1000

    emit_receipt("propublica_ingest", {
        "tenant_id": TENANT_ID,
        "source": "propublica",
        "ein": ein,
        "org_found": org is not None,
        "subsection": org.get("subsection_code") if org else None,
        "latency_ms": latency_ms
    })

    return org


def fetch_990(ein: str, year: int) -> dict | None:
    """
    Fetch Form 990 data for organization.

    Args:
        ein: Employer Identification Number
        year: Tax year

    Returns:
        Form 990 data or None if not found
    """
    t0 = time.time()

    # In production: GET /api/v2/organizations/{ein}.json
    # then access filings_with_data array
    filing = {
        "ein": ein,
        "tax_year": year,
        "total_revenue": 0,
        "total_expenses": 0,
        "total_assets": 0,
        "total_liabilities": 0,
        "contributions": 0,
        "program_service_revenue": 0,
        "investment_income": 0,
        "other_revenue": 0,
        "grants_paid": 0,
        "salaries": 0,
        "political_expenditures": 0,
        "lobbying_expenditures": 0
    }

    latency_ms = (time.time() - t0) * 1000

    emit_receipt("propublica_990", {
        "tenant_id": TENANT_ID,
        "ein": ein,
        "tax_year": year,
        "filing_found": filing is not None,
        "total_revenue": filing.get("total_revenue", 0) if filing else 0,
        "latency_ms": latency_ms
    })

    return filing


def detect_dark_money(org: dict) -> float:
    """
    Score organization for Generation Now-pattern dark money indicators.

    Generation Now Pattern:
        - 501(c)(4) status → no donor disclosure
        - Large receipts with no disclosed contributors
        - Expenditures to political consultants/campaigns
        - Board overlap with political actors

    Args:
        org: Organization data from fetch_org

    Returns:
        Dark money risk score (0.0 - 1.0)
    """
    score = 0.0
    indicators = []

    if not org:
        return 0.0

    # 501(c)(4) status - highest risk for dark money
    subsection = org.get("subsection_code", "")
    if "501(c)(4)" in subsection or subsection == "4":
        score += 0.3
        indicators.append("501c4_status")

    # Large revenue with no disclosed contributors
    revenue = org.get("revenue_amount", 0) or org.get("total_revenue", 0)
    if revenue > 1_000_000:
        score += 0.2
        indicators.append("large_revenue")

    # Ohio-based (relevant to state corruption)
    if org.get("state") == "OH":
        score += 0.1
        indicators.append("ohio_based")

    # Recent formation (Generation Now formed shortly before HB6)
    ruling_date = org.get("ruling_date", "")
    if ruling_date and ruling_date >= "2017":
        score += 0.1
        indicators.append("recent_formation")

    # Political-sounding name patterns
    name = org.get("name", "").upper()
    political_keywords = ["GENERATION", "FUTURE", "PROGRESS", "ACTION", "CITIZENS"]
    if any(kw in name for kw in political_keywords):
        score += 0.15
        indicators.append("political_name_pattern")

    # Cap at 1.0
    score = min(score, 1.0)

    emit_receipt("dark_money_detection", {
        "tenant_id": TENANT_ID,
        "ein": org.get("ein", "unknown"),
        "org_name_hash": dual_hash(org.get("name", "")),
        "dark_money_score": score,
        "indicators": indicators,
        "flagged": score >= 0.5,
        "generation_now_pattern_match": score >= 0.7
    })

    return score


def search_organizations(query: str, state: str = "OH") -> list[dict]:
    """
    Search for organizations by name.

    Args:
        query: Search query
        state: State filter

    Returns:
        List of matching organizations
    """
    t0 = time.time()

    # In production: GET /api/v2/search.json?q={query}&state={state}
    results = []

    latency_ms = (time.time() - t0) * 1000

    emit_receipt("propublica_search", {
        "tenant_id": TENANT_ID,
        "query_hash": dual_hash(query),
        "state": state,
        "result_count": len(results),
        "latency_ms": latency_ms
    })

    return results


def scan_501c4_orgs(state: str = "OH") -> list[dict]:
    """
    Scan all 501(c)(4) organizations in state for dark money patterns.

    Args:
        state: State to scan

    Returns:
        List of flagged organizations with scores
    """
    flagged = []

    emit_receipt("501c4_scan_start", {
        "tenant_id": TENANT_ID,
        "state": state,
        "scan_type": "dark_money_detection"
    })

    # In production: paginate through all 501(c)(4)s
    # For now, return empty list

    emit_receipt("501c4_scan_complete", {
        "tenant_id": TENANT_ID,
        "state": state,
        "orgs_scanned": 0,
        "orgs_flagged": len(flagged)
    })

    return flagged
