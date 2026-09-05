from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents import get_agent, get_dynamic_agent
from database import memory_db
from enterprise_orchestrator import RedTeamEnterpriseOrchestrator, ModelClient
from llm import get_llm_client, LLMConfig, ProviderType
from stream import stream_manager
from tools.registry import get_registry
from authz import authz
from audit import audit
from detection import detector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

app = FastAPI(
    title="RedTeam AI Enterprise Dashboard",
    description="Professional Autonomous Red Teaming and Vulnerability Analysis API",
    version="4.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class AssessmentRequest(BaseModel):
    network_info: str
    system_details: str
    logs: str


class AssessmentResponse(BaseModel):
    status: str
    report: str
    timestamp: str


class AgenticRequest(BaseModel):
    target: str
    task: str
    session_id: str | None = None
    llm_provider: str | None = None  # "anthropic" | "openai"
    phases: list[str] | None = None  # constrain which phases to run


class AgenticResponse(BaseModel):
    session_id: str
    status: str
    result: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# State — keep legacy orchestrator for backward compat
# ---------------------------------------------------------------------------
_client = ModelClient()
_orchestrator = RedTeamEnterpriseOrchestrator(_client)
_llm_client: Any | None = None  # lazy init


# ---------------------------------------------------------------------------
# Existing endpoints (backward compatible)
# ---------------------------------------------------------------------------


@app.get("/", tags=["General"])
async def root():
    return {
        "message": "RedTeam AI Enterprise API is Online",
        "version": "4.0.0",
        "docs": "/docs",
        "endpoints": [
            "/analyze",
            "/agent",
            "/agentic/assess",
            "/agentic/session/{id}",
            "/ws/{session_id}",
            "/authz/targets",
            "/authz/check/{target}",
            "/audit/log",
            "/audit/verify",
            "/detection/start",
            "/detection/stop",
            "/detection/status",
            "/detection/scan",
            "/detection/events",
            "/health",
            "/tools",
            "/phases",
            "/categories",
        ],
    }


@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "version": "4.0.0"}


@app.post("/analyze", response_model=AssessmentResponse, tags=["Analysis"])
async def run_analysis(request: AssessmentRequest):
    """Legacy endpoint — uses the Enterprise Orchestrator with mock LLM."""
    try:
        report = _orchestrator.execute_pipeline(
            network_info=request.network_info,
            system_details=request.system_details,
            logs=request.logs,
        )
        return AssessmentResponse(
            status="success",
            report=report,
            timestamp=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agent", tags=["Analysis"])
async def run_agent(task: str = Query(..., description="Natural language task")):
    """Legacy endpoint — routes task to the appropriate pipeline agent."""
    from agents.base import BaseAgent
    agent: BaseAgent = get_agent(task)
    result = await agent.run(task)
    return result


# ---------------------------------------------------------------------------
# New agentic endpoint — DynamicAgent with full LLM tool-use
# ---------------------------------------------------------------------------


@app.post("/agentic/assess", response_model=AgenticResponse, tags=["Agentic"])
async def agentic_assess(request: AgenticRequest):
    """Run an LLM-driven agentic assessment.

    The agent uses Claude or GPT to reason about the task, dynamically
    choose tools, execute them, and produce a final analysis.
    """
    session_id = request.session_id or str(uuid.uuid4())

    try:
        llm_client = _get_llm_client(request.llm_provider)

        agent = get_dynamic_agent(
            llm_client=llm_client,
            memory_db=memory_db,
            stream_manager=stream_manager,
            context={
                "target": request.target,
                "session_id": session_id,
                "phases": request.phases,
            },
        )

        result = await agent.run(request.task)

        return AgenticResponse(
            session_id=session_id,
            status="success",
            result=result,
        )
    except Exception as e:
        logger.exception("Agentic assessment failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agentic/session/{session_id}", tags=["Agentic"])
async def get_session(session_id: str):
    """Retrieve full session history and memory context."""
    try:
        history = await memory_db.get_session_history(session_id)
        return {
            "session_id": session_id,
            "conversation": history,
            "turn_count": len(history),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/agentic/session/{session_id}", tags=["Agentic"])
async def clear_session(session_id: str):
    """Clear session memory."""
    # For now, no-op. In production, delete from memory_db.
    return {"status": "cleared", "session_id": session_id}


# ---------------------------------------------------------------------------
# WebSocket live-streaming
# ---------------------------------------------------------------------------


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(ws: WebSocket, session_id: str):
    await stream_manager.connect(session_id, ws)
    try:
        # Keep the connection alive — agent pushes events via stream_manager
        while True:
            # Wait for client messages (ping / cancel)
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))
            elif data == "cancel":
                logger.info(f"Cancellation requested for session {session_id}")
                await ws.send_text(json.dumps({"type": "cancelled"}))
                break
    except WebSocketDisconnect:
        pass
    finally:
        await stream_manager.disconnect(session_id, ws)


# ---------------------------------------------------------------------------
# Tools & category endpoints (used by frontend)
# ---------------------------------------------------------------------------


