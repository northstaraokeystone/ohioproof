"""
OhioProof Ingest Modules - Unified data ingestion from 7 Ohio government data sources.

Sources:
    - ohio_checkbook: Ohio Checkbook spending data ($400B+ transactions)
    - usaspending: Federal awards/contracts/grants via USASpending API
    - propublica: 501(c) nonprofit filings via ProPublica API
    - nppes: NPI Registry for provider verification
    - campaign_finance: Ohio SOS campaign finance data
    - lobbying: OLAC lobbying activity data
    - puco: PUCO utility filings

Receipt: ingest_module_init
Gate: t8h
"""

from src.ingest.ohio_checkbook import fetch_transactions, parse_vendor, detect_shell
from src.ingest.usaspending import fetch_awards, fetch_contracts, cross_reference
from src.ingest.propublica import fetch_org, fetch_990, detect_dark_money
from src.ingest.nppes import search_npi, verify_provider, detect_address_anomaly
from src.ingest.campaign_finance import (
    fetch_contributions,
    fetch_expenditures,
    correlate_lobbying,
    detect_timing
)
from src.ingest.lobbying import fetch_lobbyists, fetch_activity, detect_unregistered
from src.ingest.puco import fetch_case, extract_rate_impact, track_commissioner

__all__ = [
    # ohio_checkbook
    "fetch_transactions", "parse_vendor", "detect_shell",
    # usaspending
    "fetch_awards", "fetch_contracts", "cross_reference",
    # propublica
    "fetch_org", "fetch_990", "detect_dark_money",
    # nppes
    "search_npi", "verify_provider", "detect_address_anomaly",
    # campaign_finance
    "fetch_contributions", "fetch_expenditures", "correlate_lobbying", "detect_timing",
    # lobbying
    "fetch_lobbyists", "fetch_activity", "detect_unregistered",
    # puco
    "fetch_case", "extract_rate_impact", "track_commissioner",
]
