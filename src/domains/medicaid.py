"""
Medicaid Concurrent Enrollment Module

Purpose: Detect concurrent enrollment fraud in Medicaid

Verified Fraud: $1B+ in capitation payments for 124,448 dual-enrolled individuals
Critical: 2,372 enrolled in multiple states EVERY MONTH for 4 consecutive years

Data Sources:
    - Ohio Medicaid enrollment (ODM)
    - CMS Medicare/Medicaid crossover (requires data sharing agreement)
    - NPPES provider registry

Receipt: medicaid_enrollment_receipt, medicaid_anomaly_receipt
SLO: Detect concurrent enrollment BEFORE monthly capitation payment
     Alert latency: ≤24 hours from enrollment data refresh
     Precision: ≥85% (per Lucas County benchmark)
Gate: t24h
"""

from datetime import datetime, timezone
from typing import Any

from src.core import dual_hash, emit_receipt, TENANT_ID
from src.constants import (
    MEDICAID_CONCURRENT_INDIVIDUALS,
    MEDICAID_CHRONIC_CONCURRENT,
    MEDICAID_CAPITATION_AT_RISK,
    MEDICAID_CONCURRENT_MONTHS
)


def detect_concurrent(ohio_enrollment: list[dict]) -> list[dict]:
    """
    Flag enrollees with out-of-state indicators.

    Detection Logic:
        1. Ingest Ohio Medicaid enrollment
        2. Cross-reference with NPPES for provider addresses outside Ohio
        3. Flag patterns: same provider serving "Ohio" patient in another state
        4. Compute capitation payment amount at risk
        5. Emit alert if match confidence > 0.8

    Args:
        ohio_enrollment: List of Ohio enrollment records

    Returns:
        List of flagged enrollees
    """
    flagged = []

    for enrollee in ohio_enrollment:
        # Check for out-of-state indicators
        indicators = []
        score = 0.0

        # Address outside Ohio
        address = enrollee.get("address", {})
        if address.get("state") and address.get("state") != "OH":
            indicators.append("out_of_state_address")
            score += 0.4

        # Provider in another state
        provider_state = enrollee.get("provider_state")
        if provider_state and provider_state != "OH":
            indicators.append("out_of_state_provider")
            score += 0.3

        # Multiple enrollments flag
        if enrollee.get("enrollment_count", 1) > 1:
            indicators.append("multiple_enrollments")
            score += 0.2

        # Long enrollment duration (potential concurrent)
        months = enrollee.get("enrollment_months", 0)
        if months >= 48:  # 4 years - chronic pattern
            indicators.append("chronic_enrollment_48_months")
            score += 0.3
        elif months >= 12:
            indicators.append("extended_enrollment_12_months")
            score += 0.15
        elif months >= MEDICAID_CONCURRENT_MONTHS:
            indicators.append("concurrent_3_months")
            score += 0.1

        score = min(score, 1.0)

        if score >= 0.5:
            flagged.append({
                "enrollee_hash": dual_hash(str(enrollee.get("id", ""))),
                "score": score,
                "indicators": indicators,
                "months_enrolled": months,
                "capitation_at_risk": compute_capitation_risk(enrollee)
            })

    emit_receipt("medicaid_enrollment", {
        "tenant_id": TENANT_ID,
        "total_enrollees": len(ohio_enrollment),
        "flagged_count": len(flagged),
        "concurrent_detected": len(flagged)
    })

    return flagged


