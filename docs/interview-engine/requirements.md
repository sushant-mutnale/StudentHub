# Interview Engine — Confirmed Requirements (Discovery Record)

Status: draft discovery record. **Confirmed** means accepted by the product owner. It is not a technical design. No model provider, agent framework, memory technology, vector database, queue or sandbox implementation has been selected.

## 1. Confirmed product requirements

### Lifecycle

1. **Hybrid lifecycle.** Practice interviews are durable and resumable. Formal assessments are time-bound, controlled and assessment-oriented. Practice history must not automatically bias formal assessment scoring.

### Personalization and memory

2. **Explicit consent.** Candidate information is used for cross-session personalization only after explicit consent.
3. **Candidate control.** Candidates can inspect, correct, delete and disable persistent personalization memory.
4. **Memory separation.** Memory is separated into: candidate profile/preferences; demonstrated competency and skill evidence; previous interview experiences and outcomes; learning history and progress; current interview session state.
5. **Provenance.** Every stored item is labelled self-reported, extracted, demonstrated, verified or inferred.
6. **No inference laundering.** An inferred skill assessment never becomes an established candidate fact. Private model reasoning is never stored as candidate memory.
7. **Deletion completeness.** Deletion covers derived memories, retrieval indexes and cached copies.
8. **Practice/assessment isolation.** Practice evidence may improve practice personalization and learning recommendations, but formal assessment rubrics and scores remain independent.

### Candidate understanding and planning

9. **Candidate context sources.** Resumes/profiles, projects and experience, target roles/JDs, previous interview performance, demonstrated skills/gaps, learning history and career objectives.
10. **No invention.** The system must not invent candidate experience or project details.
11. **Interview blueprint.** Before each interview, define competency coverage, question selection, follow-up opportunities, time allocation and difficulty progression, avoiding redundant previously assessed topics.

### Conversational behaviour

12. **Adaptive interviewing.** Contextual follow-ups, difficulty adjustment, project/decision exploration, misconception probing, conversation continuity, relevant memory of earlier answers, non-repetitive questions, appropriate thinking time and clarifications.
13. **Natural interaction.** Avoid robotic acknowledgements and generic question sequences.
14. **Single conversational owner.** Only one agent owns the candidate-facing conversation at a time.
15. **Small task context.** Subagents receive task-specific context projections, not the full candidate record or full conversation.

### Interview types

16. **Types to define and support.** Behavioral/HR, technical knowledge, DSA/coding, system design, resume/project deep-dive, debugging/code review, case-based, company/job-specific. Each needs its own interaction pattern, evidence and rubric; not every type requires a separate autonomous agent.
16a. **First production types.** Behavioral/HR, technical knowledge, resume/project deep-dive, and DSA/coding are production-first, across text and voice with secure code execution. System design, debugging/code review, case-based, and company/job-specific are fully specified but not first-milestone production commitments.

### Evaluation

17. **Evidence-based evaluation.** Distinguish claims from demonstrated evidence.
18. **Consistent formal assessment.** Formal assessments preserve a defined competency blueprint and consistent scoring criteria.
18a. **Candidate-owned shareable report.** Formal assessments produce a structured report the candidate owns and may deliberately share with a recruiter or placement cell. First production milestone has no live proctoring, identity verification, or human sign-off. Sharing is explicit, scoped, revocable and time-limited; reports carry the rubric, evidence and session-integrity metadata. Practice evidence never alters formal scores.
18b. **AI evidence-backed scorecard.** Each competency is scored by AI against a published rubric, and every score links to quoted evidence with confidence/limitations. The candidate may annotate or dispute a score but cannot edit it. The consumer sees scores, rubric, evidence and session-integrity metadata; no human sign-off is implied.
18c. **Shared competency framework with type-specific weights.** A common competency set is weighted and evidenced differently per interview type. Competency-level scores are comparable only within the same framework/rubric version; overall scores remain type-specific.
18d. **Shared core competencies.** The shared core is problem-solving, technical/domain depth, communication, structure, and evidence/verification. Type-specific dimensions such as code quality, collaboration, and ownership/impact are scored only where the interaction produces that evidence.
18e. **Fixed type-emphasis weighting profiles.** Each production type has a published, versioned weighting profile for the five core competencies. Practice and formal assessments of the same type use the same profile. Role/JD-adjusted and candidate-adaptive weights are not used in the first tier.

