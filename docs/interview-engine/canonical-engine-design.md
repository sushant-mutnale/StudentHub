# Canonical Interview Engine — Design

Status: implemented (first slice)

Date: 2026-11-21

This design records the canonical-engine decision gate. It is not an implementation plan and does not select an LLM, STT, TTS, object-storage, or sandbox vendor. Product requirements remain in `docs/interview-engine/requirements.md`; gate decisions are recorded in ADRs 0047–0054.

## 1. Gate decisions

| Decision | Choice | Consequence |
|---|---|---|
| Frontend contract | Preserve `/agent-interview/*`, swap internals | Compatibility adapter, no big-bang UI rewrite |
| Session source of truth | MongoDB authoritative; Redis for leases/cache | Durable resume and audit; Redis loss is recoverable |
| Control plane | Deterministic code; LLM workers behind ports | Coverage and scoring rules are enforceable |
| Engine boundary | Deep module in `backend`, shared by API/workers | No new service or network hop |
| Existing engines | New engine; reuse adapters only | Structured orchestrator and multi-agent loop are retired behind the facade |
| Blueprint lifecycle | Immutable per-session snapshot | Auditability and consistent scoring; practice adapts topic order, depth, and difficulty only within declared bounds |
| Async delivery | Mongo transactional outbox with atomic claim | At-least-once delivery; no Redis delivery truth |
| Voice | Practice: browser speech. Formal: WebSocket streaming plus dedicated voice deployment | Practice degrades visibly; formal server transcript is authoritative; WebRTC deferred |
| Code execution | Dedicated sandbox worker with hardened ephemeral containers | Separate workload; hidden tests stay out of the sandbox |
| Retrieval | Structured Mongo projections plus lexical ranking | No vector database in the first tier; vector port deferred |
| Scores | Requirements win over legacy UI | No live answer score, no overall score, no hint penalty |

## 2. Goals and non-goals

### Goals

- One canonical interview engine with explicit contracts and enforceable invariants.
- First production types: behavioral/HR, technical knowledge, resume/project deep-dive, and DSA/coding, across text and voice where applicable. System design, debugging/code review, case-based, and company/job-specific types remain in scope and must not be designed out; this document fixes the type-extensible blueprint, evidence, and rubric contracts for all of them, and fully specifies their structural shape, while each deferred type's concrete slot intents, fallback text, and rubric descriptors are separate specifications tracked as tickets before that type is scheduled. That deferral is listed in §11.
- Durable, resumable practice sessions and bounded, auditable formal sessions.
- Blueprint-driven coverage with bounded adaptivity and contextual follow-ups.
- Evidence-based competency scoring with independence, provenance, confidence, and limitations.
- Candidate-owned reports with no composite score and time-limited sharing.
- Reliable asynchronous evaluation, report generation, memory updates, and retention.
- A migration path that keeps the existing interview UI working through a compatibility facade.
- Independent testability of domain rules without providers or databases.

### Non-goals for the first tier

- Full event sourcing with projections and replay.
- A separate engine microservice or durable workflow runtime.
- WebRTC, live proctoring, identity verification, or human sign-off.
- A vector database, external code-execution service, or external message broker.
- Multi-region active-active deployment.
- Migrating or rewriting existing interview data.
- A composite candidate score or recruiter ranking.

## 3. Architecture

### 3.1 Module

`backend/interview_engine/` is the sole owner of interview semantics. It exposes a small facade and versioned contracts; all other modules are private.

```
interview_engine/
  contracts/        public DTOs, commands, results, events
  domain/           Session, Blueprint, Turn, Evidence, ScoringPolicy
  application/      start, submit, pause, resume, end, evaluate, report, memory
  ports/            narrow protocols for repositories and external capabilities
  adapters/         Mongo, Redis, outbox, providers, voice, sandbox, storage
  compatibility/    /agent-interview/* mapping
```

### 3.2 Layers

- **Contracts** — immutable, versioned DTOs. Route models and provider outputs are translated at the edges. The synchronous turn-signal schema, the next-action rule, and the session-view DTO are contracts, persisted or referenced so step 6 and the outbox handler consume one recorded input.
- **Domain** — pure Python. Owns lifecycle, coverage, question ownership, hint limits, evidence independence, and score eligibility. Imports nothing external.
- **Application** — use cases and transaction boundaries. Orchestrates domain, ports, events, and outbox writes. It is the single conversational owner: no port, worker, or subagent authors final candidate-facing language. Generator ports propose text; the application validates, bounds, and selects it, or substitutes blueprint fallback text, so what the candidate finally reads is always application-selected. Voice media may transport, transcribe, and synthesize application-authored text, but it never decides what to ask or say.
- **Ports** — protocols for session repository, unit of work, outbox, lease store, question generator, hint generator, clarification responder, answer analyzer, evaluator, narrator, memory projector/retriever, STT, TTS, candidate code runner, trusted code evaluator, clock, and identifiers. Model-facing ports receive task-specific projections, never the full candidate record or full conversation. Blueprint planning is a pure domain service, not a port, because it is deterministic and has no external capability; the application retrieves any memory projection and passes it into the planner. Hints and clarification replies come from these ports but are validated and bounded by the application before they reach the candidate; fallback hint, question, and clarification text come from the blueprint when generation fails, and the report narrator falls back to a deterministic template built from the competency scores, evidence excerpts, and limitations when its port fails, so no report is blocked by a provider outage.
- **Adapters** — Mongo repositories, Redis leases/cache, Mongo outbox, provider clients, voice transport, candidate sandbox runner, trusted evaluator client, object storage. Adapters never own interview rules.
- **Compatibility** — maps the existing `/agent-interview/*` request and response shapes onto canonical use cases. It contains no interview rules.

### 3.3 Dependency rule

Domain imports nothing external. Application imports domain and ports. Adapters and compatibility import inward. Canonical code must not import `multi_agent_system`, the structured orchestrator, or route modules. LLM output is parsed into typed proposals and validated before it can change state.

### 3.4 Process boundaries

API, workers, voice media, candidate code execution, and the trusted evaluator are separate deployments that share the engine package. The API never makes a network call to the engine. Workers call the same application use cases through queue handlers.

### 3.5 Data ownership

Canonical collections use the `interview_engine_*` prefix. The session snapshot is authoritative and embeds the immutable blueprint snapshot and the accepted-turn index (turn id, sequence, slot, kind, payload reference). Turn payload text, audio references, and code references live on the append-only `interview_engine_turns` collection, so the session document stays small and bounded regardless of transcript length while resume still needs no cursor. The snapshot tracks three counters with distinct jobs: `version` is the optimistic-concurrency token, bumped by every state-changing write; `event_sequence` is a strictly increasing per-session counter assigned to every appended event, so event order is unique and monotonic even for writes that do not change interview state; `last_applied_sequence` mirrors the highest applied event sequence, which is what recovery compares. The fencing-token write is a lease guard: it is guarded by the lease, not by `version`, and does not bump `version`. A takeover issues a new token, and the previous token becomes stale, so an in-flight turn from the old device fails the token check rather than a version check. A takeover appends `SessionLeaseTakenOver` with a fresh `event_sequence` and advances `last_applied_sequence`, because event order must stay monotonic; the append is itself lease-guarded, so a concurrent state write can only interleave by taking the lease first, and the version check still protects the state write. Append-only `interview_engine_turn_analyses`, `interview_engine_evidence`, `interview_engine_code_runs`, and `interview_engine_events` collections hold async analysis, evidence, code execution, and audit records keyed by session and turn. `interview_engine_turn_commands` is a mutable collection holding the `TurnCommandRecord` (`pending|complete`, keyed by `(session_id, idempotency_key)`), separate from the immutable turn records. `interview_engine_questions` holds generated questions keyed by `question_generation_key`, `interview_engine_hints` holds provided hints keyed by `hint_idempotency_key`, and `interview_engine_submissions` holds accepted formal final submissions keyed by `(session_id, slot_id)`. `interview_engine_reports` holds the report record created at completion — id, session id, outcome, retry status, and the body once assembled — so `GetReport` and `/feedback` read a durable record with a stable id rather than a derived view. Report read models and compatibility responses are derived from the durable report record and session snapshot; candidate-controlled memory items are authoritative records, not derived models, and their corrections/deletions are the source of truth for invalidation. Required indexes include unique `(session_id, idempotency_key)` for turn commands, unique `(session_id, hint_idempotency_key)` for hints, unique `(session_id, question_generation_key)` for generated questions, unique `(session_id, run_idempotency_key)` for code runs, unique `(session_id, slot_id)` for accepted final submissions, unique `(candidate_id, client_request_id)` for session starts, unique `(session_id, command_id)` for pause/resume/principal-transfer commands, unique `(session_id, end_command_id)` for end commands, unique `(report_id, annotation_idempotency_key)` for report annotations and disputes, unique `(candidate_id, memory_mutation_idempotency_key)` for memory mutations, unique `(candidate_id, share_request_id)` for share creation and renewal, unique event id, unique outbox event id, and working indexes for candidate/status and outbox status/availability.

MongoDB must run as a replica set because session writes and outbox records commit in one transaction. Standalone Mongo is not a supported production configuration for the engine.

Legacy interview collections remain untouched. The engine does not dual-write or silently migrate them.

## 4. Domain model

### 4.1 Session aggregate

