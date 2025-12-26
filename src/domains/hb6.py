"""
HB6 Dark Money Detection Module

Purpose: HB6-pattern dark money detection

Verified Fraud: $60M bribery, largest Ohio corruption case

Data Sources:
    - ProPublica nonprofits (501c4 filings)
    - Ohio campaign finance
    - OLAC lobbying
    - PUCO filings
    - Court documents (DOJ, SEC)

Generation Now Pattern:
    - 501(c)(4) status = no donor disclosure
    - $60M received from FirstEnergy affiliates
    - Disbursed to political operatives
    - Timed with HB6 passage
    - $400K check hand-delivered ("akin to bags of cash")

Receipt: dark_money_scan_receipt, legislative_correlation_receipt
SLO: Scan all Ohio 501(c)(4)s monthly
     Flag any org with >$1M receipts and <10% disclosed donors
     Correlation score > 0.7 triggers human review
Gate: t24h
"""

from datetime import datetime, timezone
from typing import Any

from src.core import dual_hash, emit_receipt, TENANT_ID
from src.constants import (
    HB6_BRIBERY_AMOUNT,
    HB6_RATEPAYER_BAILOUT,
    HOUSEHOLDER_SENTENCE_YEARS,
    RANDAZZO_PAYMENT,
    FIRSTENERGY_DOJ_FINE,
    FIRSTENERGY_SEC_SETTLEMENT,
    FIRSTENERGY_PUCO_SETTLEMENT
)


def scan_501c4(ein: str) -> dict:
    """
    Analyze 501(c)(4) for dark money indicators.

    Generation Now indicators:
        - 501(c)(4) status → no donor disclosure
        - Large anonymous donations
        - Expenditures to political consultants/campaigns
        - Board overlap with political actors

    Args:
        ein: Employer Identification Number

    Returns:
        Scan result with dark money score
    """
    from src.ingest.propublica import fetch_org, detect_dark_money

    org = fetch_org(ein)

    if not org:
        return {
            "ein": ein,
            "found": False,
            "dark_money_score": 0.0
        }

    score = detect_dark_money(org)

    result = {
        "ein": ein,
        "found": True,
        "org_name_hash": dual_hash(org.get("name", "")),
        "subsection": org.get("subsection_code"),
        "state": org.get("state"),
        "dark_money_score": score,
        "flagged": score >= 0.7,
        "generation_now_pattern": score >= 0.8
    }

    emit_receipt("dark_money_scan", {
        "tenant_id": TENANT_ID,
        "ein": ein,
        "dark_money_score": score,
        "flagged": result["flagged"]
    })

    return result


def correlate_lobbying_spend(org: dict, lobbying: list[dict]) -> float:
    """
    Score for lobbying-payment correlation.

    Args:
        org: Organization data
        lobbying: Lobbying activity records

    Returns:
        Correlation score
    """
    score = 0.0
    indicators = []

    org_name = org.get("name", "").upper()

    for activity in lobbying:
        employer = activity.get("employer", "").upper()

        # Name match
        if org_name in employer or employer in org_name:
            score += 0.3
            indicators.append("employer_match")

        # Timing with expenditures
        activity_date = activity.get("date")
        expenditure_dates = org.get("expenditure_dates", [])

        for exp_date in expenditure_dates:
            if activity_date and exp_date:
                # Check if within 60 days
                try:
                    a_dt = datetime.fromisoformat(activity_date)
                    e_dt = datetime.fromisoformat(exp_date)
                    days_apart = abs((a_dt - e_dt).days)

                    if days_apart <= 60:
                        score += 0.2
                        indicators.append(f"timing_correlation_{days_apart}_days")
                except (ValueError, TypeError):
                    pass

    score = min(score, 1.0)

    emit_receipt("lobbying_correlation", {
        "tenant_id": TENANT_ID,
        "org_hash": dual_hash(org.get("name", "")),
        "lobbying_activities": len(lobbying),
        "correlation_score": score,
        "indicators": indicators
    })

    return score


def detect_legislative_timing(
    contribution: dict,
    votes: list[dict]
) -> dict:
    """
    Flag contributions preceding favorable votes.

    HB6 Pattern:
        - Contributions from FirstEnergy/affiliates
        - Votes on HB6 (nuclear bailout)
        - Timing within 30-60 days

    Args:
        contribution: Campaign contribution record
        votes: Legislative vote records

    Returns:
        Timing correlation result
    """
    correlations = []

    contrib_date = contribution.get("date")
    contrib_amount = contribution.get("amount", 0)

    if not contrib_date:
        return {"correlations": [], "max_score": 0}

    for vote in votes:
        vote_date = vote.get("date")

        if not vote_date:
            continue

        try:
            c_dt = datetime.fromisoformat(contrib_date)
            v_dt = datetime.fromisoformat(vote_date)

            days_before = (v_dt - c_dt).days

            if 0 < days_before <= 90:
                score = 0.0

                # Timing score
                if days_before <= 30:
                    score += 0.5
                elif days_before <= 60:
                    score += 0.35
                else:
                    score += 0.2

                # Amount score
                if contrib_amount >= 100000:
                    score += 0.3
                elif contrib_amount >= 10000:
                    score += 0.15

                # Vote outcome
                if vote.get("outcome") == "passed":
                    score += 0.2

                correlations.append({
                    "vote_id": vote.get("vote_id"),
                    "vote_hash": dual_hash(str(vote)),
                    "days_before": days_before,
                    "score": min(score, 1.0)
                })

        except (ValueError, TypeError):
            pass

    max_score = max([c["score"] for c in correlations], default=0)

    emit_receipt("legislative_correlation", {
        "tenant_id": TENANT_ID,
        "contribution_hash": dual_hash(str(contribution)),
        "votes_analyzed": len(votes),
        "correlations_found": len(correlations),
        "max_score": max_score,
        "flagged": max_score >= 0.7
    })

    return {
        "correlations": correlations,
        "max_score": max_score,
        "flagged": max_score >= 0.7
    }


