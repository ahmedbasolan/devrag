# Architecture Decision Records

## ADR-001: Use Flask over Django

**Date:** 2024-01-15

**Decision:** We will use Flask as the web framework instead of Django.

**Context:**
- Need lightweight API framework
- Team is more familiar with Flask
- No admin panel requirement
- Simpler deployment with fewer dependencies

**Consequences:**
- More flexibility in choosing components
- Need to add libraries for ORM, auth, etc.
- Less built-in functionality
- Faster startup time

## ADR-002: JWT Authentication

**Date:** 2024-01-20

**Decision:** Use JWT tokens for API authentication instead of session-based auth.

**Context:**
- Stateless API design
- Mobile app clients
- Microservices architecture planned
- No server-side session storage needed

**Consequences:**
- Tokens can't be revoked easily (use short TTL)
- Need to handle token refresh
- Simpler horizontal scaling
- Client-side token storage required

## ADR-003: SQLite for Development

**Date:** 2024-02-01

**Decision:** Use SQLite for development, PostgreSQL for production.

**Context:**
- Faster local development
- No database server setup needed
- Production needs concurrent writes
- Team needs simple local setup

**Consequences:**
- Dev/prod parity gap (different SQL dialects)
- Need to test migrations on both
- Simpler onboarding for new developers
- Production requires connection pooling

## ADR-004: Cache Invalidation Strategy

**Date:** 2024-02-10

**Decision:** Use time-based TTL with event-driven invalidation for cache.

**Context:**
- Products change infrequently
- User sessions need real-time updates
- Search results can be slightly stale
- Admin stats should be near real-time

**Consequences:**
- 5-minute TTL for most cached data
- Immediate invalidation on product updates
- User cache cleared on login/logout
- Slight data consistency trade-off for performance
