# Purpose-based consent with class-based retention tiers

Candidates consent separately to practice personalization/memory, learning recommendations, formal report creation/sharing, and analytics/model improvement. Retention is set per data class, with fixed defaults and jurisdiction overrides. Formal-report consent is independent of practice-memory consent: withdrawing one purpose does not silently disable the others.

**Status:** accepted — consent model and class-based retention tiers. Consent UX, analytics scope, deletion verification, export format and jurisdiction overrides remain open.

## Consequences

- A purpose registry and consent-state model are required, with per-purpose withdrawal.
- Every stored memory and derived artifact must carry its purpose and retention class.
- Analytics/model-improvement use is opt-in and must not consume data from withdrawn purposes.
- Formal reports need their own consent, sharing controls and retention independent of practice history.
- Deletion must propagate through derived memories, indexes, caches and backups on a defined SLA.
- Consent changes must be auditable without storing unnecessary sensitive content.
