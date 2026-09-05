import re
import asyncio
from typing import Optional

from .base import BaseAgent
from tools.registry import UnifiedToolRegistry, get_registry
from tools.executor import run_tool


class PhaseAgent(BaseAgent):
    """Generic agent that runs all tools for a given phase.

    Scans the task for the target, looks up every tool registered
    for *phase* in the ToolRegistry, and executes them concurrently.
    Results are aggregated into a single dict.
    """

    def __init__(self, phase: str, context: Optional[dict] = None):
        super().__init__(context)
        self._phase = phase
        self._registry = get_registry()

    @property
    def name(self) -> str:
        return self._phase

    @property
    def phase(self) -> str:
        return self._phase

    async def run(self, task: str) -> dict:
        target = self._extract_target(task)

        # Inherit context from previous phases
        if self.context.get("previous_results"):
            target = self.context["previous_results"].get("target") or target

        tools = self._registry.get_tools_by_phase(self._phase)
        if not tools:
            return {
                "phase": self._phase,
                "target": target,
                "status": "skipped",
                "tools_used": [],
                "results": [],
                "findings": [],
            }

        tool_names = [t.name for t in tools]
        results = await asyncio.gather(
            *(run_tool(t.name, target) for t in tools),
            return_exceptions=True,
        )

        processed = []
        for r in results:
            if isinstance(r, Exception):
                processed.append({"tool": "unknown", "status": "exception", "error": str(r)})
            else:
                processed.append(r)

        return {
            "phase": self._phase,
            "target": target,
            "status": "completed",
            "tools_used": tool_names,
            "results": processed,
            "findings": self._extract_findings(processed),
        }

    def _extract_findings(self, results: list[dict]) -> list[dict]:
        findings = []
        for r in results:
            if r.get("status") != "success":
                continue
            parsed = r.get("parsed", {})
            if isinstance(parsed, dict):
                # nmap-style
                for port in parsed.get("open_ports", []):
                    findings.append({
                        "type": "open_port",
                        "tool": r["tool"],
                        "detail": f"{port['service']} on port {port['port']}/{port['protocol']}",
                        "severity": "info",
                    })
                # sqlmap-style
                if parsed.get("vulnerable"):
                    for point in parsed.get("injection_points", []):
                        findings.append({
                            "type": "sql_injection",
                            "tool": r["tool"],
                            "detail": f"SQLi on param '{point['parameter']}' ({point['type']})",
                            "severity": "critical",
                        })
                # theHarvester-style
                for email in parsed.get("emails", []):
                    findings.append({
                        "type": "exposed_email",
                        "tool": r["tool"],
                        "detail": f"Email: {email}",
                        "severity": "medium",
                    })
                # john/hashcat-style
                for cred in parsed.get("cracked", []):
                    findings.append({
                        "type": "cracked_credential",
                        "tool": r["tool"],
                        "detail": f"{cred.get('username', cred.get('hash', '?'))}:{cred.get('password', '?')}",
                        "severity": "high",
                    })
                # hydra-style
                if isinstance(parsed, list):
                    for cred in parsed:
                        if isinstance(cred, dict) and "username" in cred and "password" in cred:
                            findings.append({
                            "type": "weak_credential",
                            "tool": r["tool"],
                            "detail": f"Login {cred['username']}:{cred['password']} on {r['tool']}",
                            "severity": "critical",
                        })
            elif isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and "finding" in item:
                        findings.append({
                            "type": "vulnerability",
                            "tool": r["tool"],
                            "detail": item["finding"],
                            "severity": "high",
                        })
        return findings

    @staticmethod
    def _extract_target(task: str) -> str:
        for prefix in ["for ", "on ", "against ", "target "]:
            if prefix in task:
                return task.split(prefix)[-1].strip().split()[0]
        return task.split()[-1]
