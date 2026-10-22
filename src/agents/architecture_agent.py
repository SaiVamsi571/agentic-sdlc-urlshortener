"""
Architecture & System Design Agent.
Synthesizes Architectural Decision Records (ADRs), component diagrams, data models, and API contracts.
"""
from typing import Any, Dict, List
from src.agents.base import BaseAgent
from src.constants import OPENAPI_VERSION, SERVICE_DESCRIPTION, SERVICE_TITLE
from src.orchestrator.graph import DAGNode
from src.orchestrator.state import PipelineContext, SDLCPhase

class ArchitectureAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="PrincipalArchitectAgent", phase=SDLCPhase.ARCHITECTURE)

    async def run(self, context: PipelineContext, node: DAGNode) -> Dict[str, Any]:
        srs = context.get_artifact("requirements_srs", {})

        adrs = [
            {
                "id": "ADR-001",
                "title": "Short Code Generation via Base62 and MurmurHash3 with Probing",
                "status": "ACCEPTED",
                "context": "Need deterministic short codes with low latency (<1ms) and uniform distribution.",
                "decision": "Use 64-bit MurmurHash3 of (original_url + salt) encoded in Base62 (characters [0-9a-zA-Z]). Upon collision, increment salt and probe.",
                "alternatives": [
                    "Auto-incrementing integer IDs: leaks volume metrics to competitors, requires coordinated sequence generation.",
                    "Random UUID substring: higher collision rate in 7 chars, non-deterministic."
                ],
                "consequences": "Provides 62^7 = 3.52 trillion distinct combinations. Collision rate < 0.001% for first 100M URLs."
            },
            {
                "id": "ADR-002",
                "title": "Tiered Caching & Sliding-Window Rate Limiting",
                "status": "ACCEPTED",
                "context": "Redirect read queries outnumber write queries by 50:1. System must withstand sudden burst traffic.",
                "decision": "Implement an LRU in-memory cache with TTL invalidation for resolved URLs, and a sliding-window counter rate limiter per client IP.",
                "alternatives": [
                    "Token bucket rate limiter: more complex state per client.",
                    "Direct database reads on every redirect: creates database bottlenecks during traffic spikes."
                ],
                "consequences": "Sub-millisecond redirect latency on cache hits. Rejection of abusive IPs with HTTP 429 Too Many Requests."
            },
            {
                "id": "ADR-003",
                "title": "GDPR-Compliant Click Analytics Lineage",
                "status": "ACCEPTED",
                "context": "Click tracking must capture engagement without violating privacy regulations regarding personal identifiable information (PII).",
                "decision": "Store SHA-256 hash of client IP concatenated with a rotating system salt. Extract and store device category and browser type from User-Agent.",
                "alternatives": [
                    "Store raw IPv4/IPv6: Violates GDPR without user consent.",
                    "No IP tracking: Prevents unique visitor calculations and fraud detection."
                ],
                "consequences": "Enables accurate unique visitor count calculation while maintaining zero PII liability."
            }
        ]

        api_spec = {
            "openapi": OPENAPI_VERSION,
            "info": {
                "title": SERVICE_TITLE,
                "version": "1.0.0",
                "description": SERVICE_DESCRIPTION,
            },
            "paths": {
                "/api/v1/shorten": {
                    "post": {
                        "summary": "Create shortened URL",
                        "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/ShortenRequest"}}}},
                        "responses": {"201": {"description": "URL created successfully"}}
                    }
                },
                "/{short_code}": {
                    "get": {
                        "summary": "Redirect to target URL",
                        "parameters": [{"name": "short_code", "in": "path", "required": True}],
                        "responses": {
                            "307": {"description": "Temporary redirect to original URL"},
                            "404": {"description": "Short code not found"},
                            "410": {"description": "Link expired"}
                        }
                    }
                },
                "/api/v1/analytics/{short_code}": {
                    "get": {
                        "summary": "Get click statistics and timeseries",
                        "parameters": [{"name": "short_code", "in": "path", "required": True}],
                        "responses": {"200": {"description": "Analytics data returned"}}
                    }
                },
                "/api/v1/health": {
                    "get": {
                        "summary": "Health check",
                        "responses": {"200": {"description": "System operational"}}
                    }
                }
            }
        }

        data_models = {
            "ShortURL": {
                "fields": {
                    "short_code": "str (PK, unique index)",
                    "original_url": "str (indexed)",
                    "custom_alias": "Optional[str] (unique index)",
                    "created_at": "datetime (default now)",
                    "expires_at": "Optional[datetime]",
                    "is_active": "bool (default True)",
                    "created_by": "Optional[str]"
                }
            },
            "ClickEvent": {
                "fields": {
                    "event_id": "str (PK)",
                    "short_code": "str (FK to ShortURL.short_code)",
                    "timestamp": "datetime",
                    "ip_hash": "str (SHA-256 salted)",
                    "referrer": "Optional[str]",
                    "user_agent": "Optional[str]",
                    "device_type": "str (mobile, desktop, tablet, bot)",
                    "browser": "str (Chrome, Firefox, Safari, Edge, Other)"
                }
            }
        }

        architecture_manifest = {
            "adrs": adrs,
            "api_spec": api_spec,
            "data_models": data_models,
            "components": [
                "storage.MemorySqliteRepository",
                "core.Base62Encoder",
                "core.URLValidator",
                "core.LRUTTLCache",
                "core.SlidingWindowRateLimiter",
                "routers.URLRouter",
                "routers.AnalyticsRouter",
                "service.URLShortenerService"
            ]
        }

        context.set_artifact("architecture_manifest", architecture_manifest)
        context.set_artifact("api_spec", api_spec)

        context.record_decision(
            node_id=node.id,
            phase=self.phase,
            agent_name=self.name,
            decision="Approved System Architecture with 3 ADRs: Base62/Murmur3, LRU+SlidingWindow, and GDPR Salted Analytics.",
            rationale="Balances enterprise-grade sub-10ms redirect latency, multi-million URL scalability, and regulatory compliance.",
            alternatives=["Postgres-only with sync queries", "Redis cluster dependency for minimal prototype"],
            inputs=["requirements_srs"],
            outputs=["architecture_manifest", "api_spec"]
        )

        return {
            "adrs_created": len(adrs),
            "components_defined": len(architecture_manifest["components"]),
            "api_endpoints_count": len(api_spec["paths"]),
            "status": "ARCHITECTURE_APPROVED"
        }
