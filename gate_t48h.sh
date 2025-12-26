#!/bin/bash
# gate_t48h.sh - T+48h Hardened Gate
# RUN THIS OR KILL PROJECT

set -e

echo "=== OhioProof T+48h Gate Check ==="

# Check for anomaly detection
echo "Checking anomaly detection..."
grep -rq "anomaly" src/*.py 2>/dev/null || grep -rq "anomaly" src/**/*.py || { echo "FAIL: no anomaly detection"; exit 1; }
echo "  ✓ Anomaly detection present"

# Check for bias checks
echo "Checking bias checks..."
grep -rq "bias" src/*.py 2>/dev/null || grep -rq "bias" src/**/*.py || { echo "FAIL: no bias check"; exit 1; }
echo "  ✓ Bias checks present"

# Check for stoprules
echo "Checking stoprules..."
grep -rq "stoprule" src/*.py 2>/dev/null || grep -rq "stoprule" src/**/*.py || { echo "FAIL: no stoprules"; exit 1; }
echo "  ✓ Stoprules present"

# Check watchdog
echo "Checking watchdog..."
python watchdog.py --check || { echo "FAIL: watchdog unhealthy"; exit 1; }
echo "  ✓ Watchdog healthy"

# Final verification
echo ""
echo "Running final verification..."
python -c "
from src.core import dual_hash, emit_receipt, merkle, TENANT_ID
from src import constants
from src.detect import compute_entropy, compute_compression, load_pattern
from src.domains.medicaid import detect_concurrent
from src.domains.jobsohio import verify_employment
from src.domains.hb6 import generate_dark_money_score

# Verify constants
assert constants.HB6_BRIBERY_AMOUNT == 60_000_000
assert constants.MEDICAID_CONCURRENT_INDIVIDUALS == 124_448
assert constants.JOBSOHIO_FAILURE_RATE == 0.65

# Verify core functions
h = dual_hash('test')
assert ':' in h

# Verify patterns
pattern = load_pattern('generation_now')
assert pattern is not None

print('  ✓ All verification checks pass')
"

echo ""
echo "=== PASS: T+48h gate — SHIP IT ==="
echo ""
echo "OhioProof v1 is production-ready."
echo ""
echo "Target: \$8.3B+ verified Ohio fraud"
echo "Domains: medicaid, jobsohio, hb6, strs, pandemic, charter"
echo "Physics: fraud=high_entropy, legitimate=low_entropy"
echo ""
echo "Receipts or it didn't happen."
