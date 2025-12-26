"""
Ohio Campaign Finance Ingest Module

Purpose: Ingest Ohio campaign finance data
Data Source: ohiosos.gov (searchable, 6 years data)

Receipt: campaign_finance_ingest_receipt
SLO: ingest_latency <= 60s per query
Gate: t8h

HB6 Relevance:
    - Track contributions preceding legislative votes
    - Correlate with lobbying activity
    - Detect timing patterns (contribution → vote correlation)
"""

import time
from datetime import datetime, timedelta
from typing import Any

from src.core import dual_hash, emit_receipt, stoprule_data_source_unavailable, TENANT_ID
from src.constants import HB6_BRIBERY_AMOUNT

# Data source info
DATA_SOURCE_URL = "https://ohiosos.gov"
YEARS_AVAILABLE = 6


def fetch_contributions(
    candidate: str | None = None,
    committee: str | None = None,
    date_range: tuple[str, str] | None = None
) -> list[dict]:
    """
    Fetch contributions by candidate or committee.

    Args:
        candidate: Candidate name filter
        committee: Committee name filter
        date_range: Tuple of (start_date, end_date) ISO8601

    Returns:
        List of contribution records
    """
    t0 = time.time()

    # In production: scrape ohiosos.gov campaign finance search
    contributions = []

    # Sample data for testing
    if candidate or committee:
        contributions = [
            {
                "contribution_id": "CONTRIB_001",
                "contributor_name": "Anonymous PAC",
                "contributor_type": "PAC",
                "amount": 10000.00,
                "date": "2019-04-15",
                "recipient_name": candidate or "Unknown Candidate",
                "recipient_type": "candidate",
                "contribution_type": "monetary"
            }
        ]

    latency_ms = (time.time() - t0) * 1000

    emit_receipt("campaign_finance_ingest", {
        "tenant_id": TENANT_ID,
        "source": "campaign_finance",
        "candidate_hash": dual_hash(candidate) if candidate else None,
        "committee_hash": dual_hash(committee) if committee else None,
        "date_range": date_range,
        "record_count": len(contributions),
        "total_amount": sum(c.get("amount", 0) for c in contributions),
        "latency_ms": latency_ms
    })

    return contributions


def fetch_expenditures(
    committee: str,
    date_range: tuple[str, str] | None = None
) -> list[dict]:
    """
    Fetch expenditures by committee.

    Args:
        committee: Committee name
        date_range: Tuple of (start_date, end_date) ISO8601

    Returns:
        List of expenditure records
    """
    t0 = time.time()

    # In production: scrape ohiosos.gov expenditure records
    expenditures = []

    latency_ms = (time.time() - t0) * 1000

    emit_receipt("campaign_finance_expenditures", {
        "tenant_id": TENANT_ID,
        "committee_hash": dual_hash(committee),
        "date_range": date_range,
        "record_count": len(expenditures),
        "total_amount": sum(e.get("amount", 0) for e in expenditures),
        "latency_ms": latency_ms
    })

    return expenditures


def correlate_lobbying(contributor: str) -> dict:
    """
    Cross-reference contributor with OLAC lobbying data.

    Args:
        contributor: Contributor name to search

    Returns:
        Correlation result with lobbying activity
    """
    contributor_hash = dual_hash(contributor)

    # In production: match against lobbying database
    result = {
        "contributor": contributor,
        "contributor_hash": contributor_hash,
        "lobbying_match": False,
        "registered_lobbyist": None,
        "employer": None,
        "clients": [],
        "correlation_score": 0.0
    }

    emit_receipt("campaign_lobbying_correlation", {
        "tenant_id": TENANT_ID,
        "contributor_hash": contributor_hash,
        "lobbying_match": result["lobbying_match"],
        "correlation_score": result["correlation_score"]
    })

    return result


