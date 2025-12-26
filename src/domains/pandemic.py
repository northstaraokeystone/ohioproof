"""
Pandemic Unemployment Fraud Detection Module

Purpose: Pandemic unemployment fraud detection

Verified Fraud: $6.9B fraud/overpayments, $1B+ to fraudsters, ~$400M recovered

Data Sources:
    - ODJFS unemployment claims
    - Ohio Checkbook disbursements
    - USASpending CARES Act awards

Receipt: pandemic_claim_receipt, pandemic_fraud_receipt
SLO: Real-time duplicate detection on new claims
     Recovery tracking updated weekly
     Dashboard showing $6.9B identified → $X recovered
Gate: t24h
"""

from datetime import datetime, timezone
from typing import Any

from src.core import dual_hash, emit_receipt, TENANT_ID
from src.constants import (
    PANDEMIC_FRAUD_TOTAL,
    PANDEMIC_CONFIRMED_FRAUD,
    PANDEMIC_RECOVERED
)


def detect_duplicate_claims(claims: list[dict]) -> list[dict]:
    """
    Flag duplicate SSN/identity across claims.

    Args:
        claims: List of unemployment claims

    Returns:
        List of flagged duplicates
    """
    # Group by identity hash
    by_identity = {}

    for claim in claims:
        identity_hash = claim.get("identity_hash") or dual_hash(
            str(claim.get("ssn", "")) + str(claim.get("dob", ""))
        )

        if identity_hash not in by_identity:
            by_identity[identity_hash] = []
        by_identity[identity_hash].append(claim)

    # Flag identities with multiple claims
    duplicates = []

    for identity_hash, identity_claims in by_identity.items():
        if len(identity_claims) > 1:
            total_amount = sum(c.get("amount", 0) for c in identity_claims)

            duplicates.append({
                "identity_hash": identity_hash,
                "claim_count": len(identity_claims),
                "total_amount": total_amount,
                "claim_dates": [c.get("date") for c in identity_claims],
                "flagged": True
            })

    emit_receipt("pandemic_duplicate_detection", {
        "tenant_id": TENANT_ID,
        "claims_analyzed": len(claims),
        "unique_identities": len(by_identity),
        "duplicates_found": len(duplicates),
        "total_at_risk": sum(d["total_amount"] for d in duplicates)
    })

    return duplicates


def detect_ineligible(claim: dict) -> dict:
    """
    Cross-reference with employer wage data.

    Args:
        claim: Unemployment claim

    Returns:
        Eligibility check result
    """
    issues = []
    eligible = True

    # Check employment status during claim period
    claim_start = claim.get("claim_start")
    claim_end = claim.get("claim_end")
    wages_during_claim = claim.get("wages_during_claim", 0)

    if wages_during_claim > 0:
        # Had income during claim period
        weekly_wage = wages_during_claim / 4  # Approximate
        weekly_benefit = claim.get("weekly_benefit", 0)

        if weekly_wage >= weekly_benefit:
            issues.append("income_exceeds_benefit")
            eligible = False

    # Check for death records (fraud indicator)
    if claim.get("claimant_deceased_before_claim"):
        issues.append("deceased_claimant")
        eligible = False

    # Check for incarceration
    if claim.get("claimant_incarcerated"):
        issues.append("incarcerated_claimant")
        eligible = False

    # Check for out-of-state residence
    if claim.get("residence_state") != "OH":
        issues.append("non_ohio_resident")

    result = {
        "claim_hash": dual_hash(str(claim)),
        "eligible": eligible,
        "issues": issues,
        "fraud_indicators": len(issues)
    }

    if not eligible:
        emit_receipt("pandemic_ineligible", {
            "tenant_id": TENANT_ID,
            "claim_hash": result["claim_hash"],
            "issues": issues,
            "amount": claim.get("amount", 0)
        })

    return result


