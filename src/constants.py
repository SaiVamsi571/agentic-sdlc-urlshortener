"""
AetherSDLC - Centralized Constants and Configuration Literals.

All magic strings, numeric thresholds, URL patterns, branding labels,
and domain-specific constants are defined here to avoid scattering
raw literals throughout the codebase.
"""

# ─── Branding & Identity ───────────────────────────────────────────────
APP_TITLE = "AetherSDLC - Agentic Software Engineering Orchestration System"
APP_VERSION = "2.0.0"
SERVICE_TITLE = "AetherSDLC Enterprise URL Shortener"
DASHBOARD_TITLE = "AetherSDLC Orchestration Dashboard & Enterprise URL Shortener"
DASHBOARD_DESCRIPTION = (
    "Autonomous Agentic SDLC with Controlled Autonomy, "
    "Human-In-The-Loop Governance, and Production URL Shortener."
)
SERVICE_DESCRIPTION = (
    "High-performance, secure URL shortener service "
    "with analytics and SLA rate limiting."
)

# ─── CLI Branding ──────────────────────────────────────────────────────
CLI_BANNER = """
    ========================================================================
             AETHERSDLC : AGENTIC SOFTWARE ENGINEERING SYSTEM
              Autonomous Lifecycle Orchestration & Controlled Autonomy
    ========================================================================
"""
CLI_DESCRIPTION = "AetherSDLC Command Line Interface"

# ─── Encoding & Hashing ───────────────────────────────────────────────
BASE62_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE62_RADIX = len(BASE62_ALPHABET)  # 62
DEFAULT_CODE_LENGTH = 7
DEFAULT_ENCODER_SALT = "aether_enterprise_salt_2026"

# ─── URL Validation & Security ─────────────────────────────────────────
ALLOWED_URL_SCHEMES = ("http", "https")
MAX_URL_LENGTH = 2048
ALIAS_PATTERN = r"^[a-zA-Z0-9_\-]{3,30}$"

RESERVED_ALIASES = frozenset({
    "api", "docs", "redoc", "openapi.json", "health", "metrics",
    "admin", "dashboard", "static", "assets", "favicon.ico", "robots.txt",
    "shorten", "analytics", "login", "logout", "settings", "register",
})

BLOCKED_HOSTNAMES = frozenset({
    "localhost", "127.0.0.1", "0.0.0.0", "::1", "169.254.169.254",
})

DEFAULT_SERVICE_DOMAINS = frozenset({
    "localhost", "127.0.0.1", "short.aethersdlc.dev",
})

# ─── HTTP Status Semantics ─────────────────────────────────────────────
HTTP_REDIRECT_STATUS = 307
HTTP_GONE_STATUS = 410
HTTP_CREATED_STATUS = 201
HTTP_NOT_FOUND_STATUS = 404
HTTP_CONFLICT_STATUS = 409
HTTP_RATE_LIMITED_STATUS = 429

# ─── Rate Limiting Defaults ────────────────────────────────────────────
DEFAULT_RATE_LIMIT_WRITE_PER_MIN = 60
DEFAULT_RATE_LIMIT_READ_PER_MIN = 1200
RATE_LIMIT_WINDOW_SECONDS = 60

# ─── Cache Defaults ────────────────────────────────────────────────────
DEFAULT_CACHE_MAX_SIZE = 10_000
DEFAULT_CACHE_TTL_SECONDS = 300

# ─── Service Defaults ──────────────────────────────────────────────────
DEFAULT_TTL_DAYS = 30
DEFAULT_TTL_SECONDS = DEFAULT_TTL_DAYS * 86_400  # 2,592,000

# ─── Risk Scoring Thresholds ──────────────────────────────────────────
RISK_BASE_SCORE = 0.2
RISK_SCHEMA_WEIGHT = 0.4
RISK_ROUTER_WEIGHT = 0.2
RISK_MODULE_COUNT_WEIGHT = 0.2
RISK_MODULE_COUNT_THRESHOLD = 3
RISK_MAX_SCORE = 1.0

