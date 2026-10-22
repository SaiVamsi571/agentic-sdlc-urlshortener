# AetherSDLC: Agentic Software Engineering Orchestration System
### Production-Grade Autonomous SDLC with Controlled Governance & URL Shortener Domain
**Production Deliverable: Enterprise AI Engineering Assessment**

---

## 🌟 Executive Summary
**AetherSDLC** is an enterprise-grade agentic software engineering system that transforms high-level product requirements into fully reviewable, production-ready engineering outcomes. Built on the core principle of **controlled autonomy**, AetherSDLC enables AI agents to autonomously handle complex, multi-step engineering tasks (requirements interpretation, architectural design, codebase reasoning, parallel code generation, security SAST, and automated verification) while maintaining **human oversight, policy guardrails, and audit-grade decision lineage**.

To demonstrate these capabilities, the system autonomously designs, builds, refactors, and tests a **high-performance, production-ready URL Shortener Service** with Base62/MurmurHash3 encoding, collision probing, SSRF protection, in-memory LRU caching, sliding-window rate limiting, and GDPR-compliant salted click analytics.

---

## 🏗 Key Architectural Highlights

| Core Pillar | Engineering Implementation |
| :--- | :--- |
| **Workflow Orchestration (Critical Differentiator)** | Explicit stateful Directed Acyclic Graph (**DAG**) with strict entry/exit gates, topological scheduling, and **parallel fan-out / fan-in synchronization layers**. |
| **Controlled Autonomy & Governance** | **Human-in-the-Loop (HITL)** checkpoints for high-impact actions (schema migrations, breaking API changes, release readiness) with automated snapshot rollback. |
| **Dynamic Re-planning & Self-Healing** | Feedback loop that isolates failed subgraphs upon test or SAST failure, injecting diagnostic context with **bounded retries (max 3)** and automatic safe-stop. |
| **Brownfield Codebase Reasoning** | Dynamic **Python AST (Abstract Syntax Tree)** parsing that computes symbol dependencies, caller-callee linkages, and exact blast radius risk scores (0.0 to 1.0). |
| **Policy Guardrails** | Automated AST & regex scanners enforcing OWASP Top 10, SSRF loopback filtering, parameterized SQL queries, secret leakage prevention, and GDPR IP hashing. |
| **Audit-Grade Lineage & Observability** | Immutable JSONL audit trail tracking every prompt, state transition, rationale, gate verdict, and metric (Success Rate, MTTR, Rollback Freq, Latency). |

---

## 🚀 Quickstart & Setup Instructions

### Prerequisites
- Python 3.10+ (tested on Python 3.14)
- Standard pip package manager

### 1. Installation
Clone the repository and install dependencies:
```bash
cd agentic-sdlc-urlshortener
python -m pip install -r requirements.txt
```

