"""
Comprehensive Tests for the Agentic Orchestration Layer.
Validates DAG scheduling, parallel layering, gates, HITL governance, dynamic re-planning,
rollback safety, guardrails, and reliability metrics.
"""

from __future__ import annotations
import asyncio
import pytest
from pathlib import Path
from src.agents.base import BaseAgent
from src.orchestrator.engine import OrchestrationEngine
from src.orchestrator.graph import DAGNode, ExecutionGraph, GateCondition
from src.orchestrator.guardrails import GuardrailEngine
from src.orchestrator.hitl import HITLManager
from src.orchestrator.metrics import MetricsTracker
from src.orchestrator.replanner import DynamicReplanner
from src.orchestrator.rollback import RollbackController
from src.orchestrator.state import PipelineContext, SDLCPhase, TaskStatus

class MockSuccessAgent(BaseAgent):
    def __init__(self, name="MockSuccess"):
        super().__init__(name=name, phase=SDLCPhase.IMPLEMENTATION)

    async def run(self, context: PipelineContext, node: DAGNode):
        context.set_artifact(f"art_{node.id}", f"output_{node.id}")
        return {"status": "success", "node": node.id}

class MockFailingThenSucceedingAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="MockFlaky", phase=SDLCPhase.TESTING)
        self.attempts = 0

    async def run(self, context: PipelineContext, node: DAGNode):
        self.attempts += 1
        if self.attempts == 1:
            raise AssertionError("Simulated test failure on attempt 1")
        return {"status": "recovered", "attempts": self.attempts}

class MockPermanentlyFailingAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="MockBroken", phase=SDLCPhase.TESTING)
        self.attempts = 0

    async def run(self, context: PipelineContext, node: DAGNode):
        self.attempts += 1
        raise AssertionError(f"Persistent failure on attempt {self.attempts}")

def test_dag_cycle_detection():
    graph = ExecutionGraph("CycleTest")
    graph.add_node(DAGNode(id="A", name="Node A", phase=SDLCPhase.REQUIREMENTS, description="A"))
    graph.add_node(DAGNode(id="B", name="Node B", phase=SDLCPhase.ARCHITECTURE, description="B", dependencies=["A"]))
    # Adding cycle: A depends on B
    graph.nodes["A"].dependencies.append("B")
    graph.graph.add_edge("B", "A")

    with pytest.raises(ValueError, match="Cyclic dependency detected"):
        graph.get_topological_order()

def test_dag_execution_layers_concurrency():
    graph = ExecutionGraph("LayerTest")
    # Layer 0: Root node
    graph.add_node(DAGNode(id="ROOT", name="Root", phase=SDLCPhase.REQUIREMENTS, description="Root"))
    # Layer 1: Two parallel nodes depending on ROOT (Fan-out)
    graph.add_node(DAGNode(id="P1", name="Parallel 1", phase=SDLCPhase.IMPLEMENTATION, description="P1", dependencies=["ROOT"]))
    graph.add_node(DAGNode(id="P2", name="Parallel 2", phase=SDLCPhase.IMPLEMENTATION, description="P2", dependencies=["ROOT"]))
    # Layer 2: Join node depending on both P1 and P2 (Fan-in / synchronization)
    graph.add_node(DAGNode(id="JOIN", name="Join", phase=SDLCPhase.TESTING, description="Join", dependencies=["P1", "P2"]))

    layers = graph.get_execution_layers()
    assert len(layers) == 3
    assert layers[0] == ["ROOT"]
    assert set(layers[1]) == {"P1", "P2"}
    assert layers[2] == ["JOIN"]

def test_orchestrator_parallel_execution_and_gates():
    async def _inner():
        graph = ExecutionGraph("PipelineTest")
        graph.add_node(DAGNode(
            id="N1",
            name="Node 1",
            phase=SDLCPhase.REQUIREMENTS,
            description="N1",
            exit_gate=GateCondition(name="N1_Gate", description="Produces art_N1", required_artifacts=["art_N1"])
        ))
        graph.add_node(DAGNode(
            id="N2",
            name="Node 2",
            phase=SDLCPhase.IMPLEMENTATION,
            description="N2",
            dependencies=["N1"],
            entry_gate=GateCondition(name="N2_Gate", description="Requires art_N1", required_artifacts=["art_N1"])
        ))

        context = PipelineContext(scenario_name="test_pipeline")
        engine = OrchestrationEngine(hitl_manager=HITLManager(auto_approve_default=True))
        engine.register_agent("N1", MockSuccessAgent("Agent1"))
        engine.register_agent("N2", MockSuccessAgent("Agent2"))

        final_ctx = await engine.execute_pipeline(graph, context)
        assert final_ctx.status == TaskStatus.COMPLETED
        assert final_ctx.get_artifact("art_N1") == "output_N1"
        assert final_ctx.get_artifact("art_N2") == "output_N2"
        assert len(final_ctx.audit_events) > 0

    asyncio.run(_inner())