def compute_overpayment(claim: dict) -> float:
    """
    Calculate improper payment amount.

    Args:
        claim: Claim record

    Returns:
        Overpayment amount
    """
    eligibility = detect_ineligible(claim)

    if eligibility["eligible"]:
        return 0.0

    # Full claim amount is overpayment if completely ineligible
    if "deceased_claimant" in eligibility["issues"]:
        overpayment = claim.get("total_paid", 0)
    elif "income_exceeds_benefit" in eligibility["issues"]:
        # Partial overpayment
        wages = claim.get("wages_during_claim", 0)
        benefit = claim.get("total_paid", 0)
        overpayment = min(wages, benefit)
    else:
        overpayment = claim.get("total_paid", 0)

    emit_receipt("pandemic_overpayment", {
        "tenant_id": TENANT_ID,
        "claim_hash": dual_hash(str(claim)),
        "overpayment_amount": overpayment,
        "issues": eligibility["issues"]
    })

    return overpayment


def track_recovery(overpayment: dict) -> dict:
    """
    Track collection status.

    Args:
        overpayment: Overpayment record

    Returns:
        Recovery tracking data
    """
    recovery = {
        "overpayment_id": overpayment.get("id"),
        "overpayment_hash": dual_hash(str(overpayment)),
        "original_amount": overpayment.get("amount", 0),
        "recovered_amount": overpayment.get("recovered", 0),
        "pending_amount": 0,
        "recovery_rate": 0.0,
        "status": "pending",
        "last_updated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }

    original = recovery["original_amount"]
    recovered = recovery["recovered_amount"]

    if original > 0:
        recovery["pending_amount"] = original - recovered
        recovery["recovery_rate"] = recovered / original

        if recovery["recovery_rate"] >= 1.0:
            recovery["status"] = "recovered"
        elif recovery["recovery_rate"] > 0:
            recovery["status"] = "partial"
        else:
            recovery["status"] = "pending"

    emit_receipt("pandemic_recovery", {
        "tenant_id": TENANT_ID,
        "overpayment_hash": recovery["overpayment_hash"],
        "original_amount": original,
        "recovered_amount": recovered,
        "recovery_rate": recovery["recovery_rate"],
        "status": recovery["status"]
    })

    return recovery


def generate_pandemic_dashboard() -> dict:
    """
    Generate pandemic fraud dashboard.

    Returns:
        Dashboard data
    """
    recovery_rate = PANDEMIC_RECOVERED / PANDEMIC_FRAUD_TOTAL if PANDEMIC_FRAUD_TOTAL > 0 else 0

    dashboard = {
        "generated_ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "summary": {
            "total_identified": PANDEMIC_FRAUD_TOTAL,
            "confirmed_fraud": PANDEMIC_CONFIRMED_FRAUD,
            "recovered": PANDEMIC_RECOVERED,
            "pending_recovery": PANDEMIC_FRAUD_TOTAL - PANDEMIC_RECOVERED,
            "recovery_rate": recovery_rate
        },
        "breakdown": {
            "duplicate_claims": "TBD",
            "deceased_claimants": "TBD",
            "out_of_state": "TBD",
            "identity_fraud": "TBD"
        },
        "source": "Ohio Auditor reports",
        "notes": "$6.9B identified, $1B+ confirmed to fraudsters, ~$400M recovered"
    }

    emit_receipt("pandemic_dashboard", {
        "tenant_id": TENANT_ID,
        "total_identified": PANDEMIC_FRAUD_TOTAL,
        "recovered": PANDEMIC_RECOVERED,
        "recovery_rate": recovery_rate
    })

    return dashboard


def batch_fraud_detection(claims: list[dict]) -> dict:
    """
    Run full fraud detection on batch of claims.

    Args:
        claims: List of claims

    Returns:
        Batch detection results
    """
    duplicates = detect_duplicate_claims(claims)

    ineligible = []
    total_overpayment = 0.0

    for claim in claims:
        eligibility = detect_ineligible(claim)
        if not eligibility["eligible"]:
            overpayment = compute_overpayment(claim)
            total_overpayment += overpayment
            ineligible.append({
                "claim_hash": eligibility["claim_hash"],
                "issues": eligibility["issues"],
                "overpayment": overpayment
            })

    result = {
        "claims_analyzed": len(claims),
        "duplicates_found": len(duplicates),
        "ineligible_found": len(ineligible),
        "total_overpayment": total_overpayment,
        "fraud_rate": (len(duplicates) + len(ineligible)) / len(claims) if claims else 0
    }

    emit_receipt("pandemic_batch_detection", {
        "tenant_id": TENANT_ID,
        **result
    })

    return result
