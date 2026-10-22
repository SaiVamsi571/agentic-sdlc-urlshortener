# Demonstration Scenarios Walkthrough: AetherSDLC
### Greenfield, Brownfield, and Ambiguous SDLC Lifecycle Executions

---

## Scenario 1: Greenfield Implementation (URL Shortener from Scratch)

### 1.1 Input Requirement
```text
Build an enterprise-grade URL shortener service with Base62 encoding, custom aliases,
30-day default expiration with HTTP 410 Gone for expired links, HTTP 307 temporary redirects,
LRU caching, and GDPR-compliant click analytics.
```

### 1.2 Step-by-Step Lifecycle Execution

#### Phase 1: Requirements Understanding (`REQ-01`)
- **Agent**: `RequirementsAnalystAgent`
- **Ambiguity Scoring**: Evaluated against 6 architectural dimensions. Ambiguity score: **0.40** (well-specified core, but minor ambiguities around custom alias length and GDPR hashing rules).
- **Outcome**: Formulates normalized System Requirements Specification (SRS) with locked assumptions:
  - Default TTL: 30 days; minimum custom TTL: 60 seconds.
  - Base62 7-character short codes generated via MurmurHash3.
  - HTTP 307 Temporary Redirects (preserves HTTP method and allows hop tracking).
  - GDPR compliance: Salted SHA-256 client IP hashing.

#### Phase 2: System Architecture & ADR Formulation (`ARCH-01`)
- **Agent**: `PrincipalArchitectAgent`
- **ADRs Synthesized**:
  1. `ADR-001`: Short Code Generation via Base62 and MurmurHash3 with Nonce Probing.
  2. `ADR-002`: Tiered Caching & Sliding-Window Rate Limiting.
  3. `ADR-003`: GDPR-Compliant Click Analytics Lineage.
- **Contract Definition**: OpenAPI 3.0.3 specification with `/api/v1/shorten`, `/{short_code}`, and `/api/v1/analytics/{short_code}`.

#### Phase 3: Task Decomposition (`DECOMP-01`)
- **Agent**: `TechnicalProgramDecompositionAgent`
- **WBS Breakdown**: 10 sequenced tasks across 5 parallel layers. Identifies that Core Encoder, Validator, and Cache can be developed concurrently in Layer 3 before synchronizing at Service Facade in Layer 4.

#### Phase 4: Implementation (`CODE-01`)
- **Agent**: `SeniorFullStackEngineerAgent`
- **Output**: 11 modules created and verified (1,107 LOC) adhering to clean separation of domain, storage, core, service, and API routers.

#### Phase 5: Security SAST & Guardrails (`SEC-01`)
- **Agent**: `SecurityComplianceOfficerAgent`
- **Findings**: 0 critical violations, 0 high violations. Parameterized queries verified in `SQLiteURLRepository`; loopback and cloud metadata SSRF filters verified in `URLValidator`. Verdict: **PASSED**.

#### Phase 6: Automated Testing (`TEST-01`)
- **Agent**: `QualityAssuranceTestAgent`
- **Results**: 28 tests executed across Unit, API, Concurrency, and Orchestrator suites. 100% passed in 2.25s.

#### Phase 7: HITL Governance Gate (`HITL-01`)
- **Gate**: Human sign-off on test results and security report.
- **Verdict**: Auto-approved under non-production policy rule / signed off in Web UI.

#### Phase 8: Release Readiness (`REL-01`)
- **Agent**: `ReleaseManagerAgent`
- **Artifact**: `release_manifest.json` compiled with release ID `REL-1.0.0` and automated rollback procedure checkpoint.

---

## Scenario 2: Brownfield Enhancement & Refactoring

### 2.1 Input Requirement
```text
Add sliding-window rate limiting (60 req/min write, 1200 req/min read) and
granular device/referrer click analytics breakdown with UTM parameters to the existing URL shortener,
ensuring 100% backwards compatibility with existing API clients.
```

### 2.2 Step-by-Step Lifecycle Execution

#### Phase 1: Brownfield Scope & Backwards Compatibility (`REQ-BROWN-01`)
- Validates that existing endpoint signatures (`POST /api/v1/shorten` and `GET /{short_code}`) must not break.

