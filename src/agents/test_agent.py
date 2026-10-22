"""
Automated Test Generation and Execution Agent.
Executes Unit, Integration, Concurrency, and Contract tests, capturing assertion failures
to drive the dynamic re-planning feedback loop.
"""
import subprocess
import sys
import time
from typing import Any, Dict, List
from src.agents.base import BaseAgent
from src.config import BASE_DIR
from src.constants import (
    AGENT_NAME_TEST,
    STATUS_TESTS_FAILED,
    STATUS_TESTS_PASSED,
)
from src.orchestrator.graph import DAGNode
from src.orchestrator.state import AuditLevel, PipelineContext, SDLCPhase

class TestAgent(BaseAgent):
    def __init__(self):
        super().__init__(name=AGENT_NAME_TEST, phase=SDLCPhase.TESTING)

    async def run(self, context: PipelineContext, node: DAGNode) -> Dict[str, Any]:
        test_dir = BASE_DIR / "tests"
        start_time = time.time()
        
        # Execute pytest as subprocess
        cmd = [sys.executable, "-m", "pytest", str(test_dir), "-v", "--tb=short"]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=str(BASE_DIR),
                capture_output=True,
                text=True,
                timeout=60
            )
            duration = round(time.time() - start_time, 2)
            stdout = result.stdout
            passed = result.returncode == 0
        except Exception as e:
            duration = round(time.time() - start_time, 2)
            stdout = str(e)
            passed = False

        # Parse test outcomes
        passed_count = stdout.count(" PASSED")
        failed_count = stdout.count(" FAILED")
        total_tests = passed_count + failed_count

        test_report = {
            "passed": passed,
            "status": STATUS_TESTS_PASSED if passed else STATUS_TESTS_FAILED,
            "total_tests": total_tests,
            "passed_tests": passed_count,
            "failed_tests": failed_count,
            "duration_seconds": duration,
            "output_snippet": stdout[-1200:] if len(stdout) > 1200 else stdout
        }

        context.set_artifact("test_execution_report", test_report)

        level = AuditLevel.INFO if passed else AuditLevel.ERROR
        context.add_audit_event(
            action="TEST_SUITE_EXECUTION",
            message=f"Test run completed: {passed_count} passed, {failed_count} failed in {duration}s",
            node_id=node.id,
            phase=self.phase,
            level=level,
            metadata={"passed": passed_count, "failed": failed_count}
        )

        context.record_decision(
            node_id=node.id,
            phase=self.phase,
            agent_name=self.name,
            decision=f"Test Suite verdict: {'PASSED' if passed else 'FAILED'}.",
            rationale=f"Executed {total_tests} tests covering core hashing, validation, SSRF, caching, HTTP redirects, and concurrency.",
            alternatives=["Skip testing"],
            inputs=["codebase_modules", "test_files"],
            outputs=["test_execution_report"],
            governance_passed=passed
        )

        if not passed:
            raise AssertionError(f"Test suite failures detected:\n{stdout[-600:]}")

        return test_report
