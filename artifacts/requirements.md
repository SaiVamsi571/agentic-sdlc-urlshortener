# Software Requirements Specification (SRS)
**Scenario**: AMBIGUOUS
**Pipeline**: `58dd8e46-cb65-470c-83d5-cdad9337668f`

## Input Prompt
> "Make the URL shortener faster, add marketing campaign things, and ensure expired links don't break horribly."

## Ambiguity Assessment
- Ambiguity Score: `0.8`
- Status: `NORMALIZED_AND_LOCKED`

## Normalized Constraints
- Code Length: 7 characters Base62 ([0-9a-zA-Z])
- Default TTL: 30 days (2,592,000 seconds)
- Expiration Status: HTTP 410 Gone
- Redirection Status: HTTP 307 Temporary Redirect
- Rate Limiting: 60 write req/min, 1200 read req/min
- Privacy: GDPR salted SHA-256 IP hashing
