"""
Scenario 3: Ambiguous Requirements & Controlled Disambiguation.
Takes a vague, underspecified stakeholder prompt, computes multi-dimensional ambiguity scores,
executes an interactive clarification gate, normalizes into canonical engineering specifications,
and safely executes the workflow.
"""

from __future__ import annotations
import asyncio
from typing import Callable, Optional
from src.agents.architecture_agent import ArchitectureAgent
from src.agents.coder_agent import CoderAgent
from src.agents.release_agent import ReleaseAgent
from src.agents.requirements_agent import RequirementsAgent
from src.agents.security_agent import SecurityAgent
from src.agents.test_agent import TestAgent
from src.constants import SCENARIO_AMBIGUOUS, SCENARIO_PROMPTS
from src.orchestrator.engine import OrchestrationEngine
from src.orchestrator.graph import DAGNode, ExecutionGraph, GateCondition
from src.orchestrator.hitl import HITLManager
from src.orchestrator.state import PipelineContext, SDLCPhase

def build_ambiguous_graph() -> ExecutionGraph:
    graph = ExecutionGraph(name="Ambiguous_Requirement_Disambiguation_Pipeline")

    # Node 1: Ambiguity Detection & Scoring
    graph.add_node(DAGNode(
        id="AMBIG-01",
        name="Ambiguity Scoring & Missing Constraint Identification",
        phase=SDLCPhase.REQUIREMENTS,
        description="Analyze vague intent, identify underspecified SLAs/TTL/analytics, and compute ambiguity score (0.0 - 1.0).",
        exit_gate=GateCondition(name="AmbiguityScored", description="Needs ambiguity assessment", required_artifacts=["ambiguity_assessment"])
    ))

    # Node 2: Interactive Disambiguation & Stakeholder Alignment Gate
    graph.add_node(DAGNode(
        id="HITL-DISAMBIG-01",
        name="Stakeholder Clarification & Assumptions Gate",
        phase=SDLCPhase.HITL_APPROVAL,
        description="Present ambiguities and proposed architectural defaults to human stakeholder for resolution.",
        dependencies=["AMBIG-01"],
        is_hitl_checkpoint=True,
        hitl_prompt="Review 4 detected ambiguities: 1) LRU In-memory Caching, 2) 30-day default TTL + HTTP 410 Gone, 3) UTM campaign metadata tags, 4) Sliding-window rate limiting. Confirm resolution.",
        metadata={"risk_level": "HIGH"}
    ))

    # Node 3: Architecture & ADR Synthesis based on Resolved Constraints
    graph.add_node(DAGNode(
        id="ARCH-AMBIG-01",
        name="Synthesize Architecture from Clarified Constraints",
        phase=SDLCPhase.ARCHITECTURE,
        description="Formalize ADRs, component contracts, and schemas derived from resolved requirements.",
        dependencies=["HITL-DISAMBIG-01"]
    ))

    # Node 4: Implementation
    graph.add_node(DAGNode(
        id="CODE-AMBIG-01",
        name="Targeted Implementation & Verification",
        phase=SDLCPhase.IMPLEMENTATION,
        description="Implement validated features: LRU caching, UTM campaign extraction, and HTTP 410 expired handling.",
        dependencies=["ARCH-AMBIG-01"]
    ))

    # Node 5: Security SAST Audit
    graph.add_node(DAGNode(
        id="SEC-AMBIG-01",
        name="Security & Policy Compliance Verification",
        phase=SDLCPhase.GUARDRAILS_PRE,
        description="Ensure SSRF and GDPR policies remain intact under new marketing and expiration rules.",
        dependencies=["CODE-AMBIG-01"]
    ))

    # Node 6: Verification Tests
    graph.add_node(DAGNode(
        id="TEST-AMBIG-01",
        name="Targeted Test Execution & Assertion Validation",
        phase=SDLCPhase.TESTING,
        description="Verify expired URL returns 410 Gone and UTM tags are correctly logged.",
        dependencies=["SEC-AMBIG-01"]
    ))

    # Node 7: Release Readiness
    graph.add_node(DAGNode(
        id="REL-AMBIG-01",
        name="Release Readiness Sign-Off",
        phase=SDLCPhase.RELEASE_READINESS,
        description="Compile release manifest and traceability lineage report.",
        dependencies=["TEST-AMBIG-01"]
    ))

    return graph

async def run_ambiguous_scenario(
    auto_approve: bool = True,
    event_callback: Optional[Callable] = None,
    hitl_manager: Optional[HITLManager] = None,
    context: Optional[PipelineContext] = None
) -> PipelineContext:
    graph = build_ambiguous_graph()
    if context is None:
        context = PipelineContext(
            scenario_name=SCENARIO_AMBIGUOUS,
            requirement_prompt=SCENARIO_PROMPTS[SCENARIO_AMBIGUOUS],
        )

    hitl_mgr = hitl_manager or HITLManager(auto_approve_default=auto_approve)
    engine = OrchestrationEngine(hitl_manager=hitl_mgr, event_callback=event_callback)

    engine.register_agent("AMBIG-01", RequirementsAgent())
    engine.register_agent("ARCH-AMBIG-01", ArchitectureAgent())
    engine.register_agent("CODE-AMBIG-01", CoderAgent())
    engine.register_agent("SEC-AMBIG-01", SecurityAgent())
    engine.register_agent("TEST-AMBIG-01", TestAgent())
    engine.register_agent("REL-AMBIG-01", ReleaseAgent())

    return await engine.execute_pipeline(graph, context)
