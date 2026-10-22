"""
Scenario 2: Brownfield Enhancement & Refactoring.
Adds Sliding-Window Rate Limiting and Granular Device/Referrer Click Analytics to the existing codebase.
Demonstrates AST blast-radius reasoning, change-control guardrails, and HITL schema sign-off.
"""
import asyncio
from typing import Callable, Optional
from src.agents.blast_radius_agent import BlastRadiusAgent
from src.agents.coder_agent import CoderAgent
from src.agents.release_agent import ReleaseAgent
from src.agents.requirements_agent import RequirementsAgent
from src.agents.security_agent import SecurityAgent
from src.agents.test_agent import TestAgent
from src.constants import BLAST_RADIUS_PROPOSALS, SCENARIO_BROWNFIELD, SCENARIO_PROMPTS
from src.orchestrator.engine import OrchestrationEngine
from src.orchestrator.graph import DAGNode, ExecutionGraph, GateCondition
from src.orchestrator.hitl import HITLManager
from src.orchestrator.state import PipelineContext, SDLCPhase

def build_brownfield_graph() -> ExecutionGraph:
    graph = ExecutionGraph(name="Brownfield_Analytics_RateLimiter_Pipeline")

    # Node 1: Requirements Analysis for Brownfield Feature
    graph.add_node(DAGNode(
        id="REQ-BROWN-01",
        name="Brownfield Feature Scope & Backwards-Compatibility Requirements",
        phase=SDLCPhase.REQUIREMENTS,
        description="Define enhancement scope for rate limiting and UTM/device analytics while preserving existing contracts."
    ))

    # Node 2: AST Codebase Reasoning & Blast Radius Evaluation
    graph.add_node(DAGNode(
        id="BLAST-01",
        name="AST Codebase Reasoning & Impact Radius",
        phase=SDLCPhase.BLAST_RADIUS,
        description="Parse codebase AST, map symbol dependencies, assess affected models and API routes.",
        dependencies=["REQ-BROWN-01"],
        exit_gate=GateCondition(name="BlastRadiusReady", description="Requires blast radius report", required_artifacts=["blast_radius_report"])
    ))

    # Node 3: HITL Change Control Gate (Schema & Contract Sign-Off)
    graph.add_node(DAGNode(
        id="HITL-SCHEMA-01",
        name="HITL Change Control & Blast Radius Sign-Off",
        phase=SDLCPhase.HITL_APPROVAL,
        description="Human engineer reviews affected modules and confirms backwards compatibility before code modification.",
        dependencies=["BLAST-01"],
        is_hitl_checkpoint=True,
        hitl_prompt="Review AST blast radius report. Confirm non-breaking schema additions for analytics and rate-limiting middleware.",
        metadata={"risk_level": "MEDIUM"}
    ))

    # Node 4: Incremental Implementation (Coder)
    graph.add_node(DAGNode(
        id="CODE-BROWN-01",
        name="Incremental Module Implementation",
        phase=SDLCPhase.IMPLEMENTATION,
        description="Implement rate-limiting middleware and analytics aggregation without altering existing /api/v1/shorten contracts.",
        dependencies=["HITL-SCHEMA-01"]
    ))

    # Node 5: Security & Change Control Policy Guardrails
    graph.add_node(DAGNode(
        id="SEC-BROWN-01",
        name="Policy Guardrails & Backwards-Compatibility Audit",
        phase=SDLCPhase.GUARDRAILS_PRE,
        description="Verify no API route deletions occurred and GDPR salted IP masking is maintained.",
        dependencies=["CODE-BROWN-01"]
    ))

    # Node 6: Regression & Concurrency Testing
    graph.add_node(DAGNode(
        id="TEST-BROWN-01",
        name="Regression, Integration, and Concurrency Tests",
        phase=SDLCPhase.TESTING,
        description="Execute full test suite ensuring zero regressions and high concurrency rate limiting.",
        dependencies=["SEC-BROWN-01"]
    ))

    # Node 7: Release Readiness
    graph.add_node(DAGNode(
        id="REL-BROWN-01",
        name="Release Readiness & Changelog Generation",
        phase=SDLCPhase.RELEASE_READINESS,
        description="Compile version 1.1.0 release manifest and rollback checkpoint.",
        dependencies=["TEST-BROWN-01"]
    ))

    return graph

async def run_brownfield_scenario(
    auto_approve: bool = True,
    event_callback: Optional[Callable] = None,
    hitl_manager: Optional[HITLManager] = None,
    context: Optional[PipelineContext] = None,
    proposal: Optional[str] = "brownfield",
) -> PipelineContext:
    graph = build_brownfield_graph()
    if context is None:
        context = PipelineContext(
            scenario_name=SCENARIO_BROWNFIELD,
            requirement_prompt=SCENARIO_PROMPTS[SCENARIO_BROWNFIELD],
        )

    # Set proposed modifications in context so AST Blast Radius agent evaluates the selected proposal
    selected_proposal = proposal or "brownfield"
    proposed_files = BLAST_RADIUS_PROPOSALS.get(
        selected_proposal, BLAST_RADIUS_PROPOSALS.get("brownfield", [])
    )
    context.set_artifact("proposed_modifications", proposed_files)
    context.set_artifact("selected_proposal", selected_proposal)

    hitl_mgr = hitl_manager or HITLManager(auto_approve_default=auto_approve)
    engine = OrchestrationEngine(hitl_manager=hitl_mgr, event_callback=event_callback)

    engine.register_agent("REQ-BROWN-01", RequirementsAgent())
    engine.register_agent("BLAST-01", BlastRadiusAgent())
    engine.register_agent("CODE-BROWN-01", CoderAgent())
    engine.register_agent("SEC-BROWN-01", SecurityAgent())
    engine.register_agent("TEST-BROWN-01", TestAgent())
    engine.register_agent("REL-BROWN-01", ReleaseAgent())

    return await engine.execute_pipeline(graph, context)
