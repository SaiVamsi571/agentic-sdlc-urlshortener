"""
Security & Compliance SAST Audit Agent.
Executes static application security testing (SAST), secrets detection,
PII/GDPR compliance verification, and SSRF guardrail audits.
"""
from pathlib import Path
from typing import Any, Dict, List
from src.agents.base import BaseAgent
from src.config import BASE_DIR
from src.constants import AGENT_NAME_SECURITY
from src.llm import get_llm_client
from src.orchestrator.graph import DAGNode
from src.orchestrator.guardrails import GuardrailEngine, GuardrailReport
from src.orchestrator.state import AuditLevel, PipelineContext, SDLCPhase

class SecurityAgent(BaseAgent):
    def __init__(self):
        super().__init__(name=AGENT_NAME_SECURITY, phase=SDLCPhase.GUARDRAILS_PRE)
        self.guardrail_engine = GuardrailEngine()

    async def run(self, context: PipelineContext, node: DAGNode) -> Dict[str, Any]:
        target_dir = BASE_DIR / "src" / "service"
        all_violations = []
        all_warnings = []
        files_scanned = 0

        if target_dir.exists():
            for py_file in target_dir.rglob("*.py"):
                files_scanned += 1
                rel_path = str(py_file.relative_to(BASE_DIR)).replace("\\", "/")
                code = py_file.read_text(encoding="utf-8")
                report = self.guardrail_engine.evaluate_code(rel_path, code)
                all_violations.extend(report.violations)
                all_warnings.extend(report.warnings)

        passed = len(all_violations) == 0
        status_str = "PASSED" if passed else "FAILED"

        audit_result = {
            "passed": passed,
            "status": status_str,
            "files_scanned": files_scanned,
            "critical_violations_count": sum(1 for v in all_violations if v.severity == "CRITICAL"),
            "high_violations_count": sum(1 for v in all_violations if v.severity == "HIGH"),
            "total_violations": len(all_violations),
            "warnings_count": len(all_warnings),
            "violations": [v.model_dump() for v in all_violations],
            "warnings": [w.model_dump() for w in all_warnings]
        }

        # Dynamic LLM Threat Model (STRIDE)
        llm = get_llm_client()
        if llm.is_enabled:
            system_prompt = (
                "You are an enterprise Application Security Architect. "
                "Evaluate the security posture of this Python URL shortener service "
                "(which features SSRF validation, sliding-window rate limiting, and GDPR IP hashing). "
                "Provide a concise STRIDE threat modeling summary. "
                "Return a JSON object with keys: 'threat_model_summary' (string), 'identified_threats' (list of strings)."
            )
            threat_analysis = await llm.generate_json(system_prompt, f"Files scanned: {files_scanned}, violations: {len(all_violations)}")
            if threat_analysis:
                audit_result["threat_model"] = threat_analysis
                context.add_audit_event(
                    action="LLM_SECURITY_THREAT_MODEL",
                    message=f"Agent '{self.name}' completed STRIDE threat analysis using OpenAI ({llm.model}).",
                    node_id=node.id,
                    phase=self.phase,
                    metadata={"provider": "openai", "model": llm.model}
                )

        context.set_artifact("security_guardrail_report", audit_result)

        level = AuditLevel.INFO if passed else AuditLevel.ERROR
        context.add_audit_event(
            action="SECURITY_SAST_EVALUATION",
            message=f"Security scan completed across {files_scanned} files. Result: {status_str} (Violations: {len(all_violations)}, Warnings: {len(all_warnings)})",
            node_id=node.id,
            phase=self.phase,
            level=level,
            metadata={"violations": len(all_violations), "warnings": len(all_warnings)}
        )

        context.record_decision(
            node_id=node.id,
            phase=self.phase,
            agent_name=self.name,
            decision=f"Security Gate verdict: {status_str}.",
            rationale=f"Evaluated OWASP Top 10, SSRF prevention, SQL injection risks, and GDPR IP hashing across {files_scanned} modules.",
            alternatives=["Bypass security scan to speed up delivery"],
            inputs=["codebase_files"],
            outputs=["security_guardrail_report"],
            governance_passed=passed
        )

        if not passed:
            raise ValueError(f"Security policy guardrail violations detected: {[v.message for v in all_violations]}")

        return audit_result
