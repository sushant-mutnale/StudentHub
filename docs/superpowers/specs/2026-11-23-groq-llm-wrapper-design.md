# Groq LLM Wrapper — Design

Date: 2026-11-23
Status: Approved (design), pending implementation plan
Branch: `feat/interview-engine-first-slice`

## Problem

The canonical interview engine depends on three ports — `Analyzer`,
`QuestionGenerator`, `Evaluator` — but only scripted implementations exist.
The engine is therefore deterministic but not intelligent. We need real
adapters backed by Groq (`openai/gpt-oss-120b`) without ever letting a provider
outage or rate limit block a candidate's interview.

The hard constraint is the free tier: **30 requests/min, 1,000 requests/day,
8,000 tokens/min, 200,000 tokens/day per key**. At roughly 2,000 tokens per
interview step, **tokens per minute (8,000) binds long before requests per
minute (30)** — four calls exhaust a minute while 26 request slots sit idle.
Token accounting is therefore the primary concern, not request counting.

We have three API keys belonging to three separate Groq organisations, so each
key has an independent pool. Rotation across keys is a genuine 3x increase:
90 RPM / 24,000 TPM / 600,000 TPD combined.

## Goal

Ship a real LLM client with shared, correct rate limiting and key rotation, and
wire it to the three engine ports so a real interview can run end to end, while
preserving every existing fallback guarantee.

## Non-goals

- Migrating `backend/services/llm_service.py` (LangChain/OpenRouter, live
  callers) onto the new client. Deferred; see Deferred Work.
- Streaming responses. The engine requests one complete artifact per step.
- Parallel tool calls. `gpt-oss-120b` on Groq does not support them, and the
  engine's ports are single-shot.
- Multi-tenant per-user quota accounting. Budgets are per organisation key.
- Serving the frontend changes. Task 14 of the engine plan owns that.

## Architecture

Three layers with a strict dependency direction. Lower layers never import
upper layers, and infrastructure never learns interview concepts.

```
backend/interview_engine/adapters/llm.py     policy: interview shapes + fallback
        |  depends on
        v
backend/services/llm/                        infrastructure: transport + limits
    keys.py      ApiKeyPool
    limiter.py   RateLimiter (port), RedisRateLimiter, InMemoryRateLimiter
    groq.py      GroqLLMClient
    prompts.py   role prompts
```

The split is the point: `services/llm/` must be reusable by any agent that
later wants a Groq call, and the engine adapters must remain testable without
Redis, HTTP, or a provider. Neither layer may import the other's internals —
`services/llm/` may not import `interview_engine`, and `adapters/llm.py` may not
construct HTTP clients directly.

`services/llm/` is a new package and must not be confused with the existing
`services/llm_service.py` module. The two coexist deliberately; see Deferred
Work.

## Configuration

Add to `backend/config.py` `Settings` (already reads `backend/.env`):

| Field | Env var | Default | Purpose |
|---|---|---|---|
| `groq_api_key_1` | `GROQ_API_KEY_1` | `None` | Organisation key 1 |
| `groq_api_key_2` | `GROQ_API_KEY_2` | `None` | Organisation key 2 |
| `groq_api_key_3` | `GROQ_API_KEY_3` | `None` | Organisation key 3 |
| `groq_model` | `GROQ_MODEL` | `openai/gpt-oss-120b` | Model id |
| `groq_base_url` | `GROQ_BASE_URL` | `https://api.groq.com/openai/v1` | OpenAI-compatible endpoint |
| `groq_rpm_per_key` | `GROQ_RPM_PER_KEY` | `25` | Request budget per key per minute |
| `groq_rpd_per_key` | `GROQ_RPD_PER_KEY` | `900` | Request budget per key per day |
| `groq_tpm_per_key` | `GROQ_TPM_PER_KEY` | `7000` | Token budget per key per minute |
| `groq_tpd_per_key` | `GROQ_TPD_PER_KEY` | `180000` | Token budget per key per day |
| `groq_max_wait_seconds` | `GROQ_MAX_WAIT_SECONDS` | `60` | Bounded wait before failing |
| `groq_request_timeout_seconds` | `GROQ_REQUEST_TIMEOUT_SECONDS` | `30` | Per HTTP call timeout |
| `groq_llm_enabled` | `GROQ_LLM_ENABLED` | `false` | Master switch for the real adapters |