`Session` owns lifecycle and turn correctness:

- identity: session id, candidate id, mode, interview type, schema version, last applied sequence;
- governance: role/JD snapshot, consent snapshot, blueprint reference, rubric/weight versions;
- timing: created/started/ended timestamps, deadline, pause ledger, idle/expiry state;
- live state: status, version, current slot, plan position, adapted slot order (practice only), per-competency difficulty state, outstanding question, asked questions, hint usage;
- evidence state: coverage ledger, evidence references, integrity metadata;
- concurrency: current fencing token and its holder (candidate device or delegated voice-media principal). The lease itself is a short-lived Redis guard; Mongo holds only the authoritative token value used to reject stale writers.

Statuses:

`planned → in_progress | expired | abandoned | completed`; `in_progress ↔ paused`; `in_progress|paused → completed | abandoned`; and `planned → expired` only for a session that never started. `planned → completed` exists because a crash between persisting the session and persisting the first question leaves a `planned` session that must still be endable. A started session never expires: a formal session that reaches its deadline transitions to `completed` and is still scored, and a practice session has no deadline. This is what makes practice durably resumable.

`completed` carries a report outcome of `evaluating`, `ready`, `suppressed`, or `failed`; `suppressed` is an outcome, not a separate session status. A report record and id are created at completion for every outcome; a `suppressed` or `failed` report has an outcome but no body.

Transitions are explicit domain methods. Invalid transitions fail without partial state changes.

Invariants:

- exactly one outstanding question per session at rest; `question_pending` is the persisted substate that says the next question is being produced, and a session in that substate has no outstanding question;
- no answer is accepted without a matching outstanding question;
- no answer is accepted from an unauthorized principal: the candidate must own the session and present the current fencing token, or an authenticated voice-media service principal must be bound to that session and fencing token by a delegated token;
- an idempotency key creates at most one turn;
- a question or question intent is not repeated within a session;
- only the session application layer produces candidate-facing messages;
- formal sessions cannot request hints, adapt difficulty, retrieve practice memory, accept browser-sourced transcripts, or accept a `code` answer outside `SubmitFinalCode`;
- practice hints consume a bounded budget and are recorded;
- deadline and pause rules are evaluated server-side;
- every state change increments `version` and appends an event; the fencing-token write is a lease guard that does not change interview state and is guarded by the lease rather than `version`, so it bumps no version and appends only the `SessionLeaseTakenOver` audit event; every appended event takes the next `event_sequence`, and the event record carries it;

### 4.2 Blueprint

A blueprint is an immutable, versioned snapshot created at session start. Adaptation never mutates it; it produces a separate session `plan` (adapted group order and plan position) that references blueprint groups.

A blueprint records:

- interview type, mode, role/JD snapshot;
- competency framework version and published weight profile version;
- the shared core competencies: problem-solving, technical/domain depth, communication, structure, and evidence/verification, plus type-specific dimensions only where the interaction produces evidence;
- ordered groups, each with one competency and a slot count (fixed at 2 for the first tier); each slot has dimension, difficulty band, one question intent, target evidence count, follow-up allowance, an advisory time budget (reported as coverage metadata, never enforced as a per-slot cutoff), a pre-authored fallback question, a pre-authored clarification text, and a pre-authored hint for practice; formal slots declare a zero substantive follow-up allowance;
- type-specific configuration such as coding language or report rubric.

Each group declares its competency and a slot count; the first tier fixes that count at 2, and a type may declare more so a competency can accumulate three or more independent instances. A group is consumed when all of its slots have been asked. Each slot has its own distinct question intent, so a competency's formal independent-instance capacity equals the sum of its groups' slot counts. A slot's `target evidence count` is the per-slot evidence goal.

Practice follow-ups are distinct questions and can add one `new` instance for a slot, but only when the deterministic rule emits `follow_up`, which requires an `incomplete` or `off_topic` answer. The follow-up answer itself is analyzed normally, so it can be `sufficient`/`new` and record an instance; the triggering answer's own outcome is unchanged. Formal slots have no follow-ups, so formal capacity equals the slot count exactly. This means practice capacity for a competency is its slot count plus at most one follow-up per slot, which is why the independence ledger is sized by slots plus allowances rather than by slots alone.

First-tier blueprint shape, which the first slice implements: five groups — problem-solving, communication, structure, evidence/verification, technical/domain depth — each with two slots, giving ten slots in a fixed pair order. Each slot targets one independent instance and allows at most one substantive follow-up in practice and zero in formal, so each competency has capacity for at least two instances and ADR 0031's requirement that the blueprint create enough opportunities is met; whether two instances are actually recorded depends on the answers, since a `same` answer records none. Behavioral weights come from requirement 43. The remaining first-tier types use the same two-slot group shape with their own group-to-competency mapping, slot intents, and requirement-43 weights. Deferred types reuse the same shape and must declare a weight profile version even while their values are open.

A blueprint may declare a slot count above two for a competency, which is the only way to reach three or more opportunities. The first tier declares two for every type, so first-tier formal reports cap at `medium` confidence; a future type that needs `high` in formal mode declares three. This is a deliberate first-tier limit, not a contradiction: ADR 0032 requires that `high` be reachable, which the contract permits, while the first-tier weight profiles do not require it.

Formal blueprints are fixed. Practice may reorder groups, deepen within a slot, probe project decisions or misconceptions, and adjust difficulty only inside declared bounds; these adaptations are recorded on the session plan, never on the blueprint. Coverage requirements cannot be removed by adaptation. Practice planning uses the bounded memory projection to deprioritize previously assessed topics; formal planning does not use practice history.

Difficulty uses the fixed ADR 0022 enum per competency: `novice`, `intermediate`, `advanced`. The blueprint derives each slot's level deterministically from the role/JD seniority signal: an explicit seniority band in the role/JD text maps `intern|junior` → `novice`, `mid` → `intermediate`, `senior|staff|principal` → `advanced`, and no recognizable signal → `intermediate`. The legacy `difficulty` field (`easy|medium|hard`) is ignored by the canonical engine and is not a blueprint input; the adapter drops it. Practice movement is a pure function of the last `new` instance for that competency: `sufficient` moves one step up unless already `advanced`, `incomplete` moves one step down unless already `novice`, and `off_topic` or `same` never moves. To distinguish "candidate struggled" from "question mis-calibrated", a down-move requires the instance to be `incomplete` and the synchronous analyzer to mark the answer as substantively deficient; an instance marked as a technical or provider limitation never moves difficulty down, and a candidate-supplied "question was unclear" clarification never moves it either. Movement is capped at one step per slot, never leaves the enum, and never reverses the previous move's direction, so a competency cannot oscillate up-down-up. It is computed when the next slot for that competency is planned, so a follow-up within a slot stays at the slot's level. Formal never moves. The adaptation policy carries its own version, recorded with the blueprint so the report can state the difficulty context.

The first-tier blueprint fixes each group at two slots. `target evidence count` is authored blueprint content, fixed at 1 for every first-tier slot. Weights communicate type emphasis and never change slot composition, target counts, or the level scale.

First-tier behavioral slot content, fixed here so the slice is buildable: each competency group's first slot asks for a concrete past situation and its outcome, and its second slot asks for reflection on what the candidate would do differently or how they verified the result. Each slot's dimension is the group's competency itself, so the behavioral blueprint uses one dimension per competency. Per slot, `target evidence count` is 1, practice `follow_up_allowance` is 1, and formal `follow_up_allowance` is 0. Each slot carries its own pre-authored fallback question, clarification text, and practice hint, written as neutral prompts over the role/JD snapshot. The literal strings are a first-slice deliverable: they ship as data in the behavioral blueprint module and are authored with the slice, not deferred as a design decision.

Slot advancement is explicit: a slot advances to `next_slot` when the synchronous signal is `sufficient`, or when its `follow_up_allowance` is spent. An `answer` with an `incomplete` or `off_topic` signal and remaining allowance yields `follow_up`; once the allowance is spent the slot advances, and an unmet target records the coverage limitation.

Follow-ups differ by mode. Practice follow-ups may probe, challenge, or deepen and consume the slot's `follow_up_allowance`. Formal slots declare a zero substantive follow-up allowance, so the `follow_up` action is never emitted in formal mode; a formal candidate may only ask a clarification, which is a separate turn kind with its own `await_answer` action and never consumes allowance. Clarifications may not introduce new topics, adapt difficulty, or challenge the answer. This is stricter than ADR 0020's allowance for neutral formal follow-ups, and it supersedes that permission for the formal mode because it keeps formal turns comparable across candidates; ADR 0020's practice adaptivity is unchanged.

Planning and question generation are source-bounded: they may use the role/JD, resume/profile snapshot, prior answers, and retrieved memory projections, but they must not invent candidate experience, projects, or outcomes. Each generated question records the blueprint slot and context references that produced it. Candidate-facing phrasing must be contextual and avoid generic acknowledgements or fixed question sequences.

### 4.3 Turn

A turn is an append-only record of:

- kind: `answer` or `clarification_request`;
- question snapshot and slot reference;
- answer payload: text, audio reference, or code reference;
- idempotency key, device id, server timestamps;
- integrity data: mode, pause/disconnect state, hint state.

