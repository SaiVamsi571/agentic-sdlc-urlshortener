"""
State and Lineage Management for Agentic Orchestration.
Maintains immutable snapshots, audit events, decision lineage, and cross-stage execution context.
"""

from __future__ import annotations
import json
import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class SDLCPhase(str, Enum):
    REQUIREMENTS = "requirements"
    ARCHITECTURE = "architecture"
    BLAST_RADIUS = "blast_radius"
    DECOMPOSITION = "decomposition"
    GUARDRAILS_PRE = "guardrails_pre"
    IMPLEMENTATION = "implementation"
    CODE_REVIEW = "code_review"
    TESTING = "testing"
    HITL_APPROVAL = "hitl_approval"
    RELEASE_READINESS = "release_readiness"

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING_APPROVAL = "waiting_approval"
    REPLANNING = "replanning"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"
    SKIPPED = "skipped"

class AuditLevel(str, Enum):
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    GATE = "GATE"

class DecisionLineageRecord(BaseModel):
    record_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = Field(default_factory=time.time)
    node_id: str
    phase: SDLCPhase
    agent_name: str
    input_artifacts: List[str] = Field(default_factory=list)
    decision: str
    rationale: str
    alternatives_considered: List[str] = Field(default_factory=list)
    governance_check_passed: bool = True
    output_artifacts: List[str] = Field(default_factory=list)

class AuditEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = Field(default_factory=time.time)
    pipeline_id: str
    node_id: Optional[str] = None
    phase: Optional[SDLCPhase] = None
    agent_name: Optional[str] = None
    level: AuditLevel = AuditLevel.INFO
    action: str
    message: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    duration_ms: Optional[float] = None

class ApprovalRecord(BaseModel):
    approval_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    node_id: str
    gate_name: str
    reviewer: str
    approved: bool
    comments: str
    timestamp: float = Field(default_factory=time.time)
    diff_inspected: Optional[str] = None
    risk_level: str = "LOW"

class PipelineContext(BaseModel):
    """
    Immutable state snapshot and execution context carried across the SDLC pipeline.
    Preserves all outputs, decisions, artifacts, and execution metrics.
    """
    pipeline_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    scenario_name: str = "custom"
    requirement_prompt: str = ""
    status: TaskStatus = TaskStatus.PENDING
    start_time: float = Field(default_factory=time.time)
    end_time: Optional[float] = None
    
    # Cross-stage artifacts
    artifacts: Dict[str, Any] = Field(default_factory=dict)
    
    # State tracking
    node_statuses: Dict[str, TaskStatus] = Field(default_factory=dict)
    node_outputs: Dict[str, Any] = Field(default_factory=dict)
    node_errors: Dict[str, str] = Field(default_factory=dict)
    node_retries: Dict[str, int] = Field(default_factory=dict)
    
    # Governance & Lineage
    decision_lineage: List[DecisionLineageRecord] = Field(default_factory=list)
    audit_events: List[AuditEvent] = Field(default_factory=list)
    approvals: List[ApprovalRecord] = Field(default_factory=list)
    active_hitl_request: Optional[Dict[str, Any]] = None
    
    # Dynamic re-planning counters
    replans_count: int = 0
    rollbacks_count: int = 0
    
    def add_audit_event(
        self,
        action: str,
        message: str,
        node_id: Optional[str] = None,
        phase: Optional[SDLCPhase] = None,
        agent_name: Optional[str] = None,
        level: AuditLevel = AuditLevel.INFO,
        duration_ms: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        event = AuditEvent(
            pipeline_id=self.pipeline_id,
            node_id=node_id,
            phase=phase,
            agent_name=agent_name,
            level=level,
            action=action,
            message=message,
            duration_ms=duration_ms,
            metadata=metadata or {}
        )
        self.audit_events.append(event)
        return event

    def record_decision(
        self,
        node_id: str,
        phase: SDLCPhase,
        agent_name: str,
        decision: str,
        rationale: str,
        alternatives: Optional[List[str]] = None,
        inputs: Optional[List[str]] = None,
        outputs: Optional[List[str]] = None,
        governance_passed: bool = True
    ) -> DecisionLineageRecord:
        record = DecisionLineageRecord(
            node_id=node_id,
            phase=phase,
            agent_name=agent_name,
            input_artifacts=inputs or [],
            decision=decision,
            rationale=rationale,
            alternatives_considered=alternatives or [],
            governance_check_passed=governance_passed,
            output_artifacts=outputs or []
        )
        self.decision_lineage.append(record)
        return record

    def get_artifact(self, key: str, default: Any = None) -> Any:
        return self.artifacts.get(key, default)

    def set_artifact(self, key: str, value: Any) -> None:
        self.artifacts[key] = value

    def to_snapshot(self) -> Dict[str, Any]:
        """Produce a serialized JSON-compatible dictionary snapshot."""
        return json.loads(self.model_dump_json())
