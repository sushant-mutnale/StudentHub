# First-tier memory retrieval uses structured Mongo projections and lexical ranking

Practice memory retrieval reads typed Mongo memory items, filters by consent purpose, candidate, validity, and mode, then ranks by competency/role match, recency, non-conflict, provenance weight, and lexical relevance. The token budget is enforced server-side and every selection is recorded. Formal assessments receive an empty practice projection. Withdrawn or corrected items are excluded immediately. A vector index may be added later behind the same retrieval port; no vector database enters the first tier.

**Status:** accepted — retrieval mechanism and first-tier data dependency. Token budget, weights, staleness windows, and projection schema remain open.

## Consequences

- Retrieval is explainable and deletion-safe without a second data service.
- Ranking inputs are recorded so a report or audit can explain why an item was included.
- A vector or hybrid index can be added without changing the engine contract.
- The retrieval port must isolate storage details from the application layer.
- Formal isolation is structural: practice memory is never in the formal projection.
