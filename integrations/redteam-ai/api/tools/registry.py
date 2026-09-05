from __future__ import annotations

import os
import yaml
from dataclasses import dataclass, field
from typing import Any

from llm.base import ToolDefinition


TOOLS_YAML = os.path.join(os.path.dirname(__file__), "tools.yaml")


@dataclass
class ToolEntry:
    """A single tool loaded from tools.yaml, ready for execution."""

    name: str
    phase: str
    description: str
    keywords: list[str] = field(default_factory=list)
    command: str = ""
    args: str = ""
    check: str = ""
    timeout: int = 300
    output_parser: str = "raw"
    priority: int = 3
    use_cases: list[str] = field(default_factory=list)
    install_hint: str = ""

    def build_command(self, target: str, extra_args: str | None = None) -> str:
        cmd = self.command.replace("{target}", target)
        if extra_args:
            cmd = cmd.replace("{args}", extra_args)
        else:
            cmd = cmd.replace("{args}", self.args)
        return cmd

    def to_llm_tool_definition(self) -> ToolDefinition:
        """Convert this tool into an LLM-compatible tool definition (JSON Schema)."""
        # Determine the primary target parameter type based on the tool
        target_desc = "Target domain, IP address, or URL"
        if self.phase == "wireless":
            target_desc = "Wireless interface or BSSID"
        elif self.phase == "forensics":
            target_desc = "File path, memory dump, or evidence identifier"

        properties: dict[str, Any] = {
            "target": {
                "type": "string",
                "description": target_desc,
            },
        }

        required = ["target"]

        # Some tools accept optional arguments
        if "{args}" in self.command:
            properties["args"] = {
                "type": "string",
                "description": f"Additional arguments for {self.name}. Default: {self.args}",
            }

        return ToolDefinition(
            name=f"run_{self.name}",
            description=f"{self.description} [{self.phase}]",
            input_schema={
                "type": "object",
                "properties": properties,
                "required": required,
            },
            phase=self.phase,
        )


class UnifiedToolRegistry:
    """The single source of truth for all security tools.

    Loads tool definitions from *tools.yaml* and provides:
    - Lookup by name, phase, or keyword
    - JSON Schema generation for LLM tool-use APIs
    - Category metadata
    """

    def __init__(self, yaml_path: str = TOOLS_YAML) -> None:
        self._yaml_path = yaml_path
        self._tools: dict[str, ToolEntry] = {}
        self._phases: list[str] = []
        self._categories: dict[str, Any] = {}
        self._load()

    # ---- public queries ------------------------------------------------

    @property
    def phases(self) -> list[str]:
        return list(self._phases)

    @property
    def categories(self) -> dict[str, Any]:
        return dict(self._categories)

    def get_tool(self, name: str) -> ToolEntry | None:
        return self._tools.get(name)

    def list_tools(self) -> list[ToolEntry]:
        return list(self._tools.values())

    def get_tools_by_phase(self, phase: str) -> list[ToolEntry]:
        return sorted(
            (t for t in self._tools.values() if t.phase == phase),
            key=lambda t: t.priority,
        )

    def find_tools(self, query: str) -> list[tuple[float, ToolEntry]]:
        """Keyword-match tools against *query*. Returns (score, tool) sorted desc."""
        q = query.lower()
        scored: list[tuple[float, ToolEntry]] = []
        for tool in self._tools.values():
            score = 0.0
            for kw in tool.keywords:
                if kw.lower() in q:
                    score += 1.0
            if tool.name.lower() in q:
                score += 2.0
            for uc in tool.use_cases:
                if uc.lower() in q:
                    score += 1.0
            if score > 0:
                scored.append((score, tool))
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored

    def to_llm_tool_definitions(self, phases: list[str] | None = None) -> list[ToolDefinition]:
        """Generate LLM-compatible tool definitions, optionally filtered by phase."""
        tools = self.list_tools()
        if phases:
            phase_set = set(phases)
            tools = [t for t in tools if t.phase in phase_set]
        return [t.to_llm_tool_definition() for t in tools]

    # ---- loading -------------------------------------------------------

    def _load(self) -> None:
        if not os.path.exists(self._yaml_path):
            raise FileNotFoundError(f"Tools manifest not found: {self._yaml_path}")

        with open(self._yaml_path) as f:
            data = yaml.safe_load(f)

        self._categories = data.get("categories", {})
        self._phases = list(self._categories.keys())

        for item in data.get("tools", []):
            entry = ToolEntry(
                name=item["name"],
                phase=item.get("phase", ""),
                description=item.get("description", ""),
                keywords=item.get("keywords", []),
                command=item.get("command", ""),
                args=item.get("args", ""),
                check=item.get("check", ""),
                timeout=item.get("timeout", 300),
                output_parser=item.get("output_parser", "raw"),
                priority=item.get("priority", 3),
                use_cases=item.get("use_cases", []),
                install_hint=item.get("install_hint", ""),
            )
            self._tools[entry.name] = entry


# Global singleton
_registry: UnifiedToolRegistry | None = None


def get_registry() -> UnifiedToolRegistry:
    global _registry
    if _registry is None:
        _registry = UnifiedToolRegistry()
    return _registry
