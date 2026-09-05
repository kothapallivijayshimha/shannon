from __future__ import annotations

import asyncio
import json
import logging
import shlex
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .registry import UnifiedToolRegistry, get_registry

logger = logging.getLogger("tool_executor")


@dataclass
class ToolResult:
    """Result of executing a single security tool."""

    tool_name: str
    command: str
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    success: bool = False
    timed_out: bool = False
    started_at: str = ""
    finished_at: str = ""
    parsed_data: dict[str, Any] | list[str] | None = field(default=None)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "command": self.command,
            "stdout": self.stdout[:5000],
            "stderr": self.stderr[:2000],
            "exit_code": self.exit_code,
            "success": self.success,
            "timed_out": self.timed_out,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "parsed_data": self.parsed_data,
        }


def parse_output(parser: str, stdout: str) -> dict[str, Any] | list[str] | None:
    """Parse tool output based on the parser strategy."""
    lines = [l.strip() for l in stdout.splitlines() if l.strip()]

    if parser == "text_lines":
        return lines

    if parser == "nmap":
        open_ports = [l for l in lines if "/tcp" in l or "/udp" in l]
        return {"open_ports": open_ports, "raw_lines": lines[:100]}

    if parser == "sqlmap":
        vuln = any("vulnerable" in l.lower() for l in lines)
        params = [l for l in lines if "Parameter:" in l]
        return {"vulnerable": vuln, "parameters": params}

    if parser == "gobuster":
        found = [l for l in lines if "(Status:" in l]
        return {"found_urls": found}

    if parser == "dirb":
        found = [l for l in lines if "==> DIRECTORY:" in l or "==> FILE:" in l]
        return {"discovered": found}

    if parser == "nikto":
        issues = [l for l in lines if "+" in l and ":" in l]
        return {"issues": issues[:50]}

    if parser == "searchsploit":
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            return lines[:50]

    if parser == "json_file":
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            return {"raw": stdout[:2000]}

    if parser == "theharvester":
        return {"harvested": lines[:100]}

    if parser in ("john", "hashcat"):
        cracked = [l for l in lines if "(" in l and ")" in l]
        return {"cracked": cracked[:50]}

    if parser in ("hydra", "medusa"):
        found = [l for l in lines if "password" in l.lower() or "login" in l.lower()]
        return {"found_credentials": found[:20]}

    # raw / fallback
    return {"output": lines[:100]}


async def run_tool(
    tool_name: str,
    target: str,
    extra_args: str | None = None,
    registry: UnifiedToolRegistry | None = None,
    use_celery: bool = False,
    session_id: str | None = None,
) -> ToolResult:
    """Execute a tool from the registry against *target*.

    Before execution, the target is checked against the authorization
    whitelist.  After execution, a tamper-evident audit entry is written.

    If *use_celery* is True, the heavy lifting is delegated to a Celery worker.
    Otherwise runs synchronously via subprocess.
    """
    reg = registry or get_registry()
    tool = reg.get_tool(tool_name)
    if tool is None:
        return ToolResult(
            tool_name=tool_name,
            command="",
            stdout="",
            stderr=f"Tool '{tool_name}' not found in registry",
            success=False,
        )

    # ---- Authorization check -------------------------------------------
    from authz import authz as _authz

    allowed, reason = _authz.check(target, tool_name=tool_name, phase=tool.phase)
    if not allowed:
        logger.warning(f"Blocked unauthorized tool '{tool_name}' on '{target}': {reason}")
        return ToolResult(
            tool_name=tool_name,
            command="",
            stdout="",
            stderr=f"UNAUTHORIZED: {reason}",
            success=False,
            exit_code=403,
        )

    # ---- Execute -------------------------------------------------------
    if use_celery:
        result = await _run_via_celery(tool_name, target, extra_args)
    else:
        result = await _run_direct(tool, target, extra_args)

    # ---- Audit log -----------------------------------------------------
    from audit import audit as _audit

    try:
        _audit.log_tool_execution(
            tool_name=tool_name,
            target=target,
            phase=tool.phase,
            session_id=session_id,
            command=result.command,
            exit_code=result.exit_code,
            success=result.success,
            result_summary=json.dumps(result.parsed_data, default=str)[:500] if result.parsed_data else "",
        )
    except Exception:
        logger.exception("Failed to write audit log")

    return result


async def _run_direct(
    tool: Any, target: str, extra_args: str | None = None
) -> ToolResult:
    """Execute a tool directly via subprocess."""
    cmd = tool.build_command(target, extra_args)
    logger.info(f"Running tool [{tool.name}]: {cmd}")

    started_at = datetime.utcnow().isoformat()

    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=tool.timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            result = ToolResult(
                tool_name=tool.name,
                command=cmd,
                stdout="",
                stderr=f"Timed out after {tool.timeout}s",
                exit_code=124,
                timed_out=True,
                started_at=started_at,
                finished_at=datetime.utcnow().isoformat(),
            )
            logger.warning(f"Tool [{tool.name}] timed out after {tool.timeout}s")
            return result

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        exit_code = proc.returncode or 0

        parsed = parse_output(tool.output_parser, stdout)

        result = ToolResult(
            tool_name=tool.name,
            command=cmd,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            success=exit_code == 0,
            started_at=started_at,
            finished_at=datetime.utcnow().isoformat(),
            parsed_data=parsed,
        )

        logger.info(
            f"Tool [{tool.name}] finished (exit={exit_code}, "
            f"stdout={len(stdout)}b, stderr={len(stderr)}b)"
        )
        return result

    except Exception as e:
        logger.exception(f"Tool [{tool.name}] failed with exception")
        return ToolResult(
            tool_name=tool.name,
            command=cmd,
            stdout="",
            stderr=str(e),
            exit_code=1,
            started_at=started_at,
            finished_at=datetime.utcnow().isoformat(),
        )


async def _run_via_celery(
    tool_name: str, target: str, extra_args: str | None = None
) -> ToolResult:
    """Delegate tool execution to a Celery worker task."""
    from celery import Celery

    celery_app = Celery(
        "worker",
        broker="redis://localhost:6379/0",
        backend="redis://localhost:6379/0",
    )

    task = celery_app.send_task(
        "run_tool_task",
        args=[tool_name, target],
        kwargs={"extra_args": extra_args},
    )

    try:
        result_data = task.get(timeout=600)
    except Exception as e:
        return ToolResult(
            tool_name=tool_name,
            command="",
            stderr=f"Celery task failed: {e}",
            success=False,
        )

    if isinstance(result_data, dict):
        return ToolResult(**result_data)
    return ToolResult(
        tool_name=tool_name,
        command="",
        stdout=str(result_data),
        success=True,
    )
