"""
Export Module

Purpose: Export reports in various formats

Receipt: export_receipt
Gate: t36h
"""

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any

from src.core import emit_receipt, TENANT_ID


def export_report(
    data: dict,
    format: str = "json",
    filename: str | None = None
) -> str:
    """
    Export report in specified format.

    Args:
        data: Report data
        format: Output format (json, csv, markdown)
        filename: Optional filename

    Returns:
        Formatted report string
    """
    if format == "json":
        output = export_json(data)
    elif format == "csv":
        output = export_csv(data)
    elif format == "markdown":
        output = export_markdown(data)
    else:
        output = export_json(data)

    emit_receipt("export", {
        "tenant_id": TENANT_ID,
        "format": format,
        "filename": filename,
        "size_bytes": len(output)
    })

    return output


def export_json(data: dict) -> str:
    """
    Export data as JSON.

    Args:
        data: Data to export

    Returns:
        JSON string
    """
    return json.dumps(data, indent=2, default=str)


def export_csv(data: dict) -> str:
    """
    Export data as CSV.

    Args:
        data: Data to export (expects list of dicts or dict with lists)

    Returns:
        CSV string
    """
    output = io.StringIO()

    # Handle different data structures
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        # Try to find a list to export
        for key, value in data.items():
            if isinstance(value, list) and value:
                rows = value
                break
        else:
            # Convert dict to single row
            rows = [data]
    else:
        rows = []

    if not rows:
        return ""

    # Get all keys from all rows
    keys = set()
    for row in rows:
        if isinstance(row, dict):
            keys.update(row.keys())

    keys = sorted(keys)

    writer = csv.DictWriter(output, fieldnames=keys)
    writer.writeheader()

    for row in rows:
        if isinstance(row, dict):
            writer.writerow(row)

    return output.getvalue()


def export_markdown(data: dict) -> str:
    """
    Export data as Markdown.

    Args:
        data: Data to export

    Returns:
        Markdown string
    """
    lines = []

    # Title
    title = data.get("title", "OhioProof Report")
    lines.append(f"# {title}")
    lines.append("")

    # Generated timestamp
    ts = data.get("generated_ts", datetime.now(timezone.utc).isoformat())
    lines.append(f"*Generated: {ts}*")
    lines.append("")

    # Summary section
    if "summary" in data:
        lines.append("## Summary")
        lines.append("")
        for key, value in data["summary"].items():
            lines.append(f"- **{key.replace('_', ' ').title()}**: {value}")
        lines.append("")

    # Domain sections
    if "domains" in data:
        lines.append("## Domains")
        lines.append("")
        for domain, info in data["domains"].items():
            lines.append(f"### {domain.upper()}")
            if isinstance(info, dict):
                for key, value in info.items():
                    if key not in ["name", "description"]:
                        lines.append(f"- {key}: {value}")
            lines.append("")

    # Metrics section
    if "metrics" in data:
        lines.append("## Metrics")
        lines.append("")
        for key, value in data["metrics"].items():
            lines.append(f"- **{key}**: {value}")
        lines.append("")

    return "\n".join(lines)


def generate_fraud_report(
    domain: str | None = None
) -> dict:
    """
    Generate comprehensive fraud report.

    Args:
        domain: Optional domain filter

    Returns:
        Fraud report data
    """
    from src.constants import (
        HB6_BRIBERY_AMOUNT,
        MEDICAID_CAPITATION_AT_RISK,
        PANDEMIC_FRAUD_TOTAL,
        ECOT_FINDING_FOR_RECOVERY
    )

    report = {
        "title": f"OhioProof Fraud Report{f' - {domain.upper()}' if domain else ''}",
        "generated_ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "summary": {
            "total_verified_fraud": (
                HB6_BRIBERY_AMOUNT +
                MEDICAID_CAPITATION_AT_RISK +
                PANDEMIC_FRAUD_TOTAL +
                ECOT_FINDING_FOR_RECOVERY
            )
        },
        "domains": {
            "hb6": {
                "name": "HB6/FirstEnergy Dark Money",
                "amount": HB6_BRIBERY_AMOUNT,
                "status": "convicted"
            },
            "medicaid": {
                "name": "Medicaid Concurrent Enrollment",
                "amount_at_risk": MEDICAID_CAPITATION_AT_RISK,
                "status": "monitoring"
            },
            "pandemic": {
                "name": "Pandemic Unemployment",
                "amount": PANDEMIC_FRAUD_TOTAL,
                "status": "recovery"
            },
            "charter": {
                "name": "Charter Schools (ECOT)",
                "amount": ECOT_FINDING_FOR_RECOVERY,
                "status": "judgment"
            }
        }
    }

    if domain and domain in report["domains"]:
        report["domains"] = {domain: report["domains"][domain]}

    emit_receipt("fraud_report_generation", {
        "tenant_id": TENANT_ID,
        "domain": domain,
        "total_verified": report["summary"]["total_verified_fraud"]
    })

    return report


def save_export(
    content: str,
    filepath: str
) -> bool:
    """
    Save export to file.

    Args:
        content: Content to save
        filepath: Output path

    Returns:
        True if saved successfully
    """
    try:
        with open(filepath, "w") as f:
            f.write(content)

        emit_receipt("export_save", {
            "tenant_id": TENANT_ID,
            "filepath": filepath,
            "size_bytes": len(content),
            "success": True
        })

        return True
    except Exception as e:
        emit_receipt("export_save", {
            "tenant_id": TENANT_ID,
            "filepath": filepath,
            "success": False,
            "error": str(e)
        })
        return False
