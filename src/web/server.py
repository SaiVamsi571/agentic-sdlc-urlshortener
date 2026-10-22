"""
Web Server for AetherSDLC Orchestration Dashboard.
Provides REST endpoints and Server-Sent Events (SSE) for real-time DAG visualization,
HITL interactive approval, blast-radius exploration, and live URL Shortener playground.
"""

from __future__ import annotations
import asyncio
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from src.agents.blast_radius_agent import BlastRadiusAgent
from src.config import BASE_DIR, CONFIG
from src.constants import (
    BLAST_RADIUS_PROPOSALS,
    DASHBOARD_DESCRIPTION,
    DASHBOARD_TITLE,
    DEFAULT_OPENAI_MODEL,
    ERROR_CODE_EMPTY_KEY,
    ERROR_CODE_INVALID_KEY,
    ERROR_CODE_QUOTA_EXHAUSTED,
    MSG_API_KEY_EMPTY,
    MSG_API_KEY_INVALID,
    MSG_QUOTA_EXHAUSTED,
    SCENARIO_AMBIGUOUS,
    SCENARIO_BROWNFIELD,
    SCENARIO_GREENFIELD,
    SCENARIO_PROMPTS,
)
from src.llm import get_llm_client, reload_llm_client, reset_to_deterministic, validate_api_key
from src.orchestrator.hitl import HITLManager
from src.orchestrator.metrics import MetricsTracker
from src.orchestrator.state import PipelineContext, TaskStatus
from src.scenarios.ambiguous import run_ambiguous_scenario
from src.scenarios.brownfield import run_brownfield_scenario
from src.scenarios.greenfield import run_greenfield_scenario
from src.service.app import create_app as create_shortener_app
from src.service.routers import analytics, url

_VALID_SCENARIOS = frozenset({SCENARIO_GREENFIELD, SCENARIO_BROWNFIELD, SCENARIO_AMBIGUOUS})

# Shared state across dashboard and pipeline executions
active_context: Optional[PipelineContext] = None
hitl_manager = HITLManager(auto_approve_default=False)
metrics_tracker = MetricsTracker()
event_subscribers: List[asyncio.Queue] = []


class RunScenarioRequest(BaseModel):
    """Request body for triggering a pipeline scenario."""
    auto_approve: bool = False
    proposal: Optional[str] = "brownfield"


class HITLDecisionRequest(BaseModel):
    """Request body for resolving an HITL governance checkpoint."""
    approved: bool
    reviewer: str = "LeadArchitect"
    comments: str = "Approved via dashboard"


class ValidateLLMKeyRequest(BaseModel):
    """Request body for validating an OpenAI API key."""
    api_key: str


class ConfigureLLMRequest(BaseModel):
    """Request body for configuring OpenAI API integration."""
    api_key: str
    model: Optional[str] = None


def broadcast_event(event: Dict[str, Any]):
    """Push a pipeline event to all connected SSE subscribers."""
    event_str = json.dumps(event)
    for q in list(event_subscribers):
        try:
            q.put_nowait(event_str)
        except Exception:
            pass


