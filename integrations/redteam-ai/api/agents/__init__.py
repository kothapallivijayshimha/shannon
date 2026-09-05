from typing import Optional, Any
from .recon import ReconAgent
from .orchestrator import OrchestratorAgent
from .phase_agent import PhaseAgent
from .report import ReportAgent
from .dynamic_agent import DynamicAgent
from tools.registry import get_registry

# Phase → keyword triggers for top-level intent routing
PHASE_KEYWORDS: dict[str, list[str]] = {
    "recon": [
        "recon", "discover", "subdomain", "enumerate", "dns",
        "port scan", "nmap", "whois", "osint", "footprint",
    ],
    "web_app": [
        "web", "burp", "zap", "sqlmap", "gobuster", "ffuf",
        "wpscan", "dirb", "xss", "sqli", "lfi", "csrf", "ssrf",
    ],
    "vuln_scan": [
        "vuln", "cve", "vulnerability", "nessus", "openvas",
        "nikto", "searchsploit", "weakness", "audit",
    ],
    "exploitation": [
        "exploit", "metasploit", "payload", "shell", "beef",
        "set", "empire", "routersploit", "crackmap",
    ],
    "password": [
        "password", "crack", "hash", "brute force", "hashcat",
        "john", "hydra", "medusa", "mimikatz", "login",
    ],
    "post_exploit": [
        "post-exploit", "post_exploit", "lateral", "privilege",
        "bloodhound", "responder", "kerberos", "ad",
        "active directory", "escalation", "pivot",
    ],
    "wireless": [
        "wireless", "wifi", "aircrack", "kismet", "bettercap",
        "wardriving", "handshake",
    ],
    "forensics": [
        "forensic", "memory", "disk", "autopsy", "volatility",
        "analysis", "evidence", "report", "dradis", "cherrytree",
    ],
}

# Orchestrator triggers
_ORCHESTRATOR_TRIGGERS = {"full", "pipeline", "all phases", "complete", "pentest"}


def detect_phases(task: str) -> list[str]:
    """Return phase(s) that match the task, ordered by relevance score."""
    task_lower = task.lower()
    registry = get_registry()

    # Tool-level matching
    tool_matches = registry.find_tools(task)

    scores: dict[str, float] = {}
    for phase, keywords in PHASE_KEYWORDS.items():
        score = sum(2.0 for kw in keywords if kw in task_lower)
        # Boost from tool-level keyword matches
        for s, tool in tool_matches:
            if tool.phase == phase:
                score += s * 0.5
        if score > 0:
            scores[phase] = score

    if not scores:
        return ["recon"]

    return sorted(scores, key=scores.get, reverse=True)  # type: ignore[arg-type]


def get_agent(task: str) -> "BaseAgent":
    """Route *task* to the right agent based on intent detection."""
    from .base import BaseAgent

    task_lower = task.lower()

    # Orchestrator (multi-phase)
    if any(t in task_lower for t in _ORCHESTRATOR_TRIGGERS):
        return OrchestratorAgent()

    # Single phase
    phases = detect_phases(task)
    top_phase = phases[0]

    if top_phase == "recon":
        # Keep ReconAgent for backward compat (it has richer chain logic)
        return ReconAgent()
    if top_phase == "forensics" or "report" in task_lower:
        return ReportAgent(context={"phase_results": {}})

    return PhaseAgent(phase=top_phase)


def get_dynamic_agent(
    llm_client: Any,
    memory_db: Any = None,
    stream_manager: Any = None,
    context: Optional[dict] = None,
) -> "BaseAgent":
    """Return a DynamicAgent wired with the given LLM client."""
    from .dynamic_agent import DynamicAgent

    return DynamicAgent(
        llm_client=llm_client,
        tool_registry=get_registry(),
        memory_db=memory_db,
        stream_manager=stream_manager,
        context=context or {},
    )


__all__ = [
    "get_agent", "get_dynamic_agent", "detect_phases",
    "ReconAgent", "PhaseAgent", "ReportAgent", "OrchestratorAgent",
    "DynamicAgent",
]