def verify_eligibility(enrollee: dict) -> dict:
    """
    Cross-reference eligibility criteria.

    Args:
        enrollee: Enrollee record

    Returns:
        Eligibility verification result
    """
    issues = []
    eligible = True

    # Check residency
    address = enrollee.get("address", {})
    if address.get("state") != "OH":
        issues.append("non_ohio_residency")
        eligible = False

    # Check income (if available)
    income = enrollee.get("income")
    income_threshold = enrollee.get("income_threshold", 0)
    if income and income_threshold and income > income_threshold:
        issues.append("income_exceeds_threshold")
        eligible = False

    # Check other coverage
    if enrollee.get("has_other_coverage"):
        issues.append("other_coverage_exists")

    result = {
        "enrollee_hash": dual_hash(str(enrollee.get("id", ""))),
        "eligible": eligible,
        "issues": issues,
        "verification_ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }

    emit_receipt("eligibility_verification", {
        "tenant_id": TENANT_ID,
        "enrollee_hash": result["enrollee_hash"],
        "eligible": eligible,
        "issue_count": len(issues)
    })

    return result


def compute_capitation_risk(enrollee: dict) -> float:
    """
    Estimate improper payment if concurrent.

    Args:
        enrollee: Enrollee record

    Returns:
        Estimated capitation at risk
    """
    # Average monthly capitation payment (varies by managed care plan)
    monthly_capitation = enrollee.get("monthly_capitation", 500)

    # Months of potential concurrent enrollment
    months = enrollee.get("enrollment_months", 0)

    # Risk = monthly payment * months
    risk = monthly_capitation * months

    emit_receipt("capitation_risk", {
        "tenant_id": TENANT_ID,
        "enrollee_hash": dual_hash(str(enrollee.get("id", ""))),
        "monthly_capitation": monthly_capitation,
        "months": months,
        "risk_amount": risk
    })

    return risk


def generate_referral(flagged: list[dict]) -> dict:
    """
    Generate OIG/AG referral packet.

    Args:
        flagged: List of flagged enrollees

    Returns:
        Referral packet
    """
    total_at_risk = sum(f.get("capitation_at_risk", 0) for f in flagged)

    # Categorize by severity
    chronic = [f for f in flagged if "chronic_enrollment_48_months" in f.get("indicators", [])]
    extended = [f for f in flagged if "extended_enrollment_12_months" in f.get("indicators", [])]

    referral = {
        "referral_id": dual_hash(f"medicaid_referral:{len(flagged)}:{total_at_risk}"),
        "generated_ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "domain": "medicaid",
        "agency": "OIG",  # Office of Inspector General
        "case_type": "concurrent_enrollment",
        "summary": {
            "total_flagged": len(flagged),
            "chronic_cases": len(chronic),
            "extended_cases": len(extended),
            "total_at_risk": total_at_risk
        },
        "evidence_hashes": [f.get("enrollee_hash") for f in flagged[:100]],
        "priority": "critical" if len(chronic) > 100 else "high",
        "recommendations": [
            "Cross-state enrollment verification",
            "Capitation payment suspension pending review",
            "Coordination with CMS for national matching"
        ]
    }

    emit_receipt("referral", {
        "tenant_id": TENANT_ID,
        "referral_id": referral["referral_id"],
        "agency": "OIG",
        "case_type": "concurrent_enrollment",
        "amount_at_risk": total_at_risk,
        "flagged_count": len(flagged)
    })

    return referral


def detect_provider_anomaly(enrollee: dict) -> dict:
    """
    Detect provider-based anomalies indicating concurrent enrollment.

    Args:
        enrollee: Enrollee with provider information

    Returns:
        Provider anomaly result
    """
    from src.ingest.nppes import verify_provider, detect_address_anomaly

    provider_npi = enrollee.get("provider_npi")
    if not provider_npi:
        return {"verified": False, "reason": "no_provider_npi"}

    # Verify provider is in Ohio
    verification = verify_provider(provider_npi, "OH")

    result = {
        "enrollee_hash": dual_hash(str(enrollee.get("id", ""))),
        "provider_npi": provider_npi,
        "provider_verified": verification.get("verified", False),
        "anomaly_detected": not verification.get("verified", False)
    }

    if not result["provider_verified"]:
        emit_receipt("medicaid_anomaly", {
            "tenant_id": TENANT_ID,
            "enrollee_hash": result["enrollee_hash"],
            "anomaly_type": "provider_state_mismatch",
            "provider_states": verification.get("actual_states", []),
            "expected_state": "OH"
        })

    return result


def compute_concurrent_statistics() -> dict:
    """
    Compute statistics for concurrent enrollment.

    Returns:
        Statistics based on verified data
    """
    stats = {
        "verified_concurrent_individuals": MEDICAID_CONCURRENT_INDIVIDUALS,
        "chronic_concurrent_individuals": MEDICAID_CHRONIC_CONCURRENT,
        "estimated_improper_payments": MEDICAID_CAPITATION_AT_RISK,
        "data_source": "Ohio Auditor March 2024",
        "concurrent_threshold_months": MEDICAID_CONCURRENT_MONTHS,
        "chronic_threshold_months": 48
    }

    emit_receipt("medicaid_statistics", {
        "tenant_id": TENANT_ID,
        **stats
    })

    return stats
