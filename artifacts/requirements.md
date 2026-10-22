# Software Requirements Specification (SRS)
**Scenario**: BROWNFIELD
**Pipeline**: `8de30559-e1b0-4a66-9d34-029c9d5f9f21`

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
