# Bounded, relevance-ranked retrieval with invalidation

Practice retrieval ranks by relevance to the current competency and role, prefers recent non-conflicting evidence, excludes withdrawn or invalidated memories, and respects a token budget. Formal assessments remain isolated from practice memory.

**Status:** accepted — retrieval ranking. Token budget, projection schema and staleness windows remain open.

## Consequences

- Retrieval is a ranked projection, not a transcript search or a recency dump.
- Consent and purpose filters apply before ranking, not after.
- Withdrawn or corrected memories must be excluded immediately; stale projections must expire.
- The token budget is enforced server-side and visible in evaluation metadata.
- Formal assessment retrieval never touches practice memory, even if relevant.
- Every retrieved item carries provenance, freshness and the reason it was included.