def trace_flow(payment: dict) -> list[dict]:
    """
    Trace payment flow through intermediaries.

    HB6 Pattern: FirstEnergy → 501(c)(4) → Political Operatives

    Args:
        payment: Payment record

    Returns:
        List of traced entities
    """
    trace = []

    source = payment.get("source")
    destination = payment.get("destination")
    amount = payment.get("amount", 0)

    # Level 1: Direct payment
    trace.append({
        "level": 1,
        "from_hash": dual_hash(source) if source else None,
        "to_hash": dual_hash(destination) if destination else None,
        "amount": amount,
        "type": "direct"
    })

    # Level 2+: Would trace through intermediaries
    # In production, would query for payments from destination
    intermediaries = payment.get("intermediaries", [])

    for i, inter in enumerate(intermediaries):
        trace.append({
            "level": i + 2,
            "from_hash": dual_hash(inter.get("from", "")),
            "to_hash": dual_hash(inter.get("to", "")),
            "amount": inter.get("amount", 0),
            "type": "intermediary"
        })

    emit_receipt("payment_trace", {
        "tenant_id": TENANT_ID,
        "source_hash": dual_hash(source) if source else None,
        "trace_depth": len(trace),
        "total_amount": amount
    })

    return trace


def generate_dark_money_score(org: dict) -> float:
    """
    Composite score for dark money risk.

    Factors:
        - 501(c)(4) status
        - Donor disclosure rate
        - Political expenditure ratio
        - Timing with legislative actions
        - Board connections

    Args:
        org: Organization data

    Returns:
        Dark money risk score (0.0 - 1.0)
    """
    score = 0.0
    factors = []

    # 501(c)(4) status
    if "501(c)(4)" in org.get("subsection_code", ""):
        score += 0.25
        factors.append("501c4_status")

    # Low donor disclosure
    disclosure_rate = org.get("donor_disclosure_rate", 1.0)
    if disclosure_rate < 0.1:
        score += 0.25
        factors.append("low_disclosure")
    elif disclosure_rate < 0.5:
        score += 0.15
        factors.append("partial_disclosure")

    # High political expenditures
    political_pct = org.get("political_expenditure_pct", 0)
    if political_pct > 0.5:
        score += 0.2
        factors.append("high_political_spend")

    # Large receipts
    receipts = org.get("total_receipts", 0)
    if receipts > 10000000:
        score += 0.15
        factors.append("large_receipts_10m_plus")
    elif receipts > 1000000:
        score += 0.1
        factors.append("significant_receipts_1m_plus")

    # Recent formation
    formed_year = org.get("formation_year", 2000)
    if formed_year >= 2017:
        score += 0.1
        factors.append("recent_formation")

    score = min(score, 1.0)

    emit_receipt("dark_money_score", {
        "tenant_id": TENANT_ID,
        "org_hash": dual_hash(org.get("name", "")),
        "score": score,
        "factors": factors,
        "flagged": score >= 0.7
    })

    return score


def get_hb6_verified_data() -> dict:
    """
    Get verified HB6 case data.

    Returns:
        Verified case data
    """
    return {
        "case_name": "HB6/FirstEnergy Bribery",
        "verified_amounts": {
            "bribery_total": HB6_BRIBERY_AMOUNT,
            "ratepayer_bailout": HB6_RATEPAYER_BAILOUT,
            "randazzo_payment": RANDAZZO_PAYMENT,
            "firstenergy_doj_fine": FIRSTENERGY_DOJ_FINE,
            "firstenergy_sec_settlement": FIRSTENERGY_SEC_SETTLEMENT,
            "firstenergy_puco_settlement": FIRSTENERGY_PUCO_SETTLEMENT
        },
        "sentences": {
            "householder_years": HOUSEHOLDER_SENTENCE_YEARS
        },
        "pattern": {
            "name": "Generation Now",
            "type": "501(c)(4) dark money",
            "mechanism": "Undisclosed corporate payments through nonprofit to political operatives"
        },
        "status": "convicted",
        "source": "DOJ court documents"
    }
