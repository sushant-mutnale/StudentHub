# Resumption by mode: exact practice resume, bounded formal pause

Practice interviews resume exactly across devices. Formal assessments recover after a disconnect within the deadline and allow one bounded, logged pause/grace window; there is no unlimited pause.

**Status:** accepted — resumption model. Checkpoint granularity, pause duration and deadline extension remain open.

## Consequences

- Practice session state must be checkpointed at least per turn, including plan position, outstanding question and transcript cursor.
- Formal assessments need an auditable pause record: who, when, duration, remaining time and reason category.
- A formal disconnect does not stop the clock; only the explicit bounded pause does.
- Cross-device resume requires authenticated ownership and a single active device/lease to prevent duplicate turns.
- Deadline extension rules must be deterministic and visible to the candidate.
- An interrupted formal session must not be silently converted into a practice session.