RISK_CRITICAL_THRESHOLD = 0.8
RISK_HIGH_THRESHOLD = 0.6
RISK_MEDIUM_THRESHOLD = 0.4

RISK_CATEGORY_CRITICAL = "CRITICAL"
RISK_CATEGORY_HIGH = "HIGH"
RISK_CATEGORY_MEDIUM = "MEDIUM"
RISK_CATEGORY_LOW = "LOW"

# ─── Pipeline & Orchestration ─────────────────────────────────────────
DEFAULT_MAX_TASK_RETRIES = 3
DEFAULT_RETRY_BACKOFF_FACTOR = 1.5
DEFAULT_EXECUTION_TIMEOUT_SECONDS = 120
DEFAULT_HITL_TIMEOUT_SECONDS = 300

ROLLBACK_CHECKPOINT_ID = "PRE_RELEASE_SNAPSHOT"
ROLLBACK_RECOVERY_TIME_SEC = 2.0

# ─── Release Versions ─────────────────────────────────────────────────
GREENFIELD_VERSION = "1.0.0"
BROWNFIELD_VERSION = "1.1.0"
AMBIGUOUS_VERSION = "1.0.1"

# ─── Scenario Names ───────────────────────────────────────────────────
SCENARIO_GREENFIELD = "greenfield"
SCENARIO_BROWNFIELD = "brownfield"
SCENARIO_AMBIGUOUS = "ambiguous"
SCENARIO_ALL = "all"

SCENARIO_PROMPTS = {
    SCENARIO_GREENFIELD: (
        "Build enterprise URL shortener with Base62, custom aliases, "
        "30-day TTL, LRU caching, and click analytics."
    ),
    SCENARIO_BROWNFIELD: (
        "Add sliding-window rate limiting and granular device/referrer "
        "click analytics without breaking existing APIs."
    ),
    SCENARIO_AMBIGUOUS: (
        "Make the URL shortener faster, add marketing campaign things, "
        "and ensure expired links don't break horribly."
    ),
}

# ─── OpenAPI Spec Defaults ─────────────────────────────────────────────
OPENAPI_VERSION = "3.0.3"

# ─── GDPR & Analytics ─────────────────────────────────────────────────
IP_HASH_TRUNCATION_LENGTH = 16

# ─── Frontend Demo Defaults ───────────────────────────────────────────
DEMO_URL_PLACEHOLDER = "https://www.example.com/investing"
DEMO_URL_DEFAULT = "https://www.example.com/investing"
DEMO_ALIAS_PLACEHOLDER = "my-custom-link"
DEMO_REFERER = "https://example.com/dashboard"

# ─── Server Defaults ──────────────────────────────────────────────────
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_SERVICE_PORT = 8001
DEFAULT_DB_PATH = ":memory:"
DEFAULT_ENV = "development"

# ─── AST Blast Radius Simulation Proposals ────────────────────────────
BLAST_RADIUS_PROPOSALS = {
    "brownfield": [
        "src/service/models.py",
        "src/service/storage/memory_sqlite.py",
        "src/service/routers/analytics.py",
        "src/service/service.py",
    ],
    "validator": [
        "src/service/core/validator.py",
    ],
    "cache": [
        "src/service/core/cache.py",
        "src/service/service.py",
    ],
    "schema_migration": [
        "src/service/models.py",
        "src/service/storage/memory_sqlite.py",
    ],
    "router_only": [
        "src/service/routers/url.py",
    ],
}

# ─── Specialized Agent Identities ─────────────────────────────────────
AGENT_NAME_REQUIREMENTS = "RequirementsAnalystAgent"
AGENT_NAME_ARCHITECTURE = "PrincipalArchitectAgent"
AGENT_NAME_DECOMPOSITION = "TechnicalProgramDecompositionAgent"
AGENT_NAME_BLAST_RADIUS = "CodebaseReasoningAgent"
AGENT_NAME_CODER = "SeniorFullStackEngineerAgent"
AGENT_NAME_SECURITY = "SecurityComplianceOfficerAgent"
AGENT_NAME_TEST = "QualityAssuranceTestAgent"
AGENT_NAME_RELEASE = "ReleaseManagerAgent"

