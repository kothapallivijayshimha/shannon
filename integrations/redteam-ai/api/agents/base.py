import subprocess
import shlex
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional


def safe_run(cmd_template: str, *args: str) -> list[str]:
    """Run a shell command with safely quoted arguments."""
    safe_args = [shlex.quote(a) for a in args]
    cmd = cmd_template.format(*safe_args)
    result = subprocess.getoutput(cmd)
    return [line.strip() for line in result.splitlines() if line.strip()]


class BaseAgent(ABC):
    name: str = "base"
    phase: str = ""

    def __init__(
        self,
        context: Optional[dict] = None,
        stream_callback: Optional[Callable[[dict], Any]] = None,
    ):
        self.context = context or {}
        self.stream_callback = stream_callback

    async def emit(self, event: dict) -> None:
        """Send a streaming event if a callback is registered."""
        if self.stream_callback:
            await self.stream_callback(event)

    @abstractmethod
    async def run(self, task: str) -> dict[str, Any]:
        ...

