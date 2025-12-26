"""
Known Fraud Pattern Library

Purpose: Match transactions against known fraud patterns

Known Patterns:
    - generation_now: 501(c)(4) dark money (HB6)
    - concurrent_enrollment: Multi-state Medicaid fraud
    - ecot_attendance: Charter school attendance fraud
    - feeding_our_future: Meal program explosive growth

Receipt: pattern_match_receipt
SLO: pattern_match_latency <= 5s
Gate: t16h
"""

import json
import os
import time
from typing import Any

from src.core import dual_hash, emit_receipt, TENANT_ID
from src.constants import (
    HB6_BRIBERY_AMOUNT,
    MEDICAID_CONCURRENT_INDIVIDUALS,
    MEDICAID_CHRONIC_CONCURRENT,
    ECOT_FINDING_FOR_RECOVERY,
    GROWTH_RATE_CRITICAL
)

# Pattern definitions (embedded for reliability)
PATTERNS = {
    "generation_now": {
        "pattern_id": "generation_now",
        "type": "dark_money_501c4",
        "description": "501(c)(4) dark money pattern (HB6/FirstEnergy)",
        "indicators": [
            {"field": "tax_status", "operator": "eq", "value": "501(c)(4)"},
            {"field": "donor_disclosure_pct", "operator": "lt", "value": 0.10},
            {"field": "annual_receipts", "operator": "gt", "value": 1000000},
            {"field": "political_expenditure_pct", "operator": "gt", "value": 0.50}
        ],
        "correlations": [
            {"source": "lobbying", "timing_days": 30},
            {"source": "legislative_votes", "timing_days": 60}
        ],
        "verified_case": {
            "name": "Generation Now",
            "amount": HB6_BRIBERY_AMOUNT,
            "outcome": "20-year federal sentence"
        },
        "risk_weight": 0.9
    },
    "concurrent_enrollment": {
        "pattern_id": "concurrent_enrollment",
        "type": "medicaid_fraud",
        "description": "Multi-state Medicaid concurrent enrollment",
        "indicators": [
            {"field": "concurrent_months", "operator": "gte", "value": 3}
        ],
        "severity_tiers": [
            {"months": 3, "severity": "low", "weight": 0.3},
            {"months": 12, "severity": "medium", "weight": 0.6},
            {"months": 48, "severity": "critical", "weight": 1.0}
        ],
        "verified_case": {
            "individuals": MEDICAID_CONCURRENT_INDIVIDUALS,
            "chronic_individuals": MEDICAID_CHRONIC_CONCURRENT,
            "estimated_improper": 1000000000
        },
        "risk_weight": 0.85
    },
    "ecot_attendance": {
        "pattern_id": "ecot_attendance",
        "type": "charter_fraud",
        "description": "Virtual school attendance inflation",
        "indicators": [
            {"field": "school_type", "operator": "eq", "value": "virtual"},
            {"field": "claimed_enrollment", "operator": "gt", "value": 1000},
            {"field": "attendance_variance_pct", "operator": "gt", "value": 20}
        ],
        "red_flags": [
            "related_party_vendors",
            "enrollment_variance_gt_20pct",
            "login_hours_lt_10pct_claimed"
        ],
        "verified_case": {
            "name": "ECOT",
            "total_received": 1000000000,
            "finding_for_recovery": ECOT_FINDING_FOR_RECOVERY,
            "years_operating": 18
        },
        "risk_weight": 0.8
    },
    "feeding_our_future": {
        "pattern_id": "feeding_our_future",
        "type": "growth_anomaly",
        "description": "Explosive program growth (meal fraud pattern)",
        "indicators": [
            {"field": "yoy_growth_rate", "operator": "gt", "value": GROWTH_RATE_CRITICAL},
            {"field": "site_capacity_ratio", "operator": "gt", "value": 5.0},
            {"field": "onboarding_velocity_days", "operator": "lt", "value": 7}
        ],
        "ignored_signals": [
            "30+ complaints over 3 years",
            "sites claiming thousands of meals within days of opening"
        ],
        "verified_case": {
            "state": "Minnesota",
            "amount": 250000000,
            "growth_rate": "2800%"
        },
        "risk_weight": 0.95
    }
}


def load_pattern(pattern_name: str) -> dict | None:
    """
    Load pattern definition from library.

    Args:
        pattern_name: Name of pattern to load

    Returns:
        Pattern definition or None if not found
    """
    pattern = PATTERNS.get(pattern_name)

    if pattern:
        emit_receipt("pattern_load", {
            "tenant_id": TENANT_ID,
            "pattern_id": pattern_name,
            "pattern_type": pattern.get("type"),
            "loaded": True
        })
    else:
        emit_receipt("pattern_load", {
            "tenant_id": TENANT_ID,
            "pattern_id": pattern_name,
            "loaded": False
        })

    return pattern


