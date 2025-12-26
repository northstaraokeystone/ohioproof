"""
OhioProof Dashboard Modules - Public accountability views.

Purpose:
    - public: Public accountability views
    - metrics: KPI calculations
    - export: Report generation

Receipt: dashboard_receipt
Gate: t36h
"""

from src.dashboard.public import (
    generate_public_dashboard,
    get_domain_summary,
    get_fraud_overview
)
from src.dashboard.metrics import (
    compute_kpis,
    compute_domain_metrics,
    compute_trend_metrics
)
from src.dashboard.export import (
    export_report,
    export_csv,
    export_json
)

__all__ = [
    # public
    "generate_public_dashboard", "get_domain_summary", "get_fraud_overview",
    # metrics
    "compute_kpis", "compute_domain_metrics", "compute_trend_metrics",
    # export
    "export_report", "export_csv", "export_json",
]
