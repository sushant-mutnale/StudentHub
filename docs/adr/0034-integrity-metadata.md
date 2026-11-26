# Standard integrity metadata, without surveillance data

The shared report shows completion status, duration, mode (text/voice), pause count/duration, disconnect count, hint count (practice only), hidden-test run status, and rubric/weight version. It does not expose device/browser, IP, per-turn timestamps, or audio hashes.

**Status:** accepted — report integrity fields. Display wording and access rules remain open.

## Consequences

- Integrity metadata is factual and non-accusatory; it describes the session, not the candidate's intent.
- No device fingerprinting, IP display, or per-turn surveillance appears in the shared report.
- Practice hint counts are shown, but formal assessments have none by design.
- Hidden-test status is reported without exposing cases or per-case outputs.
- Metadata must be interpreted alongside confidence; it does not adjust scores by itself.
- Identity verification and proctoring remain out of the first tier.