def create_dashboard_app() -> FastAPI:
    """Create and configure the AetherSDLC dashboard FastAPI application."""
    app = FastAPI(
        title=DASHBOARD_TITLE,
        version="2.0.0",
        description=DASHBOARD_DESCRIPTION,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount URL Shortener routes directly into root app so they show in /docs
    app.include_router(analytics.router, prefix="/shortener")
    app.include_router(url.router, prefix="/shortener")

    # Also mount sub-app for standalone access
    shortener_app = create_shortener_app()
    app.mount("/shortener-service", shortener_app)

    @app.get("/api/pipeline/status", tags=["Pipeline Orchestrator"])
    async def get_pipeline_status():
        """Return the current pipeline execution snapshot."""
        global active_context
        if not active_context:
            return {"status": "IDLE", "message": "No active pipeline has run yet."}
        return active_context.to_snapshot()

    @app.get("/api/pipeline/metrics", tags=["Pipeline Orchestrator"])
    async def get_metrics():
        """Return aggregated reliability and observability metrics."""
        return metrics_tracker.get_summary()

    @app.get("/api/pipeline/blast-radius", tags=["AST Intelligence"])
    async def get_ast_blast_radius(proposal: Optional[str] = "brownfield"):
        """Run a live AST blast radius query against the current codebase for a given change proposal."""
        agent = BlastRadiusAgent()
        proposed_files = BLAST_RADIUS_PROPOSALS.get(
            proposal, BLAST_RADIUS_PROPOSALS.get("brownfield", [])
        )
        dummy_context = PipelineContext(
            scenario_name=f"blast_radius_query_{proposal}",
            requirement_prompt=f"Query current AST blast radius for proposal: {proposal}",
        )
        dummy_context.set_artifact("proposed_modifications", proposed_files)

        from src.orchestrator.graph import DAGNode
        from src.orchestrator.state import SDLCPhase

        node = DAGNode(
            id="BLAST-QUERY",
            name="AST Query",
            description=f"Query current AST blast radius for proposal: {proposal}",
            phase=SDLCPhase.BLAST_RADIUS,
        )
        report = await agent.run(dummy_context, node)
        report["selected_proposal"] = proposal
        report["available_proposals"] = list(BLAST_RADIUS_PROPOSALS.keys())
        return report

    @app.get("/api/pipeline/report", tags=["Pipeline Orchestrator"])
    async def get_engineering_report(include_cached: bool = False):
        """Retrieve the engineering run report for the active session, or cached archive if requested."""
        global active_context
        report_path = BASE_DIR / "artifacts" / "engineering-summary.md"
        cached_exists = report_path.exists()

        if active_context is None:
            return {
                "status": "IDLE" if not (cached_exists and include_cached) else "AVAILABLE",
                "session_active": False,
                "message": "No pipeline scenario has been executed in the current session.",
                "cached_available": cached_exists,
                "report_markdown": report_path.read_text(encoding="utf-8") if (cached_exists and include_cached) else None,
            }

        if not cached_exists:
            return {
                "status": "RUNNING" if active_context.status.value in ["running", "pending", "waiting_approval"] else "NOT_GENERATED",
                "session_active": True,
                "scenario": active_context.scenario_name,
                "message": "Engineering report is compiling. It will be finalized upon reaching Release Readiness.",
            }

        return {
            "status": "AVAILABLE",
            "session_active": True,
            "scenario": active_context.scenario_name,
            "report_markdown": report_path.read_text(encoding="utf-8"),
        }

    @app.get("/api/pipeline/llm-status", tags=["LLM Engine"])
    async def get_llm_status():
        """Return the active AI engine status (OpenAI vs Deterministic Simulation)."""
        llm = get_llm_client()
        return llm.get_status()

    @app.post("/api/pipeline/validate-llm-key", tags=["LLM Engine"])
    async def validate_key_endpoint(req: ValidateLLMKeyRequest):
        """Validate an OpenAI API key, check quota, and fetch available models.
        Reverts active engine to deterministic if key is invalid or quota is exhausted."""
        result = await validate_api_key(req.api_key)
        if not result["valid"]:
            reset_to_deterministic()
        return result

    @app.post("/api/pipeline/reset-llm", tags=["LLM Engine"])
    async def reset_llm_endpoint():
        """Reset the AI engine back to deterministic mode and return updated status."""
        return reset_to_deterministic()

    @app.post("/api/pipeline/configure-llm", tags=["LLM Engine"])
    async def configure_llm(req: ConfigureLLMRequest):
        """Validate and configure OpenAI API key and model dynamically without server restart."""
        if not req.api_key or not req.api_key.strip():
            reset_to_deterministic()
            raise HTTPException(
                status_code=400,
                detail={"valid": False, "error_code": ERROR_CODE_EMPTY_KEY, "message": MSG_API_KEY_EMPTY}
            )

        # Validate the key with OpenAI before persisting
        validation = await validate_api_key(req.api_key)
        if not validation["valid"]:
            reset_to_deterministic()
            status_code = 429 if validation.get("error_code") == ERROR_CODE_QUOTA_EXHAUSTED else 400
            raise HTTPException(status_code=status_code, detail=validation)

        selected_model = req.model.strip() if req.model else validation.get("default_model", DEFAULT_OPENAI_MODEL)

        env_path = BASE_DIR / ".env"
        lines = []
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if not line.startswith("OPENAI_API_KEY=") and not line.startswith("OPENAI_MODEL="):
                    lines.append(line)
        lines.append(f"OPENAI_API_KEY={req.api_key.strip()}")
        lines.append(f"OPENAI_MODEL={selected_model}")
        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        llm = reload_llm_client()
        status_info = llm.get_status()
        status_info["available_models"] = validation.get("models", [])
        return status_info

    @app.get("/api/pipeline/events", tags=["Pipeline Orchestrator"])
    async def stream_events(request: Request):
        """Server-Sent Events (SSE) stream for real-time pipeline updates."""
        queue: asyncio.Queue = asyncio.Queue()
        event_subscribers.append(queue)

        async def event_generator():
            try:
                # Send initial snapshot
                if active_context:
                    yield {"event": "snapshot", "data": json.dumps(active_context.to_snapshot())}

                while True:
                    if await request.is_disconnected():
                        break
                    event_str = await queue.get()
                    yield {"event": "pipeline_event", "data": event_str}
            finally:
                if queue in event_subscribers:
                    event_subscribers.remove(queue)

        return EventSourceResponse(event_generator())

    @app.post("/api/pipeline/run/{scenario_name}", tags=["Pipeline Orchestrator"])
    async def run_scenario(scenario_name: str, req: RunScenarioRequest = RunScenarioRequest()):
        """Trigger an SDLC pipeline scenario execution."""
        global active_context
        if scenario_name not in _VALID_SCENARIOS:
            raise HTTPException(status_code=400, detail=f"Unknown scenario '{scenario_name}'")

        # Set auto-approve mode on the shared manager
        hitl_manager.auto_approve_default = req.auto_approve

        prompt = SCENARIO_PROMPTS.get(scenario_name, "")
        active_context = PipelineContext(
            scenario_name=scenario_name,
            requirement_prompt=prompt,
        )

        def sse_cb(ev):
            broadcast_event(ev)

        async def runner():
            global active_context
            try:
                if scenario_name == SCENARIO_GREENFIELD:
                    ctx = await run_greenfield_scenario(
                        auto_approve=req.auto_approve,
                        event_callback=sse_cb,
                        hitl_manager=hitl_manager,
                        context=active_context,
                    )
                elif scenario_name == SCENARIO_BROWNFIELD:
                    ctx = await run_brownfield_scenario(
                        auto_approve=req.auto_approve,
                        event_callback=sse_cb,
                        hitl_manager=hitl_manager,
                        context=active_context,
                        proposal=req.proposal,
                    )
                elif scenario_name == SCENARIO_AMBIGUOUS:
                    ctx = await run_ambiguous_scenario(
                        auto_approve=req.auto_approve,
                        event_callback=sse_cb,
                        hitl_manager=hitl_manager,
                        context=active_context,
                    )
                active_context = ctx
                metrics_tracker.record_pipeline_run(ctx)
                broadcast_event({"type": "METRICS_UPDATED", "metrics": metrics_tracker.get_summary()})
            except Exception as e:
                broadcast_event({"type": "PIPELINE_ERROR", "error": str(e)})

        # Run as background task
        asyncio.create_task(runner())
        return {"status": "ACCEPTED", "scenario": scenario_name, "auto_approve": req.auto_approve}

    @app.post("/api/pipeline/hitl/{request_id}", tags=["HITL Governance"])
    async def resolve_hitl(request_id: str, req: HITLDecisionRequest):
        """Resolve an active HITL governance checkpoint."""
        global active_context
        if not active_context:
            raise HTTPException(status_code=400, detail="No active pipeline context.")
        try:
            record = hitl_manager.resolve_checkpoint(
                request_id=request_id,
                context=active_context,
                reviewer=req.reviewer,
                approved=req.approved,
                comments=req.comments,
            )
            broadcast_event({"type": "HITL_RESOLVED", **record.model_dump()})
            return record.model_dump()
        except (KeyError, ValueError) as e:
            raise HTTPException(status_code=404, detail=f"HITL request error: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal HITL error: {str(e)}")

    # Static & Assets directories
    static_dir = BASE_DIR / "src" / "web" / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
        assets_dir = static_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/", tags=["Dashboard"])
    async def index():
        """Serve the main AetherSDLC dashboard page."""
        index_file = BASE_DIR / "src" / "web" / "static" / "index.html"
        if index_file.exists():
            return HTMLResponse(index_file.read_text(encoding="utf-8"))
        return HTMLResponse("<h1>AetherSDLC Dashboard Loading...</h1>")

    return app


dashboard_app = create_dashboard_app()
