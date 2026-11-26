# Hybrid interview lifecycle: durable practice, controlled assessments

StudentHub supports two interview lifecycles over one session aggregate. Practice interviews are durable and resumable: answers are persisted before evaluation, disconnect/reload resumes the same session, evaluation is retryable, and abandoned sessions expire after a defined window. Formal assessments are time-bound and controlled: a fixed competency blueprint, consistent scoring, no resumption after the deadline, and no hint/coaching behaviour. Previous practice results may inform preparation but must not automatically bias formal assessment scores.

**Status:** accepted — hybrid lifecycle. Detailed state machine, deadlines and review process remain open.

## Consequences

- The session model needs an explicit mode and state machine, not two unrelated implementations.
- Persistence and recovery are ordinary operations for practice and exceptional, audited operations for assessments.
- Evaluation must distinguish formative feedback from summative scoring.
- The existing structured and multi-agent paths must converge on this model rather than remain parallel products.