#### Phase 2: AST Codebase Reasoning & Blast Radius Evaluation (`BLAST-01`)
- **Agent**: `CodebaseReasoningAgent`
- **AST Analysis**: Dynamically traverses Python Abstract Syntax Trees of all files in `src/service/`.
- **Dependency Mapping**:
  - Directly impacted modules: `models.py`, `storage/memory_sqlite.py`, `routers/analytics.py`, `service.py`.
  - Indirectly impacted downstream modules: `app.py`, `routers/url.py`.
- **Risk Score**: Evaluates to **`CRITICAL (1.0)`** due to table schema expansion (adding `click_events` table) and middleware injection.
- **Action Required**: Requires mandatory HITL Change Control Gate before modifying files.

#### Phase 3: HITL Change Control Gate (`HITL-SCHEMA-01`)
- Execution pauses with `TaskStatus.WAITING_APPROVAL`.
- Human reviewer reviews the AST impact report, confirming that the new fields have safe defaults and that the existing API remains backwards compatible.
- Reviewer signs off: *"Approved non-breaking schema additions for rate limiting and click analytics."*

#### Phase 4: Incremental Code Implementation (`CODE-BROWN-01`)
- Integrates `SlidingWindowRateLimiter` middleware into `app.py`.
- Adds device and browser parsing from User-Agent into `service.py`.

#### Phase 5: Change Control Guardrails (`SEC-BROWN-01`)
- `GuardrailEngine` verifies that zero existing API paths were deleted (`CHG-001` passed) and GDPR IP hashing is enforced (`COMP-001` passed).

#### Phase 6: Regression & Concurrency Tests (`TEST-BROWN-01`)
- Runs concurrency stress suite with 30 parallel worker threads. Confirms rate limiter returns HTTP 429 when threshold exceeded and thread-safe SQLite operations avoid database locks.

#### Phase 7: Release Readiness (`REL-BROWN-01`)
- Generates certified version `1.1.0` release manifest.

---

## Scenario 3: Ambiguous Requirements & Controlled Disambiguation

### 3.1 Input Requirement
```text
We want to make the URL shortener faster, add some marketing campaign things,
and make sure expired links don't break horribly.
```

### 3.2 Step-by-Step Lifecycle Execution

#### Phase 1: Ambiguity Detection & Scoring (`AMBIG-01`)
- **Agent**: `RequirementsAnalystAgent`
- **Ambiguity Score**: **0.80 / 1.0 (CRITICALLY AMBIGUOUS)**.
- **Identified Gaps**:
  1. *Speed/Performance*: Unspecified latency target, missing cache strategy (Redis vs In-Memory LRU).
  2. *Marketing*: Unspecified campaign metadata schema (UTM tags vs vanity domains).
  3. *Expired Links*: Undefined HTTP behavior for expired URLs (Silent redirect vs HTTP 410 Gone vs custom error landing page).
  4. *Reliability*: Unspecified rate limiting and abuse controls.

#### Phase 2: Interactive Disambiguation Gate (`HITL-DISAMBIG-01`)
- The system generates an explicit Disambiguation Proposal with enterprise default assumptions:
  - Cache: In-memory LRU cache with 300s TTL for sub-10ms redirect latency.
  - Marketing: Automatic extraction and persistence of `utm_source`, `utm_medium`, and `utm_campaign`.
  - Expiration: Strict HTTP 410 Gone status with clear JSON detail explaining expiration timestamp.
  - Security: Sliding-window rate limiting of 60 req/min for write operations.
- The stakeholder/reviewer accepts the clarified constraints at the HITL gate.

#### Phase 3: Architecture & ADR Synthesis (`ARCH-AMBIG-01`)
- Synthesizes architecture manifest directly derived from clarified constraints.

#### Phase 4 to 7: Implementation, Security SAST, Verification, & Release
- Implementation proceeds cleanly under normalized specifications.
- Automated tests verify that expired links return HTTP 410 Gone and UTM tags are accurately aggregated.
- Release is approved with full traceability back to the initial ambiguous user prompt.