def detect_timing(
    contribution: dict,
    legislative_action: dict
) -> float:
    """
    Score for suspicious timing (contribution → vote correlation).

    HB6 Pattern:
        - Large contributions within 30-60 days of favorable votes
        - Pattern of contributions from same source before multiple votes
        - Correlation with lobbying activity in same period

    Args:
        contribution: Contribution record
        legislative_action: Legislative action (vote, bill passage, etc.)

    Returns:
        Timing suspicion score (0.0 - 1.0)
    """
    score = 0.0
    indicators = []

    contribution_date = contribution.get("date", "")
    action_date = legislative_action.get("date", "")

    if not contribution_date or not action_date:
        return 0.0

    try:
        contrib_dt = datetime.fromisoformat(contribution_date)
        action_dt = datetime.fromisoformat(action_date)

        days_before = (action_dt - contrib_dt).days

        # Contribution within 30 days before action
        if 0 < days_before <= 30:
            score += 0.4
            indicators.append("contribution_within_30_days")
        # Contribution within 60 days before action
        elif 0 < days_before <= 60:
            score += 0.25
            indicators.append("contribution_within_60_days")
        # Contribution within 90 days before action
        elif 0 < days_before <= 90:
            score += 0.15
            indicators.append("contribution_within_90_days")

        # Large contribution (HB6 pattern: $60M total)
        amount = contribution.get("amount", 0)
        if amount >= 100000:
            score += 0.3
            indicators.append("large_contribution_100k_plus")
        elif amount >= 50000:
            score += 0.2
            indicators.append("large_contribution_50k_plus")
        elif amount >= 10000:
            score += 0.1
            indicators.append("notable_contribution_10k_plus")

    except (ValueError, TypeError):
        pass

    # Cap at 1.0
    score = min(score, 1.0)

    emit_receipt("timing_detection", {
        "tenant_id": TENANT_ID,
        "contribution_hash": dual_hash(str(contribution)),
        "action_hash": dual_hash(str(legislative_action)),
        "timing_score": score,
        "indicators": indicators,
        "flagged": score >= 0.5
    })

    return score


def analyze_contribution_pattern(
    contributions: list[dict],
    legislative_actions: list[dict]
) -> dict:
    """
    Analyze pattern of contributions across multiple legislative actions.

    Args:
        contributions: List of contribution records
        legislative_actions: List of legislative actions

    Returns:
        Pattern analysis with aggregate scoring
    """
    total_score = 0.0
    flagged_pairs = []
    contributor_patterns = {}

    for contrib in contributions:
        contributor = contrib.get("contributor_name", "unknown")
        if contributor not in contributor_patterns:
            contributor_patterns[contributor] = {
                "total_contributions": 0,
                "total_amount": 0,
                "correlated_actions": []
            }

        contributor_patterns[contributor]["total_contributions"] += 1
        contributor_patterns[contributor]["total_amount"] += contrib.get("amount", 0)

        for action in legislative_actions:
            timing_score = detect_timing(contrib, action)
            if timing_score >= 0.5:
                flagged_pairs.append({
                    "contribution_hash": dual_hash(str(contrib)),
                    "action_hash": dual_hash(str(action)),
                    "timing_score": timing_score
                })
                total_score += timing_score
                contributor_patterns[contributor]["correlated_actions"].append(
                    dual_hash(str(action))
                )

    result = {
        "total_contributions": len(contributions),
        "total_actions": len(legislative_actions),
        "flagged_pairs": len(flagged_pairs),
        "aggregate_score": total_score,
        "contributor_count": len(contributor_patterns),
        "high_risk_contributors": [
            k for k, v in contributor_patterns.items()
            if len(v["correlated_actions"]) >= 2
        ]
    }

    emit_receipt("contribution_pattern_analysis", {
        "tenant_id": TENANT_ID,
        "total_contributions": len(contributions),
        "flagged_pairs": len(flagged_pairs),
        "aggregate_score": total_score,
        "high_risk_count": len(result["high_risk_contributors"])
    })

    return result
