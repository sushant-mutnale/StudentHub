# Two to three short, labelled evidence excerpts per competency

Each competency carries two to three short verbatim excerpts, each at most two sentences, labelled by source question/turn, PII-redacted, and including counter-evidence where it exists.

**Status:** accepted — evidence excerpt policy. Redaction implementation and counter-evidence thresholds remain open.

## Amendment (canonical engine)

A competency with only one instance, or whose turn analysis failed, still carries two to three excerpts: they are drawn from the single turn, or from the verbatim turn text when analysis failed, and an insufficient-evidence limitation accompanies them. The count rule is never relaxed and no excerpt is ever invented.

A `not_assessed` competency carries no excerpts at all, because there is no evidence to excerpt; it is rendered as `not_assessed` rather than as a scored competency.

## Consequences

- Evidence selection must search the whole session, not just the answer that triggered a score.
- Counter-evidence is required when it exists; a one-sided evidence set is a defect.
- Excerpts must be verbatim and traceable to a turn, with PII redacted.
- The shared report still excludes the full transcript and audio.
- Evidence excerpt length is capped independently of answer length.
- Redaction must not change the meaning of the excerpt or hide a contradiction.
