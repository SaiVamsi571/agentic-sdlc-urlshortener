"""
Reliability Metrics and Audit-Grade Observability Tracker.
Calculates Success Rate, MTTR, Retry/Rollback Frequency, Latency, and Guardrail Interventions.
Persists structured audit logs to JSONL for enterprise traceability.
"""

from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from src.config import CONFIG
from src.orchestrator.state import AuditEvent, PipelineContext, TaskStatus

class ReliabilityMetrics(BaseModel):
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    success_rate_percent: float = 0.0
    
    total_tasks_attempted: int = 0
    total_tasks_succeeded: int = 0
    task_success_rate_percent: float = 0.0
    
    total_retries: int = 0
    retry_frequency_per_run: float = 0.0
    
    total_rollbacks: int = 0
    rollback_frequency_per_run: float = 0.0
    
    total_mttr_seconds: float = 0.0
    replan_repair_events: int = 0
    mean_time_to_repair_mttr_sec: float = 0.0
    
    avg_latency_seconds: float = 0.0
    guardrail_violations_prevented: int = 0
    human_in_the_loop_approvals: int = 0

class MetricsTracker:
    """
    Maintains system-wide telemetry and per-run metrics.
    Writes immutable audit logs conforming to financial/enterprise compliance standards.
    """
    def __init__(self, log_path: Optional[Path] = None):
        self.log_path = log_path or CONFIG.audit_log_path
        self.metrics = ReliabilityMetrics()
        self._repair_start_times: Dict[str, float] = {}

    def record_repair_start(self, node_id: str) -> None:
        self._repair_start_times[node_id] = time.time()

    def record_repair_success(self, node_id: str) -> None:
        if node_id in self._repair_start_times:
            elapsed = time.time() - self._repair_start_times.pop(node_id)
            self.metrics.total_mttr_seconds += elapsed
            self.metrics.replan_repair_events += 1
            if self.metrics.replan_repair_events > 0:
                self.metrics.mean_time_to_repair_mttr_sec = round(
                    self.metrics.total_mttr_seconds / self.metrics.replan_repair_events, 2
                )

    def record_pipeline_run(self, context: PipelineContext) -> ReliabilityMetrics:
        self.metrics.total_runs += 1
        duration = (context.end_time or time.time()) - context.start_time
        
        if context.status == TaskStatus.COMPLETED:
            self.metrics.successful_runs += 1
        else:
            self.metrics.failed_runs += 1

        self.metrics.success_rate_percent = round(
            (self.metrics.successful_runs / max(1, self.metrics.total_runs)) * 100.0, 1
        )

        # Count tasks
        completed_nodes = sum(1 for s in context.node_statuses.values() if s == TaskStatus.COMPLETED)
        total_nodes = len(context.node_statuses)
        self.metrics.total_tasks_attempted += total_nodes
        self.metrics.total_tasks_succeeded += completed_nodes
        self.metrics.task_success_rate_percent = round(
            (self.metrics.total_tasks_succeeded / max(1, self.metrics.total_tasks_attempted)) * 100.0, 1
        )

        self.metrics.total_retries += sum(context.node_retries.values())
        self.metrics.retry_frequency_per_run = round(
            self.metrics.total_retries / self.metrics.total_runs, 2
        )

        self.metrics.total_rollbacks += context.rollbacks_count
        self.metrics.rollback_frequency_per_run = round(
            self.metrics.total_rollbacks / self.metrics.total_runs, 2
        )

        self.metrics.human_in_the_loop_approvals += len(context.approvals)

        # Count violations prevented from audit events
        violations = sum(1 for e in context.audit_events if "GUARDRAIL" in e.action or "VIOLATION" in e.action)
        self.metrics.guardrail_violations_prevented += violations

        # Latency update (exponential moving average)
        if self.metrics.avg_latency_seconds == 0.0:
            self.metrics.avg_latency_seconds = round(duration, 2)
        else:
            self.metrics.avg_latency_seconds = round((self.metrics.avg_latency_seconds * 0.7) + (duration * 0.3), 2)

        # Persist audit events to file
        self.persist_audit_log(context.audit_events)

        return self.metrics

    def persist_audit_log(self, events: List[AuditEvent]) -> None:
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_path, "a", encoding="utf-8") as f:
                for event in events:
                    f.write(json.dumps(event.model_dump()) + "\n")
        except Exception as e:
            print(f"[MetricsTracker] Warning: could not write audit log: {e}")

    def get_summary(self) -> Dict[str, Any]:
        return self.metrics.model_dump()
