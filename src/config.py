"""
Agentic SDLC System - Global Configuration.
Configures paths, autonomous execution limits, policy guardrails, and HITL thresholds.
"""
import os
from pathlib import Path

from pydantic import BaseModel, Field

from src.constants import (
    APP_TITLE,
    APP_VERSION,
    DEFAULT_ENV,
    DEFAULT_EXECUTION_TIMEOUT_SECONDS,
    DEFAULT_HITL_TIMEOUT_SECONDS,
    DEFAULT_HOST,
    DEFAULT_MAX_TASK_RETRIES,
    DEFAULT_PORT,
    DEFAULT_RETRY_BACKOFF_FACTOR,
    DEFAULT_SERVICE_PORT,
    RISK_MODULE_COUNT_THRESHOLD,
)

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = BASE_DIR / "src"
LOGS_DIR = BASE_DIR / "logs"
TESTS_DIR = BASE_DIR / "tests"
DOCS_DIR = BASE_DIR / "docs"

# Ensure runtime directories exist
LOGS_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)


class GuardrailPolicy(BaseModel):
    """Static analysis and policy enforcement thresholds."""

    max_cyclomatic_complexity: int = 15
    prohibit_raw_sql: bool = True
    require_ip_anonymization: bool = True
    require_schema_backwards_compat: bool = True
    prohibit_plain_secrets: bool = True
    max_blast_radius_modules: int = RISK_MODULE_COUNT_THRESHOLD * 2


class HITLPolicy(BaseModel):
    """Human-in-the-Loop governance policy configuration."""

    require_approval_for_schema_change: bool = True
    require_approval_for_breaking_api: bool = True
    require_approval_for_release: bool = True
    auto_approve_safe_refactors: bool = True
    default_timeout_seconds: int = DEFAULT_HITL_TIMEOUT_SECONDS


class SystemConfig(BaseModel):
    """Top-level system configuration for the AetherSDLC platform."""

    app_name: str = APP_TITLE
    version: str = APP_VERSION
    environment: str = os.getenv("APP_ENV", DEFAULT_ENV)
    web_host: str = os.getenv("HOST", DEFAULT_HOST)
    web_port: int = int(os.getenv("PORT", str(DEFAULT_PORT)))
    service_port: int = int(os.getenv("SERVICE_PORT", str(DEFAULT_SERVICE_PORT)))

    # Autonomous execution parameters
    max_task_retries: int = DEFAULT_MAX_TASK_RETRIES
    retry_backoff_factor: float = DEFAULT_RETRY_BACKOFF_FACTOR
    execution_timeout_seconds: int = DEFAULT_EXECUTION_TIMEOUT_SECONDS

    # Audit & Observability
    audit_log_path: Path = LOGS_DIR / "audit_trail.jsonl"
    metrics_snapshot_path: Path = LOGS_DIR / "metrics_snapshot.json"

    # Policies
    guardrails: GuardrailPolicy = Field(default_factory=GuardrailPolicy)
    hitl: HITLPolicy = Field(default_factory=HITLPolicy)


CONFIG = SystemConfig()
