# Interview Engine — Research Synthesis (Proposals, Not Decisions)

Status: research record. Everything in this document is a **proposed technical option** unless marked as verified existing behaviour. No provider, framework, memory technology, queue or sandbox runtime is selected.

## Method

Five bounded research tracks ran in parallel: interview UX/personalization, multi-agent orchestration, voice, coding execution, and production reliability. Each received the same short product brief plus a bounded objective and a limited repository file list. Findings were checked against the code; corrections are listed below.

## Validated corrections to delegated findings

- **Authentication on agent endpoints exists.** `/agent-interview/answer`, `/hint` and `/end` use `get_current_user`; the defect is missing **session ownership/session binding**, not missing authentication (`agent_routes.py:128-215`).
- **The voice session mismatch is code-level, not runtime-measured.** Orchestrator sessions are created with `_id` and looked up by a `session_id` field (`interview_orchestrator.py:151-152` vs `voice_routes.py:142`).
- **The richer evaluator exists but is disconnected from the live loop.** `/questions/evaluate` uses `answer_evaluator`; the live multi-agent loop and orchestrator use their own generic prompts (`question_routes.py:151`, `multi_agent_system.py:594-614`, `interview_orchestrator.py:536-590`).
- **The practice→matching boost is conditional.** It runs only when `/interview-flow/complete` is called, which the current UI does not call (`interview_flow.py:167-334`, `flow_routes.py:94-112`).

## 1. Conversational design

**Verified current behaviour:** no blueprint in the live path; stage inferred from answer count; one follow-up cap; `tested_topics` not used for exclusion; previous questions not in the prompt; random fallback pools; acknowledgements are prompt instructions; no clarification intent outside DSA; client-only timers.

**Alternatives**

| Approach | Strengths | Costs |
|---|---|---|
| Blueprint + deterministic state machine | Consistency, coverage, auditability, low cost | Robotic if over-constrained; brittle to off-script answers |
| LLM planner every turn | Natural, flexible | Drift, repetition, rubric leakage, latency/cost, hard to replay |
| **Hybrid blueprint + bounded per-turn moves** | Best balance: coverage with natural phrasing; bounded retries | Needs move schema, constraint validation, stale-plan handling |
| Free-form conversational agent | Highest naturalness | Weak fairness, coverage and evaluability |

**Proposal (not accepted):** precompute a competency/topic blueprint; allow the LLM to choose only among permitted moves (`ask`, `probe`, `clarify`, `transition`, `close`); generate acknowledgements only from verified answer facts; deterministic clarification policy; explicit "take your time" control; persist a plan version with the session.

## 2. Multi-agent orchestration and context

**Verified current behaviour:** one mutable `InterviewContext` passed wholesale to every agent; no typed projections; sequential evaluate-then-interview; no parallelism; coordinator dispatch is hard-coded; Redis TTL is the session store; feedback is returned every turn even though one agent should own the conversation.

**Alternatives**

| Architecture | Strengths | Costs |
|---|---|---|
| Single conversational agent + tools | Lowest handoff loss | Bloated context; weak structured evaluation |
| Supervisor + specialists (current shape) | Clear role prompts | Shared-context leakage; coordinator drift; no isolation |
| **FSM/workflow control plane + typed projections** | Deterministic lifecycle, retries, resumability; small contexts | Projection/versioning work; less free-form |
| Blackboard + projections | Auditable shared state | Staleness and invalidation complexity |
| Event-driven pipeline | Async evaluation, voice streaming, retries | Ordering/idempotency complexity |

**Proposal (not accepted):** FSM owns lifecycle and stage transitions; a single turn-arbiter is the only agent allowed to emit candidate-facing text; specialists run after the turn with typed input/output contracts; parallel evaluation fan-out (rubric, code tests, communication) uses immutable answer snapshots; the orchestrator is deterministic, not an LLM.

**Responsibility split (proposal):** deterministic — lifecycle, timers, transitions, difficulty thresholds, scoring aggregation, question-bank retrieval, code execution, consent/provenance gates, persistence, retries; LLM — interviewer dialogue, open-ended judgment, hint wording, coaching synthesis, schema-validated extraction; hybrid — context builder, planner, memory updater (LLM proposes, deterministic gate writes), evaluator (deterministic rubric + LLM qualitative).

## 3. Voice

**Verified current behaviour:** browser-only UI; half-duplex; fixed 5.5s silence; no barge-in; server path is file-upload STT → inline logic → TTS; mock fallbacks; WebSocket stub; LiveKit token only.

**Alternatives**

| Approach | Latency/full-duplex | Control/audit | Scaling |
|---|---|---|---|
| Speech-to-speech | Lowest first-audio; native interruption | Weak for structured assessment | Provider session state |
| Chained STT→LLM→TTS | Higher but predictable; VAD endpointing | Transcript is first-class; easiest to audit | Stateless workers |
| **Real-time pipeline + async backend** | Good; framework turn detection/barge-in | Most control; evaluation off critical path | Media workers + rooms; reconnection needed |

