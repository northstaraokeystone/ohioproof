"""
STRS Ohio Pension Monitoring Module

Purpose: STRS Ohio pension monitoring

Current Investigation: AG Yost lawsuit alleging $65B contract-steering to QED Technologies

Data Sources:
    - STRS annual reports (ACFR)
    - Investment performance filings
    - Board meeting minutes
    - Court filings (AG Yost v. Steen/Fichtenbaum)

QED Technologies Pattern (alleged):
    - 2-person startup with no clients
    - Awarded contract without competitive process
    - Board members Wade Steen & Rudy Fichtenbaum connection
    - Text evidence: QED wrote questions "as though I am Mr. Steen"

Receipt: strs_investment_receipt, strs_governance_receipt
SLO: Monthly scan of new contracts
     Alert on any vendor with <3 years history receiving >$1M
     Board conflict check on all vendor relationships
Gate: t24h
"""

from datetime import datetime, timezone
from typing import Any

from src.core import dual_hash, emit_receipt, TENANT_ID
from src.constants import (
    STRS_FUND_SIZE,
    STRS_FUNDED_RATIO,
    STRS_ALLEGED_STEERING
)


def parse_investment(filing: dict) -> dict:
    """
    Extract investment manager, fees, performance.

    Args:
        filing: Investment filing data

    Returns:
        Parsed investment data
    """
    investment = {
        "manager": filing.get("manager"),
        "manager_hash": dual_hash(filing.get("manager", "")),
        "fee_amount": filing.get("fee_amount", 0),
        "fee_pct": filing.get("fee_pct", 0),
        "assets_managed": filing.get("assets_managed", 0),
        "performance_return": filing.get("return_pct", 0),
        "benchmark_return": filing.get("benchmark_pct", 0),
        "benchmark_delta": 0,
        "year": filing.get("year")
    }

    if investment["performance_return"] and investment["benchmark_return"]:
        investment["benchmark_delta"] = (
            investment["performance_return"] - investment["benchmark_return"]
        )

    emit_receipt("strs_investment", {
        "tenant_id": TENANT_ID,
        "manager_hash": investment["manager_hash"],
        "fee_pct": investment["fee_pct"],
        "benchmark_delta": investment["benchmark_delta"]
    })

    return investment


def detect_steering(contracts: list[dict]) -> list[dict]:
    """
    Flag unusual vendor selection patterns.

    QED Pattern:
        - New vendor with no track record
        - No competitive process
        - Board member connections

    Args:
        contracts: List of contract records

    Returns:
        List of flagged contracts
    """
    flagged = []

    for contract in contracts:
        score = 0.0
        indicators = []

        # New vendor (< 3 years history)
        vendor_age_years = contract.get("vendor_age_years", 10)
        if vendor_age_years < 3:
            score += 0.3
            indicators.append("new_vendor_lt_3_years")

        # No competitive process
        if not contract.get("competitive_bid"):
            score += 0.25
            indicators.append("no_competitive_process")

        # Large contract value
        value = contract.get("value", 0)
        if value > 10000000:
            score += 0.2
            indicators.append("high_value_10m_plus")
        elif value > 1000000:
            score += 0.1
            indicators.append("significant_value_1m_plus")

        # Board connection
        if contract.get("board_connection"):
            score += 0.3
            indicators.append("board_connection")

        score = min(score, 1.0)

        if score >= 0.5:
            flagged.append({
                "contract_hash": dual_hash(str(contract)),
                "vendor_hash": dual_hash(contract.get("vendor", "")),
                "score": score,
                "indicators": indicators,
                "value": value
            })

    emit_receipt("steering_detection", {
        "tenant_id": TENANT_ID,
        "contracts_analyzed": len(contracts),
        "flagged_count": len(flagged)
    })

    return flagged


def compute_fee_ratio(fund: dict) -> float:
    """
    Compute fees / assets under management.

    Args:
        fund: Fund data with fees and AUM

    Returns:
        Fee ratio (as percentage)
    """
    fees = fund.get("total_fees", 0)
    aum = fund.get("assets_under_management", 1)

    if aum == 0:
        return 0.0

    ratio = (fees / aum) * 100  # As percentage

    emit_receipt("fee_ratio", {
        "tenant_id": TENANT_ID,
        "total_fees": fees,
        "aum": aum,
        "fee_ratio_pct": ratio
    })

    return ratio


