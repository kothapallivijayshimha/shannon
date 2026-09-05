import pytest
from agents import get_agent, detect_phases
from agents.base import safe_run


# ── safe_run ─────────────────────────────────────────────────


def test_safe_run_quotes_arguments():
    result = safe_run("echo {}", "hello")
    assert result == ["hello"]


def test_safe_run_handles_multiple_args():
    result = safe_run("echo {} {}", "hello", "world")
    assert result == ["hello world"]


# ── detect_phases ────────────────────────────────────────────


def test_detect_recon_phase():
    phases = detect_phases("find subdomains for example.com")
    assert "recon" in phases
    assert phases[0] == "recon"


def test_detect_vuln_phase():
    phases = detect_phases("scan for vulnerabilities with nikto on example.com")
    assert "vuln_scan" in phases


def test_detect_exploit_phase():
    phases = detect_phases("exploit metasploit against target")
    assert "exploitation" in phases


def test_detect_web_phase():
    phases = detect_phases("sqlmap scan for sql injection on example.com")
    assert "web_app" in phases


def test_detect_password_phase():
    phases = detect_phases("crack password hash with john")
    assert "password" in phases


def test_detect_post_exploit_phase():
    phases = detect_phases("bloodhound active directory enumeration")
    assert "post_exploit" in phases


def test_detect_wireless_phase():
    phases = detect_phases("capture wpa handshake with aircrack")
    assert "wireless" in phases


def test_detect_forensics_phase():
    phases = detect_phases("analyze memory dump with volatility")
    assert "forensics" in phases


def test_detect_fallback_to_recon():
    phases = detect_phases("something random here")
    assert phases == ["recon"]


# ── get_agent routing ────────────────────────────────────────


def test_get_agent_routes_subdomain():
    agent = get_agent("find subdomains for example.com")
    assert agent.name == "recon"


def test_get_agent_routes_report():
    agent = get_agent("generate report for example.com")
    assert agent.name == "report"


def test_get_agent_routes_orchestrator():
    agent = get_agent("full pentest example.com")
    assert agent.name == "orchestrator"


def test_get_agent_routes_pipeline():
    agent = get_agent("all phases for example.com")
    assert agent.name == "orchestrator"


def test_get_agent_fallback_to_recon():
    agent = get_agent("something random here")
    assert agent.name == "recon"


def test_get_agent_explicit_phase():
    agent = get_agent("exploit this target with metasploit")
    assert agent.name == "exploitation"


def test_get_agent_vuln_phase():
    agent = get_agent("vulnerability scan on example.com with nikto")
    assert agent.name == "vuln_scan"
