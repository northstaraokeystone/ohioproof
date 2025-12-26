"""
Cross-Database Correlation Module

Purpose: Cross-database correlation for fraud signal amplification

Key Insight (Vivek): "Information is siloed in different houses"
Solution: Correlate across data sources to amplify fraud signals

Receipt: correlation_receipt
SLO: correlation_score >= 0.70 for flag
Gate: t16h
"""

import time
from datetime import datetime, timedelta
from typing import Any

from src.core import dual_hash, emit_receipt, TENANT_ID
from src.constants import CORRELATION_THRESHOLD, MEDICAID_CONCURRENT_MONTHS


def correlate_vendor(
    checkbook_vendor: dict,
    federal_vendor: dict
) -> float:
    """
    Score match confidence between Ohio Checkbook and federal vendor.

    Args:
        checkbook_vendor: Vendor from Ohio Checkbook
        federal_vendor: Vendor from USASpending

    Returns:
        Match confidence score (0.0 - 1.0)
    """
    score = 0.0
    match_factors = []

    # Name matching (normalized)
    cb_name = checkbook_vendor.get("vendor_name", "").upper().strip()
    fed_name = federal_vendor.get("recipient_name", "").upper().strip()

    if cb_name and fed_name:
        # Exact match
        if cb_name == fed_name:
            score += 0.5
            match_factors.append("exact_name_match")
        # Partial match (one contains the other)
        elif cb_name in fed_name or fed_name in cb_name:
            score += 0.3
            match_factors.append("partial_name_match")

    # Address matching
    cb_addr = checkbook_vendor.get("address", {})
    fed_addr = federal_vendor.get("address", {})

    if cb_addr.get("city") and cb_addr.get("city") == fed_addr.get("city"):
        score += 0.2
        match_factors.append("city_match")

    if cb_addr.get("state") and cb_addr.get("state") == fed_addr.get("state"):
        score += 0.1
        match_factors.append("state_match")

    # Industry/category matching
    cb_category = checkbook_vendor.get("category", "")
    fed_category = federal_vendor.get("award_type", "")

    if cb_category and fed_category and cb_category.lower() in fed_category.lower():
        score += 0.1
        match_factors.append("category_match")

    # Cap at 1.0
    score = min(score, 1.0)

    emit_receipt("vendor_correlation", {
        "tenant_id": TENANT_ID,
        "checkbook_vendor_hash": dual_hash(str(checkbook_vendor)),
        "federal_vendor_hash": dual_hash(str(federal_vendor)),
        "correlation_score": score,
        "match_factors": match_factors,
        "flagged": score >= CORRELATION_THRESHOLD
    })

    return score


def correlate_payment_lobbying(
    payment: dict,
    lobbying_activity: dict
) -> dict:
    """
    Correlate payments with lobbying activity.

    Pattern: Payments to entities that are actively lobbying
    on related legislation.

    Args:
        payment: Payment record
        lobbying_activity: Lobbying activity record

    Returns:
        Correlation result with score and details
    """
    score = 0.0
    indicators = []

    payment_entity = payment.get("vendor_name", "").upper()
    lobbying_entity = lobbying_activity.get("employer", "").upper()

    # Entity match
    if payment_entity and lobbying_entity:
        if payment_entity == lobbying_entity:
            score += 0.4
            indicators.append("exact_entity_match")
        elif payment_entity in lobbying_entity or lobbying_entity in payment_entity:
            score += 0.25
            indicators.append("partial_entity_match")

    # Timing correlation
    payment_date = payment.get("date")
    lobbying_date = lobbying_activity.get("activity_date")

    if payment_date and lobbying_date:
        try:
            p_dt = datetime.fromisoformat(payment_date)
            l_dt = datetime.fromisoformat(lobbying_date)
            days_apart = abs((p_dt - l_dt).days)

            if days_apart <= 30:
                score += 0.3
                indicators.append("timing_within_30_days")
            elif days_apart <= 90:
                score += 0.15
                indicators.append("timing_within_90_days")
        except (ValueError, TypeError):
            pass

    # Amount significance
    amount = payment.get("amount", 0)
    if amount >= 100000:
        score += 0.2
        indicators.append("significant_amount")
    elif amount >= 50000:
        score += 0.1
        indicators.append("notable_amount")

    score = min(score, 1.0)

    result = {
        "payment_hash": dual_hash(str(payment)),
        "lobbying_hash": dual_hash(str(lobbying_activity)),
        "correlation_score": score,
        "indicators": indicators,
        "flagged": score >= CORRELATION_THRESHOLD
    }

    if result["flagged"]:
        emit_receipt("payment_lobbying_correlation", {
            "tenant_id": TENANT_ID,
            **result
        })

    return result


