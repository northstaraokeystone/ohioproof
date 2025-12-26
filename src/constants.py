"""
OhioProof Constants - Triple-verified, source-cited fraud values and thresholds.

Receipt: ohioproof_constants
Gate: t2h
"""

# ═══════════════════════════════════════════════════════════════════
# OHIO FRAUD VERIFIED VALUES (triple-checked, source-cited)
# ═══════════════════════════════════════════════════════════════════

# HB6/FirstEnergy (DOJ court documents)
HB6_BRIBERY_AMOUNT = 60_000_000  # $60M proven bribery
HB6_RATEPAYER_BAILOUT = 1_300_000_000  # $1.3B bailout
HOUSEHOLDER_SENTENCE_YEARS = 20  # June 2023 sentence
RANDAZZO_PAYMENT = 4_300_000  # $4.3M PUCO Chair received
FIRSTENERGY_DOJ_FINE = 230_000_000  # Criminal fine
FIRSTENERGY_SEC_SETTLEMENT = 100_000_000  # SEC settlement
FIRSTENERGY_PUCO_SETTLEMENT = 275_000_000  # Dec 2025 customer settlement

# Medicaid Concurrent Enrollment (Ohio Auditor March 2024)
MEDICAID_CONCURRENT_INDIVIDUALS = 124_448  # 3+ month overlap
MEDICAID_CHRONIC_CONCURRENT = 2_372  # Every month for 4 years
MEDICAID_ESTIMATED_IMPROPER = 209_000_000  # Ohio Auditor estimate
MEDICAID_CAPITATION_AT_RISK = 1_000_000_000  # Broader estimate

# JobsOhio (Auditor Dec 2024 report)
JOBSOHIO_FAILURE_RATE = 0.65  # 65% missed targets
JOBSOHIO_COMPANIES_AUDITED = 60
JOBSOHIO_COMPANIES_FAILED = 39
INTEL_INCENTIVE = 2_000_000_000  # $2B+ for 3,000 jobs
GM_LORDSTOWN_CLAWBACK = 28_000_000  # Precedent clawback

# STRS Ohio (ACFR June 2024)
STRS_FUND_SIZE = 96_900_000_000  # $96.9B
STRS_FUNDED_RATIO = 0.825  # 82.5%
STRS_ALLEGED_STEERING = 65_000_000_000  # AG lawsuit allegation

# Pandemic Unemployment (Auditor reports)
PANDEMIC_FRAUD_TOTAL = 6_900_000_000  # $6.9B identified
PANDEMIC_CONFIRMED_FRAUD = 1_000_000_000  # $1B+ to fraudsters
PANDEMIC_RECOVERED = 400_000_000  # ~$400M recovered

# ECOT Charter (June 2022 judgment)
ECOT_FINDING_FOR_RECOVERY = 117_000_000  # $117M FFR
ECOT_CIVIL_JUDGMENTS = 161_600_000  # Total civil
ECOT_TOTAL_RECEIVED = 1_000_000_000  # ~$1B over 18 years

# ═══════════════════════════════════════════════════════════════════
# DETECTION THRESHOLDS (from comparable systems)
# ═══════════════════════════════════════════════════════════════════

# Compression-based fraud detection
COMPRESSION_RATIO_LEGITIMATE = 0.50  # Normal transactions
COMPRESSION_RATIO_SUSPICIOUS = 0.75  # Flag for review
COMPRESSION_RATIO_FRAUDULENT = 0.90  # High confidence fraud

# Growth rate (from Minnesota FOF)
GROWTH_RATE_ALERT = 5.0  # 500% triggers review
GROWTH_RATE_CRITICAL = 28.0  # 2800% (FOF pattern)

# Anomaly detection (per GAO guidance)
FALSE_POSITIVE_MAX = 0.15  # 15% false positive budget
PRECISION_MIN = 0.80  # 80% precision target

# Cross-database correlation
CORRELATION_THRESHOLD = 0.70  # Flag if correlation > 0.70
MEDICAID_CONCURRENT_MONTHS = 3  # Flag after 3+ months overlap

# ═══════════════════════════════════════════════════════════════════
# DATA SOURCE CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

DATA_SOURCES = {
    "ohio_checkbook": {
        "url": "https://checkbook.ohio.gov",
        "type": "scrape_csv",
        "has_api": False,
        "transactions": 112_000_000,
        "total_value": 400_000_000_000
    },
    "usaspending": {
        "url": "https://api.usaspending.gov",
        "type": "rest_api",
        "has_api": True,
        "docs": "https://api.usaspending.gov/docs/endpoints"
    },
    "propublica": {
        "url": "https://projects.propublica.org/nonprofits/api/v2",
        "type": "rest_api",
        "has_api": True
    },
    "nppes": {
        "url": "https://npiregistry.cms.hhs.gov",
        "type": "rest_api",
        "has_api": True,
        "bulk_csv": True
    },
    "campaign_finance": {
        "url": "https://ohiosos.gov",
        "type": "searchable_web",
        "has_api": False,
        "years_available": 6
    },
    "lobbying": {
        "url": "https://jlec-olig.state.oh.us",
        "type": "searchable_web",
        "has_api": False
    },
    "puco": {
        "url": "https://dis.puc.state.oh.us",
        "type": "document_system",
        "has_api": False,
        "format": "pdf"
    }
}

# ═══════════════════════════════════════════════════════════════════
# VIVEK/DOGE ALIGNMENT
# ═══════════════════════════════════════════════════════════════════

DOGE_PRIORITIES = {
    "medicaid_improper": 89_300_000_000,  # FY2024 national
    "covid_fraud": 200_000_000_000,  # National estimate
    "unauthorized_spending": 516_000_000_000  # FY2024 national
}

VIVEK_QUOTES = {
    "data_silos": "Information is siloed in different houses... don't even operate on same kind of code",
    "program_integrity": "Program integrity issues... could add up to probably hundreds of billions of dollars in savings",
    "half_trillion": "Waste, fraud, abuse, error, or program integrity issues account for roughly half a trillion dollars"
}

# ═══════════════════════════════════════════════════════════════════
# SLO THRESHOLDS
# ═══════════════════════════════════════════════════════════════════

SLO_THRESHOLDS = {
    "ingest_latency_ms": 60000,  # ≤60s per 10K records
    "parse_accuracy": 0.999,  # ≥99.9%
    "detection_latency_ms": 5000,  # ≤5s per 10K transactions
    "false_positive_rate": 0.15,  # ≤15%
    "precision": 0.80,  # ≥80%
    "correlation_score": 0.70,  # ≥0.70 for flag
    "growth_alert_rate": 5.0,  # ≥500%
    "medicaid_alert_hours": 24,  # ≤24h from data refresh
    "jobsohio_verification_days": 90,  # Quarterly
    "dashboard_freshness_days": 7,  # ≤7 days
}
