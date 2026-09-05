from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from agents.base import BaseAgent
from llm.base import BaseLLMClient, LLMEvent, StreamCallback
from llm.config import LLMConfig
from tools.executor import run_tool, ToolResult
from tools.registry import UnifiedToolRegistry, get_registry

logger = logging.getLogger("dynamic_agent")

MAX_TOOL_CALLS = 15

SYSTEM_PROMPT_TEMPLATE = """\
You are KVS Red Team AI, an autonomous cybersecurity assessment assistant.

## Role
- Security Researcher
- Red Team Analyst
- Threat Intelligence Analyst
- SOC Assistant
- Security Report Writer

## Objectives
1. Analyze provided systems, logs, applications, cloud infrastructure, and security configurations.
2. Identify vulnerabilities, misconfigurations, exposed services, weak security controls, and suspicious activity.
3. Map findings to MITRE ATT&CK, OWASP Top 10, NIST CSF, and CVSS.
4. Calculate risk levels (Critical, High, Medium, Low).
5. Explain business impact.
6. Recommend defensive mitigations and remediation steps.
7. Generate executive summaries and technical reports.
8. Detect indicators of compromise (IOCs).
9. Correlate security events and identify possible attack chains.
10. Prioritize findings based on risk and likelihood.

## Capabilities
You have access to 50+ security tools organized by assessment phase:
- **recon**: Subdomain enumeration, port scanning, OSINT
- **web_app**: Web vulnerability scanning, directory brute-forcing, SQL injection
- **vuln_scan**: Vulnerability detection, CVE lookup
- **exploitation**: Exploit verification, payload testing
- **password**: Password cracking, brute-force testing
- **post_exploit**: Lateral movement, privilege escalation, AD assessment
- **wireless**: WiFi security testing
- **forensics**: Memory analysis, evidence collection

## How to work
1. **Think step by step** — analyze what you know, decide the next best tool
2. **Use one tool at a time** unless they are independent and can run in parallel
3. **Analyze results** before deciding the next step
4. **Be thorough** — follow leads, chain findings, verify vulnerabilities

## Output Format
Always structure your final report using this format:

### Executive Summary
- Overall Risk Score
- Key Findings
- Recommended Actions

### Technical Findings
- Finding ID
- Severity
- Description
- Evidence
- MITRE ATT&CK Mapping
- CVSS Score
- Remediation

### Threat Intelligence
- Relevant CVEs
- Known Threat Actors
- Associated Techniques

### Defense Recommendations
- Immediate Actions
- Short-Term Actions
- Long-Term Actions

## Rules
- Only support authorized security testing and defensive analysis.
- Do not provide exploit code, malware, credential theft, or unauthorized access instructions.
- Focus on security assessment, detection, reporting, and remediation.
- Provide confidence scores for all findings.
- Only run tools against explicitly authorized targets.
- Always explain your reasoning before running a tool.
- If a tool returns no useful results, try a different approach.
- Stop after reaching a meaningful conclusion.
"""  # noqa: E501


@dataclass
class DynamicAgentResult:
    """Final result produced by the DynamicAgent."""

    agent: str = "dynamic_agent"
    target: str = ""
    task: str = ""
    reasoning_chain: list[dict[str, Any]] = field(default_factory=list)
    final_answer: str = ""
    tools_executed: int = 0
    phases_covered: list[str] = field(default_factory=list)
    started_at: str = ""
    completed_at: str = ""
    success: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "target": self.target,
            "task": self.task,
            "reasoning_chain": self.reasoning_chain[-10:],  # last 10 steps
            "final_answer": self.final_answer[:5000],
            "tools_executed": self.tools_executed,
            "phases_covered": self.phases_covered,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "success": self.success,
        }