def correlate_contribution_vote(
    contribution: dict,
    vote: dict
) -> dict:
    """
    Correlate campaign contributions with legislative votes.

    HB6 Pattern:
        - Contributions from FirstEnergy/affiliates
        - Votes on HB6 (nuclear bailout)
        - Timing correlation

    Args:
        contribution: Campaign contribution record
        vote: Legislative vote record

    Returns:
        Correlation result with score
    """
    score = 0.0
    indicators = []

    # Amount weighting
    amount = contribution.get("amount", 0)
    if amount >= 100000:
        score += 0.25
        indicators.append("large_contribution")
    elif amount >= 10000:
        score += 0.15
        indicators.append("significant_contribution")
    elif amount >= 1000:
        score += 0.05
        indicators.append("notable_contribution")

    # Timing (contribution before vote)
    contrib_date = contribution.get("date")
    vote_date = vote.get("date")

    if contrib_date and vote_date:
        try:
            c_dt = datetime.fromisoformat(contrib_date)
            v_dt = datetime.fromisoformat(vote_date)
            days_before = (v_dt - c_dt).days

            if 0 < days_before <= 30:
                score += 0.35
                indicators.append("contribution_30_days_before_vote")
            elif 0 < days_before <= 60:
                score += 0.25
                indicators.append("contribution_60_days_before_vote")
            elif 0 < days_before <= 180:
                score += 0.15
                indicators.append("contribution_180_days_before_vote")
        except (ValueError, TypeError):
            pass

    # Vote alignment
    vote_cast = vote.get("vote", "").lower()
    expected_vote = contribution.get("expected_alignment", "yes")

    if vote_cast == expected_vote:
        score += 0.2
        indicators.append("vote_aligned_with_contribution")

    score = min(score, 1.0)

    result = {
        "contribution_hash": dual_hash(str(contribution)),
        "vote_hash": dual_hash(str(vote)),
        "correlation_score": score,
        "indicators": indicators,
        "flagged": score >= CORRELATION_THRESHOLD
    }

    if result["flagged"]:
        emit_receipt("contribution_vote_correlation", {
            "tenant_id": TENANT_ID,
            **result
        })

    return result


def correlate_enrollment(
    ohio_enrollment: dict,
    other_state: dict
) -> dict:
    """
    Correlate enrollment records across states for Medicaid fraud detection.

    Pattern: Same individual enrolled in multiple state Medicaid programs
    simultaneously, receiving capitation payments in each.

    Ohio Verified: 124,448 individuals with 3+ month overlap
    Critical: 2,372 enrolled every month for 4 consecutive years

    Args:
        ohio_enrollment: Ohio Medicaid enrollment record
        other_state: Other state enrollment record

    Returns:
        Correlation result with fraud indicators
    """
    score = 0.0
    indicators = []

    # Identity matching (would use hashed SSN in production)
    ohio_id = ohio_enrollment.get("enrollee_id_hash", "")
    other_id = other_state.get("enrollee_id_hash", "")

    if ohio_id and other_id and ohio_id == other_id:
        score += 0.5
        indicators.append("identity_match")

    # Date overlap calculation
    ohio_start = ohio_enrollment.get("enrollment_start")
    ohio_end = ohio_enrollment.get("enrollment_end")
    other_start = other_state.get("enrollment_start")
    other_end = other_state.get("enrollment_end")

    if all([ohio_start, ohio_end, other_start, other_end]):
        try:
            o_start = datetime.fromisoformat(ohio_start)
            o_end = datetime.fromisoformat(ohio_end)
            s_start = datetime.fromisoformat(other_start)
            s_end = datetime.fromisoformat(other_end)

            # Calculate overlap
            overlap_start = max(o_start, s_start)
            overlap_end = min(o_end, s_end)

            if overlap_start < overlap_end:
                overlap_days = (overlap_end - overlap_start).days
                overlap_months = overlap_days / 30

                if overlap_months >= 48:  # 4 years - chronic
                    score += 0.5
                    indicators.append("chronic_concurrent_48_months")
                elif overlap_months >= 12:
                    score += 0.35
                    indicators.append("extended_concurrent_12_months")
                elif overlap_months >= MEDICAID_CONCURRENT_MONTHS:
                    score += 0.25
                    indicators.append(f"concurrent_{int(overlap_months)}_months")

        except (ValueError, TypeError):
            pass

    # Address anomaly (same person, different state addresses)
    ohio_addr = ohio_enrollment.get("address", {})
    other_addr = other_state.get("address", {})

    if ohio_addr.get("state") and other_addr.get("state"):
        if ohio_addr["state"] != other_addr["state"]:
            score += 0.1
            indicators.append("multi_state_addresses")

    score = min(score, 1.0)

    result = {
        "ohio_enrollment_hash": dual_hash(str(ohio_enrollment)),
        "other_state_hash": dual_hash(str(other_state)),
        "correlation_score": score,
        "indicators": indicators,
        "concurrent_months": 0,  # Would calculate actual overlap
        "flagged": score >= CORRELATION_THRESHOLD
    }

    if result["flagged"]:
        emit_receipt("enrollment_correlation", {
            "tenant_id": TENANT_ID,
            **result
        })

    return result


def batch_correlate(
    source_a_records: list[dict],
    source_b_records: list[dict],
    correlate_fn: callable,
    threshold: float = CORRELATION_THRESHOLD
) -> dict:
    """
    Batch correlate records from two sources.

    Args:
        source_a_records: Records from source A
        source_b_records: Records from source B
        correlate_fn: Correlation function to use
        threshold: Minimum score to include

    Returns:
        Batch correlation results
    """
    t0 = time.time()

    correlations = []
    flagged = []

    for a_record in source_a_records:
        for b_record in source_b_records:
            result = correlate_fn(a_record, b_record)

            if result.get("correlation_score", 0) >= threshold:
                correlations.append(result)
                if result.get("flagged"):
                    flagged.append(result)

    latency_ms = (time.time() - t0) * 1000

    batch_result = {
        "source_a_count": len(source_a_records),
        "source_b_count": len(source_b_records),
        "pairs_analyzed": len(source_a_records) * len(source_b_records),
        "correlations_found": len(correlations),
        "flagged_count": len(flagged),
        "latency_ms": latency_ms
    }

    emit_receipt("batch_correlation", {
        "tenant_id": TENANT_ID,
        **batch_result
    })

    return batch_result
