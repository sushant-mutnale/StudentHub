# Per-competency difficulty, adapted within bounds

Difficulty is tracked as novice/intermediate/advanced per core competency and adjusted within declared bounds. Coverage stays fixed. Formal assessments use role-calibrated fixed difficulty.

**Status:** accepted — per-competency difficulty levels. Movement rules and anti-oscillation remain open.

## Consequences

- Each core competency carries a proficiency state within a session, separate from the candidate's long-term memory.
- A weak answer in one competency does not lower difficulty in another.
- Difficulty movement must be bounded per turn and per session to prevent oscillation or sudden jumps.
- The report must state the difficulty context; a high score at easy difficulty is not the same as at advanced.
- Formal assessments use a fixed role-calibrated level and do not adapt.
- The engine must distinguish "candidate struggled" from "question was mis-calibrated".