class DynamicAgent(BaseAgent):
    """An agent that uses LLM-driven tool-use to dynamically decide what to do.

    The agentic loop:
      1. Receive task + target
      2. Retrieve relevant memory context (if memory_db is available)
      3. Call LLM with available tool schemas
      4. LLM responds with tool_use block(s) → execute tool(s)
      5. Feed results back to LLM
      6. Repeat until LLM returns final text answer
      7. Store episode in memory (if memory_db is available)
    """

    name = "dynamic_agent"
    phase = "dynamic"

    def __init__(
        self,
        llm_client: BaseLLMClient,
        tool_registry: UnifiedToolRegistry | None = None,
        memory_db: Any = None,
        stream_manager: Any = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(context)
        self._llm = llm_client
        self._registry = tool_registry or get_registry()
        self._memory_db = memory_db
        self._stream_manager = stream_manager
        self._config = LLMConfig.from_env()

    async def run(self, task: str) -> dict[str, Any]:
        target = self.context.get("target", "")
        session_id = self.context.get("session_id", "")
        phases = self.context.get("phases")

        result = DynamicAgentResult(
            target=target,
            task=task,
            started_at=datetime.utcnow().isoformat(),
        )

        # 1. Build the system prompt with memory context
        system_prompt = SYSTEM_PROMPT_TEMPLATE
        if self._memory_db and session_id:
            memory_context = await self._retrieve_memory(task, target)
            if memory_context:
                system_prompt += (
                    "\n\n## Previous Assessment Context\n"
                    f"{memory_context}\n"
                )

        # 2. Get available tool definitions
        if phases:
            tool_defs = self._registry.to_llm_tool_definitions(phases)
        else:
            tool_defs = self._registry.to_llm_tool_definitions()

        # 3. Build initial prompt
        prompt_parts = [f"## Task\n{task}"]
        if target:
            prompt_parts.append(f"## Target\n{target}")
        prompt_parts.append(
            "\nAvailable tools are provided. Choose the right tool step by step. "
            "Explain your reasoning, then call the tool. "
            "When you have enough information, provide a comprehensive summary."
        )
        user_prompt = "\n\n".join(prompt_parts)

        # 4. The agentic loop
        # We accumulate the conversation in `messages` and serialize it into
        # a progressively larger prompt on each turn (keeps the client
        # interface simple while maintaining full context).
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": user_prompt}
        ]
        tool_calls_remaining = self._config.max_tool_calls_per_run or MAX_TOOL_CALLS
        all_events: list[LLMEvent] = []

        while tool_calls_remaining > 0:
            tool_calls_remaining -= 1

            current_tool_uses: list[LLMEvent] = []

            # Serialize the full conversation into a single prompt
            # so the LLM has full context of previous turns.
            if len(messages) > 1:
                conversation_so_far = self._serialize_conversation(messages)
                full_prompt = (
                    f"{conversation_so_far}\n\n"
                    f"Continue the assessment. If you need more information, "
                    f"use a tool. Otherwise provide your final summary."
                )
            else:
                full_prompt = user_prompt

            async for event in self._llm.generate(
                prompt=full_prompt,
                system_prompt=system_prompt,
                tools=tool_defs,
                tool_results=None,
                on_stream=self._make_stream_callback(session_id),
            ):
                all_events.append(event)
                if event.type == "text":
                    if event.done:
                        result.final_answer = (
                            result.final_answer or ""
                        ) + (event.content or "")
                        if self._memory_db and session_id:
                            await self._store_conversation(
                                session_id, "assistant", event.content or ""
                            )
                    else:
                        result.final_answer = (
                            result.final_answer or ""
                        ) + (event.content or "")
                elif event.type == "tool_use":
                    current_tool_uses.append(event)

            # If no tool_use events, we're done
            if not current_tool_uses:
                break

            # Execute tool(s)
            for tool_use in current_tool_uses:
                tool_name = tool_use.tool_name or ""
                tool_input = tool_use.tool_input or {}
                target_val = tool_input.get("target", target)

                await self._emit_event(session_id, {
                    "type": "tool_start",
                    "tool": tool_name,
                    "args": tool_input,
                    "target": target_val,
                })

                # Execute the tool (strip 'run_' prefix if present)
                actual_tool_name = tool_name.replace("run_", "")
                tool_exec_result = await run_tool(
                    actual_tool_name,
                    target_val,
                    extra_args=tool_input.get("args"),
                    registry=self._registry,
                    session_id=session_id,
                )

                result.tools_executed += 1
                result.reasoning_chain.append({
                    "step": result.tools_executed,
                    "tool": tool_name,
                    "input": tool_input,
                    "output_summary": self._summarize_result(tool_exec_result),
                    "timestamp": datetime.utcnow().isoformat(),
                })

                tool_entry = self._registry.get_tool(actual_tool_name)
                if tool_entry and tool_entry.phase not in result.phases_covered:
                    result.phases_covered.append(tool_entry.phase)

                await self._emit_event(session_id, {
                    "type": "tool_result",
                    "tool": tool_name,
                    "data": tool_exec_result.to_dict(),
                })

                if self._memory_db and session_id:
                    await self._store_conversation(
                        session_id, "assistant",
                        json.dumps({"tool_use": tool_name, "input": tool_input}),
                    )
                    await self._store_conversation(
                        session_id, "tool",
                        json.dumps(tool_exec_result.to_dict(), default=str),
                    )

                # Append tool result to messages for context
                result_content = self._format_tool_result(tool_exec_result)
                messages.append({
                    "role": "user",
                    "content": (
                        f"## Tool Result: {tool_name}\n\n"
                        f"{result_content}"
                    ),
                })

        # 5. Done — store episode memory
        if self._memory_db and session_id:
            await self._store_episode(session_id, result)

        result.completed_at = datetime.utcnow().isoformat()
        logger.info(
            f"DynamicAgent completed: {result.tools_executed} tools, "
            f"{len(result.phases_covered)} phases"
        )

        await self._emit_event(session_id, {
            "type": "complete",
            "summary": {
                "tools_executed": result.tools_executed,
                "phases_covered": result.phases_covered,
                "final_answer": result.final_answer[:500],
            },
        })

        return result.to_dict()

    # ---- helpers --------------------------------------------------------

    def _serialize_conversation(self, messages: list[dict]) -> str:
        """Flatten the conversation history into a single prompt string."""
        parts = []
        for msg in messages:
            role = msg.get("role", "user").upper()
            content = msg.get("content", "")
            if isinstance(content, list):
                # Tool result blocks
                text_parts = []
                for block in content:
                    if isinstance(block, dict):
                        text_parts.append(block.get("content", ""))
                content = "\n".join(text_parts)
            parts.append(f"<{role}>\n{content}\n</{role}>")
        return "\n\n".join(parts)

    def _summarize_result(self, r: ToolResult) -> str:
        if not r.success:
            return f"Failed: {r.stderr[:200]}"
        preview = json.dumps(r.parsed_data, default=str)[:500] if r.parsed_data else ""
        return f"Success (exit={r.exit_code}): {preview}"

    def _format_tool_result(self, r: ToolResult) -> str:
        max_chars = self._config.tool_result_max_chars
        parts = [
            f"Command: {r.command}",
            f"Exit code: {r.exit_code}",
            f"Success: {r.success}",
        ]
        if r.stdout:
            parts.append(f"STDOUT:\n{r.stdout[:max_chars]}")
        if r.stderr:
            parts.append(f"STDERR:\n{r.stderr[:max_chars // 2]}")
        return "\n\n".join(parts)

    def _make_stream_callback(self, session_id: str) -> StreamCallback | None:
        if self._stream_manager and session_id:
            async def cb(event: LLMEvent) -> None:
                await self._stream_manager.broadcast(
                    session_id,
                    {
                        "type": f"llm_{event.type}",
                        "content": event.content,
                        "tool_name": event.tool_name,
                    },
                )
            return cb
        return None

    async def _emit_event(self, session_id: str, event: dict) -> None:
        if self._stream_manager and session_id:
            await self._stream_manager.broadcast(session_id, event)

    async def _retrieve_memory(self, task: str, target: str) -> str:
        """Retrieve relevant past episodes from the memory database."""
        if not self._memory_db:
            return ""

        try:
            # Query by target first (exact match)
            episodes = await self._memory_db.get_episodes_for_target(target, limit=3)
            memory_parts = []
            if episodes:
                for ep in episodes:
                    if isinstance(ep, dict) and ep.get("reasoning"):
                        memory_parts.append(
                            f"- Previous assessment on {ep.get('target', target)}: "
                            f"{ep['reasoning'][:500]}"
                        )

            # Also retrieve similar episodes by semantic search
            similar = await self._memory_db.search_memory(task, limit=2)
            for ep in similar:
                if isinstance(ep, dict) and ep.get("reasoning"):
                    if ep.get("target", "") != target:
                        memory_parts.append(
                            f"- Related assessment on {ep.get('target', 'unknown')}: "
                            f"{ep['reasoning'][:300]}"
                        )

            return "\n".join(memory_parts[:5]) if memory_parts else ""
        except Exception:
            logger.exception("Memory retrieval failed")
            return ""

    async def _store_conversation(self, session_id: str, role: str, content: str) -> None:
        if not self._memory_db:
            return
        try:
            await self._memory_db.store_conversation_turn(
                session_id=session_id,
                role=role,
                content=content,
                tool_name=role if role == "tool" else None,
            )
        except Exception:
            logger.exception("Failed to store conversation turn")

    async def _store_episode(self, session_id: str, result: DynamicAgentResult) -> None:
        if not self._memory_db:
            return
        try:
            await self._memory_db.store_episode(
                session_id=session_id,
                target=result.target,
                phase=",".join(result.phases_covered),
                reasoning=result.final_answer[:2000],
                tool_name="",
                tool_result="",
            )
        except Exception:
            logger.exception("Failed to store episode")