### Production

19. **Persistent sessions and reliable recovery.** Concurrent candidates, retryable evaluation, low-latency conversation, secure coding execution, voice streaming, monitoring/cost tracking, Kubernetes-based deployment.
20. Memory updates must be reliable and recoverable. Current session state stays separate from long-term candidate memory. Retrieve only relevant memories and avoid unnecessary retrieval on every conversational turn.
21. **Hybrid voice.** Practice uses browser speech with a visible degraded mode; formal assessments use a server-side real-time pipeline with authoritative transcript, consent-backed capture, and controlled turn-taking.
22. **Coding scope.** A small declared language set with function-based tasks. Practice exposes visible tests and run/test controls; formal assessments add hidden tests. Complexity is stated by the candidate with optional probes, not claimed as measured. Code, test results and execution evidence are persisted. Multi-file projects and measured asymptotic complexity are deferred.
23. **Purpose-based consent with retention tiers.** Consent is separate for (1) practice personalization and memory, (2) learning recommendations, (3) formal report creation and sharing, and (4) analytics/model improvement. Retention tiers apply per data class. Formal-report consent is independent of practice-memory consent; withdrawing one purpose does not silently disable the others.
24. **Class-based retention defaults.** Practice audio is not stored by default; formal audio is kept 30 days. Raw practice transcripts are kept 90 days; formal transcripts and reports 1 year. Competency summaries are kept until deletion or 2 years. Analytics use de-identified data only. Deletion completes within 30 days including derived data, with backups purged within 90 days.
25. **Mode-specific memory retrieval.** Practice retrieves a bounded, purpose-filtered projection of demonstrated competencies, prior feedback themes, unresolved gaps, and stated preferences. Formal assessments use only the target role, rubric, and context the candidate explicitly provides; prior practice scores are never retrieved for formal scoring.
26. **No overall score in the first-tier formal report.** The report presents competency scores with evidence and a narrative summary; progress is tracked per competency. No composite score is displayed. If a composite is ever introduced, ADR 0008's type-specific, non-comparable constraint applies.
27. **Time-limited anonymous report links.** Formal reports are shared through links that expire after 90 days by default, can be renewed while the report is retained (up to 1 year), are revocable at any time, and log access time and IP/user agent. Viewers do not need an account. PDF export is optional, not the only sharing mode.
28. **Qualitative confidence and non-adjudicated disputes.** Each competency score carries a low/medium/high confidence band with reasons and limitations. A candidate dispute creates an annotation and a visible unresolved flag; it does not change the score, trigger an automatic re-score, or imply human adjudication.
29. **Resumption by mode.** Practice resumes exactly across devices. Formal assessments recover after a disconnect within the deadline and allow one bounded, logged pause/grace window; there is no unlimited pause.
30. **Bounded adaptivity.** Practice uses a blueprint that guarantees competency coverage while adapting topic order, follow-up depth, and difficulty within predefined bounds. Formal assessments use a fixed blueprint.
31. **Practice feedback timing.** Practice offers candidate-initiated, bounded hints but no live scores; the full report arrives at the end. Formal assessments offer neither hints nor live scores.
32. **Per-competency difficulty.** Difficulty is tracked as novice/intermediate/advanced per core competency and adjusted within bounds; coverage stays fixed. Formal assessments use role-calibrated fixed difficulty.
33. **Bounded hints.** Practice allows a small, visible hint budget (for example 3 per session), logs each hint, applies no score penalty, and reflects hint use in confidence/limitations. Formal assessments have no hints.
34. **Hidden tests only at submission.** Formal coding assessments expose visible sample tests during the session; hidden tests run only at final submission and are never iterable.
35. **Coding languages.** The first tier supports Python, JavaScript, and Java. Additional languages and external execution services are deferred.
36. **Standard report contents.** The shared report includes interview type, target role, date, duration, question/difficulty coverage, competency scores with evidence and confidence, an evidence-grounded narrative summary, limitations, integrity metadata (pauses, disconnects, hint count, hidden-test result), candidate annotations/disputes, and share status/expiry. It excludes raw transcript, audio, and any role-fit verdict or ranking.
37. **Evidence excerpts.** Each competency carries two to three short verbatim excerpts, each at most two sentences, labelled by source question/turn, PII-redacted, and including counter-evidence where it exists.
38. **Turn-taking by mode.** Practice uses automatic endpointing with barge-in. Formal assessments use controlled turns with explicit cues and no barge-in.
39. **Latency and cost envelope.** Target p95 voice turn latency of 3 seconds in practice and 2 seconds in formal. Evaluation runs asynchronously with the report ready within 2 minutes. An explicit per-session cost cap guides model routing.
40. **Responsible baseline.** Prominent AI disclosure and limits at session start and in the report; a text alternative to voice; keyboard and screen-reader support to WCAG 2.2 AA for core interview/report flows; English-first with externalized strings.
41. **Evidence sufficiency.** A confident competency score requires at least two independent instances. One instance yields low confidence. No relevant evidence yields “not assessed”, never zero.
42. **Confidence band criteria.** Low confidence for one instance or conflicting evidence; medium for two consistent instances at expected difficulty; high for multiple consistent instances across contexts and difficulty with no contradictions.
43. **Per-type weight profiles.** Initial weights (problem-solving / technical depth / communication / structure / evidence): Behavioral 15/10/30/25/20; Technical 25/35/15/10/15; Resume/project 15/25/20/10/30; Coding 35/25/10/10/20. Type-specific dimensions are scored separately.
44. **Standard integrity metadata.** The shared report shows completion status, duration, mode (text/voice), pause count/duration, disconnect count, hint count (practice only), hidden-test run status, and rubric/weight version. It does not expose device/browser, IP, per-turn timestamps, or audio hashes.
45. **Optional formal audio.** Formal audio recording is a separate opt-in. Declining does not make the candidate ineligible; the assessment proceeds with the server transcript as the authoritative record.
46. **Coding test split.** Two or three visible tests cover the statement examples and basic edge cases. Hidden tests cover edge cases, invalid input, and scale. Practice may expose a broader visible set; formal assessments stay limited.
47. **Structured limitations.** Report limitations use fixed categories — insufficient evidence, conflicting evidence, time/coverage constraint, mode/technical limitation, hint assistance — each with a short factual explanation. They describe the evidence and session, never the candidate's character or intent.
48. **Independent evidence.** An independent instance is a distinct demonstration in response to a different question or a substantive follow-up. Repeating the same claim within one answer does not count.
49. **Voice fallback.** If voice is unavailable or fails, the session continues in text with a clear notice; the mode change is recorded in integrity metadata. The fallback applies to both practice and formal assessments.
50. **Coding execution isolation.** Each run uses an isolated environment with no network, read-only root, CPU/memory/PID/time limits, an ephemeral workspace and no host mounts. Execution runs as a separate workload from the API and never exposes hidden tests.
51. **Bounded retrieval.** Practice retrieval ranks by relevance to the current competency and role, prefers recent non-conflicting evidence, excludes withdrawn or invalidated memories, and respects a token budget. Formal assessments remain isolated from practice memory.
52. **First-tier topology.** Single-region managed Kubernetes with separate deployments for API, workers, voice media, and code execution. MongoDB and Redis are self-hosted. Multi-region active-active is deferred.
53. **Workload placement.** Separate node pools for general API/workers, latency-sensitive voice media, untrusted code execution, and stateful data services, with independent scaling and taints/tolerations.
54. **Self-hosted data services.** MongoDB and Redis run on dedicated VMs outside Kubernetes, on a private network, with automated backups and independent recovery.
55. **Object storage.** Resumes, formal audio, and report assets use private S3-compatible object storage with short-lived signed access and lifecycle policies matching retention classes.
56. **Separate ingress paths.** API HTTP/WebSocket traffic uses the standard ingress. Voice media uses a dedicated low-latency ingress/load balancer so long-lived voice connections do not share timeouts or failure modes with ordinary API traffic.

