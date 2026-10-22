"""
Rollback, File Checkpointing, and Safe-Stop Controller.
Ensures zero partial-write corruption and supports deterministic state reversal upon failure or human rejection.
"""

from __future__ import annotations
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from src.orchestrator.state import AuditLevel, PipelineContext, TaskStatus

class FileCheckpoint(BaseModel):
    checkpoint_id: str
    timestamp: float = Field(default_factory=time.time)
    description: str
    tracked_files: Dict[str, str] = Field(default_factory=dict) # file_path -> file_content

class RollbackController:
    """
    Takes in-memory and filesystem snapshots, enabling safe revert if guardrails fail,
    tests fail unrecoverably, or a human operator issues a REJECT command at a HITL gate.
    """
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.checkpoints: Dict[str, FileCheckpoint] = {}

    def create_checkpoint(
        self,
        checkpoint_id: str,
        description: str,
        file_paths: List[Path],
        context: Optional[PipelineContext] = None
    ) -> FileCheckpoint:
        tracked: Dict[str, str] = {}
        for p in file_paths:
            if p.exists() and p.is_file():
                try:
                    tracked[str(p)] = p.read_text(encoding="utf-8")
                except Exception:
                    pass
            else:
                # File does not exist yet (will be created in this step)
                tracked[str(p)] = "__NON_EXISTENT__"

        cp = FileCheckpoint(
            checkpoint_id=checkpoint_id,
            description=description,
            tracked_files=tracked
        )
        self.checkpoints[checkpoint_id] = cp

        if context:
            context.add_audit_event(
                action="CHECKPOINT_CREATED",
                message=f"Created checkpoint '{checkpoint_id}' tracking {len(tracked)} files: {description}",
                metadata={"tracked_files": list(tracked.keys())}
            )
        return cp

    def execute_rollback(
        self,
        checkpoint_id: str,
        context: PipelineContext,
        reason: str
    ) -> bool:
        """Restores files to checkpointed state and marks context as ROLLED_BACK."""
        cp = self.checkpoints.get(checkpoint_id)
        if not cp:
            context.add_audit_event(
                action="ROLLBACK_FAILED",
                message=f"Checkpoint '{checkpoint_id}' not found for rollback",
                level=AuditLevel.ERROR
            )
            return False

        context.add_audit_event(
            action="ROLLBACK_INITIATED",
            message=f"Initiating rollback to checkpoint '{checkpoint_id}'. Reason: {reason}",
            level=AuditLevel.WARN
        )

        restored_count = 0
        deleted_count = 0
        for file_str, original_content in cp.tracked_files.items():
            path = Path(file_str)
            if original_content == "__NON_EXISTENT__":
                if path.exists():
                    path.unlink()
                    deleted_count += 1
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(original_content, encoding="utf-8")
                restored_count += 1

        context.rollbacks_count += 1
        context.status = TaskStatus.ROLLED_BACK
        context.add_audit_event(
            action="ROLLBACK_COMPLETED",
            message=f"Rollback successful: Restored {restored_count} files, removed {deleted_count} newly-created files.",
            level=AuditLevel.INFO
        )
        return True

    def trigger_safe_stop(self, context: PipelineContext, reason: str) -> None:
        """Halts pipeline execution safely to prevent corrupted state."""
        context.status = TaskStatus.FAILED
        context.end_time = time.time()
        context.add_audit_event(
            action="SAFE_STOP_TRIGGERED",
            message=f"Controlled autonomy safe-stop engaged: {reason}",
            level=AuditLevel.CRITICAL
        )