@app.get("/tools", tags=["Tools"])
async def list_tools(phase: str | None = None):
    """List all available tools, optionally filtered by phase."""
    registry = get_registry()
    if phase:
        tools = registry.get_tools_by_phase(phase)
    else:
        tools = registry.list_tools()
    return {
        "tools": [
            {
                "name": t.name,
                "phase": t.phase,
                "description": t.description,
                "timeout": t.timeout,
                "priority": t.priority,
            }
            for t in tools
        ]
    }


@app.get("/categories", tags=["Tools"])
async def list_categories():
    """List all assessment phases/categories."""
    registry = get_registry()
    return {"categories": registry.categories}


@app.get("/phases", tags=["Tools"])
async def list_phases():
    """List all phase names in pipeline order."""
    registry = get_registry()
    return {"phases": registry.phases}


# ---------------------------------------------------------------------------
# Authorization (target whitelist management)
# ---------------------------------------------------------------------------


class AuthorizeRequest(BaseModel):
    target: str
    description: str = ""
    phases: str = "*"
    tools: str = "*"
    expires_at: str | None = None
    created_by: str = "admin"


@app.post("/authz/targets", tags=["Authorization"])
async def authorize_target(req: AuthorizeRequest):
    """Add a target to the authorized whitelist."""
    result = authz.authorize(
        target=req.target,
        description=req.description,
        phases=req.phases,
        tools=req.tools,
        expires_at=req.expires_at,
        created_by=req.created_by,
    )
    return {"status": "authorized", **result}


@app.get("/authz/targets", tags=["Authorization"])
async def list_authorized():
    """List all authorized targets."""
    return {"targets": authz.list_authorized()}


@app.delete("/authz/targets/{target}", tags=["Authorization"])
async def revoke_target(target: str):
    """Remove a target from the authorized whitelist."""
    if authz.revoke(target):
        return {"status": "revoked", "target": target}
    raise HTTPException(status_code=404, detail=f"Target '{target}' not found")


@app.delete("/authz/targets/id/{record_id}", tags=["Authorization"])
async def revoke_by_id(record_id: str):
    """Remove an authorization entry by its ID."""
    if authz.revoke_by_id(record_id):
        return {"status": "revoked", "id": record_id}
    raise HTTPException(status_code=404, detail=f"Record '{record_id}' not found")


@app.get("/authz/check/{target}", tags=["Authorization"])
async def check_authorized(target: str, tool: str | None = None, phase: str | None = None):
    """Check if a target is authorized for a given tool or phase."""
    allowed, reason = authz.check(target, tool_name=tool, phase=phase)
    return {
        "target": target,
        "allowed": allowed,
        "reason": reason,
    }


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------


@app.get("/audit/log", tags=["Audit"])
async def query_audit(
    target: str | None = None,
    tool: str | None = None,
    limit: int = 100,
    offset: int = 0,
):
    """Query the tamper-evident audit log."""
    return {
        "entries": audit.query(target=target, tool_name=tool, limit=limit, offset=offset),
    }


@app.get("/audit/verify", tags=["Audit"])
async def verify_audit_chain():
    """Verify the integrity of the audit chain hash."""
    valid = audit.verify_chain()
    return {
        "chain_intact": valid,
        "status": "verified" if valid else "TAMPERED — chain hash mismatch",
    }


# ---------------------------------------------------------------------------
# Detection (wireless monitoring)
# ---------------------------------------------------------------------------


@app.post("/detection/start", tags=["Detection"])
async def start_detection(interface: str = "wlan0"):
    """Start the background wireless monitoring engine."""
    status = await detector.start(interface=interface)
    return {"status": status, "interface": interface}


@app.post("/detection/stop", tags=["Detection"])
async def stop_detection():
    """Stop the background wireless monitoring engine."""
    status = await detector.stop()
    return {"status": status}


@app.get("/detection/status", tags=["Detection"])
async def detection_status():
    """Check if the detection engine is running."""
    return {"running": detector.is_running}


@app.post("/detection/scan", tags=["Detection"])
async def scan_once(interface: str = "wlan0"):
    """Run a one-shot wireless scan (no background engine needed)."""
    events = await detector.scan_once(interface=interface)
    return {"events": events, "count": len(events)}


@app.get("/detection/events", tags=["Detection"])
async def query_detection_events(
    event_type: str | None = None,
    severity: str | None = None,
    limit: int = 100,
    offset: int = 0,
):
    """Query detection events."""
    return {
        "events": detector.get_events(
            event_type=event_type,
            severity=severity,
            limit=limit,
            offset=offset,
        ),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_llm_client(provider: str | None = None):
    """Resolve LLM client, optionally overriding the configured provider."""
    global _llm_client
    if provider:
        config = LLMConfig.from_env()
        if provider.lower() == "anthropic":
            config.provider = ProviderType.ANTHROPIC
        elif provider.lower() == "openai":
            config.provider = ProviderType.OPENAI
        return get_llm_client(config)
    if _llm_client is None:
        _llm_client = get_llm_client()
    return _llm_client


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
