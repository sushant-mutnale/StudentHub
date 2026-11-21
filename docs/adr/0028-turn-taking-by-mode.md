# Turn-taking by mode: barge-in in practice, controlled turns in formal assessments

Practice uses automatic endpointing with barge-in. Formal assessments use controlled turns with explicit cues and no barge-in.

**Status:** accepted — turn-taking model and text fallback. Endpointing thresholds and degraded-mode UX remain open.

## Consequences

- Two turn-taking policies must be implemented and tested, not one policy with a flag.
- Practice barge-in requires voice activity detection, interruption handling and partial-response cancellation.
- Formal assessments require explicit "your turn" cues and attributable, non-overlapping capture.
- The formal transcript must never merge speakers or attribute an interruption to the candidate.
- A candidate who cannot use barge-in must still be able to complete practice via explicit turn controls.
- Degraded browser speech must fall back visibly, not silently switch policies.
