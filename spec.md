# OhioProof v1 Specification

## Overview

OhioProof is a receipts-native accountability system targeting $8B+ in verified Ohio government fraud/waste across 6 domains.

**Physics:** Fraudulent transactions are high-entropy (don't compress). Legitimate operations are low-entropy (compress efficiently).

**Target Audience:** Vivek Ramaswamy (Ohio Governor candidate, DOGE co-founder) and DOGE team.

## Inputs

| Source | URL | Type | Coverage |
|--------|-----|------|----------|
| Ohio Checkbook | checkbook.ohio.gov | CSV scrape | $400B, 112M transactions |
| USASpending | api.usaspending.gov | REST API | Federal awards to Ohio |
| ProPublica | projects.propublica.org/nonprofits | REST API | 501(c) 990s |
| NPPES | npiregistry.cms.hhs.gov | REST API + CSV | Provider NPIs |
| Campaign Finance | ohiosos.gov | Web scrape | 6 years contributions |
| OLAC Lobbying | jlec-olig.state.oh.us | Web scrape | Registered lobbyists |
| PUCO DIS | dis.puc.state.oh.us | Document system | Utility filings (PDF) |

## Outputs

### Receipts (append-only ledger)
- `ingest_receipt`: Data ingestion confirmation
- `anomaly_receipt`: Detected anomalies
- `compression_receipt`: Compression ratio scores
- `correlation_receipt`: Cross-database matches
- `pattern_match_receipt`: Known fraud pattern matches
- `anchor_receipt`: Merkle tree anchors

### Domain Receipts
- `medicaid_enrollment_receipt`: Enrollment verification
- `medicaid_anomaly_receipt`: Concurrent enrollment flags
- `jobsohio_commitment_receipt`: Job creation promises
- `jobsohio_verification_receipt`: Delivery verification
- `jobsohio_clawback_receipt`: Clawback calculations
- `dark_money_scan_receipt`: 501(c)(4) analysis
- `legislative_correlation_receipt`: Contribution-vote correlation
- `strs_investment_receipt`: Pension investment analysis
- `strs_governance_receipt`: Board governance tracking
- `pandemic_fraud_receipt`: Unemployment fraud detection
- `charter_enrollment_receipt`: Charter school verification
- `charter_attendance_receipt`: Attendance anomaly detection

### Decision Outputs
- `brief_receipt`: Evidence synthesis
- `packet_receipt`: Decision packet assembly
- `referral_receipt`: Agency referral generation
- `dashboard_receipt`: Public dashboard updates

## Receipt Schema

```json
{
  "receipt_type": "string",
  "ts": "ISO8601",
  "tenant_id": "ohioproof",
  "payload_hash": "SHA256:BLAKE3"
}
```

## SLOs (Service Level Objectives)

| SLO | Threshold | Test Assertion | Stoprule Action |
|-----|-----------|----------------|-----------------|
| Ingest Latency | ≤60s/10K records | `assert latency_ms <= 60000` | retry 3x, then halt |
| Parse Accuracy | ≥99.9% | `assert accuracy >= 0.999` | halt + review |
| Detection Latency | ≤5s/10K transactions | `assert latency_ms <= 5000` | log warning |
| False Positive Rate | ≤15% | `assert fp_rate <= 0.15` | adjust threshold |
| Precision | ≥80% | `assert precision >= 0.80` | retrain model |
| Correlation Score | ≥0.70 for flag | `assert score >= 0.70` | human review |
| Growth Alert | ≥500% | `assert rate < 5.0 OR alert` | escalate |
| Medicaid Alert | ≤24h from data refresh | `assert latency_hours <= 24` | escalate |
| JobsOhio Verification | Quarterly | `assert days_since_last <= 90` | manual trigger |
| Dashboard Freshness | ≤7 days | `assert days_stale <= 7` | alert |

## Stoprules

1. **stoprule_hash_mismatch**: Emit anomaly, halt on hash verification failure
2. **stoprule_invalid_receipt**: Emit anomaly, halt on malformed receipt
3. **stoprule_data_source_unavailable**: Emit anomaly, retry 3x, then halt
4. **stoprule_bias**: Emit anomaly, halt if disparity >= 0.5%
5. **stoprule_precision_degradation**: Emit anomaly, halt if precision < 50%

## Rollback Procedures

1. **Data Rollback**: Restore from last known-good ledger snapshot
2. **Model Rollback**: Revert to previous pattern definitions
3. **Threshold Rollback**: Restore previous SLO thresholds
4. **Full Rollback**: Complete system restore from MANIFEST.anchor

## Target Domains

| Domain | Verified Fraud | Priority |
|--------|---------------|----------|
| Medicaid Concurrent Enrollment | $1B+ | P0 |
| JobsOhio Economic Development | $1B+ waste | P0 |
| FirstEnergy/HB6 Dark Money | $60M bribery | P1 |
| STRS Pension | TBD (investigation) | P1 |
| Pandemic Unemployment | $6.9B | P2 |
| Charter School (ECOT-pattern) | $117M+ | P2 |

## Verified Fraud Values

- HB6 Bribery: $60,000,000
- Medicaid Concurrent (3+ months): 124,448 individuals
- Medicaid Chronic (48 months): 2,372 individuals
- JobsOhio Failure Rate: 65%
- Pandemic Fraud: $6,900,000,000
- ECOT Finding for Recovery: $117,000,000

## Detection Thresholds

- Compression Ratio (Legitimate): 0.50
- Compression Ratio (Suspicious): 0.75
- Compression Ratio (Fraudulent): 0.90
- Growth Rate Alert: 500%
- Growth Rate Critical: 2800%
- Correlation Threshold: 0.70

## Gate Timeline

- **T+2h**: Skeleton (spec.md, ledger_schema.json, cli.py)
- **T+8h**: Ingest modules operational
- **T+16h**: Detect modules operational
- **T+24h**: Domain modules operational (parallel)
- **T+36h**: Output modules operational
- **T+48h**: Hardened (watchdog, stoprules, tests)
