# Mode-specific memory retrieval

Practice interviews retrieve a bounded, purpose-filtered projection of demonstrated competencies, prior feedback themes, unresolved gaps and stated preferences. Formal assessments retrieve only the target role, rubric and context the candidate explicitly provides. Prior practice scores are never retrieved for formal scoring.

**Status:** accepted — retrieval by mode and ranking. Token budget, projection schema and staleness rules remain open.

## Consequences

- Retrieval is a mode-aware service, not a generic "load all memories" step.
- The practice projection excludes raw transcripts by default and is bounded by a token budget.
- Formal assessment context is isolated from practice history by construction, not by prompt instruction alone.
- Every retrieved item carries purpose, provenance and freshness metadata.
- Candidate corrections and consent withdrawal must invalidate or refresh projections.
- Stale projections must expire or be rebuilt; they cannot silently outlive the source memory.