Internal budgets sit below provider limits (25/30 RPM, 900/1000 RPD, 7000/8000
TPM, 180000/200000 TPD) to absorb clock skew and identical-timestamp races.
`groq_llm_enabled` defaults to **false** so the default app configuration keeps
using scripted adapters and the fast test suite never touches the network.

Keys are read lazily when the client is constructed, never captured at module
import. `llm_service.py`'s import-time `os.getenv` is a flaw not to be copied:
tests and worker processes must be able to set keys after import.

## Rate limiting

### Backing store

Redis, because uvicorn workers and the Task 13 outbox worker are separate
processes that share one provider quota. The limiter uses the existing
`backend/redis_client.get_redis()` client.

Redis is addressed by a **key fingerprint**, never the raw key:
`keyhash = sha256(api_key).hexdigest()[:16]`. Raw keys never enter Redis, logs,
traces, exception messages, or `repr()`.

Namespace: `llm:rl:{keyhash}:*`.

### Windows

- **Requests per minute, tokens per minute**: exact rolling 60-second windows.
  Fixed minute buckets would allow a 2x burst across a boundary, which the
  token budget cannot absorb.
- **Requests per day, tokens per day**: rolling 24-hour windows implemented as
  hour-bucket counters covering the trailing 25 hours. Buckets are cheap and
  bounded; the oldest partial hour is counted in full, so the estimate
  **over-counts and never under-counts**. Over-counting is safe (we idle
  slightly early); under-counting would spend quota the provider will reject.
  This is deliberately stricter than the provider's own daily reset, whatever
  that turns out to be.

### Reservation

Every request reserves before it is sent, in a single atomic step. The whole
check-and-consume runs as one Lua script (`eval`), because a read-then-write
across four counters is racy under concurrency.

Inputs: keyhash, now, estimated input tokens, `max_output_tokens`, configured
budgets. Output: either *reserved* or *not reserved* plus the milliseconds
until the earliest constraint frees up.

Reservation consumes:

- 1 request against the minute and day request windows, and
- `estimated_input_tokens + max_output_tokens` against the token windows.

The output length is unknown before the call, so the reservation must assume
the worst case the request is allowed to produce. `max_output_tokens` is
role-specific and small (see Engine adapters), which keeps a reservation near 2,200
tokens rather than the 4,096 an unbounded default would demand.

Input tokens are estimated as `ceil(len(text) / 4)` summed over the system and
user messages. This is deliberately rough and slightly conservative for English
prose; it is not a tokenizer and must not pretend to be. The reservation is
corrected immediately after the response (see Settlement), so the estimate only
needs to be safe, not accurate.

### Settlement

After a response, the reservation is reconciled against the provider's reported
usage in a second atomic step:

- refund the difference when actual tokens are lower than reserved;
- record the overage when actual tokens are higher, so the next reservation
  waits accordingly.

If the call fails before a response exists, the reservation is refunded in full
(the failure consumed no provider quota we can measure, and leaving it held
would leak budget).

### Waiting

When nothing can be reserved, the limiter returns the wait time. The caller
`await asyncio.sleep(wait)` — never `time.sleep`, never a busy loop — and
retries. Waiting is bounded by `groq_max_wait_seconds` (default 60) from the
start of the attempt. Past that bound the limiter raises, and the adapter's
fallback takes over. No HTTP request may hang and no API handler may hold a
connection for an unbounded time.

Daily exhaustion is distinguished from per-minute exhaustion. Per-minute waits
resolve within a minute and are worth waiting for; a daily exhaustion that
exceeds the bound fails immediately with a distinct error so logs say
"out of daily budget" rather than a generic timeout.

### 429 responses

A provider 429 is authoritative and overrides our own accounting. On 429:

1. Read `retry-after` if present; otherwise apply bounded exponential backoff.
2. Mark that key's current window as blocked for the indicated duration.
3. Retry the next request on a different key.
4. Give up after a bounded number of attempts per call.

### Redis unavailability

If Redis errors during reservation, the limiter logs once and degrades to a
per-process in-memory limiter that still enforces the same budgets for that
process. This preserves single-worker safety and keeps the app serving. It
loses cross-process enforcement, which is an accepted, documented degradation —
the alternative is taking down interviews because the cache is down.

