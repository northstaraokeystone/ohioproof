"""
OhioProof Detection Modules - Entropy-based anomaly detection.

Modeled on US Treasury's ML system ($4B savings FY2024).

Physics:
    - Legitimate transactions: LOW entropy (compression ratio 0.30-0.60)
    - Fraudulent transactions: HIGH entropy (compression ratio 0.70-0.95)
    - Cross-correlation AMPLIFIES signal

Modules:
    - anomaly: Core entropy-based anomaly detection
    - compression: Compression ratio as fraud signal (QED paradigm)
    - correlation: Cross-database correlation for signal amplification
    - patterns: Known fraud pattern library
    - growth: Growth rate anomaly detection (2800% FOF trigger)

Receipt: detect_module_init
Gate: t16h
"""

from src.detect.anomaly import (
    compute_entropy,
    detect_anomaly,
    classify_anomaly,
    emit_anomaly
)
from src.detect.compression import (
    compute_compression,
    score_transaction_set,
    flag_high_entropy
)
from src.detect.correlation import (
    correlate_vendor,
    correlate_payment_lobbying,
    correlate_contribution_vote,
    correlate_enrollment
)
from src.detect.patterns import (
    load_pattern,
    match_pattern,
    list_patterns
)
from src.detect.growth import (
    compute_growth_rate,
    flag_explosive_growth,
    detect_onboarding_velocity
)

__all__ = [
    # anomaly
    "compute_entropy", "detect_anomaly", "classify_anomaly", "emit_anomaly",
    # compression
    "compute_compression", "score_transaction_set", "flag_high_entropy",
    # correlation
    "correlate_vendor", "correlate_payment_lobbying",
    "correlate_contribution_vote", "correlate_enrollment",
    # patterns
    "load_pattern", "match_pattern", "list_patterns",
    # growth
    "compute_growth_rate", "flag_explosive_growth", "detect_onboarding_velocity",
]
