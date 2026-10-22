"""
Base Agent Interface.
Standardizes execution, performance measurement, decision lineage capture, and error handling.
"""
import abc
import time
from typing import Any, Dict, List, Optional
from src.orchestrator.graph import DAGNode
from src.orchestrator.state import AuditLevel, DecisionLineageRecord, PipelineContext, SDLCPhase

class BaseAgent(abc.ABC):
    def __init__(self, name: str, phase: SDLCPhase):
        self.name = name
        self.phase = phase

    async def execute(self, context: PipelineContext, node: DAGNode) -> Dict[str, Any]:
        start = time.time()
        context.add_audit_event(
            action="AGENT_STARTED",
            message=f"Agent '{self.name}' started work on node '{node.id}' ({self.phase.value})",
            node_id=node.id,
            phase=self.phase,
            agent_name=self.name
        )

        try:
            output = await self.run(context, node)
            duration_ms = (time.time() - start) * 1000.0
            
            context.node_outputs[node.id] = output
            context.add_audit_event(
                action="AGENT_COMPLETED",
                message=f"Agent '{self.name}' completed node '{node.id}' in {duration_ms:.1f}ms",
                node_id=node.id,
                phase=self.phase,
                agent_name=self.name,
                duration_ms=duration_ms,
                metadata={"output_keys": list(output.keys())}
            )
            return output
        except Exception as e:
            duration_ms = (time.time() - start) * 1000.0
            context.node_errors[node.id] = str(e)
            context.add_audit_event(
                action="AGENT_FAILED",
                message=f"Agent '{self.name}' failed on node '{node.id}': {str(e)}",
                node_id=node.id,
                phase=self.phase,
                agent_name=self.name,
                level=AuditLevel.ERROR,
                duration_ms=duration_ms,
                metadata={"error": str(e)}
            )
            raise

    @abc.abstractmethod
    async def run(self, context: PipelineContext, node: DAGNode) -> Dict[str, Any]:
        """Implement specific agent reasoning and artifact generation."""
        pass