def list_patterns() -> list[str]:
    """
    Return all available pattern names.

    Returns:
        List of pattern names
    """
    return list(PATTERNS.keys())


def match_pattern(
    record: dict,
    pattern: dict
) -> float:
    """
    Score match against known pattern.

    Args:
        record: Record to evaluate
        pattern: Pattern definition

    Returns:
        Match score (0.0 - 1.0)
    """
    if not pattern:
        return 0.0

    t0 = time.time()

    score = 0.0
    matched_indicators = []
    total_weight = 0.0
    matched_weight = 0.0

    indicators = pattern.get("indicators", [])

    for indicator in indicators:
        field = indicator.get("field")
        operator = indicator.get("operator")
        value = indicator.get("value")
        weight = indicator.get("weight", 1.0)

        total_weight += weight

        record_value = record.get(field)

        if record_value is not None:
            match = evaluate_operator(record_value, operator, value)

            if match:
                matched_weight += weight
                matched_indicators.append({
                    "field": field,
                    "operator": operator,
                    "expected": value,
                    "actual": record_value
                })

    if total_weight > 0:
        score = matched_weight / total_weight

    # Apply pattern risk weight
    risk_weight = pattern.get("risk_weight", 1.0)
    final_score = score * risk_weight

    latency_ms = (time.time() - t0) * 1000

    emit_receipt("pattern_match", {
        "tenant_id": TENANT_ID,
        "pattern_id": pattern.get("pattern_id"),
        "pattern_type": pattern.get("type"),
        "record_hash": dual_hash(str(record)),
        "score": final_score,
        "matched_indicators": len(matched_indicators),
        "total_indicators": len(indicators),
        "flagged": final_score >= 0.7,
        "latency_ms": latency_ms
    })

    return final_score


def evaluate_operator(value: Any, operator: str, target: Any) -> bool:
    """
    Evaluate operator condition.

    Operators: eq, ne, gt, lt, gte, lte, contains, in

    Args:
        value: Actual value
        operator: Operator string
        target: Target value

    Returns:
        True if condition is met
    """
    try:
        if operator == "eq":
            return value == target
        elif operator == "ne":
            return value != target
        elif operator == "gt":
            return float(value) > float(target)
        elif operator == "lt":
            return float(value) < float(target)
        elif operator == "gte":
            return float(value) >= float(target)
        elif operator == "lte":
            return float(value) <= float(target)
        elif operator == "contains":
            return str(target).lower() in str(value).lower()
        elif operator == "in":
            return value in target
        else:
            return False
    except (ValueError, TypeError):
        return False


def match_all_patterns(record: dict) -> dict:
    """
    Match record against all known patterns.

    Args:
        record: Record to evaluate

    Returns:
        All pattern match results
    """
    results = {}
    highest_score = 0.0
    best_match = None

    for pattern_name in PATTERNS:
        pattern = PATTERNS[pattern_name]
        score = match_pattern(record, pattern)

        results[pattern_name] = {
            "score": score,
            "flagged": score >= 0.7,
            "type": pattern.get("type")
        }

        if score > highest_score:
            highest_score = score
            best_match = pattern_name

    emit_receipt("pattern_match_all", {
        "tenant_id": TENANT_ID,
        "record_hash": dual_hash(str(record)),
        "patterns_evaluated": len(PATTERNS),
        "best_match": best_match,
        "highest_score": highest_score,
        "any_flagged": any(r["flagged"] for r in results.values())
    })

    return {
        "results": results,
        "best_match": best_match,
        "highest_score": highest_score
    }


def get_pattern_verified_case(pattern_name: str) -> dict | None:
    """
    Get verified fraud case for a pattern.

    Args:
        pattern_name: Pattern name

    Returns:
        Verified case details
    """
    pattern = PATTERNS.get(pattern_name)
    if pattern:
        return pattern.get("verified_case")
    return None


def save_pattern(pattern_name: str, pattern_data: dict, path: str = "data/patterns") -> bool:
    """
    Save pattern to file system.

    Args:
        pattern_name: Pattern name
        pattern_data: Pattern definition
        path: Directory path

    Returns:
        True if saved successfully
    """
    try:
        os.makedirs(path, exist_ok=True)
        filepath = os.path.join(path, f"{pattern_name}.json")

        with open(filepath, "w") as f:
            json.dump(pattern_data, f, indent=2)

        emit_receipt("pattern_save", {
            "tenant_id": TENANT_ID,
            "pattern_id": pattern_name,
            "path": filepath,
            "success": True
        })

        return True
    except Exception as e:
        emit_receipt("pattern_save", {
            "tenant_id": TENANT_ID,
            "pattern_id": pattern_name,
            "success": False,
            "error": str(e)
        })
        return False