Submitted turns are immutable. Async analysis state lives in a separate `TurnAnalysis` record keyed by turn id, which references the evidence it produced; turns are never updated in place. Candidate annotations are separate records. Full answers are persisted; model-facing projections are bounded by an explicit token budget and recorded, never silently truncated to a fixed character count. Turn and evidence records inherit the session's consent purposes and retention class; they do not carry independent defaults.

### 4.4 Evidence ledger

Each evidence item records:

- competency and dimension;
- provenance: `self_reported`, `extracted`, `demonstrated`, or `inferred`; `verified` is reserved and is not emitted until its definition is accepted;
- verbatim quote and normalized observation;
- strength, source turn, source question, and independence group;
- validity, redaction state, and creation metadata.

Independence is assigned explicitly by the turn's `instance` marker: a `new` marker creates a new instance, a `same` marker does not. A distinct question is `new` by default; a practice follow-up is `new` only when it asks for a new demonstration, which is how ADR 0038 reads it, and `same` when it probes the same demonstration. Repeating the same claim within one answer is always `same`. An inferred item never becomes an established candidate fact, and private model reasoning is never stored as memory.

### 4.5 Scores and report

A competency score is one of:

- a rubric level with evidence references, confidence band, reasons, and limitations;
- `not_assessed`, when there is no relevant evidence.

Confidence is decided by one ordered rule over synchronously recorded independent instances. This rule is the single source of truth:

1. no instance → `not_assessed`;
2. any synchronously flagged contradiction → `low`;
3. exactly one independent instance → `low`;
4. at least three consistent independent instances spanning at least three distinct questions, with no contradiction → `high`;
5. otherwise → `medium`.

Difficulty does not enter this rule. Each instance records the level at which it was demonstrated and whether that level was the blueprint's declared level or an adapted one. When practice adapts away from the declared level, the band is unchanged but a difficulty-context limitation is recorded and the report discloses both levels, so a reader can see that an adapted-level instance supported the score. ADR 0032's "expected difficulty" condition is satisfied in formal mode by construction, because formal never adapts.

First-tier sessions reach `medium` at most in formal mode, because a formal slot has no substantive follow-up and the first tier declares two slots per competency. In practice, a two-slot first-tier competency can reach `high` if an `incomplete` or `off_topic` answer triggers a follow-up whose own answer is `sufficient`/`new` or `incomplete`/`new`, producing a third independent instance; the confidence rule is then applied literally. A type whose rubric needs `high` in formal mode declares three or more slots, which is how ADR 0032's reachability requirement is satisfied; the first tier declares two, so first-tier formal reports stop at `medium` by construction, as stated in the ADR 0032 amendment.

The score value is a level from the published rubric for that competency and type, never a free-form number. The first-tier level scale is fixed and ordered: `emerging`, `developing`, `proficient`, `strong`. Each level has written descriptors; the descriptor text is rubric content and remains open, but the level names and their order are fixed so reports, compatibility responses, and tests can be written now. Evidence strength is a normalized enum (`weak`, `moderate`, `strong`) with rubric-defined meaning.

Level assignment is a total function of the independent instances, so every session resolves deterministically. Only `new` instances with outcome `sufficient` or `incomplete` enter it; `same` instances and `off_topic` turns never do.

- zero instances → `not_assessed`;
- no `sufficient` instance → `emerging`;
- some but fewer than half `sufficient` → `developing`;
- at least half but not all `sufficient` → `proficient`;
- all instances `sufficient` → `strong`.

With two instances this yields `emerging`, `proficient`, or `strong`, so a 1/1 split is `proficient`. A contradiction does not change the level; it caps confidence at `low` and adds a conflicting-evidence limitation. Descriptor text explains these levels to the candidate and never changes the mapping.

No composite score is produced. Weight profiles are rubric and coverage metadata: they communicate type emphasis and never aggregate into a composite score. They do not change the level scale, the slot shape, or the confidence rules.

`Report` contains:

- interview type, target role, dates, duration, mode;
- question and difficulty coverage;
- competency scores with two or three short verbatim evidence excerpts each, redacted, sourced to a question/turn, and including counter-evidence where present; when only one instance exists the excerpts are drawn from that turn and an insufficient-evidence limitation is added; when an analysis failed, the verbatim turn text substitutes; a `not_assessed` competency has no excerpts and is rendered as `not_assessed`, never as a score with empty evidence; in every other case the excerpt rule of ADR 0027 holds;
- evidence-grounded narrative summary;
- structured limitations using fixed categories: insufficient evidence, conflicting evidence, time/coverage constraint, mode/technical limitation, and hint assistance, with hint count and the questions each hint preceded;
- integrity metadata, including completion status, blueprint version, rubric/weight version, mode, pause count and total pause duration, disconnect count, hint count for practice, and hidden-test status for coding. A disconnect is counted when the device lease is lost and the session is subsequently taken over by `ResumeSession`, or when the lease expires and the session is resumed; a same-device retry is not a disconnect. Practice counts the same way for consistency, even though it has no deadline;
- candidate annotations and unresolved disputes;
- disclosure metadata: AI-generated questions, AI-assisted evaluation, no proctoring, no identity verification, and no human review of the score;
- share status and expiry; practice reports record `not_shareable` with no expiry.

A dispute creates an unresolved annotation; it does not change the score, trigger an automatic re-score, or imply human adjudication.

`ReportShare` is a separate record: hashed token, expiry, revocation state, and an access log. Links expire after 90 days by default, may be renewed while the report is retained, and are revocable at any time. The raw link is returned only at creation/renewal; the stored value is a hash. Anonymous viewers redeem it without an account and cannot see owner-only fields. Access logs are candidate-visible. Sharing is formal-only in the first tier; practice reports remain owner-visible only. Raw transcript, audio, rankings, and role-fit verdicts are excluded from the report.

### 4.6 Memory

`MemoryItem` is typed, provenance-labelled, consent-purpose-scoped, validity-aware, and linked to its source session/turn. Memory classes are candidate profile/preferences, demonstrated competency and skill evidence, previous interview experiences, learning history/progress, and current session state.

Current session state is not long-term memory. Practice retrieval uses a bounded projection. Formal assessment retrieval excludes practice memory even when relevant. Candidates can inspect, correct, delete, and disable persistent memory. Withdrawal or correction invalidates the item and all derived caches/indexes; deletion events cover derived memories, retrieval indexes, and cached copies. An inferred assessment never becomes an established fact.

## 5. Public contracts

Contracts are versioned and immutable.

### 5.1 Commands and results

**Session view** is one DTO reused by start, resume, `409`, and `202` responses: session id, status, version, report id and outcome, current slot and plan position, outstanding question (nullable), `question_pending` flag, remaining time, hint availability, and the caller's fencing token.

**Next-action rule** is deterministic and evaluated from persisted typed signals only:

1. `await_answer` when the turn was a clarification request; the question stays outstanding, and the result's `next_question` is the same question unchanged, so the client re-renders it without a new question id.
2. `end` when the session must stop: the current slot is complete and no further slot exists in the plan, remaining time is exhausted, or the candidate explicitly ends.
3. `follow_up` when the current slot is not complete, its `follow_up_allowance` remains, and the signal is `incomplete` or `off_topic`.
4. `next_slot` when the current slot is complete and a further slot exists.

A slot is complete when the synchronous signal is `sufficient`, or when its `follow_up_allowance` is spent. `target evidence count` is measured in synchronous independent instances: a `new` instance with outcome `sufficient` or `incomplete` counts one, a `same` instance and an `off_topic` turn count zero. A slot completed by allowance exhaustion with an unmet target records a coverage limitation; ending on the last slot with an unmet target also records one. Extra opportunity is expressed as more slots in the group, never by repeating one slot's intent.

Typed signals are a fixed contract recorded with every `answer` turn: `sufficient`, `incomplete`, or `off_topic`, plus an `instance` marker of `new` or `same`. Clarification is a turn kind, not a signal. `new` means the answer demonstrates something not already demonstrated for that competency; `same` means it restates an existing demonstration. The marker is the single independence rule shared by the synchronous path, the confidence rule, and the async ledger, so a same-demonstration follow-up never adds an instance anywhere.

The analyzer port proposes the signal and marker; the application validates them before they can change state, as ADR 0049 requires. Validation is structural and deterministic: an out-of-enum value, a missing field, a marker of `new` when the answer restates the immediately preceding answer turn's competency outcome for the same question, or an `off_topic` signal carrying a `new` marker is coerced to `incomplete`/`same`. Clarification turns are excluded from the comparison, so a substantive answer after a clarification is still `new` when it demonstrates a new instance. The model therefore proposes, but only a validated, schema-conforming signal can move coverage, choose the next action, or affect confidence.

`off_topic` is treated as `incomplete` for flow: it may trigger a practice follow-up, and on the last formal slot with no allowance remaining it yields `end` with a coverage limitation. It never records an instance. An answer that only restates an existing demonstration records a `same` instance, which also never increases the count and never enters level assignment.

Evidence counting for `end` and for confidence uses only the synchronous signal and instance marker, never the async ledger, so both are decidable inside the turn path. The synchronous count is the single writer of the coverage ledger. A contradiction means the synchronous analyzer flags the answer as factually inconsistent with an earlier instance for the same competency; a `sufficient`/`incomplete` pair is mixed strength, not a contradiction. When the analyzer flags one, the turn records a `contradiction` flag on that competency. The async evidence ledger enriches excerpts and strength, but an async-only conflict never changes a band: it is reported as counter-evidence inside a band the synchronous record already justified, and when the synchronous record has no contradiction the band stands, with the counter-evidence shown so the reader sees both. This keeps a band from depending on async timing while never hiding contradictory evidence.

