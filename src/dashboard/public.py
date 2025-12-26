"""
Public Dashboard Module

Purpose: Generate public accountability views

Receipt: dashboard_receipt
Gate: t36h
"""

from datetime import datetime, timezone
from typing import Any

from src.core import emit_receipt, TENANT_ID
from src.constants import (
    HB6_BRIBERY_AMOUNT,
    MEDICAID_CONCURRENT_INDIVIDUALS,
    MEDICAID_CAPITATION_AT_RISK,
    JOBSOHIO_FAILURE_RATE,
    PANDEMIC_FRAUD_TOTAL,
    PANDEMIC_RECOVERED,
    ECOT_FINDING_FOR_RECOVERY
)


def generate_public_dashboard(
    receipts: list[dict],
    domain: str | None = None
) -> dict:
    """
    Generate public accountability dashboard.

    Args:
        receipts: All receipts
        domain: Optional domain filter

    Returns:
        Dashboard data
    """
    if domain:
        receipts = [r for r in receipts if domain in r.get("receipt_type", "")]

    # Aggregate metrics
    anomalies = [r for r in receipts if r.get("receipt_type") == "anomaly"]
    flagged = [r for r in receipts if r.get("flagged")]
    correlations = [r for r in receipts if "correlation" in r.get("receipt_type", "")]

    dashboard = {
        "generated_ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "domain": domain or "all",
        "summary": {
            "total_receipts": len(receipts),
            "anomalies_detected": len(anomalies),
            "items_flagged": len(flagged),
            "correlations_found": len(correlations)
        },
        "domains": get_all_domain_summaries(),
        "verified_fraud": {
            "hb6_bribery": HB6_BRIBERY_AMOUNT,
            "medicaid_at_risk": MEDICAID_CAPITATION_AT_RISK,
            "pandemic_fraud": PANDEMIC_FRAUD_TOTAL,
            "pandemic_recovered": PANDEMIC_RECOVERED,
            "ecot_recovery": ECOT_FINDING_FOR_RECOVERY
        },
        "status": "operational"
    }

    emit_receipt("dashboard", {
        "tenant_id": TENANT_ID,
        "domain": domain or "all",
        "receipt_count": len(receipts),
        "anomaly_count": len(anomalies),
        "flagged_count": len(flagged)
    })

    return dashboard


def get_domain_summary(domain: str) -> dict:
    """
    Get summary for specific domain.

    Args:
        domain: Domain name

    Returns:
        Domain summary
    """
    summaries = {
        "medicaid": {
            "name": "Medicaid Concurrent Enrollment",
            "verified_fraud": MEDICAID_CAPITATION_AT_RISK,
            "individuals_affected": MEDICAID_CONCURRENT_INDIVIDUALS,
            "status": "monitoring",
            "priority": "P0",
            "description": "Cross-state enrollment detection for capitation fraud"
        },
        "jobsohio": {
            "name": "JobsOhio Economic Development",
            "failure_rate": JOBSOHIO_FAILURE_RATE,
            "status": "monitoring",
            "priority": "P0",
            "description": "Public accountability for private economic development"
        },
        "hb6": {
            "name": "HB6 Dark Money",
            "verified_fraud": HB6_BRIBERY_AMOUNT,
            "status": "closed_case",
            "priority": "P1",
            "description": "501(c)(4) dark money pattern detection"
        },
        "strs": {
            "name": "STRS Pension",
            "status": "investigation",
            "priority": "P1",
            "description": "Pension investment steering monitoring"
        },
        "pandemic": {
            "name": "Pandemic Unemployment",
            "verified_fraud": PANDEMIC_FRAUD_TOTAL,
            "recovered": PANDEMIC_RECOVERED,
            "status": "recovery",
            "priority": "P2",
            "description": "Unemployment fraud detection and recovery"
        },
        "charter": {
            "name": "Charter Schools",
            "verified_fraud": ECOT_FINDING_FOR_RECOVERY,
            "status": "monitoring",
            "priority": "P2",
            "description": "Attendance and enrollment verification"
        }
    }

    summary = summaries.get(domain, {"error": "unknown_domain"})

    emit_receipt("domain_summary", {
        "tenant_id": TENANT_ID,
        "domain": domain,
        "status": summary.get("status")
    })

    return summary


def get_all_domain_summaries() -> dict:
    """
    Get summaries for all domains.

    Returns:
        Dict of domain summaries
    """
    domains = ["medicaid", "jobsohio", "hb6", "strs", "pandemic", "charter"]
    return {d: get_domain_summary(d) for d in domains}


def get_fraud_overview() -> dict:
    """
    Get overview of verified fraud across all domains.

    Returns:
        Fraud overview
    """
    overview = {
        "total_verified_fraud": (
            HB6_BRIBERY_AMOUNT +
            MEDICAID_CAPITATION_AT_RISK +
            PANDEMIC_FRAUD_TOTAL +
            ECOT_FINDING_FOR_RECOVERY
        ),
        "by_domain": {
            "hb6": HB6_BRIBERY_AMOUNT,
            "medicaid": MEDICAID_CAPITATION_AT_RISK,
            "pandemic": PANDEMIC_FRAUD_TOTAL,
            "charter": ECOT_FINDING_FOR_RECOVERY
        },
        "recovered": {
            "pandemic": PANDEMIC_RECOVERED
        },
        "recovery_rate": PANDEMIC_RECOVERED / PANDEMIC_FRAUD_TOTAL
    }

    emit_receipt("fraud_overview", {
        "tenant_id": TENANT_ID,
        "total_verified": overview["total_verified_fraud"],
        "domain_count": len(overview["by_domain"])
    })

    return overview


def generate_jobsohio_dashboard() -> dict:
    """
    Generate JobsOhio-specific dashboard.

    This exposes data hidden by ORC 187.04 (public records exemption).

    Returns:
        JobsOhio accountability dashboard
    """
    dashboard = {
        "title": "JobsOhio Accountability Dashboard",
        "description": "Promised vs. Delivered outcomes for JobsOhio incentives",
        "data_note": "JobsOhio is exempt from Ohio Public Records Law (ORC 187.04)",
        "metrics": {
            "companies_audited": 60,
            "companies_failed_targets": 39,
            "failure_rate": JOBSOHIO_FAILURE_RATE,
            "zero_delivery_companies": [
                {"name": "Truepill Inc.", "promised_payroll": 6200000, "delivered": 0},
                {"name": "Surati (Canada)", "promised_jobs": 108, "delivered": 0},
                {"name": "Barbaricum", "promised_jobs": 80, "delivered": 3}
            ]
        },
        "transparency_score": 0.3,
        "recommendations": [
            "Require public reporting of commitment vs. delivery",
            "Implement clawback enforcement",
            "Quarterly verification of all active commitments"
        ]
    }

    emit_receipt("jobsohio_dashboard", {
        "tenant_id": TENANT_ID,
        "companies_audited": 60,
        "failure_rate": JOBSOHIO_FAILURE_RATE
    })

    return dashboard