## Key pool and rotation

`ApiKeyPool` holds the configured keys in order and answers one question:
*which key should serve the next request, given each key's current
availability?* It chooses the key with the earliest available slot; on a 429 or
a rejected key it marks that key unavailable for the indicated duration and the
next attempt moves on. A key that is not configured is simply absent — one key
is a valid configuration and must work.

Rotation is stateful only through the limiter's Redis records, so it survives
process restarts and works across workers. The pool holds no authoritative
mutable state of its own.

## `GroqLLMClient`

`backend/services/llm/groq.py`. The only object that performs HTTP.

```
class GroqLLMClient:
    async def complete(
        self,
        *,
        system: str,
        user: str,
        max_output_tokens: int,
        temperature: float = 0.2,
        response_format: Optional[str] = None,
    ) -> LLMCompletion
```

`LLMCompletion` carries `text`, `prompt_tokens`, `completion_tokens`,
`keyhash`, and `model`.

Implementation notes:

- Built on the `openai` SDK (`AsyncOpenAI`) pointed at `groq_base_url`. The
  dependency is already installed (2.17.0) and the endpoint is OpenAI-compatible,
  so no new dependency and no Groq-specific SDK surface to track.
- Wrapped in `asyncio.wait_for` with `groq_request_timeout_seconds`.
- Every attempt goes through reserve → call → settle, with rotation and 429
  handling between attempts.
- Request count, token counts, key index, and outcome are logged at INFO/WARNING.
  The API key itself is never logged, only `keyhash`.
- `complete` raises a typed `LLMUnavailable` when the bounded wait or attempt
  budget is exhausted, so callers can fall back without inspecting strings.

## Engine adapters

`backend/interview_engine/adapters/llm.py` implements the existing port
protocols (`ports/capabilities.py:49-61`) so the engine is untouched by
transport concerns.

| Adapter | Port method | Output shape | `max_output_tokens` |
|---|---|---|---|
| `GroqAnalyzer` | `analyze(AnalysisRequest) -> Analysis` | JSON: `instance`, `signal`, `substantively_deficient` | 300 |
| `GroqQuestionGenerator` | `generate(QuestionRequest) -> GeneratedQuestion` | Plain text question | 200 |
| `GroqEvaluator` | `evaluate(EvaluationRequest) -> EvaluatorOutput` | JSON: `reasons` per competency plus `narrative` | 900 |

`response_format` is used where the port returns structured data, and parsing
is strict: a malformed or out-of-contract response is treated as a failure, not
salvaged into a half-valid artifact. Enum values are validated against the
engine's own enums before construction, so an LLM can never invent an `instance`
or `signal` value that the scoring rules do not understand.

`EvaluationRequest` already carries each competency's `level`, `confidence`,
and `instances`, computed by the scoring rules. The evaluator therefore only
writes `reasons` and `narrative`; `EvaluatorOutput` has no score field and the
adapter must never produce one. Scoring stays in the engine.

The three prompts live in `prompts.py` as module constants, one per role, and
are part of this package's policy rather than its transport. Each prompt states
the role, company, competency, and blueprint intent, and demands the exact
output contract above. Prompts must not contain the candidate's expected answer,
any scoring rubric that the engine already applies, or instructions that could
let the model change interview state — the engine owns all of that.

`build_llm_adapters(settings, limiter, clock)` in the same adapter module is the
single selection point: it returns the three real adapters only when
`groq_llm_enabled` is true and at least one key is configured, and returns
`None` otherwise so `adapters/factory.py` keeps the scripted defaults. Nothing
else in the app inspects `groq_llm_enabled`.

### Degradation

Adapters never leak a transport error out of a port method. Each catches
`LLMUnavailable`, transport errors, and parse failures, logs once, and either
returns the degraded value the engine already understands or raises the single
typed error that the engine's existing failure path handles:

- `GroqQuestionGenerator` → return `GeneratedQuestion(text="", source="fallback")`.
  The engine's `_valid_question_text` rejects empty text and substitutes
  `slot.fallback_question` (`engine.py:245-265`), so the candidate always gets a
  usable question and the engine's existing guard is what performs the swap.
- `GroqAnalyzer` → `Analysis(instance="same", signal="incomplete",
  substantively_deficient=True, limitation="analysis_unavailable")`, which is
  exactly the existing degradation semantic: no evidence is recorded, the turn
  counts as `same`, and the interview continues.