A `code` answer's accepted submission records a `sufficient`/`new` signal when the candidate's final visible run passed, and `incomplete`/`same` otherwise; hidden results are never available synchronously and never influence the next action. A formal final submission records `sufficient`/`new` when the candidate had a passing visible run for that slot and `incomplete`/`same` otherwise, because the trusted evaluator's hidden result is asynchronous; the slot still completes on the accepted submission, and the report's hidden-test status is filled in later.

A `sufficient` answer always completes the slot regardless of the declared `target evidence count`. A `sufficient`+`same` answer completes the slot but records no new instance, so the competency's count is unchanged; the report records a coverage limitation because the demonstration was not independent.

- `StartSession` — candidate, mode, type, target role/JD, resume/profile snapshot, consent snapshot including the separate formal-audio opt-in, client request id, device id. Returns either a session view with the first question, or `202 question_pending` with the session view and no question. A candidate with an existing `planned`, `in_progress`, or `paused` session of the same type and mode gets `409 session_exists` with that session view; the view's fencing token is null when a different device holds the lease, and is the caller's own current token when the same device is retrying with a new request id, so the caller can always tell which case it is.
- `SubmitTurn` — session id, idempotency key, expected session version, device id, fencing token, turn kind (`answer|clarification_request`), answer payload (`text`, `transcript` with source/final, or `code` reference). Returns the accepted turn summary, the new session version, next action, next question, remaining time, hint availability, integrity state, and — when `next_action` is `end` — the session status with the report id and `evaluating` outcome. A `code` answer is valid only in practice; formal coding answers arrive exclusively through `SubmitFinalCode`.
- `ResumeSession` — owner-scoped lease takeover and recovery. Requires ownership and device id; does not require `expected_version`, because the caller may have crashed. Acquires or replaces the lease, returns the session view with a fresh fencing token, and recovers a missing outstanding question. Lease takeover alone bumps no `version`; it appends `SessionLeaseTakenOver` with an `event_sequence` but no state change. Unpausing a `paused` session is a separate transition and requires a `command_id`; `ResumeSession` on a `paused` session without a `command_id` is rejected with `409 command_id_required` rather than silently leaving the session paused or unpausing outside the idempotent path. With a `command_id` it unpauses, bumps `version`, appends `SessionResumed`, and is idempotent by `(session_id, command_id)`. The compatibility `/resume` supplies a derived `command_id`, so a legacy paused resume unpauses once.
- `PauseSession` — explicit pause with reason category, device identity, expected version, and command id. Retries return the resulting state rather than applying twice, enforced by a unique `(session_id, command_id)` index. A session in `question_pending` has no outstanding question, so a pause is rejected with `409 question_pending` and the client polls or resumes instead. Formal sessions allow exactly one pause; a second pause is rejected with `409 pause_limit_reached`. Practice pauses are unlimited.
- `TransferTurnPrincipal` — formal only; releases the voice-media delegation and issues a fresh fencing token to the candidate for text fallback, or the reverse. It bumps `version` because it is a state change, and the result carries the new version so the client can form the next `expected_version`. It is the one token write that bumps `version`, because it also changes who may submit; a plain lease takeover is the only token write that does not. Exactly one transfer is applied: both invocation paths resolve to the same `command_id`, derived from the session and the voice-failure record, so a duplicate from the other actor is idempotent and does not rotate the token again. The caller authenticates with whichever credential the delegation currently grants — the voice-media delegated token, or the candidate's fallback grant — never with a bare fencing token.
- `SignalVoiceFailure` — internal voice-media use case: records a typed STT/TTS failure on the session, emits `VoiceFallbackSignalled`, and returns the candidate's short-lived fallback grant plus the current session view. The voice-media deployment relays that grant to the browser over its already-authenticated channel, and the browser presents it to `TransferTurnPrincipal`.
- `EndSession` — explicit completion, explicit abandon, or timeout, discriminated by a `reason` field (`candidate_completed|candidate_abandoned|deadline`); idempotent by `(session_id, end_command_id)`. Returns immediately with the session status and, when the session is `completed`, its report outcome (`evaluating|ready|suppressed|failed`) plus the report id. A report record is created at completion for every outcome, and the same transaction enqueues `EvaluationRequested` and `ReportRequested`, so a report never sits at `evaluating` without queued work. `ready`, `suppressed`, and `failed` are all terminal for the report; `failed` additionally carries `retryable: true` and is re-driven by the report-retry worker, which reuses the same report id and may only move it to `ready`. A `suppressed` read returns the terminal outcome and no body. A formal deadline timeout completes the session with a time/coverage limitation and still produces a report. It does not wait for scoring or report assembly.
- `GetSession` / `GetReport` — owner-scoped reads. `GetReport` returns the outcome and body for `ready`, the outcome alone for `evaluating`, `suppressed`, and `failed`.
- `GetConsentSnapshot` — owner-scoped read of the candidate's stored consent purposes, used by the compatibility adapter and the consent gate.
- `EnsureQuestion` — internal idempotent recovery use case used by start retries, resume, and the outbox handler to finalize a `question_pending` session; not exposed as a route.
- `GetFinalCodeResult` — owner-scoped poll for a formal final-code submission; reads the aggregate stored on the `interview_engine_submissions` record.
- `RequestHint` — practice only; session id, outstanding question id, expected version, hint idempotency key. Returns hint content, hints used, remaining budget, the new session version, and no score penalty. Hint use is session state, so it increments `version` like any other state change. A session in `question_pending` has no outstanding question, so a hint request is rejected with `409 question_pending`. Generation is bounded; on timeout or failure the engine returns the slot's pre-authored hint text, so a hint request always yields a deterministic result. A retry with the same key returns the original hint without consuming budget. A request naming a question id that is no longer outstanding is rejected with `409 question_superseded`; on the compatibility path the adapter derives the key from the current outstanding question, so a legacy retry after the question advanced is a new hint request, not a rejected one. Formal requests are rejected.
- `RunCode` — session, outstanding question id, language, source, visible-test request, idempotency key. Always returns a run id immediately. Practice and formal visible runs only. Runs are attempts against the outstanding coding question and are stored as their own `CodeRun` records, not as turns; they do not create or consume a turn, so the candidate can iterate before answering. A retried key returns the original run; a new key may create a new visible run.
- `GetCodeRunResult` — owner-scoped poll for a visible code run by run id; returns status and visible-test output only.
- `SubmitFinalCode` — formal submission; session id, outstanding question id, client-supplied `submission_id`, expected version, language, source. The submission is itself the `code` answer turn: the engine creates the turn, the accepted submission, and a `TurnCommandRecord` keyed by `(session_id, "final_code:" + submission_id)` in one transaction, so no separate `SubmitTurn` is needed. It then runs the same next-action rule as `SubmitTurn` and returns the accepted turn summary, the new session version, next action, next question or `question_pending`, and the submission's `submission_id` with status `pending|completed|failed`, matching the vocabulary `GetFinalCodeResult` returns. When the next action is not `end`, the next question is persisted by the same outbox `QuestionGenerationRequested` path and finalizes that `TurnCommandRecord` exactly as in `SubmitTurn`, so a crash after acceptance recovers identically. It emits `TurnAnalysisRequested`, `CodeSubmissionRequested`, and, when the next action requires one, `QuestionGenerationRequested`. Visible `RunCode` attempts do not count as a submission. Each formal coding slot accepts exactly one final submission, enforced by a unique index on `(session_id, slot_id)`. The trusted evaluator processes it asynchronously; `GetFinalCodeResult` polls for the aggregate result (`passed`, `total`, `status`) and never returns per-hidden-case inputs or outputs. A retry with the same `submission_id` returns the same recorded result and never re-executes hidden tests, so hidden tests execute exactly once per accepted slot submission and are never iterable. A second distinct submission for the same slot is rejected.
- `AnnotateReport` / `DisputeScore` — owner-scoped. An annotation adds a note to the report; a score dispute targets one competency and creates an unresolved flag. Neither changes the score. Both carry an idempotency key so a retry does not duplicate the annotation or dispute.
- `InspectMemory` / `CorrectMemory` / `DeleteMemory` / `DisableMemory` — owner-scoped. Inspect returns provenance, validity, and consent-purpose metadata; mutations return the item's new status and any derived invalidation result. Mutations carry an idempotency key and expected version; retries return the resulting state.
- `CreateReportShare` / `RenewReportShare` / `RevokeReportShare` — owner-scoped, expiring share management. Formal reports only in the first tier. Creation and renewal use a client request id and return the raw share link once; only a hash is stored. Renewal rotates the token; a retry with the same request id returns the previously issued link instead of rotating again. Revoke invalidates immediately. Renew and revoke are idempotent by request id and share id respectively. `GetReportShareAccessLog` returns the candidate-visible access log.
- `ViewSharedReport` — anonymous viewer command; redeems a valid, unexpired token, logs access time and IP/user agent, and returns the consumer-visible projection. That projection includes the rubric, competency scores, evidence excerpts, narrative, limitations, integrity metadata, and candidate annotations/disputes; it excludes owner-only fields, share administration, raw transcript, audio, rankings, and role-fit verdicts.
- `GetAudioAccessLog` / `CreateAudioAccessUrl` — owner-scoped; returns the candidate-visible audio access log and a short-lived signed playback/download URL. Formal audio only. Audio consent is a separate opt-in recorded with the session; withdrawing it stops new access and schedules deletion under ADR 0035.

