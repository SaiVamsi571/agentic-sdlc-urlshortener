# AetherSDLC API Reference
### Comprehensive OpenAPI Specifications for Orchestrator & Enterprise URL Shortener

All endpoints are hosted at `http://127.0.0.1:8000` and interactive Swagger UI is available at `http://127.0.0.1:8000/docs`.

---

## 1. URL Shortener Operations

### `POST /shortener/api/v1/shorten`
Creates a shortened URL with collision probing and optional custom alias.
* **Request Body**:
  ```json
  {
    "original_url": "https://www.example.com/solutions",
    "custom_alias": "enterprise-invest",
    "ttl_seconds": 2592000,
    "tags": { "campaign": "fall_2026", "source": "portal" }
  }
  ```
* **Response `201 Created`**:
  ```json
  {
    "short_code": "enterprise-invest",
    "short_url": "http://localhost:8000/shortener/enterprise-invest",
    "original_url": "https://www.example.com/solutions",
    "created_at": "2026-10-21T18:50:00Z",
    "expires_at": "2026-11-20T18:50:00Z",
    "is_custom_alias": true,
    "tags": { "campaign": "fall_2026", "source": "portal" }
  }
  ```
* **Error Codes**: `400 Bad Request` (Invalid URL / SSRF loopback), `409 Conflict` (Alias taken), `429 Too Many Requests` (Rate limit exceeded).

---

### `GET /shortener/{short_code}`
Resolves a short code and issues an **HTTP 307 Temporary Redirect** to the destination.
* Records click analytics (GDPR salted IP, device type, referrer, timestamp).
* Sub-millisecond lookup via in-memory LRU cache.
* **Response `307 Temporary Redirect`**: `Location: https://www.example.com/solutions`
* **Error Codes**: `404 Not Found`, `410 Gone` (Expired TTL).

---

### `GET /shortener/api/v1/analytics/{short_code}`
Retrieves GDPR-compliant click analytics for a given short code.
* **Response `200 OK`**:
  ```json
  {
    "short_code": "enterprise-invest",
    "original_url": "https://www.example.com/solutions",
    "total_clicks": 142,
    "unique_visitors": 98,
    "devices": [
      { "device": "desktop", "count": 110 },
      { "device": "mobile", "count": 32 }
    ],
    "top_referrers": [
      { "referrer": "https://example.com", "count": 95 }
    ]
  }
  ```

---

## 2. Pipeline Orchestration & Governance

### `POST /api/pipeline/run/{scenario_name}`
Triggers autonomous execution of an SDLC pipeline.
* **Parameters**: `scenario_name` (`greenfield`, `brownfield`, `ambiguous`).
* **Request Body**:
  ```json
  { "auto_approve": false }
  ```
* **Response `200 OK`**: `{"status": "ACCEPTED", "scenario": "brownfield"}`

---

### `POST /api/pipeline/hitl/{request_id}`
Submits a human governance decision for an active checkpoint.
* **Request Body**:
  ```json
  {
    "approved": true,
    "reviewer": "LeadArchitect",
    "comments": "Approved AST blast radius and schema addition."
  }
  ```
* **Response `200 OK`**: Returns resolved `ApprovalRecord`.

---

### `GET /api/pipeline/events`
Server-Sent Events (SSE) streaming real-time DAG node updates, metrics, and logs.
* **Event Types**: `PIPELINE_STARTED`, `NODE_STARTED`, `NODE_COMPLETED`, `HITL_REQUESTED`, `HITL_RESOLVED`, `METRICS_UPDATED`.

---

### `GET /api/pipeline/blast-radius`
Runs live Python AST analysis on `src/service/` and returns the codebase blast radius report.
