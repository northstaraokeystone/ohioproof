#!/usr/bin/env python3
"""
OhioProof CLI - Receipts-Native Government Accountability System

Usage:
    python cli.py --test              # Emit test receipt
    python cli.py --ingest <source>   # Ingest from data source
    python cli.py --detect <domain>   # Run detection on domain
    python cli.py --dashboard         # Generate dashboard
    python cli.py --status            # System status

Receipt: ohioproof_cli
Gate: t2h
"""

import argparse
import json
import sys
from datetime import datetime, timezone

# Add src to path for imports
sys.path.insert(0, ".")

from src.core import dual_hash, emit_receipt, merkle, TENANT_ID


def test_receipt() -> dict:
    """Emit a test receipt to verify system is working."""
    return emit_receipt("test", {
        "tenant_id": TENANT_ID,
        "message": "OhioProof v1 operational",
        "target_fraud": 8_300_000_000,
        "domains": [
            "medicaid",
            "jobsohio",
            "hb6",
            "strs",
            "pandemic",
            "charter"
        ],
        "physics": "fraud=high_entropy, legitimate=low_entropy"
    })


def status() -> dict:
    """Emit system status receipt."""
    return emit_receipt("status", {
        "tenant_id": TENANT_ID,
        "version": "1.0.0",
        "gate": "t2h",
        "core_functions": {
            "dual_hash": True,
            "emit_receipt": True,
            "merkle": True
        },
        "modules": {
            "ingest": ["ohio_checkbook", "usaspending", "propublica", "nppes",
                       "campaign_finance", "lobbying", "puco"],
            "detect": ["anomaly", "compression", "correlation", "patterns", "growth"],
            "domains": ["medicaid", "jobsohio", "hb6", "strs", "pandemic", "charter"],
            "output": ["brief", "packet", "dashboard"]
        }
    })


def ingest(source: str) -> dict:
    """Stub for data ingestion. Full implementation in src/ingest/."""
    valid_sources = [
        "ohio_checkbook", "usaspending", "propublica", "nppes",
        "campaign_finance", "lobbying", "puco"
    ]
    if source not in valid_sources:
        return emit_receipt("error", {
            "tenant_id": TENANT_ID,
            "message": f"Unknown source: {source}",
            "valid_sources": valid_sources
        })

    return emit_receipt("ingest_stub", {
        "tenant_id": TENANT_ID,
        "source": source,
        "status": "stub_implementation",
        "message": f"Full implementation in src/ingest/{source}.py"
    })


def detect(domain: str) -> dict:
    """Stub for detection. Full implementation in src/domains/."""
    valid_domains = ["medicaid", "jobsohio", "hb6", "strs", "pandemic", "charter"]
    if domain not in valid_domains:
        return emit_receipt("error", {
            "tenant_id": TENANT_ID,
            "message": f"Unknown domain: {domain}",
            "valid_domains": valid_domains
        })

    return emit_receipt("detect_stub", {
        "tenant_id": TENANT_ID,
        "domain": domain,
        "status": "stub_implementation",
        "message": f"Full implementation in src/domains/{domain}.py"
    })


def dashboard() -> dict:
    """Stub for dashboard generation."""
    return emit_receipt("dashboard_stub", {
        "tenant_id": TENANT_ID,
        "status": "stub_implementation",
        "message": "Full implementation in src/dashboard/public.py"
    })


def main():
    parser = argparse.ArgumentParser(
        description="OhioProof - Receipts-Native Government Accountability System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python cli.py --test              # Verify system is working
    python cli.py --status            # Show system status
    python cli.py --ingest usaspending # Ingest from USASpending
    python cli.py --detect medicaid   # Run Medicaid detection

Target: $8.3B+ verified Ohio fraud across 6 domains
Physics: Fraudulent = high entropy = doesn't compress
        """
    )

    parser.add_argument("--test", action="store_true",
                        help="Emit test receipt to verify system")
    parser.add_argument("--status", action="store_true",
                        help="Show system status")
    parser.add_argument("--ingest", type=str, metavar="SOURCE",
                        help="Ingest data from source")
    parser.add_argument("--detect", type=str, metavar="DOMAIN",
                        help="Run detection on domain")
    parser.add_argument("--dashboard", action="store_true",
                        help="Generate public dashboard")

    args = parser.parse_args()

    if args.test:
        test_receipt()
    elif args.status:
        status()
    elif args.ingest:
        ingest(args.ingest)
    elif args.detect:
        detect(args.detect)
    elif args.dashboard:
        dashboard()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