### 5.2 Events

At minimum:

- `SessionCreated`, `SessionStarted`, `QuestionGenerationRequested`, `QuestionAsked`, `TurnSubmitted`, `ClarificationReplied`, `SessionPaused`, `SessionResumed`, `TurnPrincipalTransferred`, `VoiceFallbackSignalled`, `SessionCompleted`, `SessionExpired`, `SessionAbandoned`, `SessionLeaseTakenOver`;
- `HintRequested`, `HintProvided`;
- `TurnAnalysisRequested`, `TurnAnalyzed`, `TurnAnalysisFailed`;
- `EvaluationRequested`, `EvaluationCompleted`, `EvaluationFailed`;
- `ReportRequested`, `ReportCompleted`, `ReportFailed`;
- `ReportAnnotated`, `ScoreDisputed`, `ReportShareCreated`, `ReportShareRenewed`, `ReportShareRevoked`;
- `MemoryUpdateRequested`, `MemoryUpdated`, `MemoryInvalidated`, `MemoryCorrected`, `MemoryDeleted`, `MemoryDisabled`;
- `CodeRunRequested`, `CodeRunCompleted`, `CodeRunFailed`;
- `CodeSubmissionRequested`, `CodeSubmissionCompleted`, `CodeSubmissionFailed`;
- `RetentionActionRequested`.

Events carry event id, aggregate id, aggregate version, `event_sequence`, type, timestamp, causation/correlation ids, and a versioned payload. `event_sequence` is the per-session monotonic counter; `aggregate version` is the optimistic-concurrency version at the time of the write, and it is unchanged for a lease-takeover event. Consumers are idempotent by event id.

## 6. Runtime flows

### 6.1 Start

1. Authenticate and record the consent snapshot using the four accepted purposes plus the separate formal-audio opt-in. Practice can start without any purpose; purpose 1 gates memory retrieval/update, purpose 2 gates learning recommendations, and purpose 4 gates analytics/model improvement. Formal requires purpose 3 (formal report creation and sharing); purposes 1 and 2 are not used, and purpose 4 remains optional. Sharing is an explicit owner action under purpose 3, not a separate consent purpose. Practice reports are created without purpose 3 because they are owner-visible only and never shared; withdrawing purpose 3 therefore only affects formal sessions. Formal audio is a separate opt-in that does not affect eligibility. Withdrawal is honored per purpose and is recorded. If purpose 3 is withdrawn before a formal session completes, the completion transaction records the report as `suppressed`: it creates the report record with that terminal outcome, enqueues no `EvaluationRequested` or `ReportRequested`, `/feedback` returns that outcome, and the candidate is informed.
2. Snapshot role/JD and candidate-provided context. Practice may also use a consent-filtered projection of prior performance, demonstrated skills/gaps, prior feedback themes, unresolved gaps, learning history, stated preferences, and career objectives; formal assessment uses only the target role, rubric, and context the candidate explicitly provides.
3. Build the deterministic blueprint.
4. Generate the session id and a fresh fencing token, then acquire the Redis device lease with that token. Mongo remains authoritative; the lease is a short-lived guard. No Mongo write happens before the session exists.
5. Persist session with the embedded blueprint, the fencing token, `question_pending: true`, a `SessionCreated` event, a `QuestionGenerationRequested` outbox record, and `client_request_id` in one Mongo transaction. The token and the session are written together, so there is never a token without a session or a session without a token. `client_request_id` is unique per candidate so a retried start returns the existing session rather than creating a duplicate. The session is `planned` at this point, so the outbox handler always finds a token when it claims the request.
6. Generate the first question within a bounded timeout, outside any transaction.
7. Validate the proposal against the blueprint; otherwise use the slot's pre-authored fallback question.
8. Persist the outstanding question, transition to `in_progress`, append `SessionStarted` and `QuestionAsked`, and return the session view with the fencing token.

For formal voice, the session holds exactly one valid fencing token at a time. Start issues a voice-media delegated token bound to the session and that token, and marks the candidate's device credential as non-submitting for transcripts; the candidate's credential is not itself a fencing token, so there is still exactly one live token. `TransferTurnPrincipal` is invoked by the voice-media deployment with its delegated token, or by the candidate with the fallback grant the engine issued on the voice failure; either path rotates the fencing token once and invalidates the voice delegation.

The session becomes `in_progress` only after the first outstanding question is persisted. Until then it remains `planned` and may transition to `completed`, `expired`, or `abandoned`; `completed` covers a candidate or deadline end during recovery, so a crashed start is always endable.

The API never returns a started session without a valid outstanding question. A crash between steps 5 and 8 leaves a `planned` session with `question_pending: true`, not an orphan that blocks the candidate. A start retry with the same `client_request_id` runs the idempotent `EnsureQuestion` recovery; if another process holds generation, it waits within the request budget and returns `202 question_pending` with the session view and fencing token, not a started session.

### 6.2 Submit turn

1. Authenticate the principal. Candidate requests must verify ownership and present the current fencing token. Formal transcript turns are submitted by the authenticated voice-media service principal, which is bound to the session and fencing token by a short-lived delegated token; the service cannot submit for any other session.
2. Look up the idempotency key first. If the `TurnCommandRecord` is complete, return its stored result regardless of the submitted version. If it is pending, return `202` with `question_pending`.
3. Check status, deadline, pause state, `expected_version`, and the `question_pending` substate. A session that is already `question_pending` rejects a new idempotency key with `409 question_pending` and the session view, so only the original request or its retry can complete the turn. Two concurrent requests with the same key resolve by the unique index: the loser re-reads and returns the winner's stored result or `202`.
4. Validate that the answer maps to the outstanding question. A clarification request (`kind: clarification_request`) maps to the outstanding question without consuming it; an `answer` consumes it.
5. If the turn kind is `clarification_request`, the flow runs outside any transaction: generate the clarification reply first with a bounded timeout, falling back to the blueprint slot's pre-authored `clarification_text`. Then, in one short transaction, append the turn with the reply, write the `TurnCommandRecord`, increment version, append `TurnSubmitted` and `ClarificationReplied`, and complete the record with next action `await_answer`. It sets no `question_pending`, consumes no coverage, produces no evidence, and enqueues no `QuestionGenerationRequested`; the same question stays outstanding for the substantive answer.
6. Otherwise, produce the typed turn signals for a text/transcript answer by running the bounded synchronous analyzer outside the transaction; a practice `code` answer instead takes its signal from the visible-run result as described in §4.5, with no analyzer call. The analyzer always yields a signal: on timeout or provider failure it returns `incomplete`/`same` with a `mode/technical limitation` note, so the turn is always accepted and the next action is always decidable; the answer is never rejected or lost. Then, in one short transaction: append the turn, persist the signals and the deterministic next action, set `question_pending` unless the action is `end`, update coverage/hint/integrity state, increment version, append events, enqueue `TurnAnalysisRequested`, and enqueue `QuestionGenerationRequested` only when the action is `follow_up` or `next_slot`. The transaction writes the `TurnCommandRecord` exactly once: `complete` with the terminal result when the action is `end`, otherwise `pending`. No model call happens inside a transaction.
**The end path completes in one transaction.** For a turn whose action is `end`, step 6's transaction contains the whole terminal write: it appends the turn, enqueues `TurnAnalysisRequested`, transitions the session to `completed` with reason `candidate_completed`, creates the report record — outcome `suppressed` with no `EvaluationRequested` or `ReportRequested` if purpose 3 was withdrawn before completion, otherwise outcome `evaluating` with both enqueued — emits `SessionCompleted` (carrying the reason), and writes the `TurnCommandRecord` once in `complete` state with the terminal result. Suppression is decided at completion from the consent state then current, never during evaluation. There is no second completion transaction, so a crash cannot leave a completed session with an incomplete command record. For every other action, step 6 commits the turn and inserts the record `pending`, and step 8's second transaction finalizes it with the next question. No transaction contains a model call.

7. The next action is decided deterministically from the persisted typed signals and blueprint allowances: `await_answer` (clarification only), `follow_up`, `next_slot`, or `end`. The model does not choose the action.
8. If the action is `end`, the step-6 transaction already completed the session; no next question is generated and the stored result is the terminal one. Otherwise generate and validate the next question. In a second transaction, persist it as the outstanding question, clear `question_pending`, increment version, append `QuestionAsked`, and complete the `TurnCommandRecord` with the result that includes the next question and the new version. Deep evidence extraction remains asynchronous, but the synchronous signal is typed and bounded.

A repeated idempotency key returns the stored result once complete; while pending, the canonical contract returns `202`. A stale `expected_version` returns `409` only when no completed idempotency record exists. A paused or expired session rejects the turn with a typed conflict. If question generation exceeds its budget, the accepted turn is preserved, the fallback question is persisted, and the stored result is complete.

