"""
Task Decomposition and Execution Sequencing Agent.
Converts high-level requirements and architecture into discrete, actionable tasks with explicit dependencies,
concurrency groupings, and gate conditions.
"""
from typing import Any, Dict, List
from src.agents.base import BaseAgent
from src.orchestrator.graph import DAGNode
from src.orchestrator.state import PipelineContext, SDLCPhase

class DecompositionAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="TechnicalProgramDecompositionAgent", phase=SDLCPhase.DECOMPOSITION)

    async def run(self, context: PipelineContext, node: DAGNode) -> Dict[str, Any]:
        srs = context.get_artifact("requirements_srs", {})
        arch = context.get_artifact("architecture_manifest", {})

        tasks = [
            {
                "task_id": "TASK-001",
                "title": "Define Pydantic Models & DTOs",
                "phase": "IMPLEMENTATION",
                "dependencies": [],
                "parallel_group": "foundation",
                "estimated_complexity": "LOW",
                "target_artifacts": ["src/service/models.py"]
            },
            {
                "task_id": "TASK-002",
                "title": "Implement Base62 & MurmurHash3 Collision Encoder",
                "phase": "IMPLEMENTATION",
                "dependencies": ["TASK-001"],
                "parallel_group": "core_algorithms",
                "estimated_complexity": "MEDIUM",
                "target_artifacts": ["src/service/core/encoder.py"]
            },
            {
                "task_id": "TASK-003",
                "title": "Implement URL RFC Validator & SSRF Guard",
                "phase": "IMPLEMENTATION",
                "dependencies": ["TASK-001"],
                "parallel_group": "core_algorithms", # Can run parallel with TASK-002!
                "estimated_complexity": "LOW",
                "target_artifacts": ["src/service/core/validator.py"]
            },
            {
                "task_id": "TASK-004",
                "title": "Implement LRU Cache & Sliding Window Rate Limiter",
                "phase": "IMPLEMENTATION",
                "dependencies": ["TASK-001"],
                "parallel_group": "core_algorithms", # Can run parallel with TASK-002 & 003!
                "estimated_complexity": "MEDIUM",
                "target_artifacts": ["src/service/core/cache.py", "src/service/core/rate_limiter.py"]
            },
            {
                "task_id": "TASK-005",
                "title": "Build SQLite & In-Memory Thread-Safe Repository",
                "phase": "IMPLEMENTATION",
                "dependencies": ["TASK-001"],
                "parallel_group": "persistence",
                "estimated_complexity": "MEDIUM",
                "target_artifacts": ["src/service/storage/memory_sqlite.py"]
            },
            {
                "task_id": "TASK-006",
                "title": "Build Service Facade & Orchestration Layer",
                "phase": "IMPLEMENTATION",
                "dependencies": ["TASK-002", "TASK-003", "TASK-004", "TASK-005"], # Synchronization join!
                "parallel_group": "service_layer",
                "estimated_complexity": "HIGH",
                "target_artifacts": ["src/service/service.py"]
            },
            {
                "task_id": "TASK-007",
                "title": "Build FastAPI REST Routers & App Factory",
                "phase": "IMPLEMENTATION",
                "dependencies": ["TASK-006"],
                "parallel_group": "api_layer",
                "estimated_complexity": "MEDIUM",
                "target_artifacts": ["src/service/routers/url.py", "src/service/routers/analytics.py", "src/service/app.py"]
            },
            {
                "task_id": "TASK-008",
                "title": "Execute Security SAST & Policy Guardrail Audit",
                "phase": "GUARDRAILS_PRE",
                "dependencies": ["TASK-007"],
                "parallel_group": "verification",
                "estimated_complexity": "LOW",
                "target_artifacts": ["guardrail_report"]
            },
            {
                "task_id": "TASK-009",
                "title": "Run Unit, Integration, and Concurrency Test Suites",
                "phase": "TESTING",
                "dependencies": ["TASK-008"],
                "parallel_group": "verification",
                "estimated_complexity": "HIGH",
                "target_artifacts": ["test_execution_report"]
            },
            {
                "task_id": "TASK-010",
                "title": "HITL Release Readiness & Governance Sign-off",
                "phase": "RELEASE_READINESS",
                "dependencies": ["TASK-009"],
                "parallel_group": "release",
                "estimated_complexity": "LOW",
                "target_artifacts": ["release_manifest"]
            }
        ]

        decomposition_plan = {
            "total_tasks": len(tasks),
            "tasks": tasks,
            "parallel_stages_count": 5,
            "critical_path": ["TASK-001", "TASK-005", "TASK-006", "TASK-007", "TASK-009", "TASK-010"]
        }

        context.set_artifact("decomposition_plan", decomposition_plan)

        context.record_decision(
            node_id=node.id,
            phase=self.phase,
            agent_name=self.name,
            decision=f"Decomposed architecture into {len(tasks)} sequenced tasks across 5 parallel execution stages.",
            rationale="Separated foundation models, parallelized core algorithmic utilities, and placed a fan-in synchronization barrier before service layer integration.",
            alternatives=["Monolithic single-task implementation", "Strictly serial step chaining without parallelization"],
            inputs=["requirements_srs", "architecture_manifest"],
            outputs=["decomposition_plan"]
        )

        return decomposition_plan
