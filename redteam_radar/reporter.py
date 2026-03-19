"""
Report generation — produces both JSON and human-readable text reports.
"""

import json
import textwrap
from datetime import datetime, timezone
from typing import Optional

from .scanner import ScanReport, ProbeResult


# ---------------------------------------------------------------------------
# JSON report
# ---------------------------------------------------------------------------

def to_json(report: ScanReport, indent: int = 2) -> str:
    """Serialize a ScanReport to JSON."""

    def result_to_dict(r: ProbeResult) -> dict:
        return {
            "probe_id": r.probe.id,
            "name": r.probe.name,
            "category": r.probe.category,
            "severity": r.probe.severity,
            "status": r.status,
            "is_vulnerable": r.detection.is_vulnerable,
            "confidence": round(r.detection.confidence, 3),
            "evidence": r.detection.evidence,
            "elapsed_ms": r.elapsed_ms,
            "payload": r.probe.payload,
            "response_preview": r.response[:300] + ("…" if len(r.response) > 300 else ""),
            "reproduction": {
                "description": r.probe.description,
                "endpoint": report.target_url,
                "style": report.style,
                "model": report.model,
                "payload": r.probe.payload,
            },
            "error": r.error,
        }

    doc = {
        "meta": {
            "tool": "agentic-redteam-radar",
            "version": "1.0.0",
            "target": report.target_url,
            "model": report.model,
            "style": report.style,
            "started_at": datetime.fromtimestamp(report.started_at, tz=timezone.utc).isoformat(),
            "finished_at": datetime.fromtimestamp(report.finished_at, tz=timezone.utc).isoformat(),
            "duration_s": round(report.duration_s, 2),
        },
        "summary": {
            "total_probes": report.total,
            "vulnerable": len(report.vulnerable),
            "safe": len(report.safe),
            "errors": len(report.errors),
            "vulnerability_rate": round(report.vulnerability_rate, 3),
            "risk_score": report.risk_score(),
            "by_category": report.by_category(),
            "by_severity": report.by_severity(),
        },
        "findings": [result_to_dict(r) for r in report.results if r.detection.is_vulnerable],
        "all_results": [result_to_dict(r) for r in report.results],
    }

    return json.dumps(doc, indent=indent, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Text report
# ---------------------------------------------------------------------------

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


def to_text(report: ScanReport) -> str:
    lines = []
    sep = "=" * 72
    thin = "-" * 72

    ts = datetime.fromtimestamp(report.started_at, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines += [
        sep,
        " AGENTIC REDTEAM RADAR — SCAN REPORT",
        sep,
        f" Target : {report.target_url}",
        f" Model  : {report.model}  (style: {report.style})",
        f" Date   : {ts}",
        f" Time   : {report.duration_s:.1f}s",
        "",
    ]

    # --- Summary ---
    risk = report.risk_score()
    risk_label = (
        "🔴 CRITICAL" if risk >= 70
        else "🟠 HIGH" if risk >= 40
        else "🟡 MEDIUM" if risk >= 20
        else "🟢 LOW"
    )
    vuln_count = len(report.vulnerable)
    total = report.total
    err_count = len(report.errors)

    lines += [
        " SUMMARY",
        thin,
        f"  Risk Score      : {risk}/100  {risk_label}",
        f"  Total Probes    : {total}",
        f"  Vulnerable      : {vuln_count}",
        f"  Safe            : {len(report.safe)}",
        f"  Errors          : {err_count}",
        f"  Vuln Rate       : {report.vulnerability_rate * 100:.1f}%",
        "",
    ]

    # --- By category ---
    lines.append(" BY CATEGORY")
    lines.append(thin)
    for cat, stats in sorted(report.by_category().items()):
        lines.append(
            f"  {cat:<24}  {stats['vulnerable']:>2} vuln / {stats['total']:>2} total"
        )
    lines.append("")

    # --- By severity ---
    sev = report.by_severity()
    lines.append(" FINDINGS BY SEVERITY")
    lines.append(thin)
    for s in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        count = sev.get(s, 0)
        bar = "█" * count
        lines.append(f"  {s:<10} {count:>2}  {bar}")
    lines.append("")

    # --- Findings ---
    if report.vulnerable:
        lines.append(" VULNERABILITY DETAILS")
        lines.append(thin)

        sorted_vulns = sorted(
            report.vulnerable,
            key=lambda r: SEVERITY_ORDER.get(r.probe.severity, 99),
        )

        for r in sorted_vulns:
            lines += [
                f"  [{r.probe.severity}] {r.probe.id}: {r.probe.name}",
                f"    Category : {r.probe.category}",
                f"    Confidence: {r.detection.confidence:.0%}",
                f"    Evidence :",
            ]
            for ev in r.detection.evidence:
                lines.append(f"      • {ev}")
            lines += [
                f"    Description:",
                *[f"      {ln}" for ln in textwrap.wrap(r.probe.description, 64)],
                f"    Reproduction Steps:",
                f"      1. POST to {report.target_url} (style={report.style}, model={report.model})",
                f"      2. Payload:",
                *[f"           {ln}" for ln in textwrap.wrap(r.probe.payload, 60)],
                f"      3. Response (first 200 chars):",
                f"           {r.response[:200]!r}",
                "",
            ]
    else:
        lines += ["  ✅ No vulnerabilities detected.", ""]

    if report.errors:
        lines.append(" PROBE ERRORS")
        lines.append(thin)
        for r in report.errors:
            lines.append(f"  {r.probe.id}: {r.error}")
        lines.append("")

    lines.append(sep)
    return "\n".join(lines)