def test_hitl_approval_and_rejection():
    async def _inner():
        hitl_mgr = HITLManager(auto_approve_default=False)
        ctx = PipelineContext(scenario_name="hitl_test")
        req = hitl_mgr.create_checkpoint(ctx, "GATE_NODE", "Review Gate", "Please approve")
        
        # Resolve via approval
        hitl_mgr.resolve_checkpoint(req.request_id, ctx, reviewer="LeadArchitect", approved=True, comments="LGTM")
        record = await hitl_mgr.wait_for_decision(req.request_id, ctx, timeout_seconds=1.0)
        assert record.approved is True
        assert record.reviewer == "LeadArchitect"
        assert len(ctx.approvals) == 1

    asyncio.run(_inner())

def test_dynamic_replanning_self_healing():
    async def _inner():
        graph = ExecutionGraph("ReplanningTest")
        graph.add_node(DAGNode(id="FLAKY", name="Flaky Node", phase=SDLCPhase.TESTING, description="Flaky"))

        context = PipelineContext(scenario_name="replan_test")
        engine = OrchestrationEngine(hitl_manager=HITLManager(auto_approve_default=True))
        flaky_agent = MockFailingThenSucceedingAgent()
        engine.register_agent("FLAKY", flaky_agent)

        final_ctx = await engine.execute_pipeline(graph, context)
        assert final_ctx.status == TaskStatus.COMPLETED
        assert final_ctx.replans_count == 1
        assert final_ctx.node_retries["FLAKY"] == 1
        assert flaky_agent.attempts == 2 # Recovered on attempt 2!

    asyncio.run(_inner())

def test_dynamic_replanning_exhaustion_safe_stop():
    async def _inner():
        graph = ExecutionGraph("ExhaustionTest")
        graph.add_node(DAGNode(id="BROKEN", name="Broken Test Node", phase=SDLCPhase.TESTING, description="Always fails"))

        context = PipelineContext(scenario_name="exhaustion_test")
        replanner = DynamicReplanner(max_node_retries=2)
        engine = OrchestrationEngine(hitl_manager=HITLManager(auto_approve_default=True), replanner=replanner)
        broken_agent = MockPermanentlyFailingAgent()
        engine.register_agent("BROKEN", broken_agent)

        final_ctx = await engine.execute_pipeline(graph, context)

        assert final_ctx.status == TaskStatus.FAILED
        assert context.node_statuses["BROKEN"] == TaskStatus.FAILED
        assert context.node_retries["BROKEN"] == 2
        assert broken_agent.attempts == 3 # Initial attempt + 2 retries
        assert any("SAFE_STOP" in ev.action or "RETRY_BUDGET_EXHAUSTED" in ev.action or "PIPELINE_FAILED" in ev.action for ev in context.audit_events)

    asyncio.run(_inner())

def test_guardrails_security_detection():
    guardrails = GuardrailEngine()

    # Insecure code: SQL injection and hardcoded secret
    bad_code = '''
api_key = "ghp_1234567890abcdef1234567890abcdef1234"
def query_db(user_input):
    cursor.execute(f"SELECT * FROM users WHERE name = '{user_input}'")
'''
    report = guardrails.evaluate_code("service/insecure.py", bad_code)
    assert report.passed is False
    assert len(report.violations) >= 2
    rule_ids = [v.rule_id for v in report.violations]
    assert "SEC-001-HARDCODED-SECRETS" in rule_ids
    assert "SEC-002-RAW-SQL-INJECTION" in rule_ids

def test_guardrails_gdpr_ip_detection():
    guardrails = GuardrailEngine()
    # Code storing raw client IP without hashing
    bad_analytics = '''
def log_click(client_ip):
    db.save(client_ip=client_ip)
'''
    report = guardrails.evaluate_code("service/analytics.py", bad_analytics)
    assert report.passed is False
    assert any("COMP-001-GDPR" in v.rule_id for v in report.violations)

def test_rollback_controller(tmp_path):
    rb = RollbackController(tmp_path)
    test_file = tmp_path / "important_config.py"
    test_file.write_text("ORIGINAL_CONTENT", encoding="utf-8")

    ctx = PipelineContext(scenario_name="rollback_test")
    rb.create_checkpoint("CP1", "Before risky change", [test_file], context=ctx)

    # Corrupt or modify file
    test_file.write_text("BROKEN_CONTENT", encoding="utf-8")
    assert test_file.read_text(encoding="utf-8") == "BROKEN_CONTENT"

    # Execute Rollback
    reverted = rb.execute_rollback("CP1", ctx, reason="Verification tests failed")
    assert reverted is True
    assert test_file.read_text(encoding="utf-8") == "ORIGINAL_CONTENT"
    assert ctx.status == TaskStatus.ROLLED_BACK
    assert ctx.rollbacks_count == 1


def test_sandbox_execution_environment(tmp_path):
    from src.orchestrator.sandbox import SandboxExecutionEnvironment

    sandbox = SandboxExecutionEnvironment(sandbox_dir=tmp_path / "sandbox")
    result = sandbox.validate_patch_integrity("diff --git a/test.py b/test.py")
    assert result["valid"] is True
    assert result["modules_verified"] > 0
    assert result["isolation_status"] == "ZERO_BASELINE_MUTATION"
    sandbox.cleanup()