**Question-generation idempotency:** every generator path uses the key `(session_id, session_version_at_request, purpose)`, where `purpose` is one of `first_question`, `next_question`, or `recovery`. `session_version_at_request` is the session version *before* the transaction that requests generation; session creation persists at version 0 and its first state-changing write raises it to 1, so `first_question` uses `0` and every later request uses the version the turn transaction started from. A resume that recovers a missing question uses the same key as the outbox replay of the same request, because both derive it from the persisted request record rather than from their own call site; `recovery` is used only when no request record exists. The in-request generator and the outbox payload record exactly those components, and a unique index on `(session_id, question_generation_key)` enforces a single winner: later writers observe the persisted question and return it instead of generating a second one.

**Pending-question recovery:** a `question_pending` session or `TurnCommandRecord` is completed by whichever path runs first: a start/turn retry, a resume call, or the outbox `QuestionGenerationRequested` handler. Completion is idempotent by session version and question-generation key; the fallback question guarantees a terminal result. A request that exhausts its retries is dead-lettered, and the dead-letter write performs the same status-guarded transaction: it persists the fallback question as the outstanding question, clears `question_pending`, transitions a `planned` session to `in_progress`, and completes the `TurnCommandRecord` with a typed `generation_failed` result carrying the fallback question. A polling client therefore always converges on a real question rather than a permanent `202` or a stuck `question_pending`.

**End races question generation.** Any write that finalizes a `question_pending` record must re-read the session status inside its transaction and abandon the write if the session is `completed`, `abandoned`, or `expired`. A session that is `planned` or `in_progress` may be finalized, which is what lets the start path persist the first question and lets a turn persist the next one. A `QuestionGenerationRequested` handler that observes a terminal status discards the generated question and completes the `TurnCommandRecord` with the terminal session result. `EndSession` on a `question_pending` session completes normally, sets the report outcome, and completes any `pending` turn command with that terminal result, so a polling client always converges. A deadline completion does the same.

**Recovery preserves the outstanding intent.** The `QuestionGenerationRequested` record persists the slot id, whether the request was a follow-up or a new slot, and the generating key, so recovery regenerates exactly that intent rather than re-deriving it. Recovery never repeats a question intent already asked; if the persisted intent was already asked, recovery advances to the next unasked intent.

### 6.3 Resume and concurrency

Redis holds a short-lived device lease using atomic set-if-absent with expiry. Mongo remains authoritative. Resume validates ownership, acquires or replaces the lease with a fencing token, reloads the snapshot, and returns the outstanding question.

Principal handoff is a canonical command, not a side effect: `TransferTurnPrincipal` (formal only) releases the voice-media delegation and issues a fresh fencing token to the candidate for text fallback, or reverses it. The caller authenticates with the credential its delegation currently grants — the voice-media delegated token or the candidate's fallback grant — not with a bare fencing token. It records a `TurnPrincipalTransferred` event and is idempotent by command id. Only one principal holds a valid fencing token at a time.

- Practice sessions have no assessment deadline and never transition to `expired` while `in_progress`; they can only be completed or abandoned. An unstarted practice session expires on the idle window. This is what makes practice durably resumable.
- Formal resume preserves the deadline. A disconnect does not stop the clock; formal assessments allow exactly one explicit, bounded, logged pause. Pause duration and deadline-extension rules remain policy values. Practice may pause freely; practice pauses are counted in integrity metadata but have no deadline effect.
- A stale device cannot submit because repository updates check the fencing token and session version.
- Clarification requests are recorded as turns that do not advance coverage or create evidence; the original question stays outstanding, so the substantive answer is submitted later against the same question. Thinking time is not penalized.
- A started session with no outstanding question is recoverable: resume regenerates the persisted request's intent from the `QuestionGenerationRequested` record, using its recorded question-generation key, rather than re-deriving an intent. `question_pending` is a transient, persisted substate, not a broken session.

### 6.4 Async evaluation

Turn acceptance for an `answer` emits `TurnAnalysisRequested`; a `clarification_request` emits none, because it produces no evidence. A worker extracts evidence per turn and appends it to the ledger asynchronously.

Evidence writes are append-only to a separate evidence collection and never bump the session `version`; they carry the session id and turn id instead. The session snapshot stores the synchronous instance count and coverage state, which are `version`-guarded like any other state change; async extraction adds evidence items to the evidence collection and may add excerpts and strength but never changes the snapshot's instance count, coverage, or confidence band. So async work is not a session state change and never invalidates an in-flight `expected_version`, while every snapshot change is versioned. Session completion emits `EvaluationRequested`. End-of-session scoring waits until every per-turn analysis is terminal, and report assembly waits for a terminal evaluation: the `ReportRequested` handler checks the evaluation record and, when it is not terminal, reschedules itself without consuming an attempt or moving toward dead-letter, because waiting on a dependency is not a failure. Only a genuine assembly error counts against the attempt budget. A permanently failed turn analysis becomes a visible limitation and the report still proceeds. A competency whose only excerpts would have come from a failed analysis falls back to the verbatim turn text the candidate submitted, capped and redacted like any other excerpt, so the excerpt requirement is never violated and no evidence is invented.

The evaluator port does not assign levels. Levels come from the deterministic instance mapping in §4.5, which is pure domain code; the evaluator port only supplies qualitative reasons and rubric-descriptor-grounded wording for a level the domain already fixed, and the application discards any level the port proposes that disagrees with the domain's mapping.

Formal coding report generation additionally waits for every accepted slot submission's trusted-evaluator result, or for a terminal no-submission state. A session that ends with an outstanding final submission stays `evaluating` until that submission reaches `completed` or `failed`; the report's per-slot hidden-test statuses are recorded as `passed`, `failed`, `pending`, or `not_submitted`, and the report-level hidden-test field summarizes them as `all_passed`, `some_failed`, `pending`, or `not_submitted`. A pending submission never publishes stale metadata.

The `SubmitFinalCode` rule is scoped per coding slot, not per session: each formal coding slot accepts exactly one final submission, enforced by a unique index on `(session_id, slot_id)`. A coding blueprint declares which of its slots are coding slots — in the first-tier DSA/coding type, two of the ten — so a formal coding session with two coding slots has two accepted submissions, one per slot. The aggregate hidden-test result in the report is per competency from the union of accepted slot submissions.

The candidate-code handoff to the trusted evaluator is explicit: the evaluator receives only the accepted submission record (language, source, task id) and its own hidden-test fixtures. It never receives session transcripts, memory, or sandbox credentials, and the sandbox never receives hidden tests or evaluator results beyond the aggregate.

Report generation runs asynchronously and targets readiness within two minutes. Evaluation and report generation are never part of the conversational latency path. A permanent failure in scoring or report assembly is different: it fails the report as a whole with a retryable status, never a silent partial report.

### 6.5 Outbox

Domain state and outbox records commit together. Workers claim with an atomic lease and bounded attempts. Failures back off and eventually move to a dead-letter state with an operator-visible reason. Redis may wake workers but never owns delivery state. A worker does not publish before claiming.

### 6.6 Memory updates

After a session completes and its report outcome becomes terminal, the engine emits `MemoryUpdateRequested` when purpose 1 is granted. The terminal report handler emits it once per report id, keyed idempotently by `(report_id, memory_update)` so a `failed → ready` retry cannot emit it twice; it is never emitted from the completion transaction, because the outcome is not terminal there. Practice sessions are the only source, because formal sessions never hold purpose 1. It does not depend on report success: a `failed` report still allows memory projection from the session's own evidence, and a memory failure never blocks or retries the report. A worker projects evidence into memory items, and the deterministic gate writes only validated, provenance-labelled items; the model proposes, the gate decides. Withdrawn purposes, corrected items, and deleted items invalidate derived entries immediately.

Practice retrieval may read memory; formal sessions never do, and formal sessions write no memory items because purpose 1 is never granted to them. Current session state is never written to long-term memory.

### 6.7 Failure policy

| Condition | Behavior |
|---|---|
| Validation, authentication, ownership failure | Typed 4xx; no state change |
| Stale version, deadline, pause, lease conflict | `409`/`410` with recovery instructions |
| STT/TTS failure | Explicit text fallback, recorded in integrity metadata |
| Code execution failure | Run marked failed; limitation recorded; session continues where allowed |
| Provider timeout | Bounded retry, then deterministic fallback or visible degraded result; the synchronous analyzer degrades to `incomplete`/`same` with a limitation rather than failing the turn |
| Insufficient evidence | `not_assessed`, never zero or invented evidence |
| Permanent turn-analysis failure | Visible limitation; report proceeds |
| Permanent scoring/report-assembly failure | Report failed with retryable operator action; no silent partial report |

## 7. Adapters and operations

### 7.1 Voice

Practice and formal use different voice paths.

- **Practice:** browser speech is the primary path (`SpeechRecognition`/`speechSynthesis`), with automatic endpointing and barge-in where supported. The engine receives the final text transcript through `SubmitTurn`. If browser voice fails, the UI visibly switches to text and records the mode change.
- **Formal:** a dedicated voice-media deployment terminates WebSocket audio streams and drives STT/TTS ports. The server transcript is authoritative. Turn-taking is controlled with explicit cues and no barge-in. If voice fails, the session continues in text with a clear notice and records the mode change. In text fallback the candidate submits typed answers directly as the owner; the engine releases the voice-media delegation and issues the candidate a fresh fencing token, so exactly one principal can write at a time.
- **Contract:** transcribed answers use the `transcript` answer variant with `source: browser|server` and `final: true`. Partial transcripts never create turns. Browser-sourced transcripts are valid only in practice. Formal transcripts must be submitted by the authenticated voice-media service with `source: server`; a formal client cannot submit a browser transcript.
- **Audio:** practice audio is not stored by default; formal audio is opt-in, retained 30 days, and stored in private object storage with signed access. Declining recording does not make the candidate ineligible. Formal audio consent is a separate opt-in, not one of the four memory/report purposes. Playback/download is owner-scoped, candidate-visible, and access-logged; the candidate can see who accessed it and when.

