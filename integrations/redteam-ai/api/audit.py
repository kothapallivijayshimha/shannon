from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import Any

from database import audit_db

logger = logging.getLogger("audit")


class AuditLogger:
    """Tamper-evident audit logger.

    Every tool execution is recorded with a cryptographic chain hash so
    entries cannot be retroactively modified without detection.

    The chain works by hashing ``tool|target|phase|exit_code|success|previous_hash``
    and storing the result as ``chain_hash``.
    """

    def __init__(self) -> None:
        self._db = audit_db

    def log_tool_execution(
        self,
        tool_name: str,
        target: str,
        phase: str | None = None,
        user: str = "agent",
        session_id: str | None = None,
        command: str = "",
        exit_code: int = -1,
        success: bool = False,
        result_summary: str = "",
    ) -> dict:
        """Record a tool execution in the tamper-evident audit log."""
        return self._db.log(
            tool_name=tool_name,
            target=target,
            phase=phase,
            user=user,
            session_id=session_id,
            command=command,
            exit_code=exit_code,
            success=success,
            result_summary=result_summary,
        )

    def query(
        self,
        target: str | None = None,
        tool_name: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Query audit logs by target and/or tool name."""
        return self._db.query(target, tool_name, limit, offset)

    def verify_chain(self) -> bool:
        """Verify the full audit chain for tampering."""
        return self._db.verify_chain()


# Global singleton
audit = AuditLogger()
