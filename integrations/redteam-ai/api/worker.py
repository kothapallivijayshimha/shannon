from __future__ import annotations

import asyncio
import json
import logging
import os
import redis as sync_redis

from celery import Celery

logger = logging.getLogger("celery_worker")

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery = Celery(
    "worker",
    broker=redis_url,
    backend=redis_url,
)

# Redis client for pub/sub progress publishing
_redis_client: sync_redis.Redis | None = None


def _get_redis() -> sync_redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = sync_redis.from_url(redis_url)
    return _redis_client


def _publish_progress(task_id: str, event: dict) -> None:
    """Publish a progress event to the Redis pub/sub channel for *task_id*."""
    try:
        r = _get_redis()
        r.publish(f"tool:{task_id}", json.dumps(event, default=str))
    except Exception:
        logger.exception("Failed to publish progress event")


@celery.task(bind=True, max_retries=2, soft_time_limit=1800, time_limit=1860)
def execute_tool_task(
    self,
    tool_name: str,
    target: str,
    extra_args: str | None = None,
) -> str:
    """Execute a security tool in the background and return structured results.

    Publishes progress events to Redis pub/sub channel ``tool:<task_id>``
    so the DynamicAgent can stream results live.
    """
    task_id = self.request.id

    _publish_progress(task_id, {
        "type": "tool_start",
        "tool_name": tool_name,
        "target": target,
    })

    try:
        from tools.executor import _run_direct
        from tools.registry import get_registry

        registry = get_registry()
        tool = registry.get_tool(tool_name)
        if tool is None:
            raise ValueError(f"Tool '{tool_name}' not found in registry")

        _publish_progress(task_id, {
            "type": "tool_progress",
            "tool_name": tool_name,
            "progress": f"Starting {tool_name} against {target}",
        })

        # Run synchronously inside the Celery worker
        result = asyncio.run(_run_direct(tool, target, extra_args))

        _publish_progress(task_id, {
            "type": "tool_complete",
            "tool_name": tool_name,
            "success": result.success,
            "summary": (
                json.dumps(result.parsed_data, default=str)[:500]
                if result.parsed_data else ""
            ),
        })

        return json.dumps(result.to_dict(), default=str)

    except Exception as e:
        logger.exception(f"Tool {tool_name} failed")
        _publish_progress(task_id, {
            "type": "tool_error",
            "tool_name": tool_name,
            "error": str(e),
        })
        raise self.retry(exc=e)


@celery.task
def run_tool_task(tool_name: str, target: str) -> str:
    """Legacy compatibility wrapper — delegates to execute_tool_task."""
    return execute_tool_task(tool_name, target)
