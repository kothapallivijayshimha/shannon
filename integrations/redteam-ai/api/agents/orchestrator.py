import asyncio
from datetime import datetime, timezone
from typing import Optional

from .base import BaseAgent
from .phase_agent import PhaseAgent
from .report import ReportAgent
from database import save_phase_result

# Ordered multi-phase pipeline definition
PIPELINE = [
    {"phase": "recon",        "depends_on": []},
    {"phase": "web_app",      "depends_on": ["recon"]},
    {"phase": "vuln_scan",    "depends_on": ["recon"]},
    {"phase": "exploitation", "depends_on": ["vuln_scan"]},
    {"phase": "password",     "depends_on": ["exploitation"]},
    {"phase": "post_exploit", "depends_on": ["exploitation"]},
    {"phase": "wireless",     "depends_on": []},
    {"phase": "forensics",    "depends_on": ["recon", "vuln_scan", "exploitation",
                                              "password", "post_exploit"]},
]


class OrchestratorAgent(BaseAgent):
    """Multi-phase pipeline: recon → web_app → vuln → exploit → post-exploit → report."""

    name = "orchestrator"
    phase = "orchestrator"

    def __init__(self, context: Optional[dict] = None):
        super().__init__(context)
        self._phase_results: dict[str, dict] = {}

    async def run(self, task: str) -> dict:
        target = self._extract_target(task)
        started_at = datetime.now(timezone.utc).isoformat()

        for step in PIPELINE:
            phase = step["phase"]

            # Wire previous results as context
            prev_results = {
                dep: self._phase_results.get(dep)
                for dep in step["depends_on"]
            }

            agent = PhaseAgent(phase=phase, context={"previous_results": prev_results, "target": target})
            result = await self._run_phase(phase, agent, task)

            self._phase_results[phase] = result

            # Persist to DB
            try:
                save_phase_result(
                    domain=target,
                    phase=phase,
                    status=result.get("status", "completed"),
                    result=result,
                )
            except Exception:
                pass  # Non-critical — don't abort pipeline on DB failure

            # Halt pipeline if a non-report phase fails hard
            if result.get("status") in ("failed", "timeout") and phase != "forensics":
                break

        # Generate final report
        report_agent = ReportAgent(context={"phase_results": self._phase_results})
        report = await report_agent.run(task)

        return {
            "agent": "orchestrator",
            "target": target,
            "workflow": "full_pipeline",
            "started_at": started_at,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "phases": self._phase_results,
            "report": report,
        }

    async def _run_phase(self, phase: str, agent: PhaseAgent, task: str) -> dict:
        try:
            result = await asyncio.wait_for(agent.run(task), timeout=3600)
            return result
        except asyncio.TimeoutError:
            return {"phase": phase, "status": "timeout", "error": f"Phase '{phase}' exceeded 1h limit"}
        except Exception as e:
            return {"phase": phase, "status": "failed", "error": str(e)}

    @staticmethod
    def _extract_target(task: str) -> str:
        for prefix in ["for ", "on ", "against ", "target "]:
            if prefix in task:
                return task.split(prefix)[-1].strip().split()[0]
        return task.split()[-1]
