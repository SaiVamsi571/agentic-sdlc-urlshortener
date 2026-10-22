# Software Requirements Specification (SRS)
**Scenario**: GREENFIELD
**Pipeline**: `d4a0e43b-14f4-4a79-9457-db4cab106126`

## Input Prompt
> "Build enterprise URL shortener with Base62, custom aliases, 30-day TTL, LRU caching, and click analytics."

## Ambiguity Assessment
- Ambiguity Score: `0.5`
- Status: `NORMALIZED_AND_LOCKED`

## Normalized Constraints
- Code Length: 7 characters Base62 ([0-9a-zA-Z])
- Default TTL: 30 days (2,592,000 seconds)
- Expiration Status: HTTP 410 Gone
- Redirection Status: HTTP 307 Temporary Redirect
- Rate Limiting: 60 write req/min, 1200 read req/min
- Privacy: GDPR salted SHA-256 IP hashing
