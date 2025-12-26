"""
JobsOhio Economic Development Module

Purpose: JobsOhio accountability - expose hidden outcomes

Verified Waste: 65% of companies (39/60) failed to meet job creation targets
The Problem: JobsOhio is private 501(c)(4) exempt from Ohio Public Records Law (ORC 187.04)

Data Sources:
    - JobsOhio annual reports (PDF)
    - ODJFS employer wage data (requires matching)
    - Ohio Checkbook disbursements
    - USASpending federal grants

Receipt: jobsohio_commitment_receipt, jobsohio_verification_receipt, jobsohio_clawback_receipt
SLO: Quarterly verification of all active commitments
     Dashboard updated within 7 days of ODJFS data refresh
     Clawback trigger within 30 days of missed milestone
Gate: t24h
"""

from datetime import datetime, timezone
from typing import Any

from src.core import dual_hash, emit_receipt, TENANT_ID
from src.constants import (
    JOBSOHIO_FAILURE_RATE,
    JOBSOHIO_COMPANIES_AUDITED,
    JOBSOHIO_COMPANIES_FAILED,
    INTEL_INCENTIVE,
    GM_LORDSTOWN_CLAWBACK
)


# Known failure cases from verified research
KNOWN_FAILURES = [
    {"name": "Truepill Inc.", "promised_payroll": 6200000, "delivered_payroll": 0, "delivery_rate": 0.0},
    {"name": "Surati (Canada)", "promised_jobs": 108, "delivered_jobs": 0, "delivery_rate": 0.0},
    {"name": "Barbaricum", "promised_jobs": 80, "delivered_jobs": 3, "delivery_rate": 0.0375},
]


def parse_commitment(announcement: dict) -> dict:
    """
    Extract promised jobs, payroll, timeline from press release.

    Args:
        announcement: JobsOhio announcement/press release

    Returns:
        Parsed commitment
    """
    commitment = {
        "company": announcement.get("company", "Unknown"),
        "company_hash": dual_hash(announcement.get("company", "")),
        "promised_jobs": announcement.get("promised_jobs", 0),
        "promised_payroll": announcement.get("promised_payroll", 0),
        "promised_investment": announcement.get("promised_investment", 0),
        "incentive_amount": announcement.get("incentive_amount", 0),
        "timeline_years": announcement.get("timeline_years", 3),
        "announcement_date": announcement.get("date"),
        "milestone_date": announcement.get("milestone_date"),
        "status": "active"
    }

    emit_receipt("jobsohio_commitment", {
        "tenant_id": TENANT_ID,
        "company_hash": commitment["company_hash"],
        "promised_jobs": commitment["promised_jobs"],
        "promised_payroll": commitment["promised_payroll"],
        "incentive_amount": commitment["incentive_amount"],
        "timeline_years": commitment["timeline_years"]
    })

    return commitment


def verify_employment(company: dict, commitment: dict) -> float:
    """
    Cross-reference ODJFS wage data vs. commitment.

    Args:
        company: Company data with actual employment
        commitment: Original commitment

    Returns:
        Verification score (0.0 - 1.0)
    """
    actual_jobs = company.get("actual_jobs", 0)
    promised_jobs = commitment.get("promised_jobs", 1)

    actual_payroll = company.get("actual_payroll", 0)
    promised_payroll = commitment.get("promised_payroll", 1)

    # Calculate delivery rates
    job_delivery = min(actual_jobs / promised_jobs, 1.0) if promised_jobs > 0 else 0
    payroll_delivery = min(actual_payroll / promised_payroll, 1.0) if promised_payroll > 0 else 0

    # Weighted verification score
    score = (job_delivery * 0.6) + (payroll_delivery * 0.4)

    emit_receipt("jobsohio_verification", {
        "tenant_id": TENANT_ID,
        "company_hash": commitment.get("company_hash"),
        "actual_jobs": actual_jobs,
        "promised_jobs": promised_jobs,
        "actual_payroll": actual_payroll,
        "promised_payroll": promised_payroll,
        "job_delivery_rate": job_delivery,
        "payroll_delivery_rate": payroll_delivery,
        "verification_score": score
    })

    return score


def compute_delivery_rate(company: dict) -> float:
    """
    Compute actual jobs / promised jobs.

    Args:
        company: Company with actual and promised data

    Returns:
        Delivery rate (0.0 - 1.0+)
    """
    actual = company.get("actual_jobs", 0)
    promised = company.get("promised_jobs", 1)

    if promised == 0:
        return 0.0

    rate = actual / promised

    return rate