def flag_board_conflict(member: dict, vendor: dict) -> bool:
    """
    Flag board member connections to vendors.

    Args:
        member: Board member data
        vendor: Vendor data

    Returns:
        True if conflict detected
    """
    conflict = False
    indicators = []

    # Direct employment
    if member.get("employer") == vendor.get("name"):
        conflict = True
        indicators.append("direct_employment")

    # Prior relationship
    if vendor.get("name") in member.get("prior_employers", []):
        conflict = True
        indicators.append("prior_employment")

    # Board overlap
    member_boards = set(member.get("other_boards", []))
    vendor_boards = set(vendor.get("board_members", []))

    if member_boards.intersection(vendor_boards):
        conflict = True
        indicators.append("board_overlap")

    # Financial interest
    if member.get("has_financial_interest_in", []):
        if vendor.get("name") in member["has_financial_interest_in"]:
            conflict = True
            indicators.append("financial_interest")

    if conflict:
        emit_receipt("board_conflict", {
            "tenant_id": TENANT_ID,
            "member_hash": dual_hash(member.get("name", "")),
            "vendor_hash": dual_hash(vendor.get("name", "")),
            "indicators": indicators,
            "flagged": True
        })

    return conflict


def monitor_governance(meeting: dict) -> dict:
    """
    Track voting patterns, recusals.

    Args:
        meeting: Board meeting data

    Returns:
        Governance analysis
    """
    votes = meeting.get("votes", [])
    recusals = meeting.get("recusals", [])
    conflicts_flagged = meeting.get("conflicts_flagged", [])

    # Analyze voting patterns
    vote_analysis = {}
    for vote in votes:
        member = vote.get("member")
        if member not in vote_analysis:
            vote_analysis[member] = {"yes": 0, "no": 0, "abstain": 0}

        vote_cast = vote.get("vote", "abstain").lower()
        if vote_cast in vote_analysis[member]:
            vote_analysis[member][vote_cast] += 1

    result = {
        "meeting_date": meeting.get("date"),
        "total_votes": len(votes),
        "recusals": len(recusals),
        "conflicts_flagged": len(conflicts_flagged),
        "member_analysis": vote_analysis,
        "governance_score": compute_governance_score(meeting)
    }

    emit_receipt("strs_governance", {
        "tenant_id": TENANT_ID,
        "meeting_date": meeting.get("date"),
        "votes": len(votes),
        "recusals": len(recusals),
        "conflicts_flagged": len(conflicts_flagged),
        "governance_score": result["governance_score"]
    })

    return result


def compute_governance_score(meeting: dict) -> float:
    """
    Compute governance quality score.

    Args:
        meeting: Meeting data

    Returns:
        Governance score (0.0 - 1.0)
    """
    score = 1.0

    # Deduct for unaddressed conflicts
    conflicts = meeting.get("conflicts_flagged", [])
    addressed = meeting.get("conflicts_addressed", [])

    unaddressed = len(conflicts) - len(addressed)
    if unaddressed > 0:
        score -= unaddressed * 0.1

    # Deduct for missing recusals
    expected_recusals = meeting.get("expected_recusals", [])
    actual_recusals = meeting.get("recusals", [])

    missing_recusals = len(set(expected_recusals) - set(actual_recusals))
    if missing_recusals > 0:
        score -= missing_recusals * 0.2

    return max(score, 0.0)


def get_strs_statistics() -> dict:
    """
    Get STRS fund statistics.

    Returns:
        Fund statistics
    """
    return {
        "fund_size": STRS_FUND_SIZE,
        "funded_ratio": STRS_FUNDED_RATIO,
        "alleged_steering": STRS_ALLEGED_STEERING,
        "source": "ACFR June 2024",
        "current_investigation": "AG Yost v. Steen/Fichtenbaum"
    }