**Proposal (not accepted):** practice may use natural barge-in and browser voice as a degraded mode; formal assessments use server-side capture, authoritative transcript, conservative turn-taking, no hints, and audited recordings. Target budget (to be measured): p50 end-of-turn→first audio ≤1.2s, p95 ≤2s; evaluation asynchronous.

## 4. Coding and execution isolation

**Verified current behaviour:** Docker CLI in the API host; six advertised languages; 5s execution cap; hidden-test masking in `/sandbox/validate`; no persistence of code/results; LLM static complexity analysis; no queue.

**Alternatives**

| Approach | Isolation | Cold start/throughput | Operational cost |
|---|---|---|---|
| Restricted containers (current) | Shared kernel; strong cgroup/namespace limits | Fast when warm; high density | Moderate; Docker socket risk |
| gVisor | User-space syscall interception; stronger than runc | Moderate | Moderate-high; RuntimeClass/node pools |
| Firecracker | KVM hardware isolation; strongest | Very fast boot; needs KVM/bare metal | High |
| Kubernetes Jobs + RuntimeClass | Depends on runtime; native quotas/deadlines | Image pull/scheduling overhead | High; fits target platform |
| External execution service | Vendor-managed | Quota-bound | Low ops; data/residency/vendor risk |

**Proposal (not accepted):** execution as a separate workload, not a Docker CLI inside the API pod; immutable answer + code snapshot; hidden tests only in assessment mode; persist execution evidence; complexity as stated reasoning plus optional scaling probes, not claimed measurement.

## 5. Production reliability and session lifecycle

**Verified current behaviour:** document sessions with embedded rounds; independent writes without transactions; no duplicate-submission or ownership checks; `GET /next-question` writes; resume creates a new question; Redis-only multi-agent state; inline evaluation under a 60s request timeout; duplicated workers; non-atomic outbox claim; no scheduler; no per-session LLM cost metrics.

**State alternatives**

| Pattern | Resume/replay | Audit | Cost |
|---|---|---|---|
| Document checkpoint | Simple, fast | Weak | Low |
| Event sourcing + projections | Strong | Strong | Dual writes, projection lag |
| Append-only transcript + derived state | Natural for interviews | Strong | Non-determinism; compaction |
| **Hybrid: append-only events + materialized checkpoint** | Strong | Strong | Moderate; recommended for evaluation |

**Evaluation alternatives:** inline sync (simple, latency-bound), fire-and-forget (lossy, current), durable queue/outbox (retryable, idempotent), event-driven (reuse outbox with atomic claim). Proposal: persist submission and evaluation job together; idempotency keyed by `(session, question, answer_revision)`; bounded retries + dead-letter.

**Kubernetes workloads (proposal):** stateless API; evaluation workers scaled on queue depth/age; singleton scheduler/outbox with lease; voice media separately; sandbox execution separately. Redis is a cache, not the only session store. Instrument per-session trace IDs, LLM tokens/cost, queue lag, evaluation retries.

## 6. Open technical questions

- Canonical engine: converge on one session aggregate or keep two implementations behind an adapter?
- Event schema and projection strategy; transaction support and index plan.
- Context-contract versioning and invalidation.
- Which responsibilities are deterministic vs LLM, and where the LLM is allowed to write memory.
- Voice: browser-first practice vs server-side assessment; recording/consent.
- Sandbox: runtime choice, warm pools, language set, hidden-test policy.
- Queue and evaluation execution model; latency budget for feedback.
- Cost model per session and per assessment.

## Sources

- Anthropic, Building Effective Agents — https://www.anthropic.com/research/building-effective-agents
- Anthropic, Effective Context Engineering for AI Agents — https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- OpenAI, Realtime API — https://platform.openai.com/docs/guides/realtime
- OpenAI, Realtime VAD — https://developers.openai.com/api/docs/guides/realtime-vad
- LiveKit, Turn Detection and Interruptions — https://docs.livekit.io/agents/build/turns/
- Moshi full-duplex speech — https://arxiv.org/abs/2410.00037
- Google Cloud, Streaming STT — https://cloud.google.com/speech-to-text/docs/streaming-recognize
- Docker Engine security — https://docs.docker.com/engine/security/
- gVisor — https://gvisor.dev/docs/
- Firecracker — https://firecracker-microvm.github.io/
- Kubernetes Jobs — https://kubernetes.io/docs/concepts/workloads/controllers/job/
- Judge0 — https://github.com/judge0/judge0
- Piston — https://github.com/engineer-man/piston
- Transactional outbox — https://microservices.io/patterns/data/transactional-outbox.html
- MongoDB atomicity — https://www.mongodb.com/docs/manual/core/write-operations-atomicity/
- Event sourcing — https://martinfowler.com/eaaDev/EventSourcing.html
- OpenTelemetry GenAI semantic conventions — https://opentelemetry.io/docs/specs/semconv/gen-ai/
