# Requirements override the legacy live-score contract

The compatibility facade preserves `/agent-interview/*` endpoint names and request shapes, but accepted requirements override legacy score semantics. The canonical engine produces no live answer score, no overall score, and no hint penalty. Those legacy response fields are removed or null, hint use is reflected in confidence and limitations, and the first-slice UI is updated minimally to show competency evidence and the end-of-session report. Practice reports are owner-visible only; report sharing is formal-only in the first tier.

**Status:** accepted — compatibility semantics. Report display rules and dispute wording remain open.

## Consequences

- Compatibility contract tests must verify the absence of live and overall scores.
- The existing `MockInterview.jsx` summary is updated rather than preserving misleading score behavior.
- Hint requests remain available in practice but cannot reduce a score; formal hint requests are rejected.
- Candidate annotations and disputes never edit a score or imply human adjudication.
- Weight profiles remain rubric/coverage metadata and are never aggregated into a composite.
- Consumers that require a composite score are not supported by the canonical contract.
