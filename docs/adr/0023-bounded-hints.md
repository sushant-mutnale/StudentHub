# Bounded hints with no score penalty

Practice allows a small, visible hint budget (for example 3 per session), logs each hint, applies no score penalty, and reflects hint use in confidence/limitations. Formal assessments have no hints.

**Status:** accepted — hint policy and approximate count. Content bounds and confidence adjustment remain open.

## Consequences

- Hint budget is enforced server-side and shown to the candidate.
- Each hint is logged with its content and the answer it preceded.
- Hint use does not reduce competency scores, but it can lower confidence or add a limitation.
- Hints must not reveal the expected answer or hidden test cases.
- Formal assessments disable the hint path entirely.
- The report must disclose hint count and placement, not just a total.
