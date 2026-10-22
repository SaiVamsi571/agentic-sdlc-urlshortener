"""
Enterprise Policy Guardrails for Security, Compliance, and Safe Change Control.
Inspects generated code, schemas, and architecture before gates allow progression.
"""
import ast
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from src.config import CONFIG

class GuardrailViolation(BaseModel):
    rule_id: str
    category: str # SECURITY, COMPLIANCE, CHANGE_CONTROL, RELIABILITY
    severity: str # CRITICAL, HIGH, MEDIUM, LOW
    message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    remediation: str

class GuardrailReport(BaseModel):
    passed: bool
    violations: List[GuardrailViolation] = Field(default_factory=list)
    warnings: List[GuardrailViolation] = Field(default_factory=list)
    rules_checked: int = 0

class GuardrailEngine:
    """
    Evaluates artifacts against enterprise security, compliance, and change-control policies.
    """
    def __init__(self, policy=None):
        self.policy = policy or CONFIG.guardrails
        self.secret_patterns = [
            (r'(?i)(api[_-]?key|secret|password|token)\s*=\s*["\'][a-zA-Z0-9_\-]{16,}["\']', "Hardcoded secret or token detected"),
            (r'ghp_[a-zA-Z0-9]{36}', "GitHub Personal Access Token detected"),
            (r'AKIA[0-9A-Z]{16}', "AWS Access Key detected")
        ]

    def evaluate_code(self, filename: str, code_content: str) -> GuardrailReport:
        violations: List[GuardrailViolation] = []
        warnings: List[GuardrailViolation] = []
        rules_checked = 0

        # 1. Secret Scanning
        rules_checked += 1
        for pattern, desc in self.secret_patterns:
            matches = list(re.finditer(pattern, code_content))
            for m in matches:
                violations.append(GuardrailViolation(
                    rule_id="SEC-001-HARDCODED-SECRETS",
                    category="SECURITY",
                    severity="CRITICAL",
                    message=f"{desc}: '{m.group(0)[:20]}...'",
                    file_path=filename,
                    remediation="Extract credentials to environment variables or secret manager."
                ))

        # 2. Raw SQL / SQL Injection checks
        rules_checked += 1
        if self.policy.prohibit_raw_sql:
            raw_sql_patterns = [
                r'cursor\.execute\s*\(\s*f["\']',
                r'execute\s*\(\s*["\'].*?%s.*?["\']\s*%',
                r'\.raw\s*\(\s*f["\']',
                r'SELECT\s+.*?\s+FROM\s+.*?WHERE\s+.*?=\s*["\']?\s*\+'
            ]
            for p in raw_sql_patterns:
                if re.search(p, code_content, re.IGNORECASE):
                    violations.append(GuardrailViolation(
                        rule_id="SEC-002-RAW-SQL-INJECTION",
                        category="SECURITY",
                        severity="CRITICAL",
                        message="Potential SQL Injection vulnerability: formatted string in SQL query execution",
                        file_path=filename,
                        remediation="Use parameterized queries or SQLAlchemy ORM abstractions."
                    ))

        # 3. SSRF & Loop Redirect Protection in URL Shortener
        rules_checked += 1
        if "url" in filename.lower() or "validator" in filename.lower() or "service" in filename.lower():
            loop_or_internal_ip_check = any(term in code_content for term in [
                "127.0.0.1", "localhost", "169.254.169.254", "0.0.0.0", "private_ip", "is_loop"
            ])
            if not loop_or_internal_ip_check and "validate" in code_content:
                warnings.append(GuardrailViolation(
                    rule_id="SEC-003-SSRF-LOOP-PREVENTION",
                    category="SECURITY",
                    severity="MEDIUM",
                    message="URL validator should explicitly block localhost, metadata endpoints (169.254.169.254), and loopback redirection.",
                    file_path=filename,
                    remediation="Add loopback and private subnet IP filtering to URL validation."
                ))

        # 4. GDPR Compliance: IP Anonymization
        rules_checked += 1
        if "analytics" in filename.lower() or "models" in filename.lower():
            if "client_ip" in code_content and not any(term in code_content for term in ["hash", "anonymize", "sha256", "mask"]):
                violations.append(GuardrailViolation(
                    rule_id="COMP-001-GDPR-IP-ANONYMIZATION",
                    category="COMPLIANCE",
                    severity="HIGH",
                    message="Direct storage of raw client IP addresses without hashing violates GDPR privacy requirements.",
                    file_path=filename,
                    remediation="Hash or truncate IP addresses using SHA-256 with a rotating salt before persistence."
                ))

        # 5. AST & Complexity Checks
        rules_checked += 1
        try:
            tree = ast.parse(code_content)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Compute approximate cyclomatic complexity (branches + 1)
                    branches = sum(1 for child in ast.walk(node) if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler, ast.With)))
                    if branches > self.policy.max_cyclomatic_complexity:
                        warnings.append(GuardrailViolation(
                            rule_id="REL-001-HIGH-COMPLEXITY",
                            category="RELIABILITY",
                            severity="LOW",
                            message=f"Function '{node.name}' has high cyclomatic complexity ({branches}). Maintainability threshold is {self.policy.max_cyclomatic_complexity}.",
                            file_path=filename,
                            line_number=node.lineno,
                            remediation="Refactor function into smaller helper sub-routines."
                        ))
        except SyntaxError as e:
            violations.append(GuardrailViolation(
                rule_id="CODE-001-SYNTAX-ERROR",
                category="RELIABILITY",
                severity="CRITICAL",
                message=f"Syntax error in generated code: {e.msg}",
                file_path=filename,
                line_number=e.lineno,
                remediation="Ensure generated code adheres to valid Python 3 syntax."
            ))

        has_critical_or_high = any(v.severity in ["CRITICAL", "HIGH"] for v in violations)
        return GuardrailReport(
            passed=not has_critical_or_high,
            violations=violations,
            warnings=warnings,
            rules_checked=rules_checked
        )

    def evaluate_change_control(
        self,
        original_api_spec: Dict[str, Any],
        proposed_api_spec: Dict[str, Any]
    ) -> GuardrailReport:
        """Checks for backwards compatibility in API contract changes (e.g., deleted endpoints)."""
        violations: List[GuardrailViolation] = []
        warnings: List[GuardrailViolation] = []

        orig_endpoints = set(original_api_spec.get("paths", {}).keys())
        prop_endpoints = set(proposed_api_spec.get("paths", {}).keys())

        removed_endpoints = orig_endpoints - prop_endpoints
        if removed_endpoints:
            violations.append(GuardrailViolation(
                rule_id="CHG-001-BREAKING-API-REMOVAL",
                category="CHANGE_CONTROL",
                severity="HIGH",
                message=f"Removed existing public API routes: {list(removed_endpoints)}. Violates backwards compatibility.",
                remediation="Deprecate routes using @deprecated or versioning instead of removing."
            ))

        return GuardrailReport(
            passed=len(violations) == 0,
            violations=violations,
            warnings=warnings,
            rules_checked=len(orig_endpoints) + 1
        )
