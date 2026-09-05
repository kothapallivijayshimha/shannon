import json
from datetime import datetime, timezone
from typing import Optional

from .base import BaseAgent
from database import get_phase_results


class ReportAgent(BaseAgent):
    """Generates structured security reports from real phase results."""

    name = "report"
    phase = "forensics"

    def __init__(self, context: Optional[dict] = None):
        super().__init__(context)

    async def run(self, task: str) -> dict:
        phase_results = self.context.get("phase_results", {})

        # Fallback: fetch from DB if running standalone
        if not phase_results:
            target = task.split()[-1]
            phase_results = get_phase_results(target)

        return {
            "agent": "report",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "executive_summary": self._generate_summary(phase_results),
            "phases": self._compile_phases(phase_results),
            "findings": self._extract_findings(phase_results),
            "statistics": self._compute_stats(phase_results),
            "recommendations": self._generate_recommendations(phase_results),
            "raw_data": phase_results,
        }

    def _generate_summary(self, results: dict) -> str:
        findings = self._extract_findings(results)
        critical = sum(1 for f in findings if f.get("severity") == "critical")
        high = sum(1 for f in findings if f.get("severity") == "high")
        medium = sum(1 for f in findings if f.get("severity") == "medium")
        total_phases = sum(1 for v in results.values() if isinstance(v, dict) and v.get("status") == "completed")

        return (
            f"Assessment completed across {total_phases} phase(s). "
            f"Total findings: {len(findings)} "
            f"(Critical: {critical}, High: {high}, Medium: {medium}). "
            f"See detailed breakdown below for remediation guidance."
        )

    def _compile_phases(self, results: dict) -> list:
        phases = []
        for phase_name, data in results.items():
            if not isinstance(data, dict):
                continue
            phases.append({
                "phase": phase_name,
                "status": data.get("status", "unknown"),
                "tools_used": data.get("tools_used", []),
                "findings_count": len(data.get("findings", [])),
            })
        return phases

    def _extract_findings(self, results: dict) -> list:
        seen = set()
        findings = []
        for data in results.values():
            if not isinstance(data, dict):
                continue
            for finding in data.get("findings", []):
                key = json.dumps(finding, sort_keys=True)
                if key not in seen:
                    seen.add(key)
                    findings.append(finding)
        return findings

    def _compute_stats(self, results: dict) -> dict:
        findings = self._extract_findings(results)
        severity_counts = {}
        for f in findings:
            sev = f.get("severity", "unknown")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        return {
            "total_phases": sum(1 for v in results.values() if isinstance(v, dict)),
            "total_tools_invoked": sum(
                len(d.get("tools_used", []))
                for d in results.values() if isinstance(d, dict)
            ),
            "total_findings": len(findings),
            "severity_breakdown": severity_counts,
        }

    def _generate_recommendations(self, results: dict) -> list:
        recs = []
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        findings = self._extract_findings(results)
        findings.sort(key=lambda f: severity_order.get(f.get("severity", "low"), 99))

        for f in findings:
            ftype = f.get("type", "")
            detail = f.get("detail", "")
            severity = f.get("severity", "low")

            if ftype == "open_port":
                recs.append(f"[{severity.upper()}] Restrict access to exposed service: {detail}")
            elif ftype == "sql_injection":
                recs.append(f"[{severity.upper()}] Parameterize queries to fix: {detail}")
            elif ftype == "exposed_email":
                recs.append(f"[{severity.upper()}] Remove exposed email from public sources: {detail}")
            elif ftype == "cracked_credential":
                recs.append(f"[{severity.upper()}] Enforce strong password policy for: {detail}")
            elif ftype == "weak_credential":
                recs.append(f"[{severity.upper()}] Change default/weak credentials: {detail}")
            elif ftype == "vulnerability":
                recs.append(f"[{severity.upper()}] Investigate and patch: {detail}")
            else:
                recs.append(f"[{severity.upper()}] Review: {detail}")

        return recs[:15]