### 2. Launching the Interactive Web Dashboard
Run the unified entry point:
```bash
python main.py
```
Open your browser to:
- **Interactive Web Dashboard**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive OpenAPI Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **URL Shortener Target Service**: [http://127.0.0.1:8000/shortener](http://127.0.0.1:8000/shortener)

From the dashboard, you can trigger any scenario with one click, watch the live SVG DAG update in real time via Server-Sent Events (SSE), inspect HITL approval diffs, and test URL shortening directly in the live sandbox!

### 3. Running via Rich Terminal CLI
To run any of the 3 scenarios from the command line:
```bash
# Run Greenfield Scenario (Full build from scratch)
python main.py --scenario greenfield

# Run Brownfield Scenario (AST blast radius & non-breaking schema addition)
python main.py --scenario brownfield

# Run Ambiguous Scenario (Ambiguity scoring & stakeholder clarification)
python main.py --scenario ambiguous

# Run All Scenarios Sequentially
python main.py --scenario all
```

### 4. Running the Complete Automated Test Suite
Execute all 28 unit, integration, concurrency, and orchestration tests:
```bash
python -m pytest tests/ -v
```
*(All 28 tests pass in < 3 seconds with 100% pass rate).*

---

## 🎯 The Three Demonstration Scenarios

### Scenario 1: Greenfield (Full URL Shortener Build)
- **Input Requirement**: High-level specification for a production URL Shortener with Base62 encoding, custom aliases, 30-day default TTL, HTTP 307 redirects, LRU caching, and click analytics.
- **Agentic Flow**:
  1. `RequirementsAnalystAgent`: Scores ambiguity (0.40) and normalizes into formal SRS with locked assumptions.
  2. `PrincipalArchitectAgent`: Formulates 3 Architectural Decision Records (ADRs: Base62/Murmur3, LRU+SlidingWindow, GDPR Salted Analytics) and OpenAPI contracts.
  3. `TechnicalProgramDecompositionAgent`: Generates WBS across 5 parallel execution stages.
  4. `SeniorFullStackEngineerAgent`: Generates and verifies 11 modules (1,100+ LOC).
  5. `SecurityComplianceOfficerAgent`: Verifies OWASP, SSRF, SQL injection, and GDPR rules.
  6. `QualityAssuranceTestAgent`: Runs 28 automated tests (Unit, API, Concurrency).
  7. `HITL Approval Gate`: Enforces human review of test outcomes.
  8. `ReleaseManagerAgent`: Generates certified release manifest `REL-1.0.0`.

### Scenario 2: Brownfield (Analytics & Rate Limiting Refactor)
- **Input Requirement**: Add Sliding-Window Rate Limiting (60 write/min, 1200 read/min) and granular Device/Referrer click analytics to the existing service without breaking existing API contracts.
- **Agentic Flow**:
  1. `CodebaseReasoningAgent`: Parses Python AST across all modules in `src/service/`, builds symbol dependency graph, identifies 4 directly impacted and 3 indirectly impacted modules, and scores blast radius as `CRITICAL (1.0)` due to schema expansion.
  2. `HITL Change Control Gate`: Halts execution; human operator reviews blast radius and confirms non-breaking schema evolution.
  3. `SeniorFullStackEngineerAgent`: Incrementally integrates sliding-window middleware and device parser.
  4. `SecurityComplianceOfficerAgent`: Verifies backwards compatibility (no removed routes) and GDPR salt retention.
  5. `QualityAssuranceTestAgent`: Runs full regression and concurrency stress tests.
  6. `ReleaseManagerAgent`: Approves version `1.1.0` release.

### Scenario 3: Ambiguous Requirements & Disambiguation
- **Input Requirement**: *"We want to make the URL shortener faster, add some marketing campaign things, and make sure expired links don't break horribly."*
- **Agentic Flow**:
  1. `RequirementsAnalystAgent`: Analyzes vague intent, flags **Ambiguity Score = 0.80**, and identifies 4 missing architectural constraints (Cache strategy, UTM marketing schema, Expired 410 vs fallback behavior, Rate limits).
  2. `Stakeholder Clarification Gate`: Synthesizes ambiguity clarification proposal; stakeholder locks canonical decisions.
  3. Downstream Execution: Dynamically re-plans DAG to execute architecture, implementation, guardrail audits, and verification.

---

## 📊 Reliability & Observability Metrics

The system tracks real-time enterprise reliability telemetry:
- **Success Rate (%)**: Tracked across all pipeline tasks and end-to-end runs.
- **Mean Time to Repair (MTTR)**: Measures average duration to dynamically re-plan and self-heal failed tasks.
- **Rollback Frequency**: Quantifies state reversal events via `RollbackController`.
- **Guardrail Violations Blocked**: Counts security, SSRF, and PII violations caught before release.
- **Audit Trail**: Every execution event is appended to `logs/audit_trail.jsonl` with timestamp, duration, decision rationale, and agent identity.

---

## 📂 Repository Structure

```
agentic-sdlc-urlshortener/
├── main.py                          # Unified launcher (Web Dashboard + CLI)
├── requirements.txt                 # Project dependencies
├── README.md                        # Quickstart & architectural summary
├── docs/                            # Canonical Technical Documentation Suite
│   ├── ARCHITECTURE.md              # Deep dive on DAG, HITL, Guardrails, Metrics
│   ├── SCENARIOS.md                 # Detailed walkthrough of the 3 scenarios
│   ├── EVALUATION_REPORT.md         # Formal engineering assessment report
│   ├── API_REFERENCE.md             # Full OpenAPI endpoints & contracts
│   └── AST_BLAST_RADIUS.md          # AST parsing engine & risk formulas
│
├── src/
│   ├── config.py                    # Global policies, limits, and system paths
│   │
│   ├── orchestrator/                # The Agentic Orchestration Layer
│   │   ├── engine.py                # Stateful DAG Engine (concurrency, synchronization)
│   │   ├── graph.py                 # DAG Node, GateCondition, and ExecutionGraph
│   │   ├── state.py                 # PipelineContext, AuditEvent, DecisionLineage
│   │   ├── hitl.py                  # Human-in-the-Loop checkpoint manager
│   │   ├── guardrails.py            # Security, SAST, and compliance policy engine
│   │   ├── replanner.py             # Dynamic Re-planning & self-healing feedback loop
│   │   ├── rollback.py              # File snapshotting & safe-stop controller
│   │   └── metrics.py               # Reliability metrics & JSONL audit logger
│   │
│   ├── agents/                      # Specialized SDLC Agents
│   │   ├── base.py                  # BaseAgent abstract class
│   │   ├── requirements_agent.py    # Intent parsing & ambiguity scoring (0-1)
│   │   ├── architecture_agent.py    # ADR synthesis & OpenAPI contract design
│   │   ├── blast_radius_agent.py    # Python AST parser & dependency mapper
│   │   ├── decomposition_agent.py   # WBS task DAG generator
│   │   ├── coder_agent.py           # Multi-tier implementation agent
│   │   ├── security_agent.py        # Static analysis & policy scanner
│   │   ├── test_agent.py            # Automated pytest execution agent
│   │   └── release_agent.py         # Release readiness & changelog compiler
│   │
│   ├── service/                     # Target URL Shortener Service
│   │   ├── app.py                   # FastAPI app with rate limiting middleware
│   │   ├── config.py                # Service configuration (salt, TTL, limits)
│   │   ├── models.py                # Pydantic schemas (ShortURL, Analytics, DTOs)
│   │   ├── service.py               # Facade coordinating repo, cache, analytics
│   │   ├── core/                    # Core algorithms
│   │   │   ├── encoder.py           # Base62 + MurmurHash3 collision resolver
│   │   │   ├── validator.py         # RFC validation, SSRF, & loop protector
│   │   │   ├── cache.py             # Thread-safe LRU cache with TTL invalidation
│   │   │   └── rate_limiter.py      # Sliding-window rate limiter
│   │   ├── storage/                 # Persistence layer
│   │   │   ├── base.py              # Repository abstract interface
│   │   │   └── memory_sqlite.py     # Thread-safe SQLite repository
│   │   └── routers/
│   │       ├── url.py               # POST /shorten, GET /{code} redirect
│   │       └── analytics.py         # GET /analytics/{code}, GET /system/stats
│   │
│   ├── scenarios/                   # The 3 Demonstration Scenarios
│   │   ├── greenfield.py            # Scenario 1 implementation
│   │   ├── brownfield.py            # Scenario 2 implementation
│   │   └── ambiguous.py             # Scenario 3 implementation
│   │
│   └── web/                         # Interactive Glassmorphic Web Dashboard
│       ├── server.py                # Backend with REST and SSE event stream
│       └── static/
│           ├── index.html           # Single Page Application
│           ├── styles.css           # Glassmorphism dark-mode styles
│           └── app.js               # Reactive SVG DAG & sandbox logic
│
├── tests/                           # Complete Test Suite (28 passing tests)
│   ├── test_service_core.py         # Unit tests (Base62, Murmur3, Validator, Cache, Limiter)
│   ├── test_service_api.py          # Integration tests (Shorten, 307 redirect, 410 expired)
│   ├── test_service_analytics.py    # Analytics tests (GDPR salt hash, UTM tags, devices)
│   ├── test_service_concurrency.py  # Thread concurrency & race condition stress tests
│   └── test_orchestrator.py         # Orchestrator tests (DAG, HITL, replan, rollback, guardrails)
│
└── logs/                            # Audit logs and state snapshots
    └── audit_trail.jsonl            # Enterprise compliance audit log
```
