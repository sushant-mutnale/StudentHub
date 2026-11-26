# Explicit text fallback when voice is unavailable or fails

If voice is unavailable or fails, the session continues in text with a clear notice; the mode change is recorded in integrity metadata. The fallback applies to both practice and formal assessments.

**Status:** accepted — voice fallback. Retry policy and endpointing remain open.

## Consequences

- The candidate is told when the mode changes and why, without a silent switch.
- The transcript remains authoritative; no speech is fabricated during fallback.
- Formal scoring rules do not change in text mode, but the report records the mode change.
- Practice hints and pacing remain available in text mode.
- The voice pipeline can be retried without losing the session.
- Accessibility testing must cover the fallback path, not just the voice path.
