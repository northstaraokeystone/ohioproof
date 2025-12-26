#!/bin/bash
# gate_t2h.sh - T+2h Skeleton Gate
# RUN THIS OR KILL PROJECT

set -e

echo "=== OhioProof T+2h Gate Check ==="

# Check required files exist
echo "Checking required files..."

[ -f spec.md ] || { echo "FAIL: no spec.md"; exit 1; }
echo "  ✓ spec.md exists"

[ -f ledger_schema.json ] || { echo "FAIL: no ledger_schema.json"; exit 1; }
echo "  ✓ ledger_schema.json exists"

[ -f cli.py ] || { echo "FAIL: no cli.py"; exit 1; }
echo "  ✓ cli.py exists"

# Check cli.py emits receipt
echo "Checking cli.py emits receipt..."
python cli.py --test 2>&1 | grep -q '"receipt_type"' || { echo "FAIL: no receipt from cli.py"; exit 1; }
echo "  ✓ cli.py emits valid receipt"

# Check core module exists and works
echo "Checking core module..."
python -c "from src.core import dual_hash, emit_receipt, merkle; h=dual_hash('test'); assert ':' in h; print('  ✓ dual_hash works')"
python -c "from src.core import TENANT_ID; assert TENANT_ID == 'ohioproof'; print('  ✓ TENANT_ID correct')"

# Check constants
echo "Checking constants..."
python -c "from src.constants import HB6_BRIBERY_AMOUNT; assert HB6_BRIBERY_AMOUNT == 60_000_000; print('  ✓ constants loaded')"

echo ""
echo "=== PASS: T+2h gate ==="
echo "Skeleton is solid. Proceed to T+8h."
