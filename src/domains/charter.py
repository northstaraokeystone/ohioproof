"""
Charter School ECOT-Pattern Detection Module

Purpose: Charter school ECOT-pattern detection

Verified Fraud: ECOT received $1B over 18 years, $117M Finding for Recovery

ECOT Pattern:
    - Virtual school claiming full-time enrollment
    - Students logging in 1-2 hours/week (or not at all)
    - Full per-pupil funding collected
    - Payments to entities controlled by founders

Data Sources:
    - ODE enrollment data
    - School attendance systems (when available)
    - Ohio Checkbook school funding
    - Court judgments

Receipt: charter_enrollment_receipt, charter_attendance_receipt
SLO: Daily enrollment verification for e-schools
     Alert on any school with >20% enrollment variance
     Related-party vendor audit quarterly
Gate: t24h
"""

from datetime import datetime, timezone
from typing import Any

from src.core import dual_hash, emit_receipt, TENANT_ID
from src.constants import (
    ECOT_FINDING_FOR_RECOVERY,
    ECOT_CIVIL_JUDGMENTS,
    ECOT_TOTAL_RECEIVED
)


def verify_enrollment(school: dict) -> float:
    """
    Cross-reference claimed vs. actual enrollment.

    Args:
        school: School data with claimed and verified enrollment

    Returns:
        Verification score (actual/claimed ratio)
    """
    claimed = school.get("claimed_enrollment", 0)
    verified = school.get("verified_enrollment", 0)

    if claimed == 0:
        return 0.0

    ratio = verified / claimed
    variance_pct = abs(1 - ratio) * 100

    result = {
        "school_hash": dual_hash(school.get("name", "")),
        "claimed_enrollment": claimed,
        "verified_enrollment": verified,
        "ratio": ratio,
        "variance_pct": variance_pct,
        "flagged": variance_pct > 20
    }

    emit_receipt("charter_enrollment", {
        "tenant_id": TENANT_ID,
        **result
    })

    return ratio


def detect_attendance_anomaly(school: dict) -> dict:
    """
    Flag claimed attendance vs. login/participation data.

    ECOT Pattern:
        - Claiming full-time enrollment
        - Students logging in 1-2 hours/week (or not at all)
        - No real participation verification

    Args:
        school: School with attendance data

    Returns:
        Attendance anomaly detection result
    """
    claimed_hours = school.get("claimed_attendance_hours", 0)
    actual_hours = school.get("actual_login_hours", 0)

    if claimed_hours == 0:
        return {
            "school_hash": dual_hash(school.get("name", "")),
            "anomaly_detected": False,
            "reason": "no_claimed_hours"
        }

    ratio = actual_hours / claimed_hours
    variance_pct = abs(1 - ratio) * 100

    # ECOT-pattern: actual hours << claimed hours
    is_ecot_pattern = ratio < 0.5  # Less than 50% of claimed

    result = {
        "school_hash": dual_hash(school.get("name", "")),
        "school_type": school.get("type", "unknown"),
        "claimed_hours": claimed_hours,
        "actual_hours": actual_hours,
        "ratio": ratio,
        "variance_pct": variance_pct,
        "anomaly_detected": variance_pct > 20,
        "ecot_pattern_match": is_ecot_pattern
    }

    if result["anomaly_detected"]:
        emit_receipt("charter_attendance", {
            "tenant_id": TENANT_ID,
            **result
        })

    return result


def compute_per_pupil_risk(school: dict) -> float:
    """
    Compute funding at risk if enrollment inflated.

    Args:
        school: School data

    Returns:
        Funding amount at risk
    """
    claimed = school.get("claimed_enrollment", 0)
    verified = school.get("verified_enrollment", 0)
    per_pupil = school.get("per_pupil_funding", 7000)  # Ohio average

    if claimed <= verified:
        return 0.0

    inflated_students = claimed - verified
    risk = inflated_students * per_pupil

    emit_receipt("per_pupil_risk", {
        "tenant_id": TENANT_ID,
        "school_hash": dual_hash(school.get("name", "")),
        "claimed": claimed,
        "verified": verified,
        "inflated": inflated_students,
        "per_pupil": per_pupil,
        "risk_amount": risk
    })

    return risk


