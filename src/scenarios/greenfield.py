"""
Scenario 1: Greenfield Implementation.
Builds the complete URL shortener system from a clean-slate specification.
Demonstrates requirement normalization, ADR formulation, parallel execution, testing, and release gating.
"""

from __future__ import annotations
import asyncio
from typing import Callable, Optional
from src.agents.architecture_agent import ArchitectureAgent
from src.agents.coder_agent import CoderAgent
from src.agents.decomposition_agent import DecompositionAgent
from src.agents.release_agent import ReleaseAgent
from src.agents.requirements_agent import RequirementsAgent
from src.agents.security_agent import SecurityAgent
from src.agents.test_agent import TestAgent
from src.constants import SCENARIO_GREENFIELD, SCENARIO_PROMPTS
from src.orchestrator.engine import OrchestrationEngine
from src.orchestrator.graph import DAGNode, ExecutionGraph, GateCondition
from src.orchestrator.hitl import HITLManager
from src.orchestrator.state import PipelineContext, SDLCPhase

def build_greenfield_graph() -> ExecutionGraph:
    graph = ExecutionGraph(name="Greenfield_URL_Shortener_Pipeline")

    # Node 1: Requirements Normalization
    graph.add_node(DAGNode(
        id="REQ-01",
        name="Requirements Understanding & Ambiguity Analysis",
        phase=SDLCPhase.REQUIREMENTS,
        description="Interpret prompt, score ambiguity, normalize into SRS with locked assumptions.",
        exit_gate=GateCondition(name="SRS_Created", description="Requires SRS artifact", required_artifacts=["requirements_srs"])
    ))

    # Node 2: System Architecture & ADR Formulation
    graph.add_node(DAGNode(
        id="ARCH-01",
        name="System Architecture & ADR Synthesis",
        phase=SDLCPhase.ARCHITECTURE,
        description="Formulate ADRs (Base62, Cache, GDPR), API schemas, and component model.",
        dependencies=["REQ-01"],
        entry_gate=GateCondition(name="SRS_Available", description="Needs SRS", required_artifacts=["requirements_srs"]),
        exit_gate=GateCondition(name="Arch_Ready", description="Needs architecture", required_artifacts=["architecture_manifest"])
    ))

    # Node 3: Task Decomposition
    graph.add_node(DAGNode(
        id="DECOMP-01",
        name="WBS & Concurrency Task Decomposition",
        phase=SDLCPhase.DECOMPOSITION,
        description="Deconstruct architecture into parallel and serial work packages.",
        dependencies=["ARCH-01"],
        entry_gate=GateCondition(name="Arch_Ready", description="Needs architecture", required_artifacts=["architecture_manifest"])
    ))

    # Node 4: Implementation (Coder)
    graph.add_node(DAGNode(
        id="CODE-01",
        name="Modular Implementation & Code Verification",
        phase=SDLCPhase.IMPLEMENTATION,
        description="Implement and verify domain models, core encoders, cache, and REST routers.",
        dependencies=["DECOMP-01"]
    ))

    # Node 5: Security SAST & Policy Guardrails
    graph.add_node(DAGNode(
        id="SEC-01",
        name="Security SAST & Policy Guardrail Audit",
        phase=SDLCPhase.GUARDRAILS_PRE,
        description="Evaluate secrets, SQL injection, SSRF filters, and GDPR IP masking.",
        dependencies=["CODE-01"]
    ))

    # Node 6: Automated Test Suite Execution
    graph.add_node(DAGNode(
        id="TEST-01",
        name="Automated Test Suite Execution (Unit, API, Concurrency)",
        phase=SDLCPhase.TESTING,
        description="Run pytest suite to verify all acceptance criteria and race-condition safety.",
        dependencies=["SEC-01"]
    ))

    # Node 7: Human-in-the-Loop Governance Gate
    graph.add_node(DAGNode(
        id="HITL-01",
        name="Governance & Architecture Review Sign-Off",
        phase=SDLCPhase.HITL_APPROVAL,
        description="Human operator inspects test results, SAST report, and approves release progression.",
        dependencies=["TEST-01"],
        is_hitl_checkpoint=True,
        hitl_prompt="Review greenfield implementation artifacts and test suite outcomes for release approval.",
        metadata={"risk_level": "LOW"}
    ))

    # Node 8: Release Readiness
    graph.add_node(DAGNode(
        id="REL-01",
        name="Release Readiness & Manifest Compilation",
        phase=SDLCPhase.RELEASE_READINESS,
        description="Generate certified release manifest and rollback procedure.",
        dependencies=["HITL-01"]
    ))

    return graph

async def run_greenfield_scenario(
    auto_approve: bool = True,
    event_callback: Optional[Callable] = None,
    hitl_manager: Optional[HITLManager] = None,
    context: Optional[PipelineContext] = None
) -> PipelineContext:
    graph = build_greenfield_graph()
    if context is None:
        context = PipelineContext(
            scenario_name=SCENARIO_GREENFIELD,
            requirement_prompt=SCENARIO_PROMPTS[SCENARIO_GREENFIELD],
        )

    hitl_mgr = hitl_manager or HITLManager(auto_approve_default=auto_approve)
    engine = OrchestrationEngine(hitl_manager=hitl_mgr, event_callback=event_callback)

    # Register Agents
    engine.register_agent("REQ-01", RequirementsAgent())
    engine.register_agent("ARCH-01", ArchitectureAgent())
    engine.register_agent("DECOMP-01", DecompositionAgent())
    engine.register_agent("CODE-01", CoderAgent())
    engine.register_agent("SEC-01", SecurityAgent())
    engine.register_agent("TEST-01", TestAgent())
    # HITL-01 has no agent; handled by HITL checkpoint gate
    engine.register_agent("REL-01", ReleaseAgent())

    return await engine.execute_pipeline(graph, context)