def flag_zero_delivery(company: dict) -> bool:
    """
    Flag companies with 0% delivery (Truepill, Surati pattern).

    Args:
        company: Company data

    Returns:
        True if zero delivery
    """
    actual_jobs = company.get("actual_jobs", 0)
    actual_payroll = company.get("actual_payroll", 0)
    incentive = company.get("incentive_amount", 0)

    is_zero = actual_jobs == 0 and actual_payroll == 0 and incentive > 0

    if is_zero:
        emit_receipt("zero_delivery_flag", {
            "tenant_id": TENANT_ID,
            "company_hash": dual_hash(company.get("company", "")),
            "incentive_amount": incentive,
            "promised_jobs": company.get("promised_jobs", 0),
            "promised_payroll": company.get("promised_payroll", 0),
            "flagged": True
        })

    return is_zero


def compute_clawback(company: dict, incentive: dict) -> float:
    """
    Calculate clawback amount per contract terms.

    Precedent: GM Lordstown - $28M clawback

    Args:
        company: Company actual performance
        incentive: Original incentive terms

    Returns:
        Clawback amount
    """
    delivery_rate = compute_delivery_rate(company)
    incentive_amount = incentive.get("amount", 0)

    # Clawback calculation based on shortfall
    if delivery_rate >= 1.0:
        clawback = 0.0
    elif delivery_rate >= 0.75:
        # Minor shortfall - proportional clawback
        clawback = incentive_amount * (1 - delivery_rate) * 0.5
    elif delivery_rate >= 0.5:
        # Significant shortfall - larger clawback
        clawback = incentive_amount * (1 - delivery_rate) * 0.75
    else:
        # Major failure - full clawback consideration
        clawback = incentive_amount * (1 - delivery_rate)

    emit_receipt("jobsohio_clawback", {
        "tenant_id": TENANT_ID,
        "company_hash": dual_hash(company.get("company", "")),
        "incentive_amount": incentive_amount,
        "delivery_rate": delivery_rate,
        "clawback_amount": clawback,
        "shortfall_pct": 1 - delivery_rate
    })

    return clawback


def generate_public_dashboard(companies: list[dict]) -> dict:
    """
    Generate promised vs. delivered dashboard data.

    This exposes data hidden by ORC 187.04 (public records exemption).

    Args:
        companies: List of companies with commitment and actual data

    Returns:
        Dashboard data
    """
    total_promised_jobs = sum(c.get("promised_jobs", 0) for c in companies)
    total_actual_jobs = sum(c.get("actual_jobs", 0) for c in companies)
    total_incentives = sum(c.get("incentive_amount", 0) for c in companies)

    zero_delivery = [c for c in companies if flag_zero_delivery(c)]
    failed = [c for c in companies if compute_delivery_rate(c) < 1.0]

    overall_delivery_rate = total_actual_jobs / total_promised_jobs if total_promised_jobs > 0 else 0

    dashboard = {
        "generated_ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "summary": {
            "companies_tracked": len(companies),
            "total_promised_jobs": total_promised_jobs,
            "total_actual_jobs": total_actual_jobs,
            "overall_delivery_rate": overall_delivery_rate,
            "total_incentives": total_incentives,
            "zero_delivery_count": len(zero_delivery),
            "failed_count": len(failed),
            "failure_rate": len(failed) / len(companies) if companies else 0
        },
        "zero_delivery_companies": [
            {
                "company_hash": dual_hash(c.get("company", "")),
                "promised_jobs": c.get("promised_jobs", 0),
                "incentive_amount": c.get("incentive_amount", 0)
            }
            for c in zero_delivery
        ],
        "verified_failure_rate": JOBSOHIO_FAILURE_RATE,
        "auditor_findings": {
            "companies_audited": JOBSOHIO_COMPANIES_AUDITED,
            "companies_failed": JOBSOHIO_COMPANIES_FAILED,
            "source": "Ohio Auditor Dec 2024"
        },
        "transparency_note": "JobsOhio is exempt from Ohio Public Records Law (ORC 187.04)"
    }

    emit_receipt("jobsohio_dashboard", {
        "tenant_id": TENANT_ID,
        "companies_tracked": len(companies),
        "failure_rate": dashboard["summary"]["failure_rate"],
        "zero_delivery_count": len(zero_delivery),
        "total_incentives": total_incentives
    })

    return dashboard


def track_intel_commitment() -> dict:
    """
    Track Intel commitment (largest single commitment).

    Intel: 3,000 jobs by 2028 → production delayed to 2031

    Returns:
        Intel tracking data
    """
    intel = {
        "company": "Intel",
        "commitment": {
            "jobs": 3000,
            "original_date": "2028",
            "current_date": "2031",
            "delay_years": 3,
            "incentive_estimate": INTEL_INCENTIVE
        },
        "status": "delayed",
        "risk": "high",
        "notes": "Production delayed from 2028 to 2031"
    }

    emit_receipt("intel_tracking", {
        "tenant_id": TENANT_ID,
        "company": "Intel",
        "status": intel["status"],
        "delay_years": 3,
        "incentive_estimate": INTEL_INCENTIVE
    })

    return intel
