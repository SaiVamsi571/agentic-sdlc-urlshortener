# Software Requirements Specification (SRS)
**Scenario**: BROWNFIELD
**Pipeline**: `a51db3b1-1afb-4eea-8054-09a1b07fbdc8`

## Input Prompt
> "Add sliding-window rate limiting and granular device/referrer click analytics without breaking existing APIs."

## Ambiguity Assessment
- Ambiguity Score: `0.65`
- Status: `NORMALIZED_AND_LOCKED`

## Normalized Constraints
- Code Length: 7 characters Base62 ([0-9a-zA-Z])
- Default TTL: 30 days (2,592,000 seconds)
- Expiration Status: HTTP 410 Gone
- Redirection Status: HTTP 307 Temporary Redirect
- Rate Limiting: 60 write req/min, 1200 read req/min
- Privacy: GDPR salted SHA-256 IP hashing
