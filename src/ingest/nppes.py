"""
NPPES NPI Registry Ingest Module

Purpose: Ingest provider data from NPI Registry for Medicaid verification
Data Source: npiregistry.cms.hhs.gov (REST API, bulk CSV)

Receipt: nppes_ingest_receipt
SLO: ingest_latency <= 30s per query
Gate: t8h

Medicaid Application:
    - Cross-reference provider addresses for concurrent enrollment detection
    - Flag providers with addresses outside Ohio serving "Ohio" patients
"""

import time
from typing import Any

from src.core import dual_hash, emit_receipt, stoprule_data_source_unavailable, TENANT_ID

# API endpoint
API_BASE = "https://npiregistry.cms.hhs.gov/api"


def search_npi(
    npi: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    state: str | None = None,
    enumeration_type: str | None = None
) -> list[dict]:
    """
    Search NPI Registry for providers.

    Args:
        npi: NPI number to search
        first_name: Provider first name
        last_name: Provider last name
        state: State code
        enumeration_type: NPI-1 (individual) or NPI-2 (organization)

    Returns:
        List of matching provider records
    """
    t0 = time.time()

    # In production: GET /api/?version=2.1&number={npi}&...
    providers = []

    if npi:
        # Sample provider data
        providers = [{
            "npi": npi,
            "enumeration_type": "NPI-1",
            "basic": {
                "first_name": first_name or "John",
                "last_name": last_name or "Doe",
                "credential": "MD",
                "sole_proprietor": "NO",
                "status": "A"
            },
            "addresses": [
                {
                    "address_purpose": "LOCATION",
                    "address_1": "123 Medical Center Dr",
                    "city": "Columbus",
                    "state": "OH",
                    "postal_code": "43215",
                    "country_code": "US"
                },
                {
                    "address_purpose": "MAILING",
                    "address_1": "PO Box 1234",
                    "city": "Columbus",
                    "state": "OH",
                    "postal_code": "43216",
                    "country_code": "US"
                }
            ],
            "taxonomies": [
                {
                    "code": "207Q00000X",
                    "desc": "Family Medicine",
                    "primary": True,
                    "state": "OH",
                    "license": "MD12345"
                }
            ]
        }]

    latency_ms = (time.time() - t0) * 1000

    emit_receipt("nppes_search", {
        "tenant_id": TENANT_ID,
        "source": "nppes",
        "npi": npi,
        "state": state,
        "result_count": len(providers),
        "latency_ms": latency_ms
    })

    return providers


def verify_provider(npi: str, expected_state: str = "OH") -> dict:
    """
    Verify provider is practicing in expected state.

    Args:
        npi: NPI number
        expected_state: Expected practice state

    Returns:
        Verification result with confidence
    """
    providers = search_npi(npi=npi)

    if not providers:
        result = {
            "npi": npi,
            "verified": False,
            "reason": "npi_not_found",
            "confidence": 0.0
        }
    else:
        provider = providers[0]
        addresses = provider.get("addresses", [])
        states = [a.get("state") for a in addresses if a.get("state")]

        if expected_state in states:
            result = {
                "npi": npi,
                "verified": True,
                "reason": "state_match",
                "confidence": 1.0,
                "all_states": list(set(states))
            }
        else:
            result = {
                "npi": npi,
                "verified": False,
                "reason": "state_mismatch",
                "confidence": 0.0,
                "expected_state": expected_state,
                "actual_states": list(set(states))
            }

    emit_receipt("nppes_verification", {
        "tenant_id": TENANT_ID,
        "npi": npi,
        "expected_state": expected_state,
        "verified": result["verified"],
        "confidence": result["confidence"]
    })

    return result


def detect_address_anomaly(provider: dict, expected_state: str = "OH") -> float:
    """
    Detect address anomalies indicating potential concurrent enrollment fraud.

    Flags:
        - Provider with Ohio license but out-of-state practice address
        - Provider serving patients in multiple distant states
        - Mismatch between license state and practice location

    Args:
        provider: Provider record from search_npi
        expected_state: Expected practice state

    Returns:
        Anomaly score (0.0 - 1.0)
    """
    score = 0.0
    indicators = []

    if not provider:
        return 0.0

    addresses = provider.get("addresses", [])
    taxonomies = provider.get("taxonomies", [])

    # Get all states from addresses
    address_states = set()
    for addr in addresses:
        if addr.get("state"):
            address_states.add(addr.get("state"))

    # Get all license states
    license_states = set()
    for tax in taxonomies:
        if tax.get("state"):
            license_states.add(tax.get("state"))

    # No address in expected state
    if expected_state not in address_states:
        score += 0.4
        indicators.append("no_address_in_expected_state")

    # License in different state than practice
    if license_states and address_states:
        if not license_states.intersection(address_states):
            score += 0.3
            indicators.append("license_address_mismatch")

    # Multiple distant states
    if len(address_states) > 2:
        score += 0.2
        indicators.append("multiple_state_addresses")

    # Cap at 1.0
    score = min(score, 1.0)

    emit_receipt("nppes_address_anomaly", {
        "tenant_id": TENANT_ID,
        "npi": provider.get("npi", "unknown"),
        "expected_state": expected_state,
        "address_states": list(address_states),
        "license_states": list(license_states),
        "anomaly_score": score,
        "indicators": indicators,
        "flagged": score >= 0.5
    })

    return score


def bulk_verify_providers(npis: list[str], expected_state: str = "OH") -> list[dict]:
    """
    Batch verify multiple providers.

    Args:
        npis: List of NPI numbers
        expected_state: Expected practice state

    Returns:
        List of verification results
    """
    results = []
    flagged_count = 0

    for npi in npis:
        result = verify_provider(npi, expected_state)
        results.append(result)
        if not result["verified"]:
            flagged_count += 1

    emit_receipt("nppes_bulk_verify", {
        "tenant_id": TENANT_ID,
        "total_npis": len(npis),
        "verified_count": len(npis) - flagged_count,
        "flagged_count": flagged_count,
        "expected_state": expected_state
    })

    return results
