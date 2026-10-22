"""
Dynamic Re-planning and Feedback Loop Controller.
Enables non-linear, stateful self-healing when upstream outputs change or downstream tests/gates fail.
Avoids restart from scratch by isolating affected subgraphs.
"""
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field
from src.orchestrator.graph import ExecutionGraph
from src.orchestrator.state import AuditLevel, PipelineContext, TaskStatus

class ReplanAction(BaseModel):
    action_type: str # RETRY_WITH_FEEDBACK, TARGETED_RESCHEDULE, ROLLBACK_SAFE_STOP
    failed_node_id: str
    repaired_nodes: List[str]
    feedback_prompt: str
    retry_attempt: int
    max_retries: int

class DynamicReplanner:
    """
    Analyzes execution failures (e.g. test assertions, linter errors, policy rejections)
    and dynamically re-plans minimal downstream subgraphs with contextual repair instructions.
    """
    def __init__(self, max_node_retries: int = 3):
        self.max_node_retries = max_node_retries

    def plan_recovery(
        self,
        failed_node_id: str,
        failure_reason: str,
        error_details: str,
        graph: ExecutionGraph,
        context: PipelineContext
    ) -> ReplanAction:
        current_retries = context.node_retries.get(failed_node_id, 0)
        
        context.add_audit_event(
            action="EVALUATING_DYNAMIC_REPLAN",
            message=f"Node '{failed_node_id}' failed: {failure_reason}. Analyzing recovery graph...",
            node_id=failed_node_id,
            level=AuditLevel.WARN,
            metadata={"current_retries": current_retries, "max_retries": self.max_node_retries}
        )

        # Check bounded retry limit
        if current_retries >= self.max_node_retries:
            context.add_audit_event(
                action="RETRY_BUDGET_EXHAUSTED",
                message=f"Node '{failed_node_id}' exceeded max retries ({self.max_node_retries}). Triggering safe-stop.",
                node_id=failed_node_id,
                level=AuditLevel.CRITICAL
            )
            return ReplanAction(
                action_type="ROLLBACK_SAFE_STOP",
                failed_node_id=failed_node_id,
                repaired_nodes=[failed_node_id],
                feedback_prompt=f"Maximum bounded retries exceeded. Terminal failure: {failure_reason}",
                retry_attempt=current_retries,
                max_retries=self.max_node_retries
            )

        # Increment retry counter
        context.node_retries[failed_node_id] = current_retries + 1
        context.replans_count += 1

        # Identify minimal repair subgraph
        # For testing failure: we usually need to re-invoke Implementation (Coder) with test failure context, then Code Review, then Retest
        upstream = graph.get_upstream_nodes(failed_node_id)
        downstream = graph.get_all_downstream_nodes(failed_node_id)

        repaired_nodes: List[str] = []
        if "test" in failed_node_id.lower():
            # If testing failed, find the implementation node among upstreams
            code_nodes = [u for u in upstream if "code" in u.lower() or "impl" in u.lower()]
            if code_nodes:
                repaired_nodes.extend(code_nodes)
            repaired_nodes.append(failed_node_id)
            repaired_nodes.extend(downstream)
        else:
            repaired_nodes = [failed_node_id] + downstream

        # Reset states for repaired nodes so they execute again
        for nid in repaired_nodes:
            context.node_statuses[nid] = TaskStatus.REPLANNING

        feedback = (
            f"RECOVERY FEEDBACK FOR ATTEMPT {current_retries + 1}/{self.max_node_retries}:\n"
            f"Failure in '{failed_node_id}': {failure_reason}\n"
            f"Details: {error_details}\n"
            f"Action Required: Modify code to satisfy test assertions and security guardrails."
        )

        context.add_audit_event(
            action="DYNAMIC_REPLAN_ACTIVE",
            message=f"Dynamic re-plan triggered. Rescheduling minimal subgraph: {repaired_nodes}",
            node_id=failed_node_id,
            level=AuditLevel.INFO,
            metadata={"repaired_nodes": repaired_nodes, "retry_attempt": current_retries + 1}
        )

        return ReplanAction(
            action_type="RETRY_WITH_FEEDBACK",
            failed_node_id=failed_node_id,
            repaired_nodes=repaired_nodes,
            feedback_prompt=feedback,
            retry_attempt=current_retries + 1,
            max_retries=self.max_node_retries
        )
