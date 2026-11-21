# First-tier formal reports have no overall score

The formal report presents competency scores with linked evidence and a narrative summary. It does not display a single overall score, and progress is tracked per competency. If a composite is ever introduced, ADR 0008's rule applies: it is type-specific and never compared directly across types.

**Status:** accepted — no overall score and report shape. Per-competency rules and dispute status details remain open.

## Consequences

- The report schema must not reserve a prominent composite field that the UI can accidentally surface.
- Consumer views rank or compare only at the competency level, with type and rubric version visible.
- Narrative summaries must be grounded in the same evidence as the scores and must not imply an overall judgement.
- Progress views show competency trends, not a single improving number.
- Introducing an overall score later is a product change requiring a new decision, not a formatting change.
