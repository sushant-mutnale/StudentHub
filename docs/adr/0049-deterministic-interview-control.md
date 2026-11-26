# Deterministic control plane, model workers behind ports

Code owns the interview blueprint, coverage, ordering, state transitions, budgets, evidence rules, and scoring eligibility. LLMs and other models are confined to ports that propose questions, analyze answer signals, extract evidence, and draft narrative. Model output is parsed into typed proposals and validated before it can change state. The session application layer is the single conversational owner; subagents and workers receive task-specific projections and never speak to the candidate directly.

**Status:** accepted — control plane and conversational ownership. Provider selection, routing, and prompt strategy remain open.

## Consequences

- The model does not choose stage, coverage, follow-up, or scoring policy.
- A bounded synchronous turn signal informs follow-up choice; deep evidence extraction is asynchronous.
- Invalid or out-of-contract model output falls back to deterministic blueprint behavior.
- Model-facing context is a recorded, bounded projection, never the full candidate record or full transcript.
- Domain rules are testable without a provider or database.
- Every generated question records its blueprint slot and context references.
