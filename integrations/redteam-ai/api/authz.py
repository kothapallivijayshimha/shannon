from __future__ import annotations

import logging
from typing import Any

from database import authz_db

logger = logging.getLogger("authz")


class AuthorizationManager:
    """Authorization gate that checks targets against the whitelist before
    any tool execution.

    Delegates all persistence to ``AuthzDatabase``.
    """

    def __init__(self) -> None:
        self._db = authz_db

    # ---- Authorisation check --------------------------------------------

    def check(
        self,
        target: str,
        tool_name: str | None = None,
        phase: str | None = None,
    ) -> tuple[bool, str]:
        """Return ``(allowed: bool, reason: str)``.

        A target must be explicitly whitelisted.  Phase and tool scoping
        are additional filters on the whitelist entry.
        """
        if not target or not target.strip():
            return False, "Target cannot be empty"

        if not self._db.is_authorized(target, phase=phase, tool_name=tool_name):
            # Try to give a helpful reason
            if not self._db.is_authorized(target):
                return False, f"Target '{target}' is not in the authorized whitelist"
            return False, (
                f"Target '{target}' is authorized but not for "
                f"{'phase ' + phase if phase else 'tool ' + tool_name}"
            )

        return True, ""

    # ---- CRUD wrappers --------------------------------------------------

    def authorize(
        self,
        target: str,
        description: str = "",
        phases: str = "*",
        tools: str = "*",
        expires_at: str | None = None,
        created_by: str = "admin",
    ) -> dict:
        """Add *target* to the authorised whitelist."""
        logger.info(f"Authorizing target '{target}' (phases={phases}, tools={tools})")
        return self._db.add_target(target, description, phases, tools, expires_at, created_by)

    def revoke(self, target: str) -> bool:
        logger.info(f"Revoking authorization for target '{target}'")
        return self._db.remove_target(target)

    def revoke_by_id(self, record_id: str) -> bool:
        return self._db.remove_by_id(record_id)

    def list_authorized(self) -> list[dict[str, Any]]:
        return self._db.list_targets()

    def is_authorized(self, target: str, phase: str | None = None,
                      tool_name: str | None = None) -> bool:
        return self._db.is_authorized(target, phase, tool_name)


# Global singleton
authz = AuthorizationManager()
