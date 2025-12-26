#!/bin/bash
# gate_t24h.sh - T+24h MVP Gate
# RUN THIS OR KILL PROJECT

set -e

echo "=== OhioProof T+24h Gate Check ==="

# Run tests
echo "Running tests..."
python -m pytest tests/ -q --tb=short || { echo "FAIL: tests failed"; exit 1; }
echo "  ✓ Tests pass"

# Check emit_receipt in src files
echo "Checking emit_receipt usage..."
grep -rq "emit_receipt" src/*.py 2>/dev/null || grep -rq "emit_receipt" src/**/*.py || { echo "FAIL: no receipts in src"; exit 1; }
echo "  ✓ emit_receipt found in src"

# Check assertions in tests
echo "Checking test assertions..."
grep -rq "assert" tests/*.py 2>/dev/null || grep -rq "assert" tests/**/*.py || { echo "FAIL: no assertions in tests"; exit 1; }
echo "  ✓ Assertions found in tests"

# Check ingest modules
echo "Checking ingest modules..."
python -c "from src.ingest import fetch_transactions; print('  ✓ ohio_checkbook loads')"
python -c "from src.ingest import fetch_awards; print('  ✓ usaspending loads')"
python -c "from src.ingest import fetch_org; print('  ✓ propublica loads')"

# Check detect modules
echo "Checking detect modules..."
python -c "from src.detect import compute_entropy; print('  ✓ anomaly loads')"
python -c "from src.detect import compute_compression; print('  ✓ compression loads')"
python -c "from src.detect import load_pattern; print('  ✓ patterns loads')"

# Check domain modules
echo "Checking domain modules..."
python -c "from src.domains.medicaid import detect_concurrent; print('  ✓ medicaid loads')"
python -c "from src.domains.jobsohio import verify_employment; print('  ✓ jobsohio loads')"
python -c "from src.domains.hb6 import scan_501c4; print('  ✓ hb6 loads')"

echo ""
echo "=== PASS: T+24h gate ==="
echo "MVP is functional. Proceed to T+48h."
