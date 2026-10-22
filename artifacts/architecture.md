# Architectural Decision Records (ADRs)
**Service**: AetherSDLC Enterprise URL Shortener
**Version**: 1.1.0

## ADR-001: 64-Bit MurmurHash3 + Base62 Encoding
- **Decision**: Hash normalized URL with salt using 64-bit MurmurHash3, encode low 42 bits to 7 Base62 characters.
- **Rationale**: Provides 3.52 trillion distinct keys with uniform distribution and sub-microsecond compute speed.
- **Collision Handling**: If key exists in SQLite, re-hash with salt counter until vacant slot is found.

## ADR-002: In-Memory Thread-Safe LRU Cache with TTL
- **Decision**: Guard `OrderedDict` with `threading.RLock()`.
- **Rationale**: Eliminates SQLite disk read overhead for 90%+ read traffic.

## ADR-003: GDPR-Compliant Salted IP Analytics
- **Decision**: Hash client IP with cryptographic salt before recording click events.
- **Rationale**: Prevents storing identifiable PII while maintaining accurate unique visitor metrics.
