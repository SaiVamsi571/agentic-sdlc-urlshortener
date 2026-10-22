"""
Requirements Engineering & Disambiguation Agent.
Interprets user intent, scores ambiguity across 6 key architectural dimensions,
resolves underspecified constraints, and normalizes into a formal Software Requirements Specification (SRS).
"""

from __future__ import annotations
import re
from typing import Any, Dict, List
from src.agents.base import BaseAgent
from src.constants import (
    AGENT_NAME_REQUIREMENTS,
    STATUS_NORMALIZED,
    STATUS_NORMALIZED_AND_LOCKED,
)
from src.llm import get_llm_client
from src.orchestrator.graph import DAGNode
from src.orchestrator.state import PipelineContext, SDLCPhase

class RequirementsAgent(BaseAgent):
    def __init__(self):
        super().__init__(name=AGENT_NAME_REQUIREMENTS, phase=SDLCPhase.REQUIREMENTS)

    async def run(self, context: PipelineContext, node: DAGNode) -> Dict[str, Any]:
        prompt = context.requirement_prompt or "Build a high-performance URL shortener service."
        
        # Check if OpenAI LLM is enabled
        llm = get_llm_client()
        llm_insights = None
        if llm.is_enabled:
            system_prompt = (
                "You are an expert Requirements Analyst for enterprise software systems. "
                "Analyze the user's high-level requirement for an enterprise URL shortener service. "
                "Detect ambiguity, identify missing constraints, and suggest edge-case considerations. "
                "Return a JSON object with keys: 'ambiguity_analysis' (string), 'edge_cases' (list of strings), "
                "and 'recommended_constraints' (list of strings)."
            )
            llm_insights = await llm.generate_json(system_prompt, f"User Requirement: {prompt}")
            if llm_insights:
                context.add_audit_event(
                    action="LLM_REASONING_COMPLETED",
                    message=f"Agent '{self.name}' completed dynamic requirements reasoning using OpenAI ({llm.model}).",
                    node_id=node.id,
                    phase=self.phase,
                    agent_name=self.name,
                    metadata={"provider": "openai", "model": llm.model}
                )

        # 1. Ambiguity Scoring across 6 enterprise dimensions
        ambiguities = []
        clarifications = []
        score = 0.0

        # Dimension 1: Expiration & TTL Behavior
        if not re.search(r'(?i)(ttl|expir|lifetime|duration)', prompt):
            ambiguities.append({
                "dimension": "Link Expiration / TTL",
                "severity": "HIGH",
                "issue": "No link lifetime or TTL policy defined. Unclear if URLs live indefinitely or expire.",
                "default_assumption": "Default 30-day TTL with optional custom expiration and HTTP 410 Gone for expired links."
            })
            clarifications.append("Should shortened links expire automatically, and should users specify custom TTLs?")
            score += 0.20

        # Dimension 2: Analytics & Privacy
        if not re.search(r'(?i)(analytic|click|metric|track|referr|geo)', prompt):
            ambiguities.append({
                "dimension": "Analytics & Privacy",
                "severity": "MEDIUM",
                "issue": "Analytics depth unspecified. Need clarity on click tracking, geolocation, and GDPR IP masking.",
                "default_assumption": "Capture anonymized IP hash, user-agent device/browser classification, referrer domain, and timestamp."
            })
            clarifications.append("What analytics metrics are required, and what is the compliance threshold for IP storage?")
            score += 0.15

        # Dimension 3: Collision Resolution & Hash Encoding
        if not re.search(r'(?i)(base62|collision|hash|custom alias|short code)', prompt):
            ambiguities.append({
                "dimension": "Encoding & Collision Strategy",
                "severity": "MEDIUM",
                "issue": "Encoding algorithm and collision resolution mechanism not specified.",
                "default_assumption": "Base62 encoding over 64-bit integer hash (MurmurHash3) with salt increment collision fallback."
            })
            clarifications.append("Is a specific short code length (e.g. 7 chars) or custom alias feature required?")
            score += 0.15

        # Dimension 4: Rate Limiting & Concurrency SLAs
        if not re.search(r'(?i)(rate limit|throttle|sla|concurr|qps|rps)', prompt):
            ambiguities.append({
                "dimension": "Rate Limiting & Reliability",
                "severity": "HIGH",
                "issue": "No QPS/RPS limits or abuse protection specified.",
                "default_assumption": "Sliding-window rate limiter configured at 60 requests/min for write (shorten) and 1000 requests/min for read (redirect)."
            })
            clarifications.append("What are the target QPS limits for link creation versus redirection?")
            score += 0.20

        # Dimension 5: Redirect HTTP Status Code
        if not re.search(r'(?i)(301|302|307|permanent|temporary redirect)', prompt):
            ambiguities.append({
                "dimension": "Redirect Semantics",
                "severity": "LOW",
                "issue": "HTTP redirect status code not chosen (301 Permanent vs 302/307 Temporary).",
                "default_assumption": "HTTP 307 Temporary Redirect by default (preserves POST/GET methods, allows analytics recording on each hop)."
            })
            clarifications.append("Should redirection be HTTP 301 (cached by browser, less analytics accuracy) or HTTP 307 (accurate analytics)?")
            score += 0.10

        # Dimension 6: Malicious URL & SSRF Prevention
        if not re.search(r'(?i)(security|ssrf|phish|safet|validat|malicious)', prompt):
            ambiguities.append({
                "dimension": "URL Validation & Security",
                "severity": "HIGH",
                "issue": "URL validation criteria and SSRF protection boundaries unspecified.",
                "default_assumption": "Validate RFC 3986 format, reject localhost/private subnet IPs (SSRF protection), and enforce maximum 2048 char length."
            })
            clarifications.append("Are internal/intranet URLs permitted or must private IP ranges be blocked?")
            score += 0.20

        ambiguity_score = round(min(1.0, score), 2)
        is_ambiguous = ambiguity_score > 0.40

        # 2. Normalized Requirements Specification (SRS)
        normalized_srs = {
            "title": "URL Shortener Service - System Requirements Specification",
            "version": "1.0.0",
            "ambiguity_score": ambiguity_score,
            "status": STATUS_NORMALIZED_AND_LOCKED,
            "functional_requirements": [
                {
                    "id": "FR-001",
                    "name": "URL Shortening",
                    "description": "Accept valid HTTP/HTTPS URL and return a 7-character Base62 short code. Handle custom alias if supplied.",
                    "acceptance_criteria": "Returns 201 Created with short_url, short_code, and expires_at."
                },
                {
                    "id": "FR-002",
                    "name": "Redirection Service",
                    "description": "Resolve short code and issue HTTP 307 redirect to target URL. Return 404 for missing and 410 for expired.",
                    "acceptance_criteria": "Latency < 10ms for cached URLs; updates click analytics synchronously or asynchronously."
                },
                {
                    "id": "FR-003",
                    "name": "Analytics Tracking",
                    "description": "Aggregate click counts, timeseries breakdown, referrer domains, and GDPR-anonymized client IP hashes.",
                    "acceptance_criteria": "GET /api/v1/analytics/{short_code} returns total clicks, top referrers, and daily clicks."
                },
                {
                    "id": "FR-004",
                    "name": "Custom Alias & Expiration",
                    "description": "Support optional alphanumeric custom aliases and configurable expiration TTL (default 30 days).",
                    "acceptance_criteria": "Rejects reserved words ('api', 'docs', 'health') and duplicate aliases with 409 Conflict."
                }
            ],
            "non_functional_requirements": [
                {
                    "id": "NFR-001",
                    "category": "Reliability & Rate Limiting",
                    "target": "Sliding-window rate limiter per client IP (60 write/min, 1000 read/min)."
                },
                {
                    "id": "NFR-002",
                    "category": "Security & SSRF",
                    "target": "Filter loopback (127.0.0.1, localhost) and AWS metadata (169.254.169.254)."
                },
                {
                    "id": "NFR-003",
                    "category": "Compliance",
                    "target": "GDPR-compliant IP hashing using SHA-256 with rotating salt; no plain PII storage."
                }
            ],
            "assumptions_locked": [a["default_assumption"] for a in ambiguities]
        }
        if llm_insights:
            normalized_srs["llm_insights"] = llm_insights

        # Save to context
        context.set_artifact("requirements_srs", normalized_srs)
        context.set_artifact("ambiguity_assessment", {
            "score": ambiguity_score,
            "is_ambiguous": is_ambiguous,
            "detected_ambiguities": ambiguities,
            "clarifications_needed": clarifications
        })

        context.record_decision(
            node_id=node.id,
            phase=self.phase,
            agent_name=self.name,
            decision="Normalized high-level user prompt into formal SRS with default governance assumptions.",
            rationale=f"Prompt evaluated with ambiguity score {ambiguity_score}. Standardized on HTTP 307, Base62+Murmur3, 30-day default TTL, and GDPR IP masking.",
            alternatives=["Halt and await human clarification", "Assume infinite URL lifetime", "Use 301 permanent redirects"],
            inputs=["user_requirement_prompt"],
            outputs=["requirements_srs", "ambiguity_assessment"]
        )

        return {
            "ambiguity_score": ambiguity_score,
            "is_ambiguous": is_ambiguous,
            "detected_ambiguities_count": len(ambiguities),
            "clarifications": clarifications,
            "functional_requirements_count": len(normalized_srs["functional_requirements"])
        }