- `GroqEvaluator` → raise `LLMUnavailable`, so the engine's report path marks
  the report `failed` and the existing retry/attempt limit applies. A report
  with missing competencies must never be presented as complete; this is the
  one place where failing loudly is safer than degrading silently.

### Engine guard

`engine.py:506` calls `self.analyzer.analyze(...)` with no `try/except`, unlike
question generation and report building. Any adapter bug would therefore 500 a
candidate's answer. Add a guard at that call site that converts an analyzer
exception into the same degraded `Analysis` above and logs the exception. This
is a one-line-per-branch change, mirrors the existing generator guard, and is
required for the "no provider outage blocks an interview" guarantee to hold
independently of adapter correctness.

The engine has no knowledge of Groq after this change; the guard is
provider-agnostic and belongs to the engine.

## Fallback ladder

| Failure | Interview continues? | What the candidate sees |
|---|---|---|
| Question generation unavailable | Yes | Blueprint's fallback question text |
| Analysis unavailable | Yes | Question advances; turn recorded as `same` |
| Evaluation/report unavailable | Yes | Report marked `failed`; retried by existing attempt limit |
| Redis down | Yes | In-memory limiter per process |
| All keys exhausted | Yes, degraded | As above, per role |
| Single key 429 | Yes | Rotated to next key |

## Testing

Two levels, deliberately not exhaustive. The limiter is subtle and gets real
tests; the transport is thin and is proven by one end-to-end run.

**Deterministic, offline, no network** (`backend/tests/llm/`):

- Limiter arithmetic: window boundaries, reservation denied when any of RPM,
  TPM, RPD, TPD is exhausted, wait time equals the earliest freeing constraint,
  over-count-not-under-count property for daily buckets.
- Settlement: refund on under-use, overage recorded on over-use, full refund on
  failure.
- Rotation: prefers the key with the earliest slot; skips a 429'd key; works
  with one key and with three.
- 429 handling: honours `retry-after`, bounded attempts, typed failure.
- Redis outage: degrades to in-memory and still enforces budgets.
- No raw key appears in any Redis key or log record (assert against a thrown
  key value).
- Adapters, using a fake client: correct port output on success; each
  degradation path returns the exact degraded value; malformed JSON is a
  failure, not a partial parse.
- Engine guard: a raising analyzer does not escape `submit_turn`.

**One opt-in real test** (`integration` + `llm` markers, skipped unless a key is
configured): a full engine run — start, submit an answer, request a hint, end,
produce a report — against `openai/gpt-oss-120b`, asserting the interview
completes and the report is `complete`. This is the only test that touches the
network; the default suite must still pass with no keys and no Redis.

## Security

- The three keys currently circulating in chat are considered compromised. They
  must be revoked and regenerated in the Groq console after this work is
  verified. The regenerated keys go into `backend/.env` only.
- `backend/.env` is gitignored (`.gitignore`: `.env`, `backend/.env`). Never
  write keys into a tracked file, a test fixture, a doc, or a commit message.
- Logs, exceptions, and Redis keys use `keyhash` only.
- `groq_llm_enabled=false` by default means a misconfigured deployment cannot
  silently start spending quota.

## Deferred work

Recorded so it is not lost:

- Unify `services/llm_service.py` (OpenRouter/LangChain) with
  `services/llm/` once the engine is stable. Two LLM clients is a temporary,
  conscious cost: rewriting a client with live callers now would mix an
  interview-engine delivery with an unrelated migration.
- Per-user or per-session quota accounting, if interview volume ever justifies
  it.
- Streaming, if the UI needs first-token latency.
- A shared limiter for non-interview agents, now that the layer exists.

## References

- `docs/interview-engine/canonical-engine-design.md` §4.2–4.5, §9.1, §10.2–10.3
  (ports, adapters never own interview rules, no report blocked by an outage).
- `backend/interview_engine/ports/capabilities.py:49-75`
- `backend/interview_engine/application/engine.py:242-265` (generator guard),
  `:506` (unguarded analyzer call), `:941-997` (report path)
- `docs/superpowers/plans/2026-11-22-interview-engine-first-slice.md` Task 13
  (outbox worker shares the quota) and Task 15 (end-to-end verification).
