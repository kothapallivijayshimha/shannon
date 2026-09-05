"""Tests for the tool registry and executor."""

from tools.registry import ToolRegistry


def test_registry_loads():
    reg = ToolRegistry()
    assert len(reg.get_all_tools()) >= 50
    assert len(reg.get_phases()) >= 8


def test_get_tool_by_name():
    reg = ToolRegistry()
    tool = reg.get_tool("nmap")
    assert tool is not None
    assert tool.name == "nmap"
    assert tool.phase == "recon"
    assert len(tool.keywords) > 0
    assert len(tool.use_cases) > 0


def test_get_tool_unknown():
    reg = ToolRegistry()
    assert reg.get_tool("nonexistent_tool_xyz") is None


def test_get_tools_by_phase():
    reg = ToolRegistry()
    recon_tools = reg.get_tools_by_phase("recon")
    assert len(recon_tools) >= 5
    # Check sorted by priority
    priorities = [t.priority for t in recon_tools]
    assert priorities == sorted(priorities)


def test_find_tools_recon_keywords():
    reg = ToolRegistry()
    matches = reg.find_tools("find subdomains for example.com")
    assert len(matches) > 0
    # subfinder should rank high
    top_names = [t.name for _, t in matches[:3]]
    assert "subfinder" in top_names


def test_find_tools_exploit_keywords():
    reg = ToolRegistry()
    matches = reg.find_tools("exploit metasploit payload for target")
    assert len(matches) > 0
    top_names = [t.name for _, t in matches[:3]]
    assert "metasploit" in top_names


def test_find_tools_web_keywords():
    reg = ToolRegistry()
    matches = reg.find_tools("scan wordpress site for vulnerabilities using wpscan")
    assert len(matches) > 0
    top_names = [t.name for _, t in matches[:3]]
    assert "wpscan" in top_names


def test_find_tools_password_keywords():
    reg = ToolRegistry()
    matches = reg.find_tools("crack hash with hashcat and john")
    assert len(matches) > 0
    top_names = [t.name for _, t in matches[:3]]
    assert "hashcat" in top_names or "john" in top_names


def test_find_tools_wireless_keywords():
    reg = ToolRegistry()
    matches = reg.find_tools("capture wifi handshake and crack")
    assert len(matches) > 0
    top_names = [t.name for _, t in matches[:3]]
    assert "aircrack_ng" in top_names or "wifite2" in top_names


def test_find_tools_empty_returns_empty():
    reg = ToolRegistry()
    matches = reg.find_tools("")
    assert matches == []


def test_all_tools_have_required_fields():
    reg = ToolRegistry()
    for tool in reg.get_all_tools():
        assert tool.name, f"Tool missing name"
        assert tool.phase, f"Tool {tool.name} missing phase"
        assert tool.command, f"Tool {tool.name} missing command"
        assert tool.check, f"Tool {tool.name} missing check cmd"
        assert len(tool.keywords) > 0, f"Tool {tool.name} has no keywords"
        assert tool.timeout > 0, f"Tool {tool.name} has no/invalid timeout"


def test_categories_have_phase_order():
    reg = ToolRegistry()
    cats = reg.get_categories()
    for key, cat in cats.items():
        assert "phase_order" in cat, f"Category '{key}' missing phase_order"
        assert "color" in cat, f"Category '{key}' missing color"
        assert "label" in cat, f"Category '{key}' missing label"
