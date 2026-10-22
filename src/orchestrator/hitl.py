"""
Human-In-The-Loop (HITL) Governance & Checkpoint Controller.
Enforces human sign-off for high-impact actions (schema migrations, breaking changes, release readiness).
Supports asynchronous pause/resume, diff inspection, and review lineage.
"""
import asyncio
from typing import Any, Callable, Dict, Optional
from pydantic import BaseModel, Field
from src.orchestrator.state import ApprovalRecord, PipelineContext, TaskStatus

class HITLRequest(BaseModel):
    request_id: str
    pipeline_id: str
    node_id: str
    gate_title: str
    description: str
    risk_level: str = "MEDIUM" # LOW, MEDIUM, HIGH, CRITICAL
    proposed_diff: Optional[str] = None
    affected_components: list[str] = Field(default_factory=list)
    options: list[str] = Field(default_factory=lambda: ["Approve", "Reject", "Request Revision"])
    metadata: Dict[str, Any] = Field(default_factory=dict)

class HITLManager:
    """
    Manages interactive human checkpoints during agent execution.
    Can operate in:
      1. Interactive mode (async await for Web UI / CLI approval)
      2. Automated mode (pre-configured policies for CI/CD runs with audit log)
    """
    def __init__(self, auto_approve_default: bool = False):
        self.auto_approve_default = auto_approve_default
        self.pending_requests: Dict[str, HITLRequest] = {}
        self._waiters: Dict[str, asyncio.Event] = {}
        self._responses: Dict[str, ApprovalRecord] = {}

    def create_checkpoint(
        self,
        context: PipelineContext,
        node_id: str,
        gate_title: str,
        description: str,
        risk_level: str = "MEDIUM",
        proposed_diff: Optional[str] = None,
        affected_components: Optional[list[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> HITLRequest:
        import uuid
        request_id = str(uuid.uuid4())
        req = HITLRequest(
            request_id=request_id,
            pipeline_id=context.pipeline_id,
            node_id=node_id,
            gate_title=gate_title,
            description=description,
            risk_level=risk_level,
            proposed_diff=proposed_diff,
            affected_components=affected_components or [],
            metadata=metadata or {}
        )
        self.pending_requests[request_id] = req
        self._waiters[request_id] = asyncio.Event()
        context.active_hitl_request = req.model_dump()
        context.node_statuses[node_id] = TaskStatus.WAITING_APPROVAL
        
        context.add_audit_event(
            action="HITL_CHECKPOINT_CREATED",
            message=f"Human approval required for gate '{gate_title}' on node '{node_id}' [Risk: {risk_level}]",
            node_id=node_id,
            metadata={"request_id": request_id, "risk_level": risk_level}
        )
        return req

    async def wait_for_decision(
        self,
        request_id: str,
        context: PipelineContext,
        timeout_seconds: float = 300.0
    ) -> ApprovalRecord:
        """
        Pauses node execution until a human review is submitted via Web UI or CLI.
        If auto_approve_default is True or environment is CI/test, automatically approves.
        """
        if self.auto_approve_default:
            return self.resolve_checkpoint(
                request_id=request_id,
                context=context,
                reviewer="System-AutoGovernance",
                approved=True,
                comments=f"Auto-approved by policy rule (risk acceptable for non-production run)"
            )

        event = self._waiters.get(request_id)
        if not event:
            raise KeyError(f"No pending HITL request found with ID {request_id}")

        try:
            await asyncio.wait_for(event.wait(), timeout=timeout_seconds)
            return self._responses[request_id]
        except asyncio.TimeoutError:
            return self.resolve_checkpoint(
                request_id=request_id,
                context=context,
                reviewer="System-TimeoutPolicy",
                approved=False,
                comments=f"Approval timed out after {timeout_seconds}s. Safe-stop triggered."
            )

    def resolve_checkpoint(
        self,
        request_id: str,
        context: PipelineContext,
        reviewer: str,
        approved: bool,
        comments: str,
        modified_data: Optional[Dict[str, Any]] = None
    ) -> ApprovalRecord:
        req = self.pending_requests.pop(request_id, None)
        if not req:
            raise ValueError(f"Unknown or already resolved HITL request {request_id}")

        record = ApprovalRecord(
            node_id=req.node_id,
            gate_name=req.gate_title,
            reviewer=reviewer,
            approved=approved,
            comments=comments,
            diff_inspected=req.proposed_diff,
            risk_level=req.risk_level
        )
        
        context.approvals.append(record)
        context.active_hitl_request = None
        self._responses[request_id] = record

        action = "HITL_APPROVED" if approved else "HITL_REJECTED"
        context.add_audit_event(
            action=action,
            message=f"Gate '{req.gate_title}' {action.lower()} by {reviewer}. Reason: {comments}",
            node_id=req.node_id,
            metadata={"approved": approved, "reviewer": reviewer, "risk_level": req.risk_level}
        )

        event = self._waiters.get(request_id)
        if event and not event.is_set():
            event.set()

        return record
