# Balanced latency and cost envelope

Target p95 voice turn latency of 3 seconds in practice and 2 seconds in formal. Evaluation runs asynchronously with the report ready within 2 minutes. An explicit per-session cost cap guides model routing.

**Status:** accepted — latency/cost envelope. Cost-cap value, provider benchmarks and measurement method remain open.

## Consequences

- Voice responses must stream; TTS starts before the full answer is complete where possible.
- Evaluation is a separate asynchronous stage, not part of the conversational turn.
- Model routing and caching are cost controls, but cannot silently degrade formal assessment quality.
- Every session records latency and cost per turn/stage for budget enforcement.
- Exceeding the cap must degrade gracefully or stop, not overspend silently.
- Targets are product budgets to validate, not guarantees to publish before measurement.
