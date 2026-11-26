# Persistent personalization with candidate consent and control

StudentHub may remember a candidate's professional journey across interviews only with explicit consent. Candidates can inspect, correct, delete and disable that memory. Memory is separated into profile/preferences, demonstrated competency evidence, prior interview experiences and outcomes, learning history/progress, and current session state; every item carries provenance (self-reported, extracted, demonstrated, inferred; `verified` is reserved until its definition is accepted). Inferred assessments never become established facts. Practice history may improve practice personalization and learning recommendations but must not automatically bias formal assessment scoring.

**Status:** accepted — persistent personalization requirement. Storage and retrieval mechanics are set by ADRs 0048 and 0053; deletion mechanics, consent UX and verification rules remain open.

## Consequences

- Session state and long-term memory are different stores with different lifecycles.
- Every retrieved memory must carry provenance and be task-scoped; agents receive projections, not the whole candidate record.
- Deletion must cover derived memories, retrieval indexes and caches.
- Private model reasoning is never stored as candidate memory.
- `verified` remains reserved until its definition is accepted; first-tier producers do not emit it.
- Formal assessment blueprints and rubrics are isolated from practice-derived signals.