def flag_related_party(vendor: dict, school: dict) -> bool:
    """
    Flag payments to related parties.

    ECOT Pattern: Payments to entities controlled by founders

    Args:
        vendor: Vendor receiving payment
        school: School making payment

    Returns:
        True if related party detected
    """
    is_related = False
    indicators = []

    # Check board/founder overlap
    school_founders = set(school.get("founders", []))
    school_board = set(school.get("board_members", []))
    vendor_owners = set(vendor.get("owners", []))
    vendor_officers = set(vendor.get("officers", []))

    # Founder owns vendor
    if school_founders.intersection(vendor_owners):
        is_related = True
        indicators.append("founder_vendor_overlap")

    # Board member owns vendor
    if school_board.intersection(vendor_owners):
        is_related = True
        indicators.append("board_vendor_overlap")

    # Founder is vendor officer
    if school_founders.intersection(vendor_officers):
        is_related = True
        indicators.append("founder_vendor_officer")

    # Address match
    if school.get("address") and school["address"] == vendor.get("address"):
        indicators.append("address_match")
        is_related = True

    # Same registered agent
    if school.get("registered_agent") == vendor.get("registered_agent"):
        indicators.append("same_registered_agent")

    if is_related:
        emit_receipt("related_party_flag", {
            "tenant_id": TENANT_ID,
            "school_hash": dual_hash(school.get("name", "")),
            "vendor_hash": dual_hash(vendor.get("name", "")),
            "indicators": indicators,
            "flagged": True
        })

    return is_related


def analyze_vendor_payments(school: dict, vendors: list[dict]) -> dict:
    """
    Analyze vendor payments for anomalies.

    Args:
        school: School data
        vendors: List of vendor payment records

    Returns:
        Vendor payment analysis
    """
    related_party_payments = 0.0
    total_payments = 0.0
    flagged_vendors = []

    for vendor in vendors:
        payment = vendor.get("payment_amount", 0)
        total_payments += payment

        if flag_related_party(vendor, school):
            related_party_payments += payment
            flagged_vendors.append({
                "vendor_hash": dual_hash(vendor.get("name", "")),
                "payment": payment
            })

    related_pct = related_party_payments / total_payments if total_payments > 0 else 0

    result = {
        "school_hash": dual_hash(school.get("name", "")),
        "total_vendors": len(vendors),
        "total_payments": total_payments,
        "related_party_payments": related_party_payments,
        "related_party_pct": related_pct,
        "flagged_vendors": len(flagged_vendors),
        "high_risk": related_pct > 0.5
    }

    emit_receipt("vendor_payment_analysis", {
        "tenant_id": TENANT_ID,
        **result
    })

    return result


def get_ecot_case_data() -> dict:
    """
    Get ECOT verified case data.

    Returns:
        ECOT case data
    """
    return {
        "case_name": "Electronic Classroom of Tomorrow (ECOT)",
        "years_operating": 18,
        "total_received": ECOT_TOTAL_RECEIVED,
        "finding_for_recovery": ECOT_FINDING_FOR_RECOVERY,
        "civil_judgments": ECOT_CIVIL_JUDGMENTS,
        "pattern": {
            "name": "Attendance Inflation",
            "mechanism": "Virtual school claiming full-time enrollment for students with minimal/no participation",
            "indicators": [
                "Virtual school model",
                "Claimed enrollment >> verified enrollment",
                "Login hours << claimed hours",
                "Related party vendors"
            ]
        },
        "status": "judgment",
        "source": "June 2022 court judgment"
    }


def scan_virtual_schools(schools: list[dict]) -> dict:
    """
    Scan virtual schools for ECOT-pattern.

    Args:
        schools: List of virtual school records

    Returns:
        Scan results
    """
    flagged = []

    for school in schools:
        if school.get("type") != "virtual":
            continue

        enrollment = verify_enrollment(school)
        attendance = detect_attendance_anomaly(school)
        risk = compute_per_pupil_risk(school)

        if attendance.get("ecot_pattern_match") or enrollment < 0.8:
            flagged.append({
                "school_hash": dual_hash(school.get("name", "")),
                "enrollment_ratio": enrollment,
                "attendance_anomaly": attendance.get("anomaly_detected"),
                "ecot_pattern": attendance.get("ecot_pattern_match"),
                "risk_amount": risk
            })

    emit_receipt("virtual_school_scan", {
        "tenant_id": TENANT_ID,
        "schools_scanned": len(schools),
        "virtual_schools": len([s for s in schools if s.get("type") == "virtual"]),
        "flagged": len(flagged),
        "total_risk": sum(f["risk_amount"] for f in flagged)
    })

    return {
        "schools_scanned": len(schools),
        "flagged": flagged,
        "total_risk": sum(f["risk_amount"] for f in flagged)
    }