### 7.2 Coding

A dedicated sandbox worker consumes `CodeRunRequested` jobs. Each run gets an ephemeral container with no network, read-only root, CPU/memory/PID/time limits, and no host mounts.

- First-tier languages: Python, JavaScript, Java; function-based tasks only.
- Practice: visible tests plus run/test controls.
- Formal: two or three visible sample tests during the session; hidden tests cover edge cases, invalid input, and scale, and run only at final submission in the trusted evaluator, a separate trusted workload from the candidate sandbox.
- Complexity is stated by the candidate with optional probes; it is not measured or claimed as an asymptotic measurement. Multi-file projects and measured complexity are deferred.
- Code, outputs, test results, runtime version, and execution evidence persist on the `CodeRun` record, and the accepted answer turn references the runs that preceded it. The `CodeRun` record is the authoritative execution-evidence record; ADR 0052's "persist with the turn" is satisfied through that reference.
- `RunCode` always returns a run id immediately. The API never waits for sandbox execution, because runs are produced by the separate sandbox deployment consuming outbox jobs; the candidate polls `GetCodeRunResult`, and the compatibility adapter polls briefly on the candidate's behalf for short runs before returning the run id.

### 7.3 Retrieval

Structured Mongo memory items are the first-tier retrieval source. Ranking filters by consent purpose, candidate, validity, and mode before scoring by competency/role match, recency, non-conflict, provenance weight, and lexical relevance.

- The token budget is enforced server-side.
- Formal sessions receive an empty practice projection.
- Withdrawn or corrected items are excluded immediately.
- Each retrieval records selected items and reasons for audit.
- A vector index may be added later behind the same port; no vector database enters the first tier.

### 7.4 Deployment and observability

- Separate deployments: API, workers, voice media, candidate sandbox, and trusted evaluator. Voice media, candidate sandbox, and the general API/worker pool each have dedicated node pools per ADR 0043 and ADR 0053; the API/worker pool hosts the trusted evaluator as a distinct deployment. Stateful data services run outside these pools per ADR 0044. The trusted evaluator holds hidden tests; the candidate sandbox never receives them. The candidate sandbox never has a host Docker socket, per ADR 0040; the sandbox runtime image and isolation technology remain a deferred decision.
- MongoDB and Redis are self-hosted on dedicated private-network VMs.
- Private S3-compatible storage holds resumes, audio, and report assets with lifecycle rules matching retention classes.
- Voice media uses a dedicated ingress; ordinary API/WebSocket traffic uses the standard ingress.
- Provider adapters are configuration-selected and independently degradable.
- Target p95 voice turn latency is 3 seconds for practice and 2 seconds for formal; the report is ready within 2 minutes. A per-session cost cap is enforced per turn/stage.
- The API process does not register background workers. The worker process registers each handler once, including deadline/expiry and retention sweeps.
- Metrics: turn latency, provider latency/errors, cost per session, outbox lag, worker retries/failures, evaluation time, report time, fallback rates.
- Logs carry session/turn correlation ids but not raw answers.

## 8. Security, privacy, and retention

- Every canonical route and use case enforces candidate ownership, except anonymous report viewing through a valid share token and formal turn submission by the authenticated voice-media service principal. Session ids are not authorization; a share token authorizes only the consumer-visible report projection, and a voice-media principal authorizes only transcript submission for its delegated session.
- Consent is checked against the four accepted purposes before personalization/memory, learning recommendations, formal report creation/sharing, or analytics/model improvement. Missing optional purposes disable only their feature.
- Formal assessment never retrieves practice memory for scoring.
- Evidence excerpts are PII-redacted and limited to two sentences.
- Hidden tests are never sent to the candidate sandbox.
- Report shares are hashed, expiring, revocable, and access-logged.
- Class-based retention applies per data class: practice audio is not stored by default, formal audio is kept 30 days, raw practice transcripts 90 days, formal transcripts/reports 1 year, practice reports 1 year, and competency summaries until deletion or 2 years.
- Deletion completes within 30 days including derived data; backups are purged within 90 days. Deletion and retention events propagate to derived caches and indexes. Derived data must not outlive its source class.
- Analytics uses de-identified data only.
- Report integrity metadata excludes device/browser, IP, per-turn timestamps, and audio hashes.
- AI disclosure and limitations are shown at session start and in the report. A text alternative, keyboard access, and screen-reader support meet WCAG 2.2 AA for core flows. English-first strings are externalized.
- Audit events record actor, event sequence, session version, timestamp, and reason without storing private model reasoning.

## 9. Migration, compatibility, and rollout

### 9.1 Compatibility

`/agent-interview/start`, `/answer`, `/hint`, `/end`, `/feedback`, and `/extract-text` remain available through the compatibility adapter, and `/agent-interview/resume` is added as a net-new route because the legacy app has none. The adapter translates request/response shapes and contains no interview rules. It performs mechanical precondition synthesis only:

- `client_request_id` is a per-attempt idempotency key, not a deterministic fingerprint. The UI generates it once when the candidate starts a session and resends it on retry and on every `202` poll; the adapter generates one when the legacy shape carries none and returns it as `request_id`. It is unique per candidate, so retrying a start never creates a duplicate, while starting a genuinely new session uses a new id. The duplicate-active-session guard is a canonical rule, so it holds on both entry points.
- `idempotency_key` for `/answer` is derived from the authenticated candidate, session id, the turn's `request_id` echoed by the UI, and a hash of the answer body. The UI generates `request_id` once per answer attempt and resends it on retry, so a lost response retries to the same key even after the outstanding question advanced. When the legacy body carries no `request_id`, the adapter generates one and returns it as `turn_request_id`; without that echo a retry is a new turn, which is documented and tested as the legacy limitation.
- The consent snapshot comes from the candidate's stored consent record, which the adapter reads through a canonical `GetConsentSnapshot` use case; the legacy request body never carries consent. A candidate without the required purposes for the requested mode gets a typed `409 consent_required` rather than an implicit grant. Practice needs no purpose to start.
- Session resume on the compatibility surface has two paths. A retry with the same `request_id` returns the existing session, which covers same-device recovery. A second device has no `request_id`, so it calls `/agent-interview/resume` with the session id, which is a lease takeover and returns a fresh fencing token. `/resume` is a net-new compatibility route added by this work, not a preserved legacy route: the legacy app has no resume endpoint. Its body is `{session_id, device_id, command_id?}` and its response is the same session view shape as `/start` plus `question`, `status`, and `fencing_token`. The first-slice UI uses it for cross-device resume; `/start` with a reused `request_id` is only same-device retry.
- `/extract-text` stays a legacy helper outside the engine boundary: it parses resume files and is not an interview use case. The adapter routes it to the existing resume parser, and the canonical engine neither owns nor calls it.
- The first-slice UI adds handling for `409 session_exists` (offer resume), `409 question_pending` on a new answer key (retry the original request), and `202 question_pending` (show a short preparing state and poll). `409 consent_required` only occurs in formal mode, so it is handled by the formal-slice UI, not the first slice. `MockInterview.jsx` currently treats start errors as generic failures, so this is part of the minimal UI update.
- Response mapping is explicit: `next_question` carries the canonical question text and id, `questions_answered` counts accepted `answer` turns (clarifications excluded), `status` mirrors the session status, `report_id` and `report_status` are present whenever the session is `completed`, and `evaluation.feedback` is populated from the canonical report's narrative and limitations once `ready` and is empty while `evaluating`. The adapter never composes candidate-facing prose itself.
- The adapter holds no long-lived lease state and never reads a live token to bypass the lease. Before any mutating legacy call it performs an idempotent acquire-or-confirm of the lease for the requesting device: if that device already holds it the call proceeds, and if another device holds it the call returns `409 device_conflict` and the UI must call `/resume`. Device identity is the authenticated candidate plus a `device_id` the client generates once and persists in local storage per browser profile, and the first-slice UI sends it on every call. A legacy body that omits it is rejected with `400 device_id_required` rather than deriving one, because no server-side value can distinguish two devices with the same browser reliably.
- `SubmitTurn`, `RequestHint`, `PauseSession`, and `EndSession` validate that the calling device holds the lease in addition to the fencing-token and version checks, so a device that lost the lease is rejected even though the adapter presents a valid current token. `/resume` is the only path that takes the lease from another device.
- `expected_version` is resolved by the adapter from the session snapshot on each call, because a legacy body never carries one, so the version check is lease-enforced on the legacy path while the canonical path keeps full optimistic concurrency.
- A canonical `202 question_pending` is returned as HTTP `202` with the session view and `question_pending: true`; the UI polls the same endpoint until a question is available. The first-slice UI shows a short "preparing your next question" state for this case.
- `/end` has no command id or reason in the legacy body. The adapter generates `end_command_id` from the authenticated candidate, session id, and a body-supplied `end_request_id` when present, otherwise from a request fingerprint, and always maps the reason to `candidate_completed`. A repeated end is idempotent; a different id on an already-completed session returns the existing terminal result.
- `/hint` has no idempotency key or device id. The adapter derives `hint_idempotency_key` from the authenticated candidate, session id, and the outstanding question id, so a retried hint for the same question returns the original hint, and supplies the device id and current fencing token exactly as `/answer` does.
- `/start` legacy response fields are `session_id`, `question` (the canonical question text), `interviewer_message` (the same text), `status`, and `request_id` echoing the client request id; `/end` returns `session_id`, `status`, `report_id`, and `report_status`, and `/answer` returns those two report fields as well when the turn ends the session. These are the fields the existing UI reads, and the adapter fills them from the canonical view without composing prose.
- `/resume` is net-new and has no legacy counterpart. Its body is `{session_id, device_id, command_id?}` and its response is a session view with `question`, `status`, and `fencing_token` populated; the adapter derives the device id from the body and returns the session view. On an `in_progress` session it is a pure lease takeover; on a `paused` session it supplies a derived `command_id` so the session unpauses exactly once.
- `/agent-interview/end` maps to `candidate_completed`, because the legacy UI calls it when the candidate finishes answering. It therefore creates a report. `candidate_abandoned` is only reachable through the canonical route, and `/feedback` on an abandoned session returns the session status with no report id and a typed `409 no_report`; the legacy UI never calls `/feedback` for that case.
- The start path checks `(candidate_id, client_request_id)` before the duplicate-active-session guard, so a retried start always returns the original session rather than `409 session_exists`. `409 session_exists` is returned only for a new request id against an already-active session of the same type and mode.

