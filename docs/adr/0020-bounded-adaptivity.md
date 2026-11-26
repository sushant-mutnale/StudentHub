# Bounded adaptivity in practice, fixed blueprints in formal assessments

Practice uses a blueprint that guarantees competency coverage while adapting topic order, follow-up depth and difficulty within predefined bounds. Formal assessments use a fixed blueprint.

**Status:** accepted — adaptivity model and difficulty levels. Exact bounds, movement rules and audit rules remain open.

## Amendment (canonical engine)

The canonical engine is stricter than the "neutral clarification/follow-up" permission above: formal slots declare a zero substantive follow-up allowance, so formal sessions emit only clarification turns and never a `follow_up` action. This keeps formal turns comparable across candidates. Practice adaptivity is unchanged.

## Consequences

- The blueprint is a coverage contract, not a rigid script; deviations must stay within declared bounds.
- The engine must record planned coverage and actual coverage so gaps are detectable.
- Difficulty changes must be explicit and bounded, not an emergent side effect of prompt wording.
- Formal assessments cannot adapt topic order or difficulty; only neutral clarification/follow-up is allowed.
- Adaptation policy must be versioned with the rubric so a report can explain the interview that actually occurred.
- The model may not freely invent topics outside the blueprint.
