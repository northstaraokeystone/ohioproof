"""
OhioProof Domain Modules - Domain-specific fraud detection.

Target: $8.3B+ verified Ohio fraud across 6 domains

Domains:
    - medicaid: $1B+ concurrent enrollment
    - jobsohio: 65% failure rate exposure
    - hb6: Dark money pattern detection
    - strs: Pension steering monitoring
    - pandemic: $6.9B fraud tracking
    - charter: ECOT-pattern prevention

Receipt: domain_receipt
Gate: t24h
"""

from src.domains.medicaid import (
    detect_concurrent,
    verify_eligibility,
    compute_capitation_risk,
    generate_referral
)
from src.domains.jobsohio import (
    parse_commitment,
    verify_employment,
    compute_delivery_rate,
    flag_zero_delivery,
    compute_clawback,
    generate_public_dashboard
)
from src.domains.hb6 import (
    scan_501c4,
    correlate_lobbying_spend,
    detect_legislative_timing,
    trace_flow,
    generate_dark_money_score
)
from src.domains.strs import (
    parse_investment,
    detect_steering,
    compute_fee_ratio,
    flag_board_conflict,
    monitor_governance
)
from src.domains.pandemic import (
    detect_duplicate_claims,
    detect_ineligible,
    compute_overpayment,
    track_recovery
)
from src.domains.charter import (
    verify_enrollment,
    detect_attendance_anomaly,
    compute_per_pupil_risk,
    flag_related_party
)

__all__ = [
    # medicaid
    "detect_concurrent", "verify_eligibility", "compute_capitation_risk", "generate_referral",
    # jobsohio
    "parse_commitment", "verify_employment", "compute_delivery_rate",
    "flag_zero_delivery", "compute_clawback", "generate_public_dashboard",
    # hb6
    "scan_501c4", "correlate_lobbying_spend", "detect_legislative_timing",
    "trace_flow", "generate_dark_money_score",
    # strs
    "parse_investment", "detect_steering", "compute_fee_ratio",
    "flag_board_conflict", "monitor_governance",
    # pandemic
    "detect_duplicate_claims", "detect_ineligible", "compute_overpayment", "track_recovery",
    # charter
    "verify_enrollment", "detect_attendance_anomaly", "compute_per_pupil_risk", "flag_related_party",
]