These are translation rules, not interview rules; coverage, scoring, and lifecycle decisions stay in the engine. Demo routes are legacy surfaces and are not part of the canonical engine.

The compatibility adapter preserves endpoint names and request shapes, not legacy scoring semantics:

- `evaluation.score` is removed or null; no live score is shown.
- `final_score` is removed or null; no overall score is produced.
- Hint responses no longer carry a score penalty; hint use is reflected in confidence and limitations. Formal hint requests are rejected.
- `/feedback` maps to the canonical report/competency summary and never returns an overall rating; it returns `evaluating` until the report is ready, `suppressed` if purpose 3 was withdrawn, or `failed` with a retryable status.
- The first-slice UI is updated minimally to render competency evidence and the end-of-session report instead of live scores.

### 9.2 Data migration

New sessions write only to canonical collections. Existing interview data is not migrated, rewritten, or dual-written. Legacy routes may continue to read it until retention expiry. The canonical engine does not require legacy transcripts to operate.

### 9.3 Rollout

The engine is introduced behind a per-type/per-mode feature flag, starting with authenticated text practice. Internal sessions run first with full telemetry. Rollback is a flag flip. A failed canonical turn is never automatically retried against the legacy engine.

After parity, legacy engines and unused routes are retired. `/sessions/*` and `/interview-flow/*` are not extended during the transition.

## 10. Testing and acceptance

### 10.1 Test layers

- **Domain** — lifecycle, deadlines, pause rules, one-outstanding-question, duplicate turns, clarification turns, hint limits, coverage, independence, `not_assessed`, next-action rule, formal/practice isolation.
- **Application** — Mongo transaction plus outbox atomicity, optimistic concurrency, idempotency, lease/resume conflicts, crash recovery, and unique indexes for turn idempotency and event identity.
- **Adapters** — contract tests with fakes plus integration tests against ephemeral Mongo/Redis. Mongo tests use a replica set when transactions are exercised.
- **Compatibility** — recorded request/response shapes from `MockInterview.jsx` and `VoiceInterview.jsx`.
- **Async** — duplicate delivery, retry/backoff, dead-letter behavior, evaluation idempotency, report readiness, and `question_pending` recovery.
- **Security** — ownership/IDOR, hidden-test exposure, practice-memory leakage into formal scoring, redaction.
- **End-to-end** — authenticated practice text session from start through turns and report; formal coding slice with visible/hidden test separation.

### 10.2 First vertical slice

A single authenticated practice behavioral text session:

1. Start creates a canonical session, blueprint, event, outbox record, and device lease with a fencing token.
2. Compatibility `/agent-interview/start` returns the first question.
3. Answers are accepted idempotently, with no duplicate question and bounded follow-up.
4. `/agent-interview/answer` returns no live score.
5. The final answer's `next_action` is `end` because it is `sufficient` and completes the last slot. `/agent-interview/answer` itself returns the session status with an allocated report id and `evaluating`. The slice scripts a `sufficient`/`new` final answer, so the slot completes on the signal; an `incomplete` final answer takes the practice follow-up path first, which is covered by a separate test. Per-turn extraction and scoring complete asynchronously; `/agent-interview/feedback` polls that report id until the candidate-owned competency report is `ready`.
6. An explicit `/agent-interview/end` is idempotent and returns the same report id and outcome. Neither `/end` nor `/feedback` returns an overall score.
7. Session and report survive API restart; resume works from a second device after it acquires the lease and fencing token.

Voice, formal coding, and formal voice text fallback follow as separate tracer tickets on the same contracts.

The first slice includes the minimal UI work it requires: storing and resending `request_id` and `turn_request_id`, generating and persisting a per-browser `device_id`, handling `409 session_exists`, `409 device_conflict`, `409 question_pending`, and `202 question_pending`, calling `/resume` for cross-device takeover, adding a `/feedback` poll to `MockInterview.jsx` so it reads `report_id`/`report_status` and then the report body, keeping `/hint` working against `RequestHint`, and rendering competency evidence and the end-of-session report instead of live scores. Without that UI change the slice cannot pass compatibility tests against the existing frontend.

The slice is buildable with stubbed ports. The analyzer, evaluator, narrator, and question generator are injected ports, so the slice ships deterministic scripted implementations behind the same protocols while vendor selection stays deferred. The blueprint's authored slot strings are part of the slice.

### 10.3 Acceptance criteria

- Domain invariants are covered by tests that fail before implementation.
- Session snapshot and outbox event commit atomically on a replica set.
- Duplicate answer submission returns the original result exactly once.
- Formal sessions cannot hint or retrieve practice memory.
- Reports never contain a composite score and never show `0` for missing evidence.
- The first-slice interview flow meets WCAG 2.2 AA for keyboard access, screen-reader labels, and the AI-disclosure and limitation text, verified in the slice's UI tests.
- Compatibility tests pass for the existing frontend calls.
- Full root and backend suites pass with the existing hermetic Mongo/Redis setup extended for replica-set transactions where needed.

Subsequent tracer acceptance:
- Formal voice uses the server transcript, survives STT failure with text fallback, and records mode changes.
- Formal coding exposes only visible tests during the session; hidden tests run in the trusted evaluator at the accepted final submission and never enter the candidate sandbox.
- Retention/deletion removes derived data within the accepted windows and leaves audit evidence.
- Report shares expire, renew, revoke, and log access; practice reports cannot be shared.

## 11. Deferred decisions

These are policy values or adapter selections, not missing architecture:

- LLM, STT, TTS, object-storage, and sandbox vendor selection.
- Pause duration, deadline-extension policy, and idle-expiry values. The one-pause count is fixed by ADR 0019. The practice hint budget is three per session; requirement 33 gives three as the example value and this design adopts it as the first-tier value.
- Rubric level descriptors, which explain the fixed levels and the fixed level mapping above; their wording is open, the levels and mapping are not. Retakes and cross-session comparability remain open.
- Per-type slot intents, fallback questions, clarification text, and practice hint text for every type beyond the first-slice behavioral blueprint, plus their rubric descriptors. The first-slice behavioral blueprint's own slot content is fixed in §4.2 and the literal text ships in an appendix of the behavioral blueprint module, so it is authored content, not a design decision.
- Per-type calibration of the fixed weight profile versions.
- Retrieval token budget, staleness windows, and projection field weights.
- Cost-cap value, model-routing policy, and degradation thresholds.
- The definition and emission of the `verified` provenance value.
- Report redaction rules, limitation wording, dispute status model, and metadata display details.
- Legal holds, export format, backup-deletion verification, and jurisdiction overrides.
- Voice endpointing thresholds and assessment audit signals. Accepted owner-scoping, candidate visibility, and access logging for formal audio remain required and are not deferred.
- Coding harness details per language, runtime image, and persistence retention.
- Observability SLOs and CI/CD implementation.

Each deferred item must be decided before the ticket that depends on it; none changes the module, state, or contract boundaries above.

## 12. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Mongo replica set not provisioned | Make it an explicit deployment prerequisite and test transactions on a replica set |
| LLM latency threatens turn targets | Bounded generation, streaming, deterministic fallback questions, and async deep evaluation |
| Duplicate outbox delivery | Idempotent consumers keyed by event id; atomic claim and bounded retries |
| Legacy UI semantic drift | Compatibility contract tests plus minimal UI update in the first slice |
| Scoring inconsistency | Frozen blueprint/rubric versions, evidence independence rules, and no composite score |
| Schema evolution | Versioned contracts and events; snapshot stores schema version and last applied sequence |
| Provider outage | Ports, fallbacks, explicit degraded state, and visible limitations |
| Hidden-test leakage | Hidden tests never enter the candidate sandbox; trusted evaluator only |
