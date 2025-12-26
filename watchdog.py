#!/usr/bin/env python3
"""
OhioProof Watchdog - System health monitoring

Purpose: Monitor all OhioProof systems for health
SLO: Detect issues within 5 minutes

Receipt: watchdog_receipt
Gate: t48h
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core import dual_hash, emit_receipt, TENANT_ID


def check_core_modules() -> dict:
    """Check core modules are functional."""
    status = {"module": "core", "healthy": True, "issues": []}

    try:
        from src.core import dual_hash, emit_receipt, merkle, StopRule

        # Test dual_hash
        h = dual_hash("test")
        if ":" not in h:
            status["healthy"] = False
            status["issues"].append("dual_hash not producing dual format")

    except ImportError as e:
        status["healthy"] = False
        status["issues"].append(f"Import error: {e}")

    return status


def check_ingest_modules() -> dict:
    """Check ingest modules are functional."""
    status = {"module": "ingest", "healthy": True, "issues": []}

    modules = [
        "ohio_checkbook", "usaspending", "propublica",
        "nppes", "campaign_finance", "lobbying", "puco"
    ]

    for mod in modules:
        try:
            exec(f"from src.ingest.{mod} import *")
        except ImportError as e:
            status["healthy"] = False
            status["issues"].append(f"{mod}: {e}")

    return status


def check_detect_modules() -> dict:
    """Check detect modules are functional."""
    status = {"module": "detect", "healthy": True, "issues": []}

    modules = ["anomaly", "compression", "correlation", "patterns", "growth"]

    for mod in modules:
        try:
            exec(f"from src.detect.{mod} import *")
        except ImportError as e:
            status["healthy"] = False
            status["issues"].append(f"{mod}: {e}")

    return status


def check_domain_modules() -> dict:
    """Check domain modules are functional."""
    status = {"module": "domains", "healthy": True, "issues": []}

    domains = ["medicaid", "jobsohio", "hb6", "strs", "pandemic", "charter"]

    for domain in domains:
        try:
            exec(f"from src.domains.{domain} import *")
        except ImportError as e:
            status["healthy"] = False
            status["issues"].append(f"{domain}: {e}")

    return status


def check_constants() -> dict:
    """Check constants are loaded correctly."""
    status = {"module": "constants", "healthy": True, "issues": []}

    try:
        from src.constants import (
            HB6_BRIBERY_AMOUNT,
            MEDICAID_CONCURRENT_INDIVIDUALS,
            JOBSOHIO_FAILURE_RATE,
            PANDEMIC_FRAUD_TOTAL,
            ECOT_FINDING_FOR_RECOVERY
        )

        # Verify values
        if HB6_BRIBERY_AMOUNT != 60_000_000:
            status["healthy"] = False
            status["issues"].append("HB6_BRIBERY_AMOUNT incorrect")

        if MEDICAID_CONCURRENT_INDIVIDUALS != 124_448:
            status["healthy"] = False
            status["issues"].append("MEDICAID_CONCURRENT_INDIVIDUALS incorrect")

    except ImportError as e:
        status["healthy"] = False
        status["issues"].append(f"Import error: {e}")

    return status


def check_patterns() -> dict:
    """Check fraud patterns are loaded."""
    status = {"module": "patterns", "healthy": True, "issues": []}

    try:
        from src.detect.patterns import list_patterns, load_pattern

        patterns = list_patterns()
        expected = ["generation_now", "concurrent_enrollment", "ecot_attendance", "feeding_our_future"]

        for pattern in expected:
            if pattern not in patterns:
                status["healthy"] = False
                status["issues"].append(f"Missing pattern: {pattern}")
            else:
                p = load_pattern(pattern)
                if p is None:
                    status["healthy"] = False
                    status["issues"].append(f"Cannot load pattern: {pattern}")

    except ImportError as e:
        status["healthy"] = False
        status["issues"].append(f"Import error: {e}")

    return status


def run_health_check() -> dict:
    """Run full health check."""
    checks = [
        check_core_modules,
        check_ingest_modules,
        check_detect_modules,
        check_domain_modules,
        check_constants,
        check_patterns
    ]

    results = []
    all_healthy = True

    for check in checks:
        result = check()
        results.append(result)
        if not result["healthy"]:
            all_healthy = False

    health = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "overall_healthy": all_healthy,
        "checks": results,
        "healthy_count": sum(1 for r in results if r["healthy"]),
        "total_checks": len(results)
    }

    emit_receipt("watchdog", {
        "tenant_id": TENANT_ID,
        "overall_healthy": all_healthy,
        "healthy_count": health["healthy_count"],
        "total_checks": health["total_checks"]
    })

    return health


def main():
    parser = argparse.ArgumentParser(description="OhioProof Watchdog")
    parser.add_argument("--check", action="store_true", help="Run health check")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.check:
        health = run_health_check()

        if args.json:
            print(json.dumps(health, indent=2))
        else:
            print(f"OhioProof Watchdog - {health['timestamp']}")
            print(f"Overall: {'HEALTHY' if health['overall_healthy'] else 'UNHEALTHY'}")
            print(f"Checks: {health['healthy_count']}/{health['total_checks']} passing")
            print()

            for check in health["checks"]:
                status = "✓" if check["healthy"] else "✗"
                print(f"  {status} {check['module']}")
                for issue in check.get("issues", []):
                    print(f"      - {issue}")

        # Exit with error if unhealthy
        sys.exit(0 if health["overall_healthy"] else 1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
