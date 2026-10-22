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
