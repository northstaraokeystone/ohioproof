"""
Pytest configuration and fixtures for OhioProof tests.
"""

import json
import os
import sys
import tempfile

import pytest

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def sample_transaction():
    """Sample transaction for testing."""
    return {
        "vendor_id": "V001",
        "vendor_name": "Test Vendor LLC",
        "amount": 50000.00,
        "date": "2024-01-15",
        "agency": "ODOT",
        "program": "Highway Construction"
    }


@pytest.fixture
def sample_transactions():
    """List of sample transactions."""
    return [
        {
            "vendor_id": "V001",
            "vendor_name": "Test Vendor LLC",
            "amount": 50000.00,
            "date": "2024-01-15",
            "agency": "ODOT"
        },
        {
            "vendor_id": "V002",
            "vendor_name": "Healthcare Inc",
            "amount": 100000.00,
            "date": "2024-01-20",
            "agency": "ODM"
        },
        {
            "vendor_id": "V003",
            "vendor_name": "Construction Corp",
            "amount": 75000.00,
            "date": "2024-01-25",
            "agency": "ODOT"
        }
    ]


@pytest.fixture
def sample_enrollee():
    """Sample Medicaid enrollee."""
    return {
        "id": "ENR001",
        "address": {"state": "OH", "city": "Columbus"},
        "enrollment_months": 12,
        "provider_npi": "1234567890",
        "monthly_capitation": 500
    }


@pytest.fixture
def sample_501c4():
    """Sample 501(c)(4) organization."""
    return {
        "ein": "123456789",
        "name": "Test Political Action",
        "subsection_code": "501(c)(4)",
        "state": "OH",
        "ruling_date": "2018-01",
        "revenue_amount": 5000000,
        "total_receipts": 5000000,
        "donor_disclosure_rate": 0.05,
        "political_expenditure_pct": 0.6
    }


@pytest.fixture
def sample_school():
    """Sample charter school."""
    return {
        "name": "Virtual Academy Ohio",
        "type": "virtual",
        "claimed_enrollment": 1000,
        "verified_enrollment": 800,
        "claimed_attendance_hours": 10000,
        "actual_login_hours": 4000,
        "per_pupil_funding": 7000,
        "founders": ["John Smith"],
        "board_members": ["Jane Doe"]
    }


@pytest.fixture
def temp_ledger():
    """Create temporary ledger file."""
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def sample_receipts():
    """Sample receipts for testing."""
    return [
        {
            "receipt_type": "ingest",
            "ts": "2024-01-15T10:00:00Z",
            "tenant_id": "ohioproof",
            "payload_hash": "abc123:def456",
            "source": "ohio_checkbook"
        },
        {
            "receipt_type": "anomaly",
            "ts": "2024-01-15T10:05:00Z",
            "tenant_id": "ohioproof",
            "payload_hash": "ghi789:jkl012",
            "metric": "entropy",
            "flagged": True
        },
        {
            "receipt_type": "correlation",
            "ts": "2024-01-15T10:10:00Z",
            "tenant_id": "ohioproof",
            "payload_hash": "mno345:pqr678",
            "correlation_score": 0.85
        }
    ]
