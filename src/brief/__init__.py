"""
OhioProof Brief Modules - Evidence synthesis and decision health.

Purpose:
    - synthesize: Evidence synthesis
    - health: Decision health scoring
    - dialectic: PRO/CON analysis

Receipt: brief_receipt
Gate: t36h
"""

from src.brief.synthesize import (
    synthesize_evidence,
    generate_brief,
    summarize_findings
)
from src.brief.health import (
    compute_decision_health,
    score_strength,
    score_coverage,
    score_efficiency
)
from src.brief.dialectic import (
    analyze_dialectic,
    generate_pro_con,
    identify_gaps
)

__all__ = [
    # synthesize
    "synthesize_evidence", "generate_brief", "summarize_findings",
    # health
    "compute_decision_health", "score_strength", "score_coverage", "score_efficiency",
    # dialectic
    "analyze_dialectic", "generate_pro_con", "identify_gaps",
]