# ─── Quality & Architectural Metric Labels ─────────────────────────────
GRADE_CLEAN_DESIGN = "A+ (Modular Layered Architecture)"
INDEX_MAINTAINABILITY = "94.2 / 100 (High Cohesion, Low Coupling)"
STATUS_IMPLEMENTATION_COMPLETE = "IMPLEMENTATION_COMPLETE"
STATUS_REPAIRED_AFTER_FEEDBACK = "REPAIRED_AFTER_FEEDBACK"
STATUS_RELEASE_READY = "RELEASE_READY"
STATUS_RELEASE_BLOCKED = "RELEASE_BLOCKED"
STATUS_NORMALIZED_AND_LOCKED = "NORMALIZED_AND_LOCKED"
STATUS_NORMALIZED = "NORMALIZED"
STATUS_TESTS_PASSED = "TESTS_PASSED"
STATUS_TESTS_FAILED = "TESTS_FAILED"

# ─── Canonical Artifact Filenames ──────────────────────────────────────
ARTIFACT_REQUIREMENTS_MD = "requirements.md"
ARTIFACT_ARCHITECTURE_MD = "architecture.md"
ARTIFACT_IMPLEMENTATION_DIFF = "implementation.diff"
ARTIFACT_SCHEMA_DEFINITIONS_JSON = "schema-definitions.json"
ARTIFACT_ENGINEERING_DESIGN_MD = "engineering-design.md"
ARTIFACT_API_OPENAPI_JSON = "api-openapi.json"
ARTIFACT_TEST_RESULTS_JSON = "test-results.json"
ARTIFACT_RISK_ASSESSMENT_MD = "risk-assessment.md"
ARTIFACT_AUDIT_LOG_JSONL = "audit-log.jsonl"
ARTIFACT_ENGINEERING_SUMMARY_MD = "engineering-summary.md"

# ─── Clean Report Section Titles (Emoji-Free) ─────────────────────────
TITLE_LAYERED_ARCHITECTURE = "Layered Architecture & Separation of Concerns"
TITLE_TEST_TRACEABILITY = "Unit & Integration Test Traceability Matrix"
TITLE_CLEAN_DESIGN = "Clean Design & SOLID Principles Assessment"

TITLE_EXECUTIVE_SNAPSHOT = "Executive Snapshot"
TITLE_ARTIFACTS_PRODUCED = "Artifacts Produced"
TITLE_ENGINEERING_OUTPUT = "Engineering Output Generation & Code Quality"
TITLE_CHANGES_SUMMARY = "What Was Changed & Why"
TITLE_REQUIREMENTS_SATISFIED = "Which Requirements Were Satisfied"
TITLE_TESTS_EXECUTED = "Tests Executed & Results"
TITLE_RISKS_TRADEOFFS = "Unresolved Assumptions, Risks & Trade-Offs"
TITLE_ROLLBACK_STATUS = "Rollback & Recovery Status"
TITLE_GOVERNANCE_DECISIONS = "Human-in-the-Loop Governance Decisions"
TITLE_FINAL_VERDICT = "Final Verdict"

# ─── CLI Terminal Output Markers (ASCII Only) ─────────────────────────
CLI_MARKER_RUNNING = "[>]"
CLI_MARKER_SUCCESS = "[+]"
CLI_MARKER_REPLAN = "[*]"
CLI_MARKER_HITL = "[!]"

# ─── Domain Error & Status Messages ───────────────────────────────────
MSG_URL_NOT_FOUND = "Short URL '{code}' does not exist."
MSG_URL_EXPIRED = "Short URL '{code}' expired on {expiry}."
MSG_URL_INVALID = "Invalid destination URL syntax or protocol."
MSG_ALIAS_CONFLICT = "Custom alias '{alias}' is already in use."
MSG_ALIAS_RESERVED = "Custom alias '{alias}' is reserved by system."
MSG_RATE_LIMIT_EXCEEDED = "Rate limit exceeded. Try again in {seconds} seconds."