## 2. Explicitly not decided

- LLM provider, agent framework, memory technology, vector database, queue, sandbox runtime, voice transport/provider.
- Final session state pattern, context-contract schema, rubric schema, memory schema, retrieval token budget and projection schema.
- Consent UX, definition of "verified", legal holds, export format, jurisdiction-specific retention overrides.
- Competency definitions, limitation wording, dispute status model, metadata display rules; proctoring/human review deferred.
- Per-session cost-cap value, model routing, provider benchmarks, and degradation policy.

## 3. Validated existing-system facts

| Fact | Evidence |
|---|---|
| Two parallel interview engines: structured orchestrator (`/sessions`, `/interview-flow`) and multi-agent (`/agent-interview`) | `session_routes.py:73`, `agent_routes.py:11,99` |
| Current chat/voice UI uses the multi-agent path; the durable structured path is unused by the UI | `MockInterview.jsx:82-182`, `VoiceInterview.jsx:439-539` |
| Multi-agent transcript/context lives in memory + Redis (1h TTL); MongoDB stores only status/counters | `multi_agent_system.py:1318-1327`, `agent_routes.py:434-444` |
| Multi-agent question selection has no blueprint; `tested_topics` is recorded but not used to exclude repeats | `multi_agent_system.py:351-423` |
| Previous questions are computed but never inserted into the live question prompt | `multi_agent_system.py:359,425-438` |
| Follow-up depth is hard-capped at one per topic; fallbacks are random pools | `multi_agent_system.py:368-375,442-478` |
| Answers are truncated to 500 chars in context; final feedback transcript to 3000 chars | `multi_agent_system.py:1117-1121,1483-1501` |
| Live multi-agent evaluation uses one generic three-dimension prompt; the richer type-specific evaluator is wired only to `/questions/evaluate` | `multi_agent_system.py:594-614`, `question_routes.py:151`, `answer_evaluator.py:57-63` |
| Orchestrator drops system-design rounds when building company rounds | `interview_orchestrator.py:96-97` |
| Orchestrator `get_next_question` always inserts a new question; no outstanding-question check | `interview_orchestrator.py:214-260` |
| Orchestrator submit has no duplicate-answer check and no question-belongs-to-session check | `interview_orchestrator.py:468-515` |
| Resume only flips status and generates a new question | `session_routes.py:370-396` |
| No indexes for `interview_sessions`/`interview_questions`/`interview_answers`; indexes only cover scheduled `interviews` | `models/interview.py:13-18` |
| Structured voice sessions are created with `_id` but looked up by a `session_id` field, so that branch cannot match | `interview_orchestrator.py:151-152`, `voice_routes.py:142,271` |
| Voice UI is browser-only (`SpeechRecognition`/`speechSynthesis`) and never calls `/voice/*` | `VoiceInterview.jsx:203-216` |
| Server STT/TTS fall back to mock transcription/audio; streaming is a stub | `stt_service.py:194-201`, `tts_service.py:119-127`, `voice_routes.py:357-395` |
| Sandbox uses Docker CLI with `--network=none`, read-only root, cap-drop, PID/memory/CPU limits; hidden tests are masked | `code_sandbox.py:287-298,599-611` |
| APIs authenticate `/agent-interview/answer|hint|end`, but do not verify session ownership | `agent_routes.py:128-215` |
| Practice completion updates `ai_profile` and boosts matching **if** `/interview-flow/complete` is called; the UI does not call it | `interview_flow.py:167-334`, `flow_routes.py:94-112` |
| Outbox worker marks processing before publishing; claim is not atomic | `workers/outbox_worker.py:40-60` |
| Scheduler jobs are never registered; notification worker is only in `run_workers.py` | `background_scheduler.py:331-389`, `main.py:184-190`, `run_workers.py:38` |

## 4. Unresolved product decisions (priority order)

1. **Per-type weight calibration** — validate initial weights, per-competency evidence minimums, retakes, cross-session comparability.
2. **Report details** — redaction implementation, limitation wording, dispute status model, metadata display rules; identity/proctoring/human review deferred.
3. **Retention operations** — legal holds, backup deletion verification, export format, jurisdiction-specific overrides.
4. **Voice capture details** — endpointing thresholds, audio access controls, retry/resume behavior, assessment audit signals.
5. **Coding details** — function harness, persistence/retention, per-language harness, runtime selection.
6. **Resumption mechanics** — checkpoint granularity, pause allowance, deadline extension, cross-device authorization.
7. **Retrieval mechanics** — token budget, projection schema, staleness windows, invalidation triggers.
8. **Latency/cost validation** — cost-cap value, provider benchmarks, degradation policy, measurement method.
9. **Disclosure/accessibility details** — disclosure copy, WCAG audit, accommodation policy, localization roadmap.
10. **Adaptation bounds** — exact bounds, movement rules, anti-oscillation, audit.
11. **Hint details** — content bounds, confidence adjustment.
12. **Deployment operations** — ingress provider/transport details, observability, CI/CD.
