# Canonical engine is a deep backend module behind a compatibility facade

The canonical interview engine is a new deep module at `backend/interview_engine/`. It owns interview semantics and exposes a small facade plus versioned contracts. API, worker, voice, and sandbox processes share the package rather than calling a separate engine service. `/agent-interview/*` remains the UI-facing contract through a compatibility adapter. The structured orchestrator and multi-agent loop are retired after parity, not extended. Existing interview data is not migrated or dual-written.

**Status:** accepted — engine boundary and migration contract. Provider selections remain open.

## Consequences

- Domain and application code must not import route modules, `multi_agent_system`, or the structured orchestrator.
- The compatibility adapter translates request and response shapes but contains no interview rules.
- API processes never make a network call to the engine.
- New sessions write only to `interview_engine_*` collections; legacy collections remain read-only until retention expiry.
- Rollout uses a per-type/per-mode flag; rollback is a flag flip, not automatic fallback to the legacy engine.
- Contract tests must cover the existing frontend calls before the facade is enabled.
