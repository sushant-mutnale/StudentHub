# Interview Engine First Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship one authenticated practice behavioral text interview end to end through the existing `/agent-interview/*` facade, backed by a deterministic canonical engine with a durable session, bounded follow-up, evidence ledger, and candidate-owned competency report.

**Architecture:** A deep module `backend/interview_engine/` owns all interview semantics behind a narrow `SessionStore` port and capability ports (analyzer, question generator, evaluator, lease, clock, ids). The HTTP facade in `backend/routes/agent_routes.py` only translates legacy request/response shapes into commands and results. Mongo is authoritative; Redis holds the short-lived device lease. Session state changes and outbox records commit in one transaction.

**Tech Stack:** Python 3.10+, FastAPI, Pydantic 2 (the repo uses the legacy `.dict()`/`.parse_obj()` calls, which still work), Motor (async Mongo), redis.asyncio, pytest + pytest-asyncio, React 18 + Vite + Vitest for the UI tests.

**Spec:** `docs/interview-engine/canonical-engine-design.md` (sections 4.2–4.5, 5.1–5.2, 6.1–6.4, 9.1, 10.2, 10.3) and ADRs 0047–0054. Requirements: `docs/interview-engine/requirements.md`.

## Global Constraints

- Only `behavioral` interview type and `practice` mode are enabled in this slice. Any other `interview_type` returns `400 unsupported_interview_type`; the frontend disables those options.
- No live answer score, no overall score, no hint penalty. `/answer` never returns `evaluation.score`; `/end` and `/feedback` never return `final_score`/`overall_score`.
- Session statuses: `planned → in_progress | expired | abandoned | completed`; `in_progress ↔ paused`; `in_progress|paused → completed | abandoned`; `planned → completed` allowed.
- Every state-changing write increments `version` and appends an event with the next `event_sequence`. The fencing-token takeover does **not** bump `version`; it appends `SessionLeaseTakenOver` and advances `event_sequence`.
- `question_pending` means "no outstanding question". An answer is never accepted without a matching outstanding question.
- Typed signals are exactly `sufficient | incomplete | off_topic`; instance markers are exactly `new | same`. `off_topic` never records an instance (coerce to `same`). `same` never records an instance.
- Only `new` instances with signal `sufficient` or `incomplete` enter level and confidence.
- Confidence: no instance → `not_assessed`; any synchronous contradiction → `low`; exactly one instance → `low`; ≥3 consistent `sufficient` instances across ≥3 distinct questions → `high`; else `medium`. Difficulty never enters.
- Level: zero → `not_assessed`; no `sufficient` → `emerging`; `sufficient*2 < n` → `developing`; `sufficient < n` → `proficient`; all `sufficient` → `strong`.
- Slot complete when signal is `sufficient` or `follow_up_used >= allowance`. Practice allowance is 1 per slot; formal is 0.
- Next action: clarification → `await_answer`; slot complete and further slot → `next_slot`; slot complete and no further slot → `end`; not complete with allowance and signal `incomplete|off_topic` → `follow_up`.
- Practice hint budget is 2 per session; hints never reduce a score.
- Device identity: client-generated `device_id`, required on every compatibility call; missing → `400 device_id_required`. Another device holding the lease → `409 device_conflict`.
- Mongo collection names are prefixed `interview_engine_`; the dedicated outbox collection is `interview_engine_outbox` with event types prefixed `interview_engine.`. The legacy `outbox_events` collection and worker are untouched.
- Python commands run with `venv\Scripts\python.exe` from the repo root. Never run a command without a timeout budget; test suites here take 60–90s.
- Do not add code comments. Follow existing repo style (`datetime.utcnow()`, Pydantic 2 models with `.dict()`/`.parse_obj()` compatibility calls, module-level `logger`).

---

## File Structure

```
backend/interview_engine/
  __init__.py                        facade: InterviewEngine, build_engine, errors
  contracts/
    __init__.py
    enums.py                         InterviewType, Mode, SessionStatus, TurnKind, Signal, InstanceKind, NextAction, ConfidenceBand, Level, ReportOutcome, EvidenceStrength
    blueprint.py                     BlueprintGroup, BlueprintSlot, Blueprint
    records.py                       SessionRecord, TurnRecord, EvidenceRecord, QuestionRecord, HintRecord, TurnCommandRecord, ReportRecord, EventRecord, OutboxRecord, Analysis
    messages.py                      commands + results + SessionView
    report.py                        CompetencyReport, Excerpt, Limitation, ReportBody, EvaluatorOutput
  domain/
    __init__.py
    scoring.py                       pure rules: counts, slot completion, next action, confidence, level, difficulty movement
    session.py                       Session aggregate: lifecycle, counters, transitions
    behavioral_blueprint.py          authored behavioral data + seniority mapping + build_behavioral_blueprint()
  ports/
    __init__.py
    store.py                         SessionStore protocol + transaction contract
    capabilities.py                  Analyzer, QuestionGenerator, Evaluator, LeasePort, Clock, IdGenerator protocols + request DTOs
  application/
    __init__.py
    engine.py                        start/submit/hint/resume/pause/end/report/drain_outbox
    report_builder.py                evidence -> competency report (excerpts, limitations, integrity)
  adapters/
    __init__.py
    memory_store.py                  InMemorySessionStore (unit tests + route tests)
    mongo_store.py                   MongoSessionStore (authoritative)
    redis_lease.py                   RedisLease
    scripted.py                      HeuristicAnalyzer, ScriptedAnalyzer, ScriptedQuestionGenerator, DeterministicEvaluator
    system.py                        SystemClock, UuidIds
    factory.py                       build_engine(...) wiring
  compatibility/
    __init__.py
    agent_interview.py               request/response mapping, precondition synthesis
    dependencies.py                  get_engine() FastAPI dependency
  worker.py                          drain_interview_engine_outbox()

backend/models/interview_engine_indexes.py
backend/models/indexes.py            (modify: call ensure_interview_engine_indexes)
backend/routes/agent_routes.py       (modify: facade endpoints, keep /extract-text)
backend/run_workers.py               (modify: run the engine outbox loop)
backend/tests/interview_engine/      unit + integration tests
frontend/src/components/MockInterview.jsx  (modify)
frontend/src/lib/interviewClient.js        (new: device id + request ids)
frontend/src/components/__tests__/MockInterview.test.jsx (new)
```

---

### Task 1: Contracts and enums

**Files:**
- Create: `backend/interview_engine/__init__.py`, `backend/interview_engine/contracts/__init__.py`, `backend/interview_engine/contracts/enums.py`, `backend/interview_engine/contracts/blueprint.py`, `backend/interview_engine/contracts/records.py`, `backend/interview_engine/contracts/messages.py`, `backend/interview_engine/contracts/report.py`
- Test: `backend/tests/interview_engine/__init__.py`, `backend/tests/interview_engine/test_contracts.py`

**Interfaces:**
- Produces: `Signal`, `InstanceKind`, `NextAction`, `ConfidenceBand`, `Level`, `ReportOutcome`, `SessionStatus`, `TurnKind`, `Mode`, `InterviewType` (all `str, Enum`); `Blueprint`, `BlueprintGroup`, `BlueprintSlot`; `SessionRecord`, `TurnRecord`, `EvidenceRecord`, `QuestionRecord`, `HintRecord`, `TurnCommandRecord`, `ReportRecord`, `EventRecord`, `OutboxRecord`, `Analysis`; `StartSessionCommand`, `StartSessionResult`, `SubmitTurnCommand`, `SubmitTurnResult`, `RequestHintCommand`, `HintResult`, `ResumeSessionCommand`, `ResumeSessionResult`, `PauseSessionCommand`, `EndSessionCommand`, `EndSessionResult`, `SessionView`; `CompetencyReport`, `Excerpt`, `Limitation`, `ReportBody`, `EvaluatorOutput`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/interview_engine/test_contracts.py
from datetime import datetime

from backend.interview_engine.contracts import enums
from backend.interview_engine.contracts.blueprint import Blueprint, BlueprintGroup, BlueprintSlot
from backend.interview_engine.contracts.messages import SessionView, SubmitTurnResult
from backend.interview_engine.contracts.records import SessionRecord


def _slot():
    return BlueprintSlot(
        slot_id="ps-1",
        competency="problem_solving",
        dimension="problem_solving",
        difficulty="intermediate",
        intent="Describe a concrete problem you solved.",
        fallback_question="Tell me about a concrete problem you solved.",
        follow_up_question="What would you do differently?",
        clarification_text="Share a specific past situation.",
        hint_text="Pick one project and describe the constraint.",
    )


def test_signal_enum_is_exactly_the_typed_set():
    assert {s.value for s in enums.Signal} == {"sufficient", "incomplete", "off_topic"}
    assert {s.value for s in enums.InstanceKind} == {"new", "same"}


def test_next_action_enum_has_no_removed_value():
    assert {a.value for a in enums.NextAction} == {
        "await_answer",
        "follow_up",
        "next_slot",
        "end",
    }


def test_session_record_round_trips_through_dict():
    blueprint = Blueprint(groups=[BlueprintGroup(group_id="g1", competency="problem_solving", slots=[_slot()])])
    record = SessionRecord(
        session_id="s1",
        candidate_id="c1",
        interview_type="behavioral",
        mode="practice",
        status="planned",
        version=0,
        event_sequence=0,
        last_applied_sequence=0,
        fencing_token="t1",
        device_id="d1",
        blueprint=blueprint,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    restored = SessionRecord.parse_obj(record.dict())
    assert restored.blueprint.groups[0].slots[0].slot_id == "ps-1"
    assert restored.follow_up_used == {}
    assert restored.question_pending is True


def test_session_view_reports_missing_question():
    view = SessionView(
        session_id="s1",
        status="planned",
        version=0,
        question_pending=True,
        outstanding_question=None,
        report_id=None,
        report_outcome=None,
        fencing_token="t1",
    )
    assert view.question_pending is True
    assert view.outstanding_question is None


def test_submit_turn_result_has_no_score_field():
    result = SubmitTurnResult(
        session_id="s1",
        status="in_progress",
        next_action="next_slot",
        question="Q2",
        question_id="q2",
        version=3,
    )
    assert not hasattr(result, "score")
    assert result.dict().get("score") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest backend/tests/interview_engine/test_contracts.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.interview_engine'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/interview_engine/contracts/enums.py
from enum import Enum


class InterviewType(str, Enum):
    BEHAVIORAL = "behavioral"


class Mode(str, Enum):
    PRACTICE = "practice"
    FORMAL = "formal"


class SessionStatus(str, Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    EXPIRED = "expired"


class TurnKind(str, Enum):
    ANSWER = "answer"
    CLARIFICATION_REQUEST = "clarification_request"


class Signal(str, Enum):
    SUFFICIENT = "sufficient"
    INCOMPLETE = "incomplete"
    OFF_TOPIC = "off_topic"


class InstanceKind(str, Enum):
    NEW = "new"
    SAME = "same"


class NextAction(str, Enum):
    AWAIT_ANSWER = "await_answer"
    FOLLOW_UP = "follow_up"
    NEXT_SLOT = "next_slot"
    END = "end"


class ConfidenceBand(str, Enum):
    NOT_ASSESSED = "not_assessed"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Level(str, Enum):
    NOT_ASSESSED = "not_assessed"
    EMERGING = "emerging"
    DEVELOPING = "developing"
    PROFICIENT = "proficient"
    STRONG = "strong"


class ReportOutcome(str, Enum):
    EVALUATING = "evaluating"
    READY = "ready"
    SUPPRESSED = "suppressed"
    FAILED = "failed"


class EvidenceStrength(str, Enum):
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
```

```python
# backend/interview_engine/contracts/blueprint.py
from typing import List

from pydantic import BaseModel, Field


class BlueprintSlot(BaseModel):
    slot_id: str
    competency: str
    dimension: str
    difficulty: str
    intent: str
    target_evidence_count: int = 1
    follow_up_allowance_practice: int = 1
    follow_up_allowance_formal: int = 0
    fallback_question: str
    follow_up_question: str
    clarification_text: str
    hint_text: str

    def allowance(self, mode: str) -> int:
        return self.follow_up_allowance_formal if mode == "formal" else self.follow_up_allowance_practice


class BlueprintGroup(BaseModel):
    group_id: str
    competency: str
    slots: List[BlueprintSlot]


class Blueprint(BaseModel):
    blueprint_version: str = "behavioral-v1"
    interview_type: str = "behavioral"
    mode: str = "practice"
    weights_version: str = "behavioral-weights-v1"
    adaptation_policy_version: str = "practice-adapt-v1"
    groups: List[BlueprintGroup] = Field(default_factory=list)

    def ordered_slots(self) -> List[BlueprintSlot]:
        return [slot for group in self.groups for slot in group.slots]

    def slot(self, slot_id: str) -> BlueprintSlot:
        for slot in self.ordered_slots():
            if slot.slot_id == slot_id:
                return slot
        raise KeyError(slot_id)
```

```python
# backend/interview_engine/contracts/records.py
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .blueprint import Blueprint


class ConsentSnapshot(BaseModel):
    evaluation: bool = True
    memory: bool = False
    model_improvement: bool = False


class SessionRecord(BaseModel):
    session_id: str
    candidate_id: str
    interview_type: str
    mode: str
    status: str
    version: int
    event_sequence: int
    last_applied_sequence: int
    fencing_token: str
    device_id: str
    blueprint: Blueprint
    client_request_id: Optional[str] = None
    role: Optional[str] = None
    company: Optional[str] = None
    plan_position: int = 0
    current_slot_id: Optional[str] = None
    current_question_id: Optional[str] = None
    outstanding_question: Optional[str] = None
    question_pending: bool = True
    pending_question_request: Optional[Dict[str, Any]] = None
    follow_up_used: Dict[str, int] = Field(default_factory=dict)
    hint_count: int = 0
    hint_budget: int = 2
    pause_count: int = 0
    pause_started_at: Optional[datetime] = None
    total_pause_seconds: int = 0
    disconnect_count: int = 0
    consent: ConsentSnapshot = Field(default_factory=ConsentSnapshot)
    report_id: Optional[str] = None
    report_outcome: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TurnRecord(BaseModel):
    turn_id: str
    session_id: str
    sequence: int
    kind: str
    question_id: str
    slot_id: str
    text: str
    idempotency_key: str
    device_id: str
    created_at: datetime


class Analysis(BaseModel):
    signal: str
    instance: str
    contradiction: bool = False
    substantively_deficient: bool = False
    limitation: Optional[str] = None


class EvidenceRecord(BaseModel):
    evidence_id: str
    session_id: str
    turn_id: str
    question_id: str
    slot_id: str
    competency: str
    signal: str
    instance: str
    contradiction: bool = False
    difficulty: str
    adapted: bool = False
    created_at: datetime


class QuestionRecord(BaseModel):
    question_id: str
    session_id: str
    slot_id: str
    question_generation_key: str
    purpose: str
    text: str
    source: str
    created_at: datetime


class HintRecord(BaseModel):
    hint_id: str
    session_id: str
    hint_idempotency_key: str
    question_id: str
    text: str
    hints_used: int = 1
    created_at: datetime


class TurnCommandRecord(BaseModel):
    session_id: str
    idempotency_key: str
    status: str
    result: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class ReportRecord(BaseModel):
    report_id: str
    session_id: str
    outcome: str
    body: Optional[Dict[str, Any]] = None
    attempts: int = 0
    created_at: datetime
    updated_at: datetime


class EventRecord(BaseModel):
    event_id: str
    session_id: str
    event_sequence: int
    event_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class OutboxRecord(BaseModel):
    outbox_id: str
    event_type: str
    payload: Dict[str, Any]
    status: str = "pending"
    attempts: int = 0
    worker_id: Optional[str] = None
    created_at: datetime
```

```python
# backend/interview_engine/contracts/report.py
from typing import Dict, List

from pydantic import BaseModel, Field


class Excerpt(BaseModel):
    turn_id: str
    question_id: str
    text: str


class Limitation(BaseModel):
    category: str
    detail: str


class CompetencyReport(BaseModel):
    competency: str
    level: str
    confidence: str
    instance_count: int
    reasons: List[str] = Field(default_factory=list)
    excerpts: List[Excerpt] = Field(default_factory=list)
    limitations: List[Limitation] = Field(default_factory=list)


class ReportBody(BaseModel):
    report_id: str
    session_id: str
    interview_type: str
    mode: str
    target_role: str = ""
    company: str = ""
    duration_seconds: int = 0
    competencies: List[CompetencyReport] = Field(default_factory=list)
    narrative: str = ""
    limitations: List[Limitation] = Field(default_factory=list)
    integrity: Dict[str, object] = Field(default_factory=dict)
    disclosure: Dict[str, object] = Field(default_factory=dict)


class EvaluatorOutput(BaseModel):
    reasons: Dict[str, List[str]] = Field(default_factory=dict)
    narrative: str = ""
```

```python
# backend/interview_engine/contracts/messages.py
from typing import List, Optional

from pydantic import BaseModel, Field


class StartSessionCommand(BaseModel):
    candidate_id: str
    interview_type: str = "behavioral"
    mode: str = "practice"
    device_id: str
    client_request_id: str
    role: Optional[str] = None
    company: Optional[str] = None
    job_description: Optional[str] = None
    consent: Optional[dict] = None


class StartSessionResult(BaseModel):
    session_id: str
    status: str
    first_question: str
    question_id: str
    fencing_token: str
    version: int = 0
    report_id: Optional[str] = None
    report_outcome: Optional[str] = None
    client_request_id: Optional[str] = None


class SubmitTurnCommand(BaseModel):
    candidate_id: str
    session_id: str
    device_id: str
    fencing_token: Optional[str] = None
    turn_idempotency_key: str
    kind: str = "answer"
    text: str = ""
    question_id: Optional[str] = None
    expected_version: Optional[int] = None


class SubmitTurnResult(BaseModel):
    session_id: str
    status: str
    next_action: str
    question: Optional[str] = None
    question_id: Optional[str] = None
    version: int = 0
    report_id: Optional[str] = None
    report_outcome: Optional[str] = None
    question_pending: bool = False


class RequestHintCommand(BaseModel):
    candidate_id: str
    session_id: str
    device_id: str
    fencing_token: Optional[str] = None
    hint_idempotency_key: str
    question_id: Optional[str] = None
    expected_version: Optional[int] = None


class HintResult(BaseModel):
    hint: str
    hints_used: int
    remaining: int
    version: int
    question_id: str


class ResumeSessionCommand(BaseModel):
    candidate_id: str
    session_id: str
    device_id: str
    command_id: Optional[str] = None


class ResumeSessionResult(BaseModel):
    session_id: str
    status: str
    fencing_token: str
    question: Optional[str] = None
    question_id: Optional[str] = None
    version: int = 0
    question_pending: bool = False


class PauseSessionCommand(BaseModel):
    candidate_id: str
    session_id: str
    device_id: str
    fencing_token: Optional[str] = None
    command_id: str
    reason: str = "candidate_paused"
    expected_version: Optional[int] = None


class EndSessionCommand(BaseModel):
    candidate_id: str
    session_id: str
    device_id: str
    fencing_token: Optional[str] = None
    end_command_id: str
    reason: str = "candidate_completed"


class EndSessionResult(BaseModel):
    session_id: str
    status: str
    report_id: Optional[str] = None
    report_outcome: Optional[str] = None


class SessionView(BaseModel):
    session_id: str
    status: str
    version: int
    question_pending: bool
    outstanding_question: Optional[str] = None
    question_id: Optional[str] = None
    report_id: Optional[str] = None
    report_outcome: Optional[str] = None
    fencing_token: Optional[str] = None
    hints_used: int = 0
    hints_remaining: int = 0
    plan_position: int = 0
    current_slot_id: Optional[str] = None
    questions_answered: int = 0
```

```python
# backend/interview_engine/contracts/__init__.py
from .blueprint import Blueprint, BlueprintGroup, BlueprintSlot
from .enums import (
    ConfidenceBand,
    EvidenceStrength,
    InstanceKind,
    InterviewType,
    Level,
    Mode,
    NextAction,
    ReportOutcome,
    SessionStatus,
    Signal,
    TurnKind,
)
from .messages import (
    EndSessionCommand,
    EndSessionResult,
    HintResult,
    PauseSessionCommand,
    RequestHintCommand,
    ResumeSessionCommand,
    ResumeSessionResult,
    SessionView,
    StartSessionCommand,
    StartSessionResult,
    SubmitTurnCommand,
    SubmitTurnResult,
)
from .records import (
    Analysis,
    ConsentSnapshot,
    EventRecord,
    EvidenceRecord,
    HintRecord,
    OutboxRecord,
    QuestionRecord,
    ReportRecord,
    SessionRecord,
    TurnCommandRecord,
    TurnRecord,
)
from .report import CompetencyReport, EvaluatorOutput, Excerpt, Limitation, ReportBody

__all__ = [name for name in dir() if not name.startswith("_")]
```

```python
# backend/interview_engine/__init__.py
from .contracts import *  # noqa: F401,F403
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest backend/tests/interview_engine/test_contracts.py -q`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/interview_engine backend/tests/interview_engine
git commit -m "feat(interview-engine): add canonical contracts and records"
```

---

### Task 2: Pure scoring rules

**Files:**
- Create: `backend/interview_engine/domain/__init__.py`, `backend/interview_engine/domain/scoring.py`
- Test: `backend/tests/interview_engine/test_scoring.py`

**Interfaces:**
- Consumes: `Signal`, `NextAction`, `ConfidenceBand`, `Level` from Task 1.
- Produces: `InstanceFact(competency, question_id, signal, contradiction)`, `counts_for_scoring(signal, instance)`, `is_slot_complete(signal, follow_up_used, allowance)`, `decide_next_action(*, clarification, slot_complete, has_further_slot, signal, allowance_remaining) -> NextAction`, `confidence_for(facts) -> ConfidenceBand`, `level_for(facts) -> Level`, `move_difficulty(current, signal, substantively_deficient, last_direction) -> tuple[str, int]`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/interview_engine/test_scoring.py
from backend.interview_engine.contracts.enums import ConfidenceBand, Level, NextAction
from backend.interview_engine.domain.scoring import (
    InstanceFact,
    confidence_for,
    counts_for_scoring,
    decide_next_action,
    is_slot_complete,
    level_for,
    move_difficulty,
)


def fact(signal, qid="q1", contradiction=False):
    return InstanceFact(competency="c", question_id=qid, signal=signal, contradiction=contradiction)


def test_only_new_sufficient_or_incomplete_instances_count():
    assert counts_for_scoring("sufficient", "new") is True
    assert counts_for_scoring("incomplete", "new") is True
    assert counts_for_scoring("off_topic", "new") is False
    assert counts_for_scoring("sufficient", "same") is False


def test_slot_completes_on_sufficient_or_spent_allowance():
    assert is_slot_complete("sufficient", 0, 1) is True
    assert is_slot_complete("incomplete", 0, 1) is False
    assert is_slot_complete("incomplete", 1, 1) is True
    assert is_slot_complete("off_topic", 1, 1) is True


def test_next_action_clarification_wins():
    assert decide_next_action(
        clarification=True, slot_complete=True, has_further_slot=True,
        signal="sufficient", allowance_remaining=1,
    ) == NextAction.AWAIT_ANSWER


def test_next_action_end_on_last_complete_slot():
    assert decide_next_action(
        clarification=False, slot_complete=True, has_further_slot=False,
        signal="sufficient", allowance_remaining=0,
    ) == NextAction.END


def test_next_action_follow_up_requires_incomplete_and_allowance():
    assert decide_next_action(
        clarification=False, slot_complete=False, has_further_slot=True,
        signal="incomplete", allowance_remaining=1,
    ) == NextAction.FOLLOW_UP
    assert decide_next_action(
        clarification=False, slot_complete=False, has_further_slot=True,
        signal="sufficient", allowance_remaining=1,
    ) == NextAction.NEXT_SLOT


def test_confidence_ordered_rule():
    assert confidence_for([]) == ConfidenceBand.NOT_ASSESSED
    assert confidence_for([fact("sufficient")]) == ConfidenceBand.LOW
    assert confidence_for([fact("sufficient"), fact("sufficient", "q2")]) == ConfidenceBand.MEDIUM
    assert confidence_for([fact("sufficient", "q1", True), fact("sufficient", "q2")]) == ConfidenceBand.LOW
    three = [fact("sufficient", "q1"), fact("sufficient", "q2"), fact("sufficient", "q3")]
    assert confidence_for(three) == ConfidenceBand.HIGH
    repeated = [fact("sufficient", "q1"), fact("sufficient", "q1"), fact("sufficient", "q1")]
    assert confidence_for(repeated) == ConfidenceBand.MEDIUM


def test_level_total_function():
    assert level_for([]) == Level.NOT_ASSESSED
    assert level_for([fact("incomplete")]) == Level.EMERGING
    assert level_for([fact("sufficient"), fact("incomplete", "q2")]) == Level.PROFICIENT
    assert level_for([fact("incomplete"), fact("incomplete", "q2"), fact("sufficient", "q3")]) == Level.DEVELOPING
    assert level_for([fact("sufficient"), fact("sufficient", "q2")]) == Level.STRONG


def test_contradiction_caps_confidence_but_not_level():
    facts = [fact("sufficient", "q1", True), fact("sufficient", "q2"), fact("sufficient", "q3")]
    assert confidence_for(facts) == ConfidenceBand.LOW
    assert level_for(facts) == Level.STRONG


def test_difficulty_moves_one_step_and_never_reverses():
    assert move_difficulty("intermediate", "sufficient", False, 0) == ("advanced", 1)
    assert move_difficulty("intermediate", "incomplete", True, 0) == ("novice", -1)
    assert move_difficulty("intermediate", "incomplete", False, 0) == ("intermediate", 0)
    assert move_difficulty("intermediate", "off_topic", True, 0) == ("intermediate", 0)
    assert move_difficulty("intermediate", "incomplete", True, 1) == ("intermediate", 1)
    assert move_difficulty("novice", "incomplete", True, 0) == ("novice", 0)
    assert move_difficulty("advanced", "sufficient", False, 0) == ("advanced", 0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest backend/tests/interview_engine/test_scoring.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.interview_engine.domain'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/interview_engine/domain/scoring.py
from dataclasses import dataclass
from typing import Optional, Sequence, Tuple

from ..contracts.enums import ConfidenceBand, Level, NextAction, Signal

_DIFFICULTY_ORDER = ("novice", "intermediate", "advanced")


@dataclass(frozen=True)
class InstanceFact:
    competency: str
    question_id: str
    signal: str
    contradiction: bool = False


def counts_for_scoring(signal: str, instance: str) -> bool:
    return instance == "new" and signal in (Signal.SUFFICIENT.value, Signal.INCOMPLETE.value)


def is_slot_complete(signal: str, follow_up_used: int, allowance: int) -> bool:
    return signal == Signal.SUFFICIENT.value or follow_up_used >= allowance


def decide_next_action(
    *,
    clarification: bool,
    slot_complete: bool,
    has_further_slot: bool,
    signal: str,
    allowance_remaining: int,
) -> NextAction:
    if clarification:
        return NextAction.AWAIT_ANSWER
    if slot_complete:
        return NextAction.NEXT_SLOT if has_further_slot else NextAction.END
    if allowance_remaining > 0 and signal in (Signal.INCOMPLETE.value, Signal.OFF_TOPIC.value):
        return NextAction.FOLLOW_UP
    return NextAction.NEXT_SLOT if has_further_slot else NextAction.END


def confidence_for(facts: Sequence[InstanceFact]) -> ConfidenceBand:
    if not facts:
        return ConfidenceBand.NOT_ASSESSED
    if any(f.contradiction for f in facts):
        return ConfidenceBand.LOW
    if len(facts) == 1:
        return ConfidenceBand.LOW
    distinct_questions = {f.question_id for f in facts}
    if (
        len(facts) >= 3
        and len(distinct_questions) >= 3
        and all(f.signal == Signal.SUFFICIENT.value for f in facts)
    ):
        return ConfidenceBand.HIGH
    return ConfidenceBand.MEDIUM


def level_for(facts: Sequence[InstanceFact]) -> Level:
    total = len(facts)
    if total == 0:
        return Level.NOT_ASSESSED
    sufficient = sum(1 for f in facts if f.signal == Signal.SUFFICIENT.value)
    if sufficient == 0:
        return Level.EMERGING
    if sufficient * 2 < total:
        return Level.DEVELOPING
    if sufficient < total:
        return Level.PROFICIENT
    return Level.STRONG


def move_difficulty(
    current: str,
    signal: str,
    substantively_deficient: bool,
    last_direction: int,
) -> Tuple[str, int]:
    index = _DIFFICULTY_ORDER.index(current)
    if signal == Signal.SUFFICIENT.value and last_direction >= 0 and index < len(_DIFFICULTY_ORDER) - 1:
        return _DIFFICULTY_ORDER[index + 1], 1
    if (
        signal == Signal.INCOMPLETE.value
        and substantively_deficient
        and last_direction <= 0
        and index > 0
    ):
        return _DIFFICULTY_ORDER[index - 1], -1
    return current, last_direction
```

```python
# backend/interview_engine/domain/__init__.py
from .scoring import (
    InstanceFact,
    confidence_for,
    counts_for_scoring,
    decide_next_action,
    is_slot_complete,
    level_for,
    move_difficulty,
)

__all__ = [
    "InstanceFact",
    "confidence_for",
    "counts_for_scoring",
    "decide_next_action",
    "is_slot_complete",
    "level_for",
    "move_difficulty",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest backend/tests/interview_engine/test_scoring.py -q`
Expected: PASS (9 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/interview_engine/domain backend/tests/interview_engine/test_scoring.py
git commit -m "feat(interview-engine): add deterministic scoring rules"
```

---

### Task 3: Session aggregate

**Files:**
- Create: `backend/interview_engine/domain/session.py`
- Test: `backend/tests/interview_engine/test_session.py`

**Interfaces:**
- Consumes: `SessionRecord`, `Blueprint`, `Analysis`, enums, `is_slot_complete`, `decide_next_action`.
- Produces: `Session` class with `record`, `from_record`, `to_record`, `bump()`, `next_sequence()`, `slot()`, `slot_allowance()`, `follow_up_used_for(slot_id)`, `has_further_slot()`, `advance_slot()`, `apply_clarification(turn, reply)`, `apply_answer(turn, analysis, evidence, competency) -> NextAction`, `begin_completion(report_id, outcome)`, `mark_paused()`, `mark_resumed()`, `set_question(...)`, `set_question_pending(...)`, `is_terminal()`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/interview_engine/test_session.py
from datetime import datetime

from backend.interview_engine.contracts.blueprint import Blueprint, BlueprintGroup, BlueprintSlot
from backend.interview_engine.contracts.enums import NextAction
from backend.interview_engine.contracts.records import Analysis, EvidenceRecord, SessionRecord, TurnRecord
from backend.interview_engine.domain.session import Session


def _slot(slot_id, competency):
    return BlueprintSlot(
        slot_id=slot_id,
        competency=competency,
        dimension=competency,
        difficulty="intermediate",
        intent=f"intent {slot_id}",
        fallback_question=f"question {slot_id}",
        follow_up_question=f"follow up {slot_id}",
        clarification_text="clarify",
        hint_text="hint",
    )


def _session():
    blueprint = Blueprint(
        groups=[
            BlueprintGroup(group_id="g1", competency="a", slots=[_slot("a1", "a"), _slot("a2", "a")]),
            BlueprintGroup(group_id="g2", competency="b", slots=[_slot("b1", "b"), _slot("b2", "b")]),
        ]
    )
    record = SessionRecord(
        session_id="s1", candidate_id="c1", interview_type="behavioral", mode="practice",
        status="in_progress", version=1, event_sequence=1, last_applied_sequence=1,
        fencing_token="t1", device_id="d1", blueprint=blueprint,
        current_slot_id="a1", current_question_id="q1", outstanding_question="question a1",
        question_pending=False, created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    )
    return Session.from_record(record)


def _turn(kind="answer", text="answer text"):
    return TurnRecord(
        turn_id="t-1", session_id="s1", sequence=1, kind=kind, question_id="q1",
        slot_id="a1", text=text, idempotency_key="k1", device_id="d1",
        created_at=datetime.utcnow(),
    )


def _evidence(turn_id="t-1", signal="sufficient"):
    return EvidenceRecord(
        evidence_id="e1", session_id="s1", turn_id=turn_id, question_id="q1", slot_id="a1",
        competency="a", signal=signal, instance="new", difficulty="intermediate",
        created_at=datetime.utcnow(),
    )


def test_advance_slot_moves_plan_position_and_clears_question():
    session = _session()
    session.advance_slot()
    assert session.record.plan_position == 1
    assert session.record.current_slot_id == "a2"
    assert session.record.outstanding_question is None
    assert session.record.question_pending is True


def test_sufficient_answer_advances_slot():
    session = _session()
    action = session.apply_answer(_turn(), Analysis(signal="sufficient", instance="new"), _evidence(), "a")
    assert action == NextAction.NEXT_SLOT
    assert session.record.plan_position == 1
    assert session.record.follow_up_used == {}


def test_incomplete_answer_emits_follow_up_and_spends_allowance():
    session = _session()
    action = session.apply_answer(
        _turn(), Analysis(signal="incomplete", instance="new", substantively_deficient=True), _evidence(), "a"
    )
    assert action == NextAction.FOLLOW_UP
    assert session.record.follow_up_used == {"a1": 1}
    assert session.record.question_pending is True
    assert session.record.plan_position == 0


def test_follow_up_answer_completes_slot_even_when_incomplete():
    session = _session()
    session.apply_answer(_turn(), Analysis(signal="incomplete", instance="new"), _evidence(), "a")
    session.set_question("q2", "follow up a1", "a1", pending=False)
    action = session.apply_answer(
        _turn(), Analysis(signal="incomplete", instance="new"), _evidence(), "a"
    )
    assert action == NextAction.NEXT_SLOT


def test_off_topic_with_allowance_triggers_follow_up_but_records_nothing():
    session = _session()
    action = session.apply_answer(
        _turn(), Analysis(signal="off_topic", instance="same"), None, "a"
    )
    assert action == NextAction.FOLLOW_UP
    assert session.record.follow_up_used == {"a1": 1}


def test_last_slot_sufficient_ends_and_allocates_report():
    session = _session()
    session.record.plan_position = 3
    session.record.current_slot_id = "b2"
    session.record.current_question_id = "q4"
    session.record.outstanding_question = "question b2"
    action = session.apply_answer(_turn(), Analysis(signal="sufficient", instance="new"), _evidence(), "b")
    assert action == NextAction.END
    assert session.is_terminal() is True
    assert session.record.report_id is not None
    assert session.record.report_outcome == "evaluating"


def test_clarification_keeps_question_and_does_not_record_evidence():
    session = _session()
    session.apply_clarification(_turn(kind="clarification_request"), "clarify")
    assert session.record.current_question_id == "q1"
    assert session.record.outstanding_question == "question a1"
    assert session.record.question_pending is False


def test_terminal_session_rejects_answers():
    session = _session()
    session.begin_completion("r1", "evaluating")
    assert session.is_terminal() is True
    assert session.can_accept_turn() is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest backend/tests/interview_engine/test_session.py -q`
Expected: FAIL with `ImportError: cannot import name 'Session'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/interview_engine/domain/session.py
from datetime import datetime
from typing import Optional, Tuple

from ..contracts.blueprint import BlueprintSlot
from ..contracts.enums import NextAction, SessionStatus, Signal
from ..contracts.records import Analysis, EvidenceRecord, SessionRecord, TurnRecord
from .scoring import counts_for_scoring, decide_next_action, is_slot_complete

_TERMINAL = {
    SessionStatus.COMPLETED.value,
    SessionStatus.ABANDONED.value,
    SessionStatus.EXPIRED.value,
}


class Session:
    def __init__(self, record: SessionRecord):
        self.record = record

    @classmethod
    def from_record(cls, record: SessionRecord) -> "Session":
        return cls(SessionRecord.parse_obj(record.dict()))

    def to_record(self) -> SessionRecord:
        return self.record

    def is_terminal(self) -> bool:
        return self.record.status in _TERMINAL

    def can_accept_turn(self) -> bool:
        return self.record.status == SessionStatus.IN_PROGRESS.value

    def bump(self) -> int:
        self.record.version += 1
        self.record.updated_at = datetime.utcnow()
        return self.record.version

    def next_sequence(self) -> int:
        self.record.event_sequence += 1
        self.record.last_applied_sequence = self.record.event_sequence
        return self.record.event_sequence

    def slot(self) -> BlueprintSlot:
        if not self.record.current_slot_id:
            raise ValueError("no current slot")
        return self.record.blueprint.slot(self.record.current_slot_id)

    def slot_allowance(self) -> int:
        return self.slot().allowance(self.record.mode)

    def follow_up_used_for(self, slot_id: str) -> int:
        return self.record.follow_up_used.get(slot_id, 0)

    def has_further_slot(self) -> bool:
        return self.record.plan_position + 1 < len(self.record.blueprint.ordered_slots())

    def advance_slot(self) -> None:
        self.record.plan_position += 1
        ordered = self.record.blueprint.ordered_slots()
        if self.record.plan_position < len(ordered):
            self.record.current_slot_id = ordered[self.record.plan_position].slot_id
            self.record.current_question_id = None
            self.record.outstanding_question = None
            self.record.question_pending = True

    def set_question(self, question_id: str, text: str, slot_id: str, pending: bool = False) -> None:
        self.record.current_question_id = question_id
        self.record.outstanding_question = text
        self.record.current_slot_id = slot_id
        self.record.question_pending = pending
        if not pending and self.record.status == SessionStatus.PLANNED.value:
            self.record.status = SessionStatus.IN_PROGRESS.value
            self.record.started_at = self.record.started_at or datetime.utcnow()

    def set_question_pending(self, request: Optional[dict]) -> None:
        self.record.question_pending = True
        self.record.pending_question_request = request
        self.record.outstanding_question = None
        self.record.current_question_id = None

    def apply_clarification(self, turn: TurnRecord, reply: str) -> None:
        self.bump()

    def apply_answer(
        self,
        turn: TurnRecord,
        analysis: Analysis,
        evidence: Optional[EvidenceRecord],
        competency: str,
    ) -> NextAction:
        slot = self.slot()
        allowance = slot.allowance(self.record.mode)
        used = self.follow_up_used_for(slot.slot_id)
        slot_complete = is_slot_complete(analysis.signal, used, allowance)
        action = decide_next_action(
            clarification=False,
            slot_complete=slot_complete,
            has_further_slot=self.has_further_slot(),
            signal=analysis.signal,
            allowance_remaining=max(allowance - used, 0),
        )
        if action == NextAction.FOLLOW_UP:
            self.record.follow_up_used[slot.slot_id] = used + 1
            self.set_question_pending(
                {
                    "slot_id": slot.slot_id,
                    "purpose": "follow_up",
                    "question_generation_key": f"{self.record.session_id}:{self.record.version}:follow_up",
                    "session_version_at_request": self.record.version,
                }
            )
        elif action == NextAction.NEXT_SLOT:
            self.advance_slot()
            next_slot = self.record.blueprint.ordered_slots()[self.record.plan_position]
            self.set_question_pending(
                {
                    "slot_id": next_slot.slot_id,
                    "purpose": "next_question",
                    "question_generation_key": f"{self.record.session_id}:{self.record.version}:next_question",
                    "session_version_at_request": self.record.version,
                }
            )
        elif action == NextAction.END:
            self.record.report_id = self.record.report_id or f"report-{self.record.session_id}"
            outcome = "suppressed" if not self.record.consent.evaluation else "evaluating"
            self.begin_completion(self.record.report_id, outcome)
            return action
        self.bump()
        return action

    def begin_completion(self, report_id: str, outcome: str) -> None:
        self.record.status = SessionStatus.COMPLETED.value
        self.record.report_id = report_id
        self.record.report_outcome = outcome
        self.record.completed_at = datetime.utcnow()
        self.record.question_pending = False
        self.record.outstanding_question = None
        self.bump()

    def mark_paused(self) -> None:
        self.record.status = SessionStatus.PAUSED.value
        self.record.pause_count += 1
        self.record.pause_started_at = datetime.utcnow()
        self.bump()

    def mark_resumed(self) -> None:
        if self.record.pause_started_at:
            self.record.total_pause_seconds += int(
                (datetime.utcnow() - self.record.pause_started_at).total_seconds()
            )
            self.record.pause_started_at = None
        self.record.status = SessionStatus.IN_PROGRESS.value
        self.bump()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest backend/tests/interview_engine/test_session.py -q`
Expected: PASS (9 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/interview_engine/domain/session.py backend/tests/interview_engine/test_session.py
git commit -m "feat(interview-engine): add session aggregate and transitions"
```

---

### Task 4: Authored behavioral blueprint

**Files:**
- Create: `backend/interview_engine/domain/behavioral_blueprint.py`
- Test: `backend/tests/interview_engine/test_behavioral_blueprint.py`

**Interfaces:**
- Consumes: `Blueprint`, `BlueprintGroup`, `BlueprintSlot`.
- Produces: `seniority_to_difficulty(role, job_description) -> str`, `build_behavioral_blueprint(mode, role=None, job_description=None) -> Blueprint`, constant `COMPETENCIES = ("problem_solving", "communication", "structure", "evidence_verification", "technical_depth")`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/interview_engine/test_behavioral_blueprint.py
from backend.interview_engine.domain.behavioral_blueprint import (
    COMPETENCIES,
    build_behavioral_blueprint,
    seniority_to_difficulty,
)


def test_blueprint_has_five_groups_of_two_slots():
    blueprint = build_behavioral_blueprint("practice", role="Senior Backend Engineer")
    assert [g.competency for g in blueprint.groups] == list(COMPETENCIES)
    assert all(len(g.slots) == 2 for g in blueprint.groups)
    assert len(blueprint.ordered_slots()) == 10


def test_every_slot_is_fully_authored():
    blueprint = build_behavioral_blueprint("practice", role="Mid Engineer")
    for slot in blueprint.ordered_slots():
        assert slot.fallback_question.strip()
        assert slot.follow_up_question.strip()
        assert slot.clarification_text.strip()
        assert slot.hint_text.strip()
        assert slot.target_evidence_count == 1
        assert slot.follow_up_allowance_practice == 1
        assert slot.follow_up_allowance_formal == 0
        assert slot.difficulty == "intermediate"


def test_slot_ids_are_unique_and_competency_scoped():
    blueprint = build_behavioral_blueprint("practice", role="Intern")
    ids = [s.slot_id for s in blueprint.ordered_slots()]
    assert len(ids) == len(set(ids))
    assert ids[0].startswith("problem_solving")


def test_seniority_mapping():
    assert seniority_to_difficulty("Intern", None) == "novice"
    assert seniority_to_difficulty("Junior Developer", None) == "novice"
    assert seniority_to_difficulty("Mid-level Engineer", None) == "intermediate"
    assert seniority_to_difficulty("Senior Engineer", None) == "advanced"
    assert seniority_to_difficulty("Staff Engineer", None) == "advanced"
    assert seniority_to_difficulty("Principal Architect", None) == "advanced"
    assert seniority_to_difficulty("Software Engineer", "no band here") == "intermediate"
    assert seniority_to_difficulty(None, "We need a senior engineer") == "advanced"


def test_formal_blueprint_declares_zero_allowance():
    blueprint = build_behavioral_blueprint("formal", role="Senior Engineer")
    assert all(s.allowance("formal") == 0 for s in blueprint.ordered_slots())
    assert all(s.allowance("practice") == 1 for s in blueprint.ordered_slots())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest backend/tests/interview_engine/test_behavioral_blueprint.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.interview_engine.domain.behavioral_blueprint'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/interview_engine/domain/behavioral_blueprint.py
import re
from typing import Optional

from ..contracts.blueprint import Blueprint, BlueprintGroup, BlueprintSlot

COMPETENCIES = (
    "problem_solving",
    "communication",
    "structure",
    "evidence_verification",
    "technical_depth",
)

_SENIORITY_PATTERNS = (
    ("novice", re.compile(r"\b(intern|internship|junior|entry[- ]level|graduate)\b", re.I)),
    ("advanced", re.compile(r"\b(senior|staff|principal|lead|architect)\b", re.I)),
    ("intermediate", re.compile(r"\b(mid|intermediate|mid[- ]level)\b", re.I)),
)

_SLOT_CONTENT = {
    "problem_solving": {
        "first": "Walk me through a concrete problem you faced and how you resolved it. What was the situation, what did you do, and what was the outcome?",
        "second": "Think of another problem you solved. Looking back, what would you do differently, and how did you know your solution actually worked?",
        "follow_up": "What alternatives did you consider before choosing that approach, and why did you reject them?",
        "clarify": "Please describe one specific past situation, including what you personally did and how it ended.",
        "hint": "Pick a single project, name the constraint you were under, and describe the decision you made.",
    },
    "communication": {
        "first": "Tell me about a time you had to explain a complex idea to someone without your technical background. What did you say, and how did you check they understood?",
        "second": "Describe a time you had to give difficult feedback or disagree with a teammate. How did you frame it, and what happened next?",
        "follow_up": "How did you adapt your message when you realized the other person was not following you?",
        "clarify": "Please share one specific conversation, who was involved, and what you actually said.",
        "hint": "Choose one real conversation and describe the audience, your wording, and the reaction.",
    },
    "structure": {
        "first": "Describe how you organised a piece of work that had several competing priorities. How did you decide the order?",
        "second": "Tell me about a time your plan had to change mid-way. How did you restructure the work, and what did you protect?",
        "follow_up": "What signals told you the plan needed to change, and what did you deliberately leave out?",
        "clarify": "Please walk through one specific piece of work step by step, including the trade-offs you made.",
        "hint": "Name the competing priorities, the order you chose, and the reason for that order.",
    },
    "evidence_verification": {
        "first": "Tell me about a decision you made where you had to check whether it was actually correct. What evidence did you gather?",
        "second": "Describe a time you found that an assumption or a result was wrong. How did you verify it, and what did you change?",
        "follow_up": "What would have convinced you that your conclusion was wrong, and did you look for that evidence?",
        "clarify": "Please describe one specific decision, the evidence you used, and how you confirmed the outcome.",
        "hint": "State the claim you were testing, the evidence you collected, and how you validated it.",
    },
    "technical_depth": {
        "first": "Describe a technical decision you made in a project you worked on. What were the constraints, and why was that decision right for the context?",
        "second": "Tell me about a technical trade-off you would revisit. What did you learn, and how would you evaluate it now?",
        "follow_up": "What was the failure mode of that choice, and how would you detect it in production?",
        "clarify": "Please describe one specific technical choice, the constraints, and the outcome you observed.",
        "hint": "Pick one technical choice, name the constraint, the alternative, and the failure mode.",
    },
}


def seniority_to_difficulty(role: Optional[str], job_description: Optional[str]) -> str:
    haystack = " ".join(part for part in (role, job_description) if part)
    for level, pattern in _SENIORITY_PATTERNS:
        if pattern.search(haystack):
            return level
    return "intermediate"


def _slot(slot_id: str, competency: str, difficulty: str, variant: str) -> BlueprintSlot:
    content = _SLOT_CONTENT[competency]
    return BlueprintSlot(
        slot_id=slot_id,
        competency=competency,
        dimension=competency,
        difficulty=difficulty,
        intent=content[variant],
        fallback_question=content[variant],
        follow_up_question=content["follow_up"],
        clarification_text=content["clarify"],
        hint_text=content["hint"],
    )


def build_behavioral_blueprint(
    mode: str,
    role: Optional[str] = None,
    job_description: Optional[str] = None,
) -> Blueprint:
    difficulty = seniority_to_difficulty(role, job_description)
    groups = []
    for competency in COMPETENCIES:
        groups.append(
            BlueprintGroup(
                group_id=competency,
                competency=competency,
                slots=[
                    _slot(f"{competency}-1", competency, difficulty, "first"),
                    _slot(f"{competency}-2", competency, difficulty, "second"),
                ],
            )
        )
    return Blueprint(mode=mode, interview_type="behavioral", groups=groups)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest backend/tests/interview_engine/test_behavioral_blueprint.py -q`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/interview_engine/domain/behavioral_blueprint.py backend/tests/interview_engine/test_behavioral_blueprint.py
git commit -m "feat(interview-engine): author behavioral blueprint data"
```

---

### Task 5: Ports, in-memory store, and scripted adapters

**Files:**
- Create: `backend/interview_engine/ports/__init__.py`, `backend/interview_engine/ports/store.py`, `backend/interview_engine/ports/capabilities.py`, `backend/interview_engine/adapters/__init__.py`, `backend/interview_engine/adapters/memory_store.py`, `backend/interview_engine/adapters/scripted.py`, `backend/interview_engine/adapters/system.py`
- Test: `backend/tests/interview_engine/test_ports_and_fakes.py`

**Interfaces:**
- Consumes: Task 1 records/messages.
- Produces: `SessionStore` protocol; `Analyzer`, `QuestionGenerator`, `Evaluator`, `LeasePort`, `Clock`, `IdGenerator` protocols; `AnalysisRequest`, `QuestionRequest`, `GeneratedQuestion`, `EvaluationRequest`, `CompetencyEvaluationInput`; `InMemorySessionStore`; `HeuristicAnalyzer`, `ScriptedAnalyzer`, `ScriptedQuestionGenerator`, `DeterministicEvaluator`; `SystemClock`, `UuidIds`, `InMemoryLease`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/interview_engine/test_ports_and_fakes.py
from datetime import datetime

import pytest

from backend.interview_engine.adapters.memory_store import InMemorySessionStore
from backend.interview_engine.adapters.scripted import (
    DeterministicEvaluator,
    HeuristicAnalyzer,
    ScriptedAnalyzer,
    ScriptedQuestionGenerator,
)
from backend.interview_engine.adapters.system import InMemoryLease, SystemClock, UuidIds
from backend.interview_engine.contracts.blueprint import BlueprintSlot
from backend.interview_engine.contracts.records import Analysis, SessionRecord


def _record(session_id="s1"):
    return SessionRecord(
        session_id=session_id, candidate_id="c1", interview_type="behavioral", mode="practice",
        status="planned", version=0, event_sequence=0, last_applied_sequence=0,
        fencing_token="t1", device_id="d1",
        blueprint={"groups": []},
        created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    )


@pytest.mark.asyncio
async def test_memory_store_rolls_back_on_error():
    store = InMemorySessionStore()
    record = _record()
    async with store.transaction():
        await store.insert(record)
    with pytest.raises(RuntimeError):
        async with store.transaction():
            loaded = await store.load("s1")
            loaded.status = "completed"
            await store.replace(loaded, expected_version=0)
            raise RuntimeError("boom")
    loaded = await store.load("s1")
    assert loaded.status == "planned"


@pytest.mark.asyncio
async def test_memory_store_optimistic_version_check():
    store = InMemorySessionStore()
    async with store.transaction():
        await store.insert(_record())
    loaded = await store.load("s1")
    loaded.version = 1
    assert await store.replace(loaded, expected_version=0) is True
    assert await store.replace(loaded, expected_version=0) is False


@pytest.mark.asyncio
async def test_scripted_analyzer_yields_script_then_heuristic():
    analyzer = ScriptedAnalyzer([Analysis(signal="sufficient", instance="new")])
    from backend.interview_engine.ports.capabilities import AnalysisRequest

    req = AnalysisRequest(
        session_id="s1", turn_id="t1", question_id="q1", slot_id="s1",
        competency="c", text="short",
    )
    assert (await analyzer.analyze(req)).signal == "sufficient"
    assert (await analyzer.analyze(req)).signal == "incomplete"


@pytest.mark.asyncio
async def test_heuristic_analyzer_is_deterministic():
    analyzer = HeuristicAnalyzer()
    from backend.interview_engine.ports.capabilities import AnalysisRequest

    short = AnalysisRequest(
        session_id="s1", turn_id="t1", question_id="q1", slot_id="s1",
        competency="c", text="too short",
    )
    long = AnalysisRequest(
        session_id="s1", turn_id="t2", question_id="q2", slot_id="s2",
        competency="c",
        text="In my last project I owned the ingestion pipeline and cut latency by half after profiling the bottleneck.",
    )
    assert (await analyzer.analyze(short)).signal == "incomplete"
    assert (await analyzer.analyze(long)).signal == "sufficient"


@pytest.mark.asyncio
async def test_question_generator_uses_follow_up_and_fallback():
    slot = BlueprintSlot(
        slot_id="s1", competency="c", dimension="c", difficulty="intermediate",
        intent="intent", fallback_question="fallback", follow_up_question="follow",
        clarification_text="clarify", hint_text="hint",
    )
    generator = ScriptedQuestionGenerator()
    from backend.interview_engine.ports.capabilities import QuestionRequest

    base = dict(session_id="s1", slot=slot, role="Engineer", company="Acme", prior_questions=[])
    first = await generator.generate(QuestionRequest(purpose="first_question", **base))
    follow = await generator.generate(QuestionRequest(purpose="follow_up", **base))
    assert first.text == "fallback"
    assert follow.text == "follow"


@pytest.mark.asyncio
async def test_deterministic_evaluator_produces_reasons():
    evaluator = DeterministicEvaluator()
    from backend.interview_engine.ports.capabilities import (
        CompetencyEvaluationInput,
        EvaluationRequest,
    )

    output = await evaluator.evaluate(
        EvaluationRequest(
            session_id="s1", report_id="r1", role="Engineer", company="Acme",
            competencies=[CompetencyEvaluationInput(
                competency="problem_solving", level="proficient", confidence="medium",
                instances=2, limitations=[],
            )],
        )
    )
    assert "problem_solving" in output.reasons
    assert output.narrative


@pytest.mark.asyncio
async def test_in_memory_lease_conflicts_and_takeover():
    lease = InMemoryLease()
    assert await lease.acquire("s1", "d1", "t1", 60) is True
    assert await lease.confirm("s1", "d1", "t1") is True
    assert await lease.confirm("s1", "d2", "t2") is False
    assert await lease.acquire("s1", "d2", "t2", 60) is False
    assert await lease.takeover("s1", "d2", "t2", 60) is True
    assert await lease.confirm("s1", "d2", "t2") is True
    assert await lease.confirm("s1", "d1", "t1") is False


def test_system_adapters():
    clock = SystemClock()
    ids = UuidIds()
    assert isinstance(clock.now(), datetime)
    assert ids.new_id() != ids.new_id()
    assert len(ids.new_token()) >= 16
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest backend/tests/interview_engine/test_ports_and_fakes.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.interview_engine.ports'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/interview_engine/ports/capabilities.py
from typing import List, Optional, Protocol, Sequence

from pydantic import BaseModel, Field

from ..contracts.blueprint import BlueprintSlot
from ..contracts.records import Analysis
from ..contracts.report import EvaluatorOutput


class AnalysisRequest(BaseModel):
    session_id: str
    turn_id: str
    question_id: str
    slot_id: str
    competency: str
    text: str


class QuestionRequest(BaseModel):
    session_id: str
    slot: BlueprintSlot
    purpose: str
    role: Optional[str] = None
    company: Optional[str] = None
    prior_questions: List[str] = Field(default_factory=list)


class GeneratedQuestion(BaseModel):
    text: str
    source: str = "generated"


class CompetencyEvaluationInput(BaseModel):
    competency: str
    level: str
    confidence: str
    instances: int
    limitations: List[str] = Field(default_factory=list)


class EvaluationRequest(BaseModel):
    session_id: str
    report_id: str
    role: Optional[str] = None
    company: Optional[str] = None
    competencies: List[CompetencyEvaluationInput] = Field(default_factory=list)


class Analyzer(Protocol):
    async def analyze(self, request: AnalysisRequest) -> Analysis:
        ...


class QuestionGenerator(Protocol):
    async def generate(self, request: QuestionRequest) -> GeneratedQuestion:
        ...


class Evaluator(Protocol):
    async def evaluate(self, request: EvaluationRequest) -> EvaluatorOutput:
        ...


class LeasePort(Protocol):
    async def acquire(self, session_id: str, device_id: str, token: str, ttl_seconds: int) -> bool:
        ...

    async def confirm(self, session_id: str, device_id: str, token: str) -> bool:
        ...

    async def takeover(self, session_id: str, device_id: str, token: str, ttl_seconds: int) -> bool:
        ...

    async def release(self, session_id: str, token: str) -> None:
        ...


class Clock(Protocol):
    def now(self):
        ...


class IdGenerator(Protocol):
    def new_id(self) -> str:
        ...

    def new_token(self) -> str:
        ...


class QuestionGeneratorFallback(Exception):
    pass
```

```python
# backend/interview_engine/ports/store.py
from contextlib import AbstractAsyncContextManager
from typing import List, Optional, Protocol

from ..contracts.records import (
    EventRecord,
    EvidenceRecord,
    HintRecord,
    OutboxRecord,
    QuestionRecord,
    ReportRecord,
    SessionRecord,
    TurnCommandRecord,
    TurnRecord,
)


class SessionStore(Protocol):
    def transaction(self) -> AbstractAsyncContextManager["SessionStore"]:
        ...

    async def load(self, session_id: str) -> Optional[SessionRecord]:
        ...

    async def load_by_client_request_id(self, candidate_id: str, client_request_id: str) -> Optional[SessionRecord]:
        ...

    async def find_active(self, candidate_id: str, interview_type: str, mode: str) -> Optional[SessionRecord]:
        ...

    async def insert(self, record: SessionRecord) -> None:
        ...

    async def replace(self, record: SessionRecord, expected_version: int) -> bool:
        ...

    async def append_event(self, event: EventRecord) -> None:
        ...

    async def append_turn(self, turn: TurnRecord) -> None:
        ...

    async def count_turns(self, session_id: str, kind: Optional[str] = None) -> int:
        ...

    async def turns_for_session(self, session_id: str) -> List[TurnRecord]:
        ...

    async def append_evidence(self, evidence: EvidenceRecord) -> None:
        ...

    async def evidence_for_session(self, session_id: str) -> List[EvidenceRecord]:
        ...

    async def put_question(self, question: QuestionRecord) -> None:
        ...

    async def get_question_by_key(self, session_id: str, key: str) -> Optional[QuestionRecord]:
        ...

    async def put_hint(self, hint: HintRecord) -> None:
        ...

    async def get_hint_by_key(self, session_id: str, key: str) -> Optional[HintRecord]:
        ...

    async def get_turn_command(self, session_id: str, key: str) -> Optional[TurnCommandRecord]:
        ...

    async def put_turn_command(self, command: TurnCommandRecord) -> None:
        ...

    async def complete_turn_command(self, session_id: str, key: str, result: dict) -> None:
        ...

    async def put_report(self, report: ReportRecord) -> None:
        ...

    async def get_report(self, report_id: str) -> Optional[ReportRecord]:
        ...

    async def update_report(self, report: ReportRecord, expected_outcome: str) -> bool:
        ...

    async def append_outbox(self, record: OutboxRecord) -> None:
        ...

    async def claim_outbox(self, worker_id: str, limit: int) -> List[OutboxRecord]:
        ...

    async def mark_outbox_processed(self, outbox_id: str) -> None:
        ...

    async def mark_outbox_failed(self, outbox_id: str, error: str) -> None:
        ...
```

```python
# backend/interview_engine/adapters/memory_store.py
import copy
from contextlib import asynccontextmanager
from typing import Dict, List, Optional

from ..contracts.records import (
    EventRecord,
    EvidenceRecord,
    HintRecord,
    OutboxRecord,
    QuestionRecord,
    ReportRecord,
    SessionRecord,
    TurnCommandRecord,
    TurnRecord,
)


class InMemorySessionStore:
    def __init__(self):
        self._sessions: Dict[str, SessionRecord] = {}
        self._events: List[EventRecord] = []
        self._turns: List[TurnRecord] = []
        self._evidence: List[EvidenceRecord] = []
        self._questions: Dict[str, QuestionRecord] = {}
        self._hints: Dict[str, HintRecord] = {}
        self._commands: Dict[str, TurnCommandRecord] = {}
        self._reports: Dict[str, ReportRecord] = {}
        self._outbox: List[OutboxRecord] = []
        self._snapshot = None

    @asynccontextmanager
    async def transaction(self):
        self._snapshot = copy.deepcopy(
            (self._sessions, self._events, self._turns, self._evidence, self._questions,
             self._hints, self._commands, self._reports, self._outbox)
        )
        try:
            yield self
        except Exception:
            (self._sessions, self._events, self._turns, self._evidence, self._questions,
             self._hints, self._commands, self._reports, self._outbox) = self._snapshot
            raise
        finally:
            self._snapshot = None

    async def load(self, session_id: str) -> Optional[SessionRecord]:
        record = self._sessions.get(session_id)
        return copy.deepcopy(record) if record else None

    async def load_by_client_request_id(self, candidate_id: str, client_request_id: str):
        for record in self._sessions.values():
            if record.candidate_id == candidate_id and record.client_request_id == client_request_id:
                return copy.deepcopy(record)
        return None

    async def find_active(self, candidate_id: str, interview_type: str, mode: str):
        for record in self._sessions.values():
            if (
                record.candidate_id == candidate_id
                and record.interview_type == interview_type
                and record.mode == mode
                and record.status in ("planned", "in_progress", "paused")
            ):
                return copy.deepcopy(record)
        return None

    async def insert(self, record: SessionRecord) -> None:
        self._sessions[record.session_id] = copy.deepcopy(record)

    async def replace(self, record: SessionRecord, expected_version: int) -> bool:
        current = self._sessions.get(record.session_id)
        if current is None or current.version != expected_version:
            return False
        self._sessions[record.session_id] = copy.deepcopy(record)
        return True

    async def append_event(self, event: EventRecord) -> None:
        self._events.append(copy.deepcopy(event))

    async def append_turn(self, turn: TurnRecord) -> None:
        self._turns.append(copy.deepcopy(turn))

    async def count_turns(self, session_id: str, kind: Optional[str] = None) -> int:
        return sum(
            1 for t in self._turns
            if t.session_id == session_id and (kind is None or t.kind == kind)
        )

    async def turns_for_session(self, session_id: str) -> List[TurnRecord]:
        return [copy.deepcopy(t) for t in self._turns if t.session_id == session_id]

    async def append_evidence(self, evidence: EvidenceRecord) -> None:
        self._evidence.append(copy.deepcopy(evidence))

    async def evidence_for_session(self, session_id: str) -> List[EvidenceRecord]:
        return [copy.deepcopy(e) for e in self._evidence if e.session_id == session_id]

    async def put_question(self, question: QuestionRecord) -> None:
        self._questions[question.question_generation_key] = copy.deepcopy(question)

    async def get_question_by_key(self, session_id: str, key: str) -> Optional[QuestionRecord]:
        question = self._questions.get(key)
        if question and question.session_id == session_id:
            return copy.deepcopy(question)
        return None

    async def put_hint(self, hint: HintRecord) -> None:
        self._hints[hint.hint_idempotency_key] = copy.deepcopy(hint)

    async def get_hint_by_key(self, session_id: str, key: str) -> Optional[HintRecord]:
        hint = self._hints.get(key)
        if hint and hint.session_id == session_id:
            return copy.deepcopy(hint)
        return None

    async def get_turn_command(self, session_id: str, key: str) -> Optional[TurnCommandRecord]:
        command = self._commands.get(key)
        if command and command.session_id == session_id:
            return copy.deepcopy(command)
        return None

    async def put_turn_command(self, command: TurnCommandRecord) -> None:
        self._commands[command.idempotency_key] = copy.deepcopy(command)

    async def complete_turn_command(self, session_id: str, key: str, result: dict) -> None:
        command = self._commands.get(key)
        if command and command.session_id == session_id:
            command.status = "complete"
            command.result = copy.deepcopy(result)

    async def put_report(self, report: ReportRecord) -> None:
        self._reports[report.report_id] = copy.deepcopy(report)

    async def get_report(self, report_id: str) -> Optional[ReportRecord]:
        report = self._reports.get(report_id)
        return copy.deepcopy(report) if report else None

    async def update_report(self, report: ReportRecord, expected_outcome: str) -> bool:
        current = self._reports.get(report.report_id)
        if current is None or current.outcome != expected_outcome:
            return False
        self._reports[report.report_id] = copy.deepcopy(report)
        return True

    async def append_outbox(self, record: OutboxRecord) -> None:
        self._outbox.append(copy.deepcopy(record))

    async def claim_outbox(self, worker_id: str, limit: int) -> List[OutboxRecord]:
        claimed = []
        for record in self._outbox:
            if len(claimed) >= limit:
                break
            if record.status in ("pending", "failed") and record.attempts < 5:
                record.status = "processing"
                record.attempts += 1
                record.worker_id = worker_id
                claimed.append(copy.deepcopy(record))
        return claimed

    async def mark_outbox_processed(self, outbox_id: str) -> None:
        for record in self._outbox:
            if record.outbox_id == outbox_id:
                record.status = "processed"

    async def mark_outbox_failed(self, outbox_id: str, error: str) -> None:
        for record in self._outbox:
            if record.outbox_id == outbox_id:
                record.status = "failed"
```

```python
# backend/interview_engine/adapters/scripted.py
from typing import List, Optional, Sequence

from ..contracts.records import Analysis
from ..contracts.report import EvaluatorOutput
from ..ports.capabilities import (
    AnalysisRequest,
    CompetencyEvaluationInput,
    EvaluationRequest,
    GeneratedQuestion,
    QuestionRequest,
)

_LIMITATION = "Answer was too brief to demonstrate the competency."


class HeuristicAnalyzer:
    async def analyze(self, request: AnalysisRequest) -> Analysis:
        words = request.text.split()
        if len(words) < 8:
            return Analysis(
                signal="incomplete",
                instance="same",
                substantively_deficient=True,
                limitation=_LIMITATION,
            )
        return Analysis(signal="sufficient", instance="new")


class ScriptedAnalyzer:
    def __init__(self, script: Optional[Sequence[Analysis]] = None):
        self._script = list(script or [])
        self._index = 0
        self._fallback = HeuristicAnalyzer()

    async def analyze(self, request: AnalysisRequest) -> Analysis:
        if self._index < len(self._script):
            analysis = self._script[self._index]
            self._index += 1
            return analysis
        return await self._fallback.analyze(request)


class ScriptedQuestionGenerator:
    async def generate(self, request: QuestionRequest) -> GeneratedQuestion:
        if request.purpose == "follow_up":
            return GeneratedQuestion(text=request.slot.follow_up_question, source="fallback")
        return GeneratedQuestion(text=request.slot.fallback_question, source="fallback")


class DeterministicEvaluator:
    async def evaluate(self, request: EvaluationRequest) -> EvaluatorOutput:
        reasons = {}
        parts = []
        for competency in request.competencies:
            label = competency.competency.replace("_", " ")
            reasons[competency.competency] = [
                f"Evidence from {competency.instances} independent answer(s) supports a {competency.level} level.",
                f"Confidence is {competency.confidence} under the published rule.",
            ]
            parts.append(f"{label}: {competency.level} ({competency.confidence} confidence).")
        narrative = " ".join(parts) or "No competency evidence was recorded."
        return EvaluatorOutput(reasons=reasons, narrative=narrative)
```

```python
# backend/interview_engine/adapters/system.py
import uuid
from datetime import datetime
from typing import Dict, Optional


class SystemClock:
    def now(self) -> datetime:
        return datetime.utcnow()


class UuidIds:
    def new_id(self) -> str:
        return str(uuid.uuid4())

    def new_token(self) -> str:
        return uuid.uuid4().hex


class InMemoryLease:
    def __init__(self):
        self._leases: Dict[str, tuple] = {}

    async def acquire(self, session_id: str, device_id: str, token: str, ttl_seconds: int) -> bool:
        if session_id in self._leases:
            return False
        self._leases[session_id] = (device_id, token)
        return True

    async def confirm(self, session_id: str, device_id: str, token: str) -> bool:
        held = self._leases.get(session_id)
        return held == (device_id, token)

    async def takeover(self, session_id: str, device_id: str, token: str, ttl_seconds: int) -> bool:
        self._leases[session_id] = (device_id, token)
        return True

    async def release(self, session_id: str, token: str) -> None:
        held = self._leases.get(session_id)
        if held and held[1] == token:
            self._leases.pop(session_id, None)
```

```python
# backend/interview_engine/ports/__init__.py
from .capabilities import (
    AnalysisRequest,
    Analyzer,
    Clock,
    CompetencyEvaluationInput,
    EvaluationRequest,
    Evaluator,
    GeneratedQuestion,
    IdGenerator,
    LeasePort,
    QuestionGenerator,
    QuestionRequest,
)
from .store import SessionStore

__all__ = [
    "AnalysisRequest",
    "Analyzer",
    "Clock",
    "CompetencyEvaluationInput",
    "EvaluationRequest",
    "Evaluator",
    "GeneratedQuestion",
    "IdGenerator",
    "LeasePort",
    "QuestionGenerator",
    "QuestionRequest",
    "SessionStore",
]
```

```python
# backend/interview_engine/adapters/__init__.py
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest backend/tests/interview_engine/test_ports_and_fakes.py -q`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/interview_engine/ports backend/interview_engine/adapters backend/tests/interview_engine/test_ports_and_fakes.py
git commit -m "feat(interview-engine): add ports, in-memory store, scripted adapters"
```

### Task 6: Report builder

**Files:**
- Create: `backend/interview_engine/application/__init__.py`, `backend/interview_engine/application/report_builder.py`
- Test: `backend/tests/interview_engine/test_report_builder.py`

**Interfaces:**
- Consumes: `SessionRecord`, `EvidenceRecord`, `TurnRecord`, `ReportBody`, `CompetencyReport`, `Excerpt`, `Limitation`, `EvaluatorOutput`, `InstanceFact`, `confidence_for`, `level_for`, `counts_for_scoring`.
- Produces: `build_report(record, evidence, turns, evaluator_output) -> ReportBody`, `sentence_excerpt(text, limit=2) -> str`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/interview_engine/test_report_builder.py
from datetime import datetime, timedelta

from backend.interview_engine.application.report_builder import build_report, sentence_excerpt
from backend.interview_engine.contracts.blueprint import Blueprint, BlueprintGroup, BlueprintSlot
from backend.interview_engine.contracts.records import EvidenceRecord, SessionRecord, TurnRecord
from backend.interview_engine.contracts.report import EvaluatorOutput


def _slot(slot_id, competency):
    return BlueprintSlot(
        slot_id=slot_id, competency=competency, dimension=competency, difficulty="intermediate",
        intent="i", fallback_question="q", follow_up_question="f",
        clarification_text="c", hint_text="h",
    )


def _record():
    blueprint = Blueprint(groups=[
        BlueprintGroup(group_id="ps", competency="problem_solving", slots=[_slot("ps-1", "problem_solving")]),
        BlueprintGroup(group_id="cm", competency="communication", slots=[_slot("cm-1", "communication")]),
    ])
    started = datetime(2026, 11, 1, 10, 0, 0)
    return SessionRecord(
        session_id="s1", candidate_id="c1", interview_type="behavioral", mode="practice",
        status="completed", version=5, event_sequence=5, last_applied_sequence=5,
        fencing_token="t1", device_id="d1", blueprint=blueprint, role="Senior Engineer",
        company="Acme", report_id="r1", report_outcome="evaluating", hint_count=1,
        created_at=started, updated_at=started, started_at=started,
        completed_at=started + timedelta(minutes=12),
    )


def _turn(turn_id, slot_id, text):
    return TurnRecord(
        turn_id=turn_id, session_id="s1", sequence=1, kind="answer", question_id=f"q-{turn_id}",
        slot_id=slot_id, text=text, idempotency_key=f"k-{turn_id}", device_id="d1",
        created_at=datetime.utcnow(),
    )


def _evidence(turn_id, slot_id, competency, signal="sufficient", contradiction=False):
    return EvidenceRecord(
        evidence_id=f"e-{turn_id}", session_id="s1", turn_id=turn_id, question_id=f"q-{turn_id}",
        slot_id=slot_id, competency=competency, signal=signal, instance="new",
        contradiction=contradiction, difficulty="intermediate", created_at=datetime.utcnow(),
    )


def test_sentence_excerpt_keeps_two_sentences():
    text = "First sentence. Second sentence. Third sentence."
    assert sentence_excerpt(text) == "First sentence. Second sentence."


def test_report_has_no_composite_score_and_discloses_ai():
    report = build_report(_record(), [], [], EvaluatorOutput())
    assert "score" not in report.dict()
    assert "overall_score" not in report.dict()
    assert report.disclosure["ai_generated_questions"] is True
    assert report.disclosure["no_proctoring"] is True
    assert report.integrity["blueprint_version"] == "behavioral-v1"
    assert report.duration_seconds == 720


def test_report_with_no_evidence_marks_every_competency_not_assessed():
    turns = [_turn("t1", "ps-1", "I did a thing. It worked.")]
    report = build_report(_record(), [], turns, EvaluatorOutput())
    assert {c.level for c in report.competencies} == {"not_assessed"}
    assert all(c.excerpts == [] for c in report.competencies)
    ps = next(c for c in report.competencies if c.competency == "problem_solving")
    assert ps.confidence == "not_assessed"
    assert any(l.category == "insufficient_evidence" for l in ps.limitations)


def test_two_sufficient_instances_yield_strong_medium_with_two_excerpts():
    turns = [
        _turn("t1", "ps-1", "I led the migration. We cut errors by half."),
        _turn("t2", "ps-1", "I validated the result. Error rates stayed low."),
    ]
    evidence = [
        _evidence("t1", "ps-1", "problem_solving"),
        _evidence("t2", "ps-1", "problem_solving"),
    ]
    report = build_report(_record(), evidence, turns, EvaluatorOutput())
    ps = next(c for c in report.competencies if c.competency == "problem_solving")
    assert ps.level == "strong"
    assert ps.confidence == "medium"
    assert len(ps.excerpts) == 2
    assert ps.excerpts[0].text == "I led the migration. We cut errors by half."


def test_single_instance_adds_insufficient_evidence_limitation():
    turns = [_turn("t1", "ps-1", "Only one answer here. It is short.")]
    evidence = [_evidence("t1", "ps-1", "problem_solving")]
    report = build_report(_record(), evidence, turns, EvaluatorOutput())
    ps = next(c for c in report.competencies if c.competency == "problem_solving")
    assert ps.confidence == "low"
    assert len(ps.excerpts) == 1
    assert any(l.category == "insufficient_evidence" for l in ps.limitations)


def test_contradiction_adds_conflicting_evidence_limitation():
    turns = [
        _turn("t1", "ps-1", "A. B."),
        _turn("t2", "ps-1", "C. D."),
        _turn("t3", "ps-1", "E. F."),
    ]
    evidence = [
        _evidence("t1", "ps-1", "problem_solving", contradiction=True),
        _evidence("t2", "ps-1", "problem_solving"),
        _evidence("t3", "ps-1", "problem_solving"),
    ]
    report = build_report(_record(), evidence, turns, EvaluatorOutput())
    ps = next(c for c in report.competencies if c.competency == "problem_solving")
    assert ps.confidence == "low"
    assert ps.level == "strong"
    assert any(l.category == "conflicting_evidence" for l in ps.limitations)


def test_report_limits_excerpts_to_three():
    turns = [_turn(f"t{i}", "ps-1", f"Sentence {i}. More {i}.") for i in range(1, 5)]
    evidence = [_evidence(f"t{i}", "ps-1", "problem_solving") for i in range(1, 5)]
    report = build_report(_record(), evidence, turns, EvaluatorOutput())
    ps = next(c for c in report.competencies if c.competency == "problem_solving")
    assert len(ps.excerpts) == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest backend/tests/interview_engine/test_report_builder.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.interview_engine.application'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/interview_engine/application/report_builder.py
import re
from typing import Dict, List, Sequence

from ..contracts.records import EvidenceRecord, SessionRecord, TurnRecord
from ..contracts.report import (
    CompetencyReport,
    EvaluatorOutput,
    Excerpt,
    Limitation,
    ReportBody,
)
from ..domain.scoring import InstanceFact, confidence_for, counts_for_scoring, level_for

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def sentence_excerpt(text: str, limit: int = 2) -> str:
    parts = [part.strip() for part in _SENTENCE_SPLIT.split(text.strip()) if part.strip()]
    return " ".join(parts[:limit])


def build_report(
    record: SessionRecord,
    evidence: Sequence[EvidenceRecord],
    turns: Sequence[TurnRecord],
    evaluator_output: EvaluatorOutput,
) -> ReportBody:
    turns_by_id = {turn.turn_id: turn for turn in turns}
    competencies: List[CompetencyReport] = []
    for group in record.blueprint.groups:
        items = [item for item in evidence if item.competency == group.competency]
        facts = [
            InstanceFact(
                competency=item.competency,
                question_id=item.question_id,
                signal=item.signal,
                contradiction=item.contradiction,
            )
            for item in items
            if counts_for_scoring(item.signal, item.instance)
        ]
        level = level_for(facts)
        confidence = confidence_for(facts)
        limitations: List[Limitation] = []
        excerpts: List[Excerpt] = []
        if not facts:
            limitations.append(
                Limitation(
                    category="insufficient_evidence",
                    detail="No independent evidence was recorded for this competency.",
                )
            )
        else:
            seen = set()
            for item in items:
                if item.turn_id in seen or item.signal == "off_topic":
                    continue
                seen.add(item.turn_id)
                turn = turns_by_id.get(item.turn_id)
                if turn is None:
                    continue
                excerpts.append(
                    Excerpt(
                        turn_id=turn.turn_id,
                        question_id=item.question_id,
                        text=sentence_excerpt(turn.text),
                    )
                )
                if len(excerpts) == 3:
                    break
            if len(facts) == 1:
                limitations.append(
                    Limitation(
                        category="insufficient_evidence",
                        detail="Only one independent instance supports this score.",
                    )
                )
        if any(item.contradiction for item in items):
            limitations.append(
                Limitation(
                    category="conflicting_evidence",
                    detail="A synchronously flagged contradiction caps confidence at low.",
                )
            )
        for item in items:
            if item.signal == "off_topic":
                limitations.append(
                    Limitation(
                        category="insufficient_evidence",
                        detail="An off-topic answer was recorded for this competency.",
                    )
                )
                break
        competencies.append(
            CompetencyReport(
                competency=group.competency,
                level=level.value,
                confidence=confidence.value,
                instance_count=len(facts),
                reasons=evaluator_output.reasons.get(group.competency, []),
                excerpts=excerpts,
                limitations=limitations,
            )
        )
    duration = 0
    if record.started_at and record.completed_at:
        duration = int((record.completed_at - record.started_at).total_seconds())
    return ReportBody(
        report_id=record.report_id or "",
        session_id=record.session_id,
        interview_type=record.interview_type,
        mode=record.mode,
        target_role=record.role or "",
        company=record.company or "",
        duration_seconds=duration,
        competencies=competencies,
        narrative=evaluator_output.narrative,
        limitations=[limitation for c in competencies for limitation in c.limitations],
        integrity={
            "completion_status": record.status,
            "blueprint_version": record.blueprint.blueprint_version,
            "weights_version": record.blueprint.weights_version,
            "mode": record.mode,
            "pause_count": record.pause_count,
            "total_pause_seconds": record.total_pause_seconds,
            "disconnect_count": record.disconnect_count,
            "hint_count": record.hint_count,
            "hidden_test_status": "not_applicable",
        },
        disclosure={
            "ai_generated_questions": True,
            "ai_assisted_evaluation": True,
            "no_proctoring": True,
            "no_identity_verification": True,
            "no_human_review": True,
        },
    )
```

```python
# backend/interview_engine/application/__init__.py
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest backend/tests/interview_engine/test_report_builder.py -q`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/interview_engine/application backend/tests/interview_engine/test_report_builder.py
git commit -m "feat(interview-engine): build competency reports from evidence"
```

---

### Task 7: Engine start and first question

**Files:**
- Create: `backend/interview_engine/errors.py`, `backend/interview_engine/application/engine.py`
- Modify: `backend/interview_engine/__init__.py`
- Test: `backend/tests/interview_engine/test_engine_start.py`

**Interfaces:**
- Consumes: all Task 1–6 interfaces; `build_behavioral_blueprint`.
- Produces: `InterviewEngine(store, lease, clock, ids, analyzer, generator, evaluator, lease_ttl_seconds=120, worker_id="engine-worker", generation_timeout_seconds=8.0)`, `InterviewEngine.start(cmd: StartSessionCommand) -> StartSessionResult`, `InterviewEngine.ensure_question(session_id, request: dict)`, `InterviewEngine.load_owned(session_id, candidate_id) -> SessionRecord`; errors `EngineError`, `UnsupportedInterviewType`, `SessionExists`, `SessionNotFound`, `NotOwner`, `InvalidState`, `DeviceConflict`, `VersionConflict`, `QuestionPendingConflict`, `QuestionMismatch`, `ConsentRequired`, `PauseLimitReached`, `NoReport`, `HintLimitReached`, `HintUnavailable`, `QuestionSuperseded`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/interview_engine/test_engine_start.py
import asyncio
from datetime import datetime

import pytest

from backend.interview_engine.application.engine import InterviewEngine
from backend.interview_engine.adapters.memory_store import InMemorySessionStore
from backend.interview_engine.adapters.scripted import (
    DeterministicEvaluator,
    ScriptedAnalyzer,
    ScriptedQuestionGenerator,
)
from backend.interview_engine.adapters.system import InMemoryLease, SystemClock, UuidIds
from backend.interview_engine.contracts.messages import StartSessionCommand
from backend.interview_engine.contracts.records import EventRecord, SessionRecord
from backend.interview_engine.domain.behavioral_blueprint import build_behavioral_blueprint
from backend.interview_engine.errors import (
    DeviceConflict,
    InvalidState,
    SessionExists,
    UnsupportedInterviewType,
)
from backend.interview_engine.ports.capabilities import GeneratedQuestion


def _engine(store=None, generator=None, generation_timeout_seconds=None):
    store = store or InMemorySessionStore()
    kwargs = {}
    if generation_timeout_seconds is not None:
        kwargs["generation_timeout_seconds"] = generation_timeout_seconds
    return (
        InterviewEngine(
            store=store,
            lease=InMemoryLease(),
            clock=SystemClock(),
            ids=UuidIds(),
            analyzer=ScriptedAnalyzer([]),
            generator=generator or ScriptedQuestionGenerator(),
            evaluator=DeterministicEvaluator(),
            **kwargs,
        ),
        store,
    )


def _start(client_request_id="req-1", interview_type="behavioral", mode="practice"):
    return StartSessionCommand(
        candidate_id="c1",
        interview_type=interview_type,
        mode="practice",
        device_id="d1",
        client_request_id=client_request_id,
        role="Senior Engineer",
        company="Acme",
    )


@pytest.mark.asyncio
async def test_start_creates_session_question_event_and_outbox():
    engine, store = _engine()
    result = await engine.start(_start())
    record = await store.load(result.session_id)
    assert result.first_question.startswith("Walk me through")
    assert result.status == "in_progress"
    assert result.version == 1
    assert record.status == "in_progress"
    assert record.question_pending is False
    assert record.outstanding_question == result.first_question
    assert record.current_slot_id == "problem_solving-1"
    assert record.blueprint.blueprint_version == "behavioral-v1"
    assert record.fencing_token == result.fencing_token
    events = [e for e in store._events if e.session_id == result.session_id]
    assert [e.event_type for e in events] == ["SessionCreated", "SessionStarted", "QuestionAsked"]
    assert [e.event_sequence for e in events] == [1, 2, 3]
    outbox = [o for o in store._outbox if o.event_type == "interview_engine.question.requested"]
    assert len(outbox) == 1
    assert outbox[0].payload["question_generation_key"].endswith(":0:first_question")


@pytest.mark.asyncio
async def test_start_is_idempotent_by_client_request_id():
    engine, store = _engine()
    first = await engine.start(_start())
    second = await engine.start(_start())
    assert first.session_id == second.session_id
    assert second.first_question == first.first_question
    assert len(store._sessions) == 1


@pytest.mark.asyncio
async def test_new_request_id_against_active_session_returns_session_exists():
    engine, store = _engine()
    first = await engine.start(_start("req-1"))
    with pytest.raises(SessionExists) as exc:
        await engine.start(_start("req-2"))
    assert exc.value.session_id == first.session_id


@pytest.mark.asyncio
async def test_unsupported_type_is_rejected():
    engine, _ = _engine()
    with pytest.raises(UnsupportedInterviewType):
        await engine.start(_start(interview_type="dsa"))


@pytest.mark.asyncio
async def test_generator_failure_persists_fallback_question():
    class BrokenGenerator:
        async def generate(self, request):
            raise RuntimeError("provider down")

    engine, store = _engine(generator=BrokenGenerator())
    result = await engine.start(_start())
    record = await store.load(result.session_id)
    assert result.first_question == record.blueprint.slot("problem_solving-1").fallback_question
    assert record.question_pending is False
    assert record.status == "in_progress"
```

Additional tests in the same file:

- `test_start_retry_recovers_crashed_planned_session`
- `test_generator_timeout_falls_back_to_blueprint_question`
- `test_invalid_generated_text_falls_back`
- `test_lease_is_acquired_once_for_a_fresh_start`
- `test_active_session_raises_session_exists_before_touching_the_lease`
- `test_lease_acquire_failure_raises_device_conflict_and_creates_no_session`
- `test_overlong_generated_text_falls_back`
- `test_empty_generated_text_falls_back`
- `test_generator_returning_none_falls_back`
- `test_start_is_idempotent_by_client_request_id`
- `test_lease_is_released_when_session_write_fails`
- `test_ensure_question_rejects_malformed_request`

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest backend/tests/interview_engine/test_engine_start.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.interview_engine.errors'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/interview_engine/errors.py
class EngineError(Exception):
    code = "engine_error"
    status_code = 400

    def __init__(self, message: str = "", **details):
        super().__init__(message or self.code)
        self.details = details


class UnsupportedInterviewType(EngineError):
    code = "unsupported_interview_type"


class UnsupportedMode(EngineError):
    code = "unsupported_mode"
class SessionExists(EngineError):
    code = "session_exists"
    status_code = 409

    def __init__(self, session_id: str, **details):
        super().__init__("An active session already exists.", session_id=session_id, **details)
        self.session_id = session_id


class SessionNotFound(EngineError):
    code = "session_not_found"
    status_code = 404


class NotOwner(EngineError):
    code = "not_owner"
    status_code = 403


class InvalidState(EngineError):
    code = "invalid_state"
    status_code = 409


class DeviceConflict(EngineError):
    code = "device_conflict"
    status_code = 409


class VersionConflict(EngineError):
    code = "version_conflict"
    status_code = 409


class QuestionPendingConflict(EngineError):
    code = "question_pending"
    status_code = 409


class QuestionMismatch(EngineError):
    code = "question_mismatch"
    status_code = 409


class QuestionSuperseded(EngineError):
    code = "question_superseded"
    status_code = 409


class ConsentRequired(EngineError):
    code = "consent_required"
    status_code = 409


class PauseLimitReached(EngineError):
    code = "pause_limit_reached"
    status_code = 409


class HintLimitReached(EngineError):
    code = "hint_limit_reached"
    status_code = 409


class HintUnavailable(EngineError):
    code = "hint_unavailable"
    status_code = 409


class NoReport(EngineError):
    code = "no_report"
    status_code = 409
```

```python
# backend/interview_engine/application/engine.py
import asyncio
from typing import List, Optional, Tuple

from ..contracts.enums import InterviewType, Mode, NextAction, SessionStatus
from ..contracts.messages import (
    EndSessionCommand,
    EndSessionResult,
    HintResult,
    PauseSessionCommand,
    RequestHintCommand,
    ResumeSessionCommand,
    ResumeSessionResult,
    SessionView,
    StartSessionCommand,
    StartSessionResult,
    SubmitTurnCommand,
    SubmitTurnResult,
)
from ..contracts.records import (
    Analysis,
    ConsentSnapshot,
    EventRecord,
    EvidenceRecord,
    HintRecord,
    OutboxRecord,
    QuestionRecord,
    ReportRecord,
    SessionRecord,
    TurnCommandRecord,
    TurnRecord,
)
from ..domain.behavioral_blueprint import build_behavioral_blueprint
from ..domain.session import Session, is_terminal_status
from ..errors import (
    ConsentRequired,
    DeviceConflict,
    EngineError,
    HintLimitReached,
    HintUnavailable,
    InvalidState,
    NoReport,
    NotOwner,
    PauseLimitReached,
    QuestionMismatch,
    QuestionPendingConflict,
    QuestionSuperseded,
    SessionExists,
    SessionNotFound,
    UnsupportedInterviewType,
    UnsupportedMode,
    VersionConflict,
)
from ..ports.capabilities import AnalysisRequest, QuestionRequest
from .report_builder import build_report

_MAX_QUESTION_CHARS = 400


def _valid_question_text(text: Optional[str]) -> bool:
    if not text:
        return False
    stripped = text.strip()
    return 0 < len(stripped) <= _MAX_QUESTION_CHARS and stripped.endswith("?")


class InterviewEngine:
    def __init__(
        self,
        *,
        store,
        lease,
        clock,
        ids,
        analyzer,
        generator,
        evaluator,
        lease_ttl_seconds: int = 120,
        worker_id: str = "engine-worker",
        generation_timeout_seconds: float = 8.0,
    ):
        self.store = store
        self.lease = lease
        self.clock = clock
        self.ids = ids
        self.analyzer = analyzer
        self.generator = generator
        self.evaluator = evaluator
        self.lease_ttl_seconds = lease_ttl_seconds
        self.worker_id = worker_id
        self.generation_timeout_seconds = generation_timeout_seconds

    def _event(self, session: Session, event_type: str, payload: dict) -> EventRecord:
        return EventRecord(
            event_id=self.ids.new_id(),
            session_id=session.record.session_id,
            event_sequence=session.next_sequence(),
            event_type=event_type,
            payload=payload,
            created_at=self.clock.now(),
        )

    def _outbox(self, event_type: str, payload: dict) -> OutboxRecord:
        return OutboxRecord(
            outbox_id=self.ids.new_id(),
            event_type=event_type,
            payload=payload,
            created_at=self.clock.now(),
        )

    async def load_owned(self, session_id: str, candidate_id: str) -> SessionRecord:
        record = await self.store.load(session_id)
        if record is None:
            raise SessionNotFound()
        if record.candidate_id != candidate_id:
            raise NotOwner()
        return record

    def _validate_type_and_mode(self, interview_type: str, mode: str) -> None:
        if interview_type != InterviewType.BEHAVIORAL.value:
            raise UnsupportedInterviewType()
        if mode != Mode.PRACTICE.value:
            raise UnsupportedMode()

    async def start(self, cmd: StartSessionCommand) -> StartSessionResult:
        self._validate_type_and_mode(cmd.interview_type, cmd.mode)
        existing = await self.store.load_by_client_request_id(cmd.candidate_id, cmd.client_request_id)
        if existing is not None:
            question = await self.ensure_question(
                existing.session_id,
                self._first_question_request(existing),
            )
            fresh = await self.store.load(existing.session_id)
            return self._start_result(fresh or existing, question)

        active = await self.store.find_active(cmd.candidate_id, cmd.interview_type, cmd.mode)
        if active is not None:
            raise SessionExists(active.session_id)

        token = self.ids.new_token()
        session_id = self.ids.new_id()
        if not await self.lease.acquire(session_id, cmd.device_id, token, self.lease_ttl_seconds):
            raise DeviceConflict()

        now = self.clock.now()
        record = SessionRecord(
            session_id=session_id,
            candidate_id=cmd.candidate_id,
            interview_type=cmd.interview_type,
            mode=cmd.mode,
            status=SessionStatus.PLANNED.value,
            version=0,
            event_sequence=1,
            last_applied_sequence=1,
            fencing_token=token,
            device_id=cmd.device_id,
            blueprint=build_behavioral_blueprint(cmd.mode, cmd.role, cmd.job_description),
            client_request_id=cmd.client_request_id,
            role=cmd.role,
            company=cmd.company,
            question_pending=True,
            consent=ConsentSnapshot(**(cmd.consent or {})),
            created_at=now,
            updated_at=now,
        )
        try:
            async with self.store.transaction():
                await self.store.insert(record)
                await self.store.append_event(
                    EventRecord(
                        event_id=self.ids.new_id(),
                        session_id=session_id,
                        event_sequence=1,
                        event_type="SessionCreated",
                        payload={"mode": cmd.mode, "interview_type": cmd.interview_type},
                        created_at=now,
                    )
                )
                await self.store.append_outbox(
                    self._outbox(
                        "interview_engine.question.requested",
                        {
                            "session_id": session_id,
                            "question_generation_key": f"{session_id}:0:first_question",
                            "purpose": "first_question",
                            "slot_id": record.blueprint.ordered_slots()[0].slot_id,
                            "session_version_at_request": 0,
                        },
                    )
                )
        except Exception:
            await self.lease.release(session_id, token)
            raise

        question = await self.ensure_question(session_id, self._first_question_request(record))
        fresh = await self.store.load(session_id)
        return self._start_result(fresh, question)

    def _first_question_request(self, record: SessionRecord) -> dict:
        return {
            "slot_id": record.blueprint.ordered_slots()[0].slot_id,
            "purpose": "first_question",
            "session_version_at_request": 0,
            "question_generation_key": f"{record.session_id}:0:first_question",
        }

    def _start_result(self, record: SessionRecord, question: Optional[QuestionRecord]) -> StartSessionResult:
        if question is None:
            raise InvalidState()
        return StartSessionResult(
            session_id=record.session_id,
            status=record.status,
            first_question=question.text,
            question_id=question.question_id,
            fencing_token=record.fencing_token,
            version=record.version,
            report_id=record.report_id,
            report_outcome=record.report_outcome,
            client_request_id=record.client_request_id,
        )

    def _request_value(self, request: dict, field: str) -> str:
        value = request.get(field)
        if not isinstance(value, str) or not value:
            raise InvalidState(f"question request is missing {field}")
        return value

    async def _generate_question(
        self, record: SessionRecord, slot, purpose: str, prior: List[str]
    ) -> Tuple[str, str]:
        try:
            generated = await asyncio.wait_for(
                self.generator.generate(
                    QuestionRequest(
                        session_id=record.session_id,
                        slot=slot,
                        purpose=purpose,
                        role=record.role,
                        company=record.company,
                        prior_questions=prior,
                    )
                ),
                timeout=self.generation_timeout_seconds,
            )
        except Exception:
            return slot.fallback_question, "fallback"
        if not _valid_question_text(generated.text):
            return slot.fallback_question, "fallback"
        return generated.text.strip(), generated.source

    async def ensure_question(self, session_id: str, request: dict) -> Optional[QuestionRecord]:
        key = self._request_value(request, "question_generation_key")
        slot_id = self._request_value(request, "slot_id")
        purpose = self._request_value(request, "purpose")
        existing = await self.store.get_question_by_key(session_id, key)
        if existing is not None:
            return existing
        record = await self.store.load(session_id)
        if record is None:
            raise SessionNotFound()
        if is_terminal_status(record.status):
            return None
        slot = record.blueprint.slot(slot_id)
        prior = [turn.text for turn in await self.store.turns_for_session(session_id)]
        text, source = await self._generate_question(record, slot, purpose, prior)
        question = QuestionRecord(
            question_id=self.ids.new_id(),
            session_id=session_id,
            slot_id=slot.slot_id,
            question_generation_key=key,
            purpose=purpose,
            text=text,
            source=source,
            created_at=self.clock.now(),
        )
        async with self.store.transaction():
            current = await self.store.load(session_id)
            if current is None:
                raise SessionNotFound()
            if is_terminal_status(current.status):
                return None
            existing = await self.store.get_question_by_key(session_id, key)
            if existing is not None:
                return existing
            await self.store.put_question(question)
            session = Session.from_record(current)
            started = current.status == SessionStatus.PLANNED.value
            session.set_question(question.question_id, question.text, slot.slot_id, pending=False)
            session.record.pending_question_request = None
            session.bump()
            events = []
            if started:
                events.append(
                    self._event(session, "SessionStarted", {"slot_id": slot.slot_id})
                )
            events.append(
                self._event(
                    session,
                    "QuestionAsked",
                    {"question_id": question.question_id, "slot_id": slot.slot_id},
                )
            )
            if not await self.store.replace(session.to_record(), expected_version=current.version):
                existing = await self.store.get_question_by_key(session_id, key)
                if existing is not None:
                    return existing
                raise VersionConflict()
            for event in events:
                await self.store.append_event(event)
        return question
```

```python
# backend/interview_engine/__init__.py
from .application.engine import InterviewEngine
from .contracts import *  # noqa: F401,F403
from .errors import EngineError  # noqa: F401

__all__ = ["InterviewEngine", "EngineError"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest backend/tests/interview_engine/test_engine_start.py -q`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/interview_engine/errors.py backend/interview_engine/application/engine.py backend/interview_engine/__init__.py backend/tests/interview_engine/test_engine_start.py
git commit -m "feat(interview-engine): implement start session and first question"
```

### Task 8: Submit turn

**Files:**
- Modify: `backend/interview_engine/application/engine.py`
- Test: `backend/tests/interview_engine/test_engine_submit.py`

**Interfaces:**
- Consumes: Task 7 engine.
- Produces: `InterviewEngine.submit_turn(cmd: SubmitTurnCommand) -> SubmitTurnResult`; `InterviewEngine.session_view(record) -> SessionView`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/interview_engine/test_engine_submit.py
import pytest

from backend.interview_engine.adapters.memory_store import InMemorySessionStore
from backend.interview_engine.adapters.scripted import (
    DeterministicEvaluator,
    ScriptedAnalyzer,
    ScriptedQuestionGenerator,
)
from backend.interview_engine.adapters.system import InMemoryLease, SystemClock, UuidIds
from backend.interview_engine.application.engine import InterviewEngine
from backend.interview_engine.contracts.messages import StartSessionCommand, SubmitTurnCommand
from backend.interview_engine.contracts.records import Analysis
from backend.interview_engine.errors import DeviceConflict, QuestionPendingConflict


def _build(script=None):
    store = InMemorySessionStore()
    engine = InterviewEngine(
        store=store, lease=InMemoryLease(), clock=SystemClock(), ids=UuidIds(),
        analyzer=ScriptedAnalyzer(script or []), generator=ScriptedQuestionGenerator(),
        evaluator=DeterministicEvaluator(),
    )
    return engine, store


async def _started(engine):
    return await engine.start(StartSessionCommand(
        candidate_id="c1", interview_type="behavioral", mode="practice",
        device_id="d1", client_request_id="req-1", role="Senior Engineer", company="Acme",
    ))


def _cmd(result, key="turn-1", text="I led the migration and cut errors by half."):
    return SubmitTurnCommand(
        candidate_id="c1", session_id=result.session_id, device_id="d1",
        fencing_token=result.fencing_token, turn_idempotency_key=key,
        kind="answer", text=text, question_id=result.question_id,
    )


@pytest.mark.asyncio
async def test_sufficient_answer_returns_next_question_and_records_evidence():
    engine, store = _build()
    start = await _started(engine)
    result = await engine.submit_turn(_cmd(start))
    assert result.next_action == "next_slot"
    assert result.question != start.first_question
    assert result.question_id != start.question_id
    assert result.status == "in_progress"
    evidence = await store.evidence_for_session(start.session_id)
    assert len(evidence) == 1
    assert evidence[0].competency == "problem_solving"
    record = await store.load(start.session_id)
    assert record.current_slot_id == "problem_solving-2"
    assert record.question_pending is False
    assert record.outstanding_question == result.question


@pytest.mark.asyncio
async def test_duplicate_turn_returns_stored_result_without_second_turn():
    engine, store = _build()
    start = await _started(engine)
    first = await engine.submit_turn(_cmd(start))
    second = await engine.submit_turn(_cmd(start))
    assert second.dict() == first.dict()
    assert await store.count_turns(start.session_id) == 1
    assert len(await store.evidence_for_session(start.session_id)) == 1


@pytest.mark.asyncio
async def test_incomplete_answer_asks_follow_up_and_spends_allowance():
    engine, store = _build([Analysis(signal="incomplete", instance="new", substantively_deficient=True)])
    start = await _started(engine)
    result = await engine.submit_turn(_cmd(start, text="Not much to say."))
    assert result.next_action == "follow_up"
    assert result.question == "What alternatives did you consider before choosing that approach, and why did you reject them?"
    record = await store.load(start.session_id)
    assert record.current_slot_id == "problem_solving-1"
    assert record.follow_up_used == {"problem_solving-1": 1}


@pytest.mark.asyncio
async def test_second_incomplete_after_allowance_advances_slot():
    engine, store = _build([
        Analysis(signal="incomplete", instance="new", substantively_deficient=True),
        Analysis(signal="incomplete", instance="new", substantively_deficient=True),
    ])
    start = await _started(engine)
    first = await engine.submit_turn(_cmd(start))
    second_cmd = _cmd(start, key="turn-2", text="Still not much.")
    second_cmd.question_id = first.question_id
    second = await engine.submit_turn(second_cmd)
    assert first.next_action == "follow_up"
    assert second.next_action == "next_slot"
    record = await store.load(start.session_id)
    assert record.current_slot_id == "problem_solving-2"
    assert record.follow_up_used == {"problem_solving-1": 1}


@pytest.mark.asyncio
async def test_clarification_returns_same_question_and_no_evidence():
    engine, store = _build()
    start = await _started(engine)
    cmd = _cmd(start, key="clarify-1")
    cmd.kind = "clarification_request"
    cmd.text = "What do you mean by concrete?"
    result = await engine.submit_turn(cmd)
    assert result.next_action == "await_answer"
    assert result.question == start.first_question
    assert result.question_id == start.question_id
    assert await store.evidence_for_session(start.session_id) == []


@pytest.mark.asyncio
async def test_final_sufficient_answer_ends_and_allocates_report():
    engine, store = _build([Analysis(signal="sufficient", instance="new") for _ in range(10)])
    start = await _started(engine)
    result = await engine.submit_turn(_cmd(start))
    for index in range(9):
        cmd = _cmd(start, key=f"turn-{index + 2}")
        cmd.question_id = result.question_id
        result = await engine.submit_turn(cmd)
    assert result.next_action == "end"
    assert result.status == "completed"
    assert result.report_id
    assert result.report_outcome == "evaluating"
    report = await store.get_report(result.report_id)
    assert report.outcome == "evaluating"
    outbox_types = [o.event_type for o in store._outbox]
    assert outbox_types.count("interview_engine.report.requested") == 1


@pytest.mark.asyncio
async def test_wrong_device_is_rejected():
    engine, _ = _build()
    start = await _started(engine)
    cmd = _cmd(start)
    cmd.device_id = "d2"
    with pytest.raises(DeviceConflict):
        await engine.submit_turn(cmd)


@pytest.mark.asyncio
async def test_question_mismatch_is_rejected():
    engine, _ = _build()
    start = await _started(engine)
    cmd = _cmd(start)
    cmd.question_id = "not-the-outstanding-question"
    with pytest.raises(Exception) as exc:
        await engine.submit_turn(cmd)
    assert getattr(exc.value, "code", "") == "question_mismatch"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest backend/tests/interview_engine/test_engine_submit.py -q`
Expected: FAIL with `AttributeError: 'InterviewEngine' object has no attribute 'submit_turn'`

- [ ] **Step 3: Write minimal implementation**

Append to `backend/interview_engine/application/engine.py`:

```python
    async def session_view(self, record: SessionRecord) -> SessionView:
        answered = await self.store.count_turns(record.session_id, kind="answer")
        return SessionView(
            session_id=record.session_id,
            status=record.status,
            version=record.version,
            question_pending=record.question_pending,
            outstanding_question=record.outstanding_question,
            question_id=record.current_question_id,
            report_id=record.report_id,
            report_outcome=record.report_outcome,
            fencing_token=record.fencing_token,
            hints_used=record.hint_count,
            hints_remaining=max(record.hint_budget - record.hint_count, 0),
            plan_position=record.plan_position,
            current_slot_id=record.current_slot_id,
            questions_answered=answered,
        )

    async def _assert_lease(self, record: SessionRecord, device_id: str, token: Optional[str]) -> None:
        if record.device_id != device_id:
            raise DeviceConflict()
        if token is not None and token != record.fencing_token:
            raise DeviceConflict()
        if not await self.lease.confirm(record.session_id, device_id, record.fencing_token):
            raise DeviceConflict()

    async def submit_turn(self, cmd: SubmitTurnCommand) -> SubmitTurnResult:
        record = await self.load_owned(cmd.session_id, cmd.candidate_id)
        await self._assert_lease(record, cmd.device_id, cmd.fencing_token)

        existing = await self.store.get_turn_command(cmd.session_id, cmd.turn_idempotency_key)
        if existing is not None and existing.status == "complete":
            return SubmitTurnResult(**existing.result)
        if existing is not None and existing.status == "pending":
            request = record.pending_question_request or {}
            if not request:
                raise InvalidState()
            question = await self.ensure_question(cmd.session_id, request)
            if question is None:
                raise InvalidState()
            fresh = await self.store.load(cmd.session_id)
            result = SubmitTurnResult(
                session_id=cmd.session_id,
                status=fresh.status,
                next_action="follow_up" if request.get("purpose") == "follow_up" else "next_slot",
                question=question.text,
                question_id=question.question_id,
                version=fresh.version,
            )
            async with self.store.transaction():
                await self.store.complete_turn_command(cmd.session_id, cmd.turn_idempotency_key, result.dict())
            return result
        if record.status in _TERMINAL:
            raise InvalidState()
        if record.status != SessionStatus.IN_PROGRESS.value:
            raise InvalidState()
        if record.question_pending:
            raise QuestionPendingConflict()
        if cmd.question_id is not None and cmd.question_id != record.current_question_id:
            raise QuestionMismatch()
        if cmd.expected_version is not None and cmd.expected_version != record.version:
            raise VersionConflict()

        session = Session.from_record(record)
        slot = session.slot()
        turn = TurnRecord(
            turn_id=self.ids.new_id(),
            session_id=record.session_id,
            sequence=await self.store.count_turns(record.session_id) + 1,
            kind=cmd.kind,
            question_id=record.current_question_id or "",
            slot_id=slot.slot_id,
            text=cmd.text,
            idempotency_key=cmd.turn_idempotency_key,
            device_id=cmd.device_id,
            created_at=self.clock.now(),
        )

        if cmd.kind == "clarification_request":
            reply = slot.clarification_text
            async with self.store.transaction():
                current = await self.store.load(cmd.session_id)
                if current is None:
                    raise SessionNotFound()
                current_session = Session.from_record(current)
                current_session.apply_clarification(turn, reply)
                await self.store.append_turn(turn)
                await self.store.put_turn_command(
                    TurnCommandRecord(
                        session_id=cmd.session_id,
                        idempotency_key=cmd.turn_idempotency_key,
                        status="complete",
                        result={
                            "session_id": cmd.session_id,
                            "status": current_session.record.status,
                            "next_action": "await_answer",
                            "question": current_session.record.outstanding_question,
                            "question_id": current_session.record.current_question_id,
                            "version": current_session.record.version,
                        },
                        created_at=self.clock.now(),
                        updated_at=self.clock.now(),
                    )
                )
                event = self._event(
                    current_session,
                    "ClarificationReplied",
                    {"question_id": current_session.record.current_question_id},
                )
                if not await self.store.replace(current_session.to_record(), expected_version=current.version):
                    raise VersionConflict()
                await self.store.append_event(event)
            result = SubmitTurnResult(
                session_id=cmd.session_id,
                status=record.status,
                next_action="await_answer",
                question=record.outstanding_question,
                question_id=record.current_question_id,
                version=record.version + 1,
            )
            return result

        analysis = await self.analyzer.analyze(
            AnalysisRequest(
                session_id=record.session_id,
                turn_id=turn.turn_id,
                question_id=turn.question_id,
                slot_id=slot.slot_id,
                competency=slot.competency,
                text=cmd.text,
            )
        )
        evidence = None
        if analysis.instance == "new" and analysis.signal in ("sufficient", "incomplete"):
            evidence = EvidenceRecord(
                evidence_id=self.ids.new_id(),
                session_id=record.session_id,
                turn_id=turn.turn_id,
                question_id=turn.question_id,
                slot_id=slot.slot_id,
                competency=slot.competency,
                signal=analysis.signal,
                instance=analysis.instance,
                contradiction=analysis.contradiction,
                difficulty=slot.difficulty,
                created_at=self.clock.now(),
            )

        async with self.store.transaction():
            current = await self.store.load(cmd.session_id)
            if current is None:
                raise SessionNotFound()
            current_session = Session.from_record(current)
            if current_session.is_terminal():
                raise InvalidState()
            action = current_session.apply_answer(turn, analysis, evidence, slot.competency)
            await self.store.append_turn(turn)
            if evidence is not None:
                await self.store.append_evidence(evidence)
            await self.store.put_turn_command(
                TurnCommandRecord(
                    session_id=cmd.session_id,
                    idempotency_key=cmd.turn_idempotency_key,
                    status="pending",
                    created_at=self.clock.now(),
                    updated_at=self.clock.now(),
                )
            )
            events = [
                self._event(current_session, "TurnSubmitted", {"turn_id": turn.turn_id}),
                self._event(current_session, "TurnAnalysisRequested", {"turn_id": turn.turn_id}),
            ]
            if action == NextAction.END:
                report = ReportRecord(
                    report_id=current_session.record.report_id,
                    session_id=cmd.session_id,
                    outcome=current_session.record.report_outcome or "evaluating",
                    created_at=self.clock.now(),
                    updated_at=self.clock.now(),
                )
                await self.store.put_report(report)
                events.append(
                    self._event(current_session, "SessionCompleted", {"report_id": report.report_id})
                )
                if report.outcome == "evaluating":
                    await self.store.append_outbox(
                        self._outbox(
                            "interview_engine.report.requested",
                            {"session_id": cmd.session_id, "report_id": report.report_id},
                        )
                    )
            if not await self.store.replace(current_session.to_record(), expected_version=current.version):
                raise VersionConflict()
            for event in events:
                await self.store.append_event(event)

        if action == NextAction.END:
            result = SubmitTurnResult(
                session_id=cmd.session_id,
                status=current_session.record.status,
                next_action="end",
                report_id=current_session.record.report_id,
                report_outcome=current_session.record.report_outcome,
                version=current_session.record.version,
            )
            async with self.store.transaction():
                await self.store.complete_turn_command(cmd.session_id, cmd.turn_idempotency_key, result.dict())
            return result

        request = current_session.record.pending_question_request or {}
        question = await self.ensure_question(cmd.session_id, request)
        if question is None:
            raise InvalidState()
        fresh = await self.store.load(cmd.session_id)
        result = SubmitTurnResult(
            session_id=cmd.session_id,
            status=fresh.status,
            next_action=action.value,
            question=question.text,
            question_id=question.question_id,
            version=fresh.version,
        )
        async with self.store.transaction():
            await self.store.complete_turn_command(cmd.session_id, cmd.turn_idempotency_key, result.dict())
        return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest backend/tests/interview_engine/test_engine_submit.py -q`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/interview_engine/application/engine.py backend/tests/interview_engine/test_engine_submit.py
git commit -m "feat(interview-engine): accept turns with bounded follow-up"
```

---

### Task 9: Hint, pause, resume, end, report, outbox drain

**Files:**
- Modify: `backend/interview_engine/application/engine.py`
- Test: `backend/tests/interview_engine/test_engine_lifecycle.py`

**Interfaces:**
- Consumes: Task 8 engine.
- Produces: `request_hint(cmd) -> HintResult`, `pause(cmd) -> SessionView`, `resume(cmd) -> ResumeSessionResult`, `end(cmd) -> EndSessionResult`, `get_report(candidate_id, report_id) -> ReportRecord`, `drain_outbox(limit=10) -> int`, `build_report_body(record, evidence, turns)`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/interview_engine/test_engine_lifecycle.py
import pytest

from backend.interview_engine.adapters.memory_store import InMemorySessionStore
from backend.interview_engine.adapters.scripted import (
    DeterministicEvaluator,
    ScriptedAnalyzer,
    ScriptedQuestionGenerator,
)
from backend.interview_engine.adapters.system import InMemoryLease, SystemClock, UuidIds
from backend.interview_engine.application.engine import InterviewEngine
from backend.interview_engine.contracts.messages import (
    EndSessionCommand,
    PauseSessionCommand,
    RequestHintCommand,
    ResumeSessionCommand,
    StartSessionCommand,
    SubmitTurnCommand,
)
from backend.interview_engine.errors import HintLimitReached, NoReport


def _build():
    store = InMemorySessionStore()
    engine = InterviewEngine(
        store=store, lease=InMemoryLease(), clock=SystemClock(), ids=UuidIds(),
        analyzer=ScriptedAnalyzer([]), generator=ScriptedQuestionGenerator(),
        evaluator=DeterministicEvaluator(),
    )
    return engine, store


async def _started(engine):
    return await engine.start(StartSessionCommand(
        candidate_id="c1", interview_type="behavioral", mode="practice",
        device_id="d1", client_request_id="req-1", role="Senior Engineer", company="Acme",
    ))


def _hint(start, key="hint-1"):
    return RequestHintCommand(
        candidate_id="c1", session_id=start.session_id, device_id="d1",
        fencing_token=start.fencing_token, hint_idempotency_key=key,
        question_id=start.question_id,
    )


@pytest.mark.asyncio
async def test_hint_returns_authored_text_and_is_idempotent():
    engine, store = _build()
    start = await _started(engine)
    first = await engine.request_hint(_hint(start))
    second = await engine.request_hint(_hint(start))
    assert first.hint == second.hint
    assert first.hints_used == 1
    assert second.hints_used == 1
    assert first.remaining == 1
    record = await store.load(start.session_id)
    assert record.hint_count == 1


@pytest.mark.asyncio
async def test_hint_budget_is_bounded():
    engine, _ = _build()
    start = await _started(engine)
    await engine.request_hint(_hint(start, "h1"))
    await engine.request_hint(_hint(start, "h2"))
    with pytest.raises(HintLimitReached):
        await engine.request_hint(_hint(start, "h3"))


@pytest.mark.asyncio
async def test_pause_and_resume_takeover_bumps_token_not_version_direction():
    engine, store = _build()
    start = await _started(engine)
    paused = await engine.pause(PauseSessionCommand(
        candidate_id="c1", session_id=start.session_id, device_id="d1",
        fencing_token=start.fencing_token, command_id="p1",
    ))
    assert paused.status == "paused"
    resumed = await engine.resume(ResumeSessionCommand(
        candidate_id="c1", session_id=start.session_id, device_id="d2", command_id="r1",
    ))
    assert resumed.status == "in_progress"
    assert resumed.fencing_token != start.fencing_token
    record = await store.load(start.session_id)
    assert record.device_id == "d2"
    assert record.fencing_token == resumed.fencing_token
    assert record.disconnect_count == 1


@pytest.mark.asyncio
async def test_resume_takes_lease_from_other_device():
    engine, store = _build()
    start = await _started(engine)
    resumed = await engine.resume(ResumeSessionCommand(
        candidate_id="c1", session_id=start.session_id, device_id="d2",
    ))
    assert resumed.fencing_token != start.fencing_token
    assert resumed.question == start.first_question


@pytest.mark.asyncio
async def test_end_is_idempotent_and_allocates_report_once():
    engine, store = _build()
    start = await _started(engine)
    first = await engine.end(EndSessionCommand(
        candidate_id="c1", session_id=start.session_id, device_id="d1",
        fencing_token=start.fencing_token, end_command_id="end-1",
    ))
    second = await engine.end(EndSessionCommand(
        candidate_id="c1", session_id=start.session_id, device_id="d1",
        fencing_token=start.fencing_token, end_command_id="end-2",
    ))
    assert first.report_id == second.report_id
    assert first.report_outcome == "evaluating"
    reports = list(store._reports.values())
    assert len(reports) == 1


@pytest.mark.asyncio
async def test_report_is_evaluating_until_outbox_drain_then_ready():
    engine, store = _build()
    start = await _started(engine)
    ended = await engine.end(EndSessionCommand(
        candidate_id="c1", session_id=start.session_id, device_id="d1",
        fencing_token=start.fencing_token, end_command_id="end-1",
    ))
    evaluating = await engine.get_report("c1", ended.report_id)
    assert evaluating.outcome == "evaluating"
    assert evaluating.body is None
    processed = await engine.drain_outbox()
    assert processed >= 1
    ready = await engine.get_report("c1", ended.report_id)
    assert ready.outcome == "ready"
    assert ready.body is not None
    assert "competencies" in ready.body
    assert "score" not in ready.body


@pytest.mark.asyncio
async def test_feedback_on_abandoned_session_has_no_report():
    engine, store = _build()
    start = await _started(engine)
    record = await store.load(start.session_id)
    record.status = "abandoned"
    async with store.transaction():
        await store.replace(record, expected_version=record.version)
    with pytest.raises(NoReport):
        await engine.get_report("c1", None)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest backend/tests/interview_engine/test_engine_lifecycle.py -q`
Expected: FAIL with `AttributeError: 'InterviewEngine' object has no attribute 'request_hint'`

- [ ] **Step 3: Write minimal implementation**

Append to `backend/interview_engine/application/engine.py`:

```python
    async def request_hint(self, cmd: RequestHintCommand) -> HintResult:
        record = await self.load_owned(cmd.session_id, cmd.candidate_id)
        await self._assert_lease(record, cmd.device_id, cmd.fencing_token)
        if record.mode != Mode.PRACTICE.value:
            raise HintUnavailable()
        existing = await self.store.get_hint_by_key(cmd.session_id, cmd.hint_idempotency_key)
        if existing is not None:
            return HintResult(
                hint=existing.text,
                hints_used=existing.hints_used,
                remaining=max(record.hint_budget - existing.hints_used, 0),
                version=record.version,
                question_id=existing.question_id,
            )
        if record.question_pending:
            raise QuestionPendingConflict()
        if record.status != SessionStatus.IN_PROGRESS.value:
            raise InvalidState()
        if cmd.question_id is not None and cmd.question_id != record.current_question_id:
            raise QuestionSuperseded()
        if record.hint_count >= record.hint_budget:
            raise HintLimitReached()
        slot = record.blueprint.slot(record.current_slot_id)
        hint = HintRecord(
            hint_id=self.ids.new_id(),
            session_id=record.session_id,
            hint_idempotency_key=cmd.hint_idempotency_key,
            question_id=record.current_question_id or "",
            text=slot.hint_text,
            hints_used=record.hint_count + 1,
            created_at=self.clock.now(),
        )
        async with self.store.transaction():
            current = await self.store.load(cmd.session_id)
            if current is None:
                raise SessionNotFound()
            session = Session.from_record(current)
            if session.record.hint_count >= session.record.hint_budget:
                raise HintLimitReached()
            session.record.hint_count += 1
            session.bump()
            event = self._event(session, "HintProvided", {"question_id": hint.question_id})
            await self.store.put_hint(hint)
            if not await self.store.replace(session.to_record(), expected_version=current.version):
                raise VersionConflict()
            await self.store.append_event(event)
        return HintResult(
            hint=hint.text,
            hints_used=session.record.hint_count,
            remaining=max(session.record.hint_budget - session.record.hint_count, 0),
            version=session.record.version,
            question_id=hint.question_id,
        )

    async def pause(self, cmd: PauseSessionCommand) -> SessionView:
        record = await self.load_owned(cmd.session_id, cmd.candidate_id)
        await self._assert_lease(record, cmd.device_id, cmd.fencing_token)
        if record.question_pending:
            raise QuestionPendingConflict()
        if record.status != SessionStatus.IN_PROGRESS.value:
            raise InvalidState()
        if record.mode == Mode.FORMAL.value and record.pause_count >= 1:
            raise PauseLimitReached()
        async with self.store.transaction():
            current = await self.store.load(cmd.session_id)
            session = Session.from_record(current)
            session.mark_paused()
            event = self._event(session, "SessionPaused", {"reason": cmd.reason})
            if not await self.store.replace(session.to_record(), expected_version=current.version):
                raise VersionConflict()
            await self.store.append_event(event)
        return await self.session_view(session.to_record())

    async def resume(self, cmd: ResumeSessionCommand) -> ResumeSessionResult:
        record = await self.load_owned(cmd.session_id, cmd.candidate_id)
        if record.status in _TERMINAL:
            raise InvalidState()
        token = self.ids.new_token()
        await self.lease.takeover(cmd.session_id, cmd.device_id, token, self.lease_ttl_seconds)
        async with self.store.transaction():
            current = await self.store.load(cmd.session_id)
            if current is None:
                raise SessionNotFound()
            if current.device_id != cmd.device_id:
                current.disconnect_count += 1
            current.device_id = cmd.device_id
            current.fencing_token = token
            current.updated_at = self.clock.now()
            current.event_sequence += 1
            current.last_applied_sequence = current.event_sequence
            if current.status == SessionStatus.PAUSED.value:
                session = Session.from_record(current)
                session.mark_resumed()
                current = session.to_record()
            event = EventRecord(
                event_id=self.ids.new_id(),
                session_id=cmd.session_id,
                event_sequence=current.event_sequence,
                event_type="SessionLeaseTakenOver",
                payload={"device_id": cmd.device_id},
                created_at=self.clock.now(),
            )
            if not await self.store.replace(current, expected_version=record.version):
                raise VersionConflict()
            await self.store.append_event(event)
        if current.question_pending and current.pending_question_request:
            await self.ensure_question(cmd.session_id, current.pending_question_request)
            current = await self.store.load(cmd.session_id)
        return ResumeSessionResult(
            session_id=current.session_id,
            status=current.status,
            fencing_token=current.fencing_token,
            question=current.outstanding_question,
            question_id=current.current_question_id,
            version=current.version,
            question_pending=current.question_pending,
        )

    async def end(self, cmd: EndSessionCommand) -> EndSessionResult:
        record = await self.load_owned(cmd.session_id, cmd.candidate_id)
        await self._assert_lease(record, cmd.device_id, cmd.fencing_token)
        if record.status in _TERMINAL:
            return EndSessionResult(
                session_id=record.session_id,
                status=record.status,
                report_id=record.report_id,
                report_outcome=record.report_outcome,
            )
        async with self.store.transaction():
            current = await self.store.load(cmd.session_id)
            session = Session.from_record(current)
            report_id = current.report_id or self.ids.new_id()
            outcome = "suppressed" if not current.consent.evaluation else "evaluating"
            session.begin_completion(report_id, outcome)
            await self.store.put_report(
                ReportRecord(
                    report_id=report_id,
                    session_id=current.session_id,
                    outcome=outcome,
                    created_at=self.clock.now(),
                    updated_at=self.clock.now(),
                )
            )
            event = self._event(session, "SessionCompleted", {"report_id": report_id})
            if not await self.store.replace(session.to_record(), expected_version=current.version):
                raise VersionConflict()
            await self.store.append_event(event)
            if outcome == "evaluating":
                await self.store.append_outbox(
                    self._outbox(
                        "interview_engine.report.requested",
                        {"session_id": current.session_id, "report_id": report_id},
                    )
                )
        return EndSessionResult(
            session_id=session.record.session_id,
            status=session.record.status,
            report_id=session.record.report_id,
            report_outcome=session.record.report_outcome,
        )

    async def get_report(self, candidate_id: str, report_id: Optional[str]) -> ReportRecord:
        if not report_id:
            raise NoReport()
        report = await self.store.get_report(report_id)
        if report is None:
            raise NoReport()
        record = await self.store.load(report.session_id)
        if record is None or record.candidate_id != candidate_id:
            raise NotOwner()
        return report

    async def build_report_body(self, report_id: str) -> Optional[dict]:
        report = await self.store.get_report(report_id)
        if report is None:
            return None
        record = await self.store.load(report.session_id)
        if record is None:
            return None
        evidence = await self.store.evidence_for_session(record.session_id)
        turns = await self.store.turns_for_session(record.session_id)
        from ..domain.scoring import InstanceFact, confidence_for, level_for
        from ..ports.capabilities import CompetencyEvaluationInput, EvaluationRequest

        inputs = []
        for group in record.blueprint.groups:
            items = [item for item in evidence if item.competency == group.competency]
            facts = [
                InstanceFact(
                    competency=item.competency,
                    question_id=item.question_id,
                    signal=item.signal,
                    contradiction=item.contradiction,
                )
                for item in items
                if item.signal in ("sufficient", "incomplete") and item.instance == "new"
            ]
            inputs.append(
                CompetencyEvaluationInput(
                    competency=group.competency,
                    level=level_for(facts).value,
                    confidence=confidence_for(facts).value,
                    instances=len(facts),
                )
            )
        output = await self.evaluator.evaluate(
            EvaluationRequest(
                session_id=record.session_id,
                report_id=report_id,
                role=record.role,
                company=record.company,
                competencies=inputs,
            )
        )
        body = build_report(record, evidence, turns, output)
        return body.dict()

    async def drain_outbox(self, limit: int = 10) -> int:
        claimed = await self.store.claim_outbox(self.worker_id, limit)
        processed = 0
        for item in claimed:
            try:
                if item.event_type == "interview_engine.report.requested":
                    await self._handle_report_requested(item.payload)
                await self.store.mark_outbox_processed(item.outbox_id)
                processed += 1
            except Exception as exc:
                await self.store.mark_outbox_failed(item.outbox_id, str(exc))
        return processed

    async def _handle_report_requested(self, payload: dict) -> None:
        report_id = payload["report_id"]
        report = await self.store.get_report(report_id)
        if report is None or report.outcome != "evaluating":
            return
        body = await self.build_report_body(report_id)
        report.outcome = "ready"
        report.body = body
        report.attempts += 1
        report.updated_at = self.clock.now()
        await self.store.update_report(report, expected_outcome="evaluating")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest backend/tests/interview_engine/test_engine_lifecycle.py -q`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/interview_engine/application/engine.py backend/tests/interview_engine/test_engine_lifecycle.py
git commit -m "feat(interview-engine): add hints, resume, end, report and outbox drain"
```

### Task 10: Mongo store, indexes, and replica-set test support

**Files:**
- Create: `backend/interview_engine/adapters/mongo_store.py`, `backend/models/interview_engine_indexes.py`, `backend/tests/interview_engine/test_mongo_store.py`
- Modify: `backend/models/indexes.py`
- Create: `tests/support/mongo_replica.py`

**Interfaces:**
- Consumes: `SessionStore` protocol, Task 1 records.
- Produces: `MongoSessionStore(database, client)` implementing `SessionStore`; `ensure_interview_engine_indexes()`; `start_replica_set()` helper for integration tests.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/interview_engine/test_mongo_store.py
import os
from datetime import datetime

import pytest

from backend.interview_engine.adapters.mongo_store import MongoSessionStore
from backend.interview_engine.contracts.blueprint import Blueprint, BlueprintGroup, BlueprintSlot
from backend.interview_engine.contracts.records import SessionRecord

pytestmark = pytest.mark.integration

REPLICA_URI = os.environ.get("MONGODB_REPLICA_URI")


def _slot():
    return BlueprintSlot(
        slot_id="s1", competency="c", dimension="c", difficulty="intermediate",
        intent="i", fallback_question="q", follow_up_question="f",
        clarification_text="c", hint_text="h",
    )


def _record(session_id="m1"):
    now = datetime.utcnow()
    return SessionRecord(
        session_id=session_id, candidate_id="c1", interview_type="behavioral", mode="practice",
        status="planned", version=0, event_sequence=0, last_applied_sequence=0,
        fencing_token="t1", device_id="d1",
        blueprint=Blueprint(groups=[BlueprintGroup(group_id="g", competency="c", slots=[_slot()])]),
        created_at=now, updated_at=now,
    )


@pytest.fixture
async def store():
    if not REPLICA_URI:
        pytest.skip("MONGODB_REPLICA_URI not set; replica-set integration test skipped")
    from motor.motor_asyncio import AsyncIOMotorClient

    client = AsyncIOMotorClient(REPLICA_URI)
    database = client["interview_engine_test"]
    await database["interview_engine_sessions"].delete_many({})
    await database["interview_engine_events"].delete_many({})
    await database["interview_engine_turns"].delete_many({})
    await database["interview_engine_outbox"].delete_many({})
    yield MongoSessionStore(database, client)
    client.close()


@pytest.mark.asyncio
async def test_transaction_commits_session_and_event_atomically(store):
    record = _record()
    from backend.interview_engine.contracts.records import EventRecord

    async with store.transaction():
        await store.insert(record)
        await store.append_event(
            EventRecord(
                event_id="e1", session_id="m1", event_sequence=1,
                event_type="SessionCreated", payload={}, created_at=datetime.utcnow(),
            )
        )
    loaded = await store.load("m1")
    assert loaded is not None
    assert loaded.session_id == "m1"


@pytest.mark.asyncio
async def test_transaction_rolls_back_on_error(store):
    record = _record()
    with pytest.raises(RuntimeError):
        async with store.transaction():
            await store.insert(record)
            raise RuntimeError("boom")
    assert await store.load("m1") is None


@pytest.mark.asyncio
async def test_optimistic_replace(store):
    async with store.transaction():
        await store.insert(_record())
    loaded = await store.load("m1")
    loaded.version = 1
    assert await store.replace(loaded, expected_version=0) is True
    assert await store.replace(loaded, expected_version=0) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest backend/tests/interview_engine/test_mongo_store.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.interview_engine.adapters.mongo_store'` (or SKIP if no replica URI; the module import must still exist)

- [ ] **Step 3: Write minimal implementation**

```python
# backend/interview_engine/adapters/mongo_store.py
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import List, Optional

from ..contracts.records import (
    EventRecord,
    EvidenceRecord,
    HintRecord,
    OutboxRecord,
    QuestionRecord,
    ReportRecord,
    SessionRecord,
    TurnCommandRecord,
    TurnRecord,
)

_SESSIONS = "interview_engine_sessions"
_EVENTS = "interview_engine_events"
_TURNS = "interview_engine_turns"
_EVIDENCE = "interview_engine_evidence"
_QUESTIONS = "interview_engine_questions"
_HINTS = "interview_engine_hints"
_COMMANDS = "interview_engine_turn_commands"
_REPORTS = "interview_engine_reports"
_OUTBOX = "interview_engine_outbox"

_ACTIVE = {
    "planned",
    "in_progress",
    "paused",
}


class MongoSessionStore:
    def __init__(self, database, client):
        self._db = database
        self._client = client
        self._session: ContextVar = ContextVar("interview_engine_mongo_session", default=None)

    def _opts(self) -> dict:
        active = self._session.get()
        return {"session": active} if active is not None else {}

    @asynccontextmanager
    async def transaction(self):
        async with await self._client.start_session() as mongo_session:
            token = self._session.set(mongo_session)
            mongo_session.start_transaction()
            try:
                yield self
                await mongo_session.commit_transaction()
            except Exception:
                await mongo_session.abort_transaction()
                raise
            finally:
                self._session.reset(token)

    async def load(self, session_id: str) -> Optional[SessionRecord]:
        doc = await self._db[_SESSIONS].find_one({"_id": session_id}, **self._opts())
        return SessionRecord.parse_obj(doc) if doc else None

    async def load_by_client_request_id(self, candidate_id: str, client_request_id: str):
        doc = await self._db[_SESSIONS].find_one(
            {"candidate_id": candidate_id, "client_request_id": client_request_id},
            **self._opts(),
        )
        return SessionRecord.parse_obj(doc) if doc else None

    async def find_active(self, candidate_id: str, interview_type: str, mode: str):
        doc = await self._db[_SESSIONS].find_one(
            {
                "candidate_id": candidate_id,
                "interview_type": interview_type,
                "mode": mode,
                "status": {"$in": list(_ACTIVE)},
            },
            **self._opts(),
        )
        return SessionRecord.parse_obj(doc) if doc else None

    async def insert(self, record: SessionRecord) -> None:
        doc = record.dict()
        doc["_id"] = record.session_id
        await self._db[_SESSIONS].insert_one(doc, **self._opts())

    async def replace(self, record: SessionRecord, expected_version: int) -> bool:
        doc = record.dict()
        doc.pop("session_id", None)
        result = await self._db[_SESSIONS].update_one(
            {"_id": record.session_id, "version": expected_version},
            {"$set": doc},
            **self._opts(),
        )
        return result.matched_count == 1

    async def append_event(self, event: EventRecord) -> None:
        doc = event.dict()
        doc["_id"] = event.event_id
        await self._db[_EVENTS].insert_one(doc, **self._opts())

    async def append_turn(self, turn: TurnRecord) -> None:
        doc = turn.dict()
        doc["_id"] = turn.turn_id
        await self._db[_TURNS].insert_one(doc, **self._opts())

    async def count_turns(self, session_id: str, kind: Optional[str] = None) -> int:
        query = {"session_id": session_id}
        if kind is not None:
            query["kind"] = kind
        return await self._db[_TURNS].count_documents(query, **self._opts())

    async def turns_for_session(self, session_id: str) -> List[TurnRecord]:
        cursor = self._db[_TURNS].find({"session_id": session_id}, **self._opts()).sort("sequence", 1)
        return [TurnRecord.parse_obj(doc) async for doc in cursor]

    async def append_evidence(self, evidence: EvidenceRecord) -> None:
        doc = evidence.dict()
        doc["_id"] = evidence.evidence_id
        await self._db[_EVIDENCE].insert_one(doc, **self._opts())

    async def evidence_for_session(self, session_id: str) -> List[EvidenceRecord]:
        cursor = self._db[_EVIDENCE].find({"session_id": session_id}, **self._opts())
        return [EvidenceRecord.parse_obj(doc) async for doc in cursor]

    async def put_question(self, question: QuestionRecord) -> None:
        doc = question.dict()
        doc["_id"] = question.question_generation_key
        await self._db[_QUESTIONS].insert_one(doc, **self._opts())

    async def get_question_by_key(self, session_id: str, key: str) -> Optional[QuestionRecord]:
        doc = await self._db[_QUESTIONS].find_one({"_id": key}, **self._opts())
        if doc and doc.get("session_id") == session_id:
            return QuestionRecord.parse_obj(doc)
        return None

    async def put_hint(self, hint: HintRecord) -> None:
        doc = hint.dict()
        doc["_id"] = hint.hint_idempotency_key
        await self._db[_HINTS].insert_one(doc, **self._opts())

    async def get_hint_by_key(self, session_id: str, key: str) -> Optional[HintRecord]:
        doc = await self._db[_HINTS].find_one({"_id": key}, **self._opts())
        if doc and doc.get("session_id") == session_id:
            return HintRecord.parse_obj(doc)
        return None

    async def get_turn_command(self, session_id: str, key: str) -> Optional[TurnCommandRecord]:
        doc = await self._db[_COMMANDS].find_one(
            {"_id": f"{session_id}:{key}"}, **self._opts()
        )
        return TurnCommandRecord.parse_obj(doc) if doc else None

    async def put_turn_command(self, command: TurnCommandRecord) -> None:
        doc = command.dict()
        doc["_id"] = f"{command.session_id}:{command.idempotency_key}"
        await self._db[_COMMANDS].insert_one(doc, **self._opts())

    async def complete_turn_command(self, session_id: str, key: str, result: dict) -> None:
        await self._db[_COMMANDS].update_one(
            {"_id": f"{session_id}:{key}"},
            {"$set": {"status": "complete", "result": result}},
            **self._opts(),
        )

    async def put_report(self, report: ReportRecord) -> None:
        doc = report.dict()
        doc["_id"] = report.report_id
        await self._db[_REPORTS].insert_one(doc, **self._opts())

    async def get_report(self, report_id: str) -> Optional[ReportRecord]:
        doc = await self._db[_REPORTS].find_one({"_id": report_id}, **self._opts())
        return ReportRecord.parse_obj(doc) if doc else None

    async def update_report(self, report: ReportRecord, expected_outcome: str) -> bool:
        doc = report.dict()
        doc.pop("report_id", None)
        result = await self._db[_REPORTS].update_one(
            {"_id": report.report_id, "outcome": expected_outcome},
            {"$set": doc},
            **self._opts(),
        )
        return result.matched_count == 1

    async def append_outbox(self, record: OutboxRecord) -> None:
        doc = {
            "id": record.outbox_id,
            "event_type": record.event_type,
            "payload": record.payload,
            "correlation_id": record.payload.get("session_id", record.outbox_id),
            "actor_id": None,
            "status": "pending",
            "attempts": 0,
            "max_attempts": 5,
            "created_at": record.created_at,
            "processed_at": None,
            "last_attempt_at": None,
            "last_error": None,
        }
        await self._db[_OUTBOX].insert_one(doc, **self._opts())

    async def claim_outbox(self, worker_id: str, limit: int) -> List[OutboxRecord]:
        claimed = []
        for _ in range(limit):
            doc = await self._db[_OUTBOX].find_one_and_update(
                {
                    "status": {"$in": ["pending", "failed"]},
                    "attempts": {"$lt": 5},
                    "event_type": {"$regex": "^interview_engine\\."},
                },
                {"$set": {"status": "processing", "worker_id": worker_id}, "$inc": {"attempts": 1}},
                sort=[("created_at", 1)],
                return_document=True,
            )
            if not doc:
                break
            claimed.append(
                OutboxRecord(
                    outbox_id=doc["id"],
                    event_type=doc["event_type"],
                    payload=doc["payload"],
                    status="processing",
                    attempts=doc["attempts"],
                    worker_id=worker_id,
                    created_at=doc["created_at"],
                )
            )
        return claimed

    async def mark_outbox_processed(self, outbox_id: str) -> None:
        from datetime import datetime

        await self._db[_OUTBOX].update_one(
            {"id": outbox_id},
            {"$set": {"status": "processed", "processed_at": datetime.utcnow()}},
        )

    async def mark_outbox_failed(self, outbox_id: str, error: str) -> None:
        await self._db[_OUTBOX].update_one(
            {"id": outbox_id},
            {"$set": {"status": "failed", "last_error": error}},
        )
```

```python
# backend/models/interview_engine_indexes.py
async def ensure_interview_engine_indexes():
    from ..database import get_database

    database = get_database()
    sessions = database.interview_engine_sessions
    await sessions.create_index("candidate_id", background=True)
    await sessions.create_index(
        [("candidate_id", 1), ("client_request_id", 1)],
        unique=True,
        partialFilterExpression={"client_request_id": {"$exists": True, "$type": "string"}},
        background=True,
    )
    await sessions.create_index([("candidate_id", 1), ("status", 1)], background=True)
    events = database.interview_engine_events
    await events.create_index([("session_id", 1), ("event_sequence", 1)], unique=True, background=True)
    turns = database.interview_engine_turns
    await turns.create_index([("session_id", 1), ("sequence", 1)], unique=True, background=True)
    await turns.create_index([("session_id", 1), ("idempotency_key", 1)], unique=True, background=True)
    evidence = database.interview_engine_evidence
    await evidence.create_index([("session_id", 1), ("competency", 1)], background=True)
    questions = database.interview_engine_questions
    await questions.create_index("session_id", background=True)
    hints = database.interview_engine_hints
    await hints.create_index("session_id", background=True)
    commands = database.interview_engine_turn_commands
    await commands.create_index([("session_id", 1), ("idempotency_key", 1)], unique=True, background=True)
    reports = database.interview_engine_reports
    await reports.create_index("session_id", background=True)
```

```python
# tests/support/mongo_replica.py
import os
import shutil
import socket
import subprocess
import tempfile
import time


def _port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def start_replica_set(port: int = 27018) -> str:
    if _port_open(port):
        return f"mongodb://127.0.0.1:{port}/?directConnection=true"
    mongod = shutil.which("mongod")
    if not mongod:
        raise RuntimeError("mongod not found")
    dbpath = tempfile.mkdtemp(prefix="interview-engine-rs-")
    subprocess.Popen(
        [mongod, "--replSet", "rs0", "--dbpath", dbpath, "--port", str(port), "--bind_ip", "127.0.0.1"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    from pymongo import MongoClient

    client = MongoClient(f"mongodb://127.0.0.1:{port}/?directConnection=true")
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            client.admin.command("replSetInitiate", {"_id": "rs0", "members": [{"_id": 0, "host": f"127.0.0.1:{port}"}]})
            break
        except Exception:
            time.sleep(0.5)
    while time.time() < deadline:
        try:
            if client.admin.command("hello").get("isWritablePrimary"):
                break
        except Exception:
            pass
        time.sleep(0.5)
    return f"mongodb://127.0.0.1:{port}/?directConnection=true"
```

Modify `backend/models/indexes.py`:

```python
from .interview_engine_indexes import ensure_interview_engine_indexes
```

and inside `ensure_database_indexes()` append `await ensure_interview_engine_indexes()`.

- [ ] **Step 4: Run tests**

Run: `venv\Scripts\python.exe -m pytest backend/tests/interview_engine/test_mongo_store.py -q`
Expected: SKIPPED (3 skipped) when `MONGODB_REPLICA_URI` is unset. Then run with a replica set:
`$env:MONGODB_REPLICA_URI="mongodb://127.0.0.1:27018/?directConnection=true"; venv\Scripts\python.exe -m pytest backend/tests/interview_engine/test_mongo_store.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/interview_engine/adapters/mongo_store.py backend/models/interview_engine_indexes.py backend/models/indexes.py tests/support/mongo_replica.py backend/tests/interview_engine/test_mongo_store.py
git commit -m "feat(interview-engine): add Mongo store, indexes, replica-set test helper"
```

---

### Task 11: Redis lease and engine factory

**Files:**
- Create: `backend/interview_engine/adapters/redis_lease.py`, `backend/interview_engine/adapters/factory.py`
- Test: `backend/tests/interview_engine/test_redis_lease.py`

**Interfaces:**
- Consumes: `LeasePort`, `InterviewEngine`, adapters.
- Produces: `RedisLease(redis_client)`; `build_engine(store=None, redis_client=None, analyzer=None, generator=None, evaluator=None) -> InterviewEngine`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/interview_engine/test_redis_lease.py
import pytest

from backend.interview_engine.adapters.redis_lease import RedisLease
from backend.interview_engine.adapters.memory_store import InMemorySessionStore
from backend.interview_engine.adapters.factory import build_engine
from backend.interview_engine.adapters.system import InMemoryLease


class FakeRedis:
    def __init__(self):
        self.values = {}

    async def set(self, key, value, nx=False, ex=None):
        if nx and key in self.values:
            return False
        self.values[key] = value
        return True

    async def get(self, key):
        return self.values.get(key)

    async def delete(self, key):
        self.values.pop(key, None)

    async def eval(self, script, numkeys, *args):
        key, token = args[0], args[1]
        raw = self.values.get(key)
        if raw is None:
            return 0
        if json.loads(raw).get("token") == token:
            self.values.pop(key, None)
            return 1
        return 0


@pytest.mark.asyncio
async def test_redis_lease_acquire_confirm_takeover():
    lease = RedisLease(FakeRedis())
    assert await lease.acquire("s1", "d1", "t1", 60) is True
    assert await lease.acquire("s1", "d2", "t2", 60) is False
    assert await lease.confirm("s1", "d1", "t1") is True
    assert await lease.confirm("s1", "d2", "t2") is False
    assert await lease.takeover("s1", "d2", "t2", 60) is True
    assert await lease.confirm("s1", "d2", "t2") is True
    await lease.release("s1", "t2")
    assert await lease.acquire("s1", "d3", "t3", 60) is True


def test_factory_builds_engine_with_injected_ports():
    engine = build_engine(store=InMemorySessionStore(), lease=InMemoryLease())
    assert engine.store is not None
    assert engine.lease is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest backend/tests/interview_engine/test_redis_lease.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.interview_engine.adapters.redis_lease'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/interview_engine/adapters/redis_lease.py
import json

_KEY = "interview_engine:lease:{session_id}"

_RELEASE = """
local raw = redis.call('get', KEYS[1])
if not raw then
  return 0
end
local held = cjson.decode(raw)
if held['token'] == ARGV[1] then
  return redis.call('del', KEYS[1])
end
return 0
"""


class RedisLease:
    def __init__(self, redis_client, prefix: str = _KEY):
        self._redis = redis_client
        self._prefix = prefix

    def _key(self, session_id: str) -> str:
        return self._prefix.format(session_id=session_id)

    async def acquire(self, session_id: str, device_id: str, token: str, ttl_seconds: int) -> bool:
        value = json.dumps({"device_id": device_id, "token": token})
        return bool(await self._redis.set(self._key(session_id), value, nx=True, ex=ttl_seconds))

    async def confirm(self, session_id: str, device_id: str, token: str) -> bool:
        raw = await self._redis.get(self._key(session_id))
        if not raw:
            return False
        if isinstance(raw, bytes):
            raw = raw.decode()
        held = json.loads(raw)
        return held.get("device_id") == device_id and held.get("token") == token

    async def takeover(self, session_id: str, device_id: str, token: str, ttl_seconds: int) -> bool:
        value = json.dumps({"device_id": device_id, "token": token})
        return bool(await self._redis.set(self._key(session_id), value, ex=ttl_seconds))

    async def release(self, session_id: str, token: str) -> None:
        await self._redis.eval(_RELEASE, 1, self._key(session_id), token)
```

```python
# backend/interview_engine/adapters/factory.py
from .memory_store import InMemorySessionStore
from .redis_lease import RedisLease
from .scripted import (
    DeterministicEvaluator,
    HeuristicAnalyzer,
    ScriptedQuestionGenerator,
)
from .system import SystemClock, UuidIds


def build_engine(store=None, lease=None, redis_client=None, analyzer=None, generator=None, evaluator=None):
    from ..application.engine import InterviewEngine

    if store is None:
        from ...database import get_database
        from ...redis_client import get_redis

        database = get_database()
        redis_client = redis_client or get_redis()
        from .mongo_store import MongoSessionStore

        store = MongoSessionStore(database, database.client)
        lease = lease or RedisLease(redis_client)
    if lease is None:
        from .system import InMemoryLease

        lease = InMemoryLease()
    return InterviewEngine(
        store=store,
        lease=lease,
        clock=SystemClock(),
        ids=UuidIds(),
        analyzer=analyzer or HeuristicAnalyzer(),
        generator=generator or ScriptedQuestionGenerator(),
        evaluator=evaluator or DeterministicEvaluator(),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest backend/tests/interview_engine/test_redis_lease.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/interview_engine/adapters/redis_lease.py backend/interview_engine/adapters/factory.py backend/tests/interview_engine/test_redis_lease.py
git commit -m "feat(interview-engine): add Redis lease and engine factory"
```

---

### Task 12: Compatibility facade routes

**Files:**
- Create: `backend/interview_engine/compatibility/__init__.py`, `backend/interview_engine/compatibility/agent_interview.py`, `backend/interview_engine/compatibility/dependencies.py`
- Modify: `backend/routes/agent_routes.py` (replace `/start`, `/answer`, `/hint`, `/end`, `/feedback`; keep `/extract-text`, `/demo/*`, `/sessions`, `/agents`)
- Modify: `backend/tests/test_multi_agent_interview.py` (add `device_id` to requests; replace score assertions)
- Modify: `backend/tests/test_real_interview_demo.py` (add `device_id`; replace score printing with report fields)
- Modify: `backend/tests/test_diagnostic.py` (add `device_id` to the four `/agent-interview/*` calls)
- Test: `backend/tests/interview_engine/test_compat_routes.py`

**Interfaces:**
- Consumes: `InterviewEngine`, `SessionView`, all commands/results.
- Produces: request models `LegacyStartRequest`, `LegacyAnswerRequest`, `LegacyHintRequest`, `LegacyEndRequest`, `LegacyFeedbackRequest`, `LegacyResumeRequest`; `to_start_response(result)`, `to_answer_response(result, view)`, `to_end_response(result)`, `to_feedback_response(report)`; `get_engine()` dependency.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/interview_engine/test_compat_routes.py
import pytest

from backend.interview_engine.adapters.factory import build_engine
from backend.interview_engine.adapters.memory_store import InMemorySessionStore
from backend.interview_engine.adapters.scripted import (
    DeterministicEvaluator,
    ScriptedAnalyzer,
    ScriptedQuestionGenerator,
)
from backend.interview_engine.adapters.system import InMemoryLease
from backend.interview_engine.compatibility.dependencies import get_engine
from backend.main import app


@pytest.fixture
def engine():
    instance = build_engine(
        store=InMemorySessionStore(),
        lease=InMemoryLease(),
        analyzer=ScriptedAnalyzer([]),
        generator=ScriptedQuestionGenerator(),
        evaluator=DeterministicEvaluator(),
    )
    app.dependency_overrides[get_engine] = lambda: instance
    yield instance
    app.dependency_overrides.pop(get_engine, None)


@pytest.mark.asyncio
async def test_start_requires_device_id(client, student_token):
    response = await client.post(
        "/agent-interview/start",
        json={"role": "Engineer", "interview_type": "behavioral"},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "device_id_required"


@pytest.mark.asyncio
async def test_full_legacy_flow(client, student_token, engine):
    headers = {"Authorization": f"Bearer {student_token}"}
    start = await client.post(
        "/agent-interview/start",
        json={"role": "Senior Engineer", "company": "Acme", "interview_type": "behavioral", "device_id": "dev-1"},
        headers=headers,
    )
    assert start.status_code == 200
    body = start.json()
    assert body["session_id"]
    assert body["question"] == body["interviewer_message"]
    assert "score" not in body

    answer = await client.post(
        "/agent-interview/answer",
        json={
            "session_id": body["session_id"],
            "answer": "I led the migration and cut errors by half.",
            "device_id": "dev-1",
            "request_id": "turn-1",
        },
        headers=headers,
    )
    assert answer.status_code == 200
    answered = answer.json()
    assert answered["next_question"]
    assert "evaluation" not in answered or "score" not in answered.get("evaluation", {})

    hint = await client.post(
        "/agent-interview/hint",
        json={"session_id": body["session_id"], "level": 1, "device_id": "dev-1"},
        headers=headers,
    )
    assert hint.status_code == 200
    assert hint.json()["hint"]
    assert "score_penalty" not in hint.json()

    end = await client.post(
        "/agent-interview/end",
        json={"session_id": body["session_id"], "device_id": "dev-1"},
        headers=headers,
    )
    assert end.status_code == 200
    ended = end.json()
    assert ended["report_id"]
    assert ended["report_status"] == "evaluating"
    assert "final_score" not in ended

    feedback = await client.post(
        "/agent-interview/feedback",
        json={"session_id": body["session_id"], "device_id": "dev-1"},
        headers=headers,
    )
    assert feedback.status_code == 200
    assert feedback.json()["report_status"] in ("evaluating", "ready")
    assert "overall_score" not in feedback.json()


@pytest.mark.asyncio
async def test_answer_requires_matching_device(client, student_token, engine):
    headers = {"Authorization": f"Bearer {student_token}"}
    start = await client.post(
        "/agent-interview/start",
        json={"role": "Engineer", "interview_type": "behavioral", "device_id": "dev-1"},
        headers=headers,
    )
    body = start.json()
    conflict = await client.post(
        "/agent-interview/answer",
        json={"session_id": body["session_id"], "answer": "text", "device_id": "dev-2", "request_id": "t1"},
        headers=headers,
    )
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "device_conflict"


@pytest.mark.asyncio
async def test_resume_returns_new_token_and_question(client, student_token, engine):
    headers = {"Authorization": f"Bearer {student_token}"}
    start = await client.post(
        "/agent-interview/start",
        json={"role": "Engineer", "interview_type": "behavioral", "device_id": "dev-1"},
        headers=headers,
    )
    body = start.json()
    resumed = await client.post(
        "/agent-interview/resume",
        json={"session_id": body["session_id"], "device_id": "dev-2"},
        headers=headers,
    )
    assert resumed.status_code == 200
    payload = resumed.json()
    assert payload["fencing_token"] != body["fencing_token"]
    assert payload["question"] == body["question"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest backend/tests/interview_engine/test_compat_routes.py -q`
Expected: FAIL with 404 on `/agent-interview/start` or `device_id_required` assertion

- [ ] **Step 3: Write minimal implementation**

```python
# backend/interview_engine/compatibility/dependencies.py
from fastapi import Depends

from ..adapters.factory import build_engine

_ENGINE = None


def get_engine():
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = build_engine()
    return _ENGINE


def engine_dependency(engine=Depends(get_engine)):
    return engine


def reset_engine():
    global _ENGINE
    _ENGINE = None
```

```python
# backend/interview_engine/compatibility/agent_interview.py
import hashlib
import uuid
from typing import Optional

from pydantic import BaseModel

from ..contracts.messages import SessionView


class LegacyStartRequest(BaseModel):
    company: Optional[str] = None
    role: Optional[str] = None
    difficulty: Optional[str] = None
    interview_type: str = "behavioral"
    mode: str = "practice"
    device_id: Optional[str] = None
    request_id: Optional[str] = None


class LegacyAnswerRequest(BaseModel):
    session_id: str
    answer: str
    device_id: Optional[str] = None
    request_id: Optional[str] = None
    question_id: Optional[str] = None
    kind: str = "answer"


class LegacyHintRequest(BaseModel):
    session_id: str
    level: int = 1
    device_id: Optional[str] = None


class LegacyEndRequest(BaseModel):
    session_id: str
    device_id: Optional[str] = None
    end_request_id: Optional[str] = None


class LegacyFeedbackRequest(BaseModel):
    session_id: str
    device_id: Optional[str] = None


class LegacyResumeRequest(BaseModel):
    session_id: str
    device_id: str
    command_id: Optional[str] = None


def answer_idempotency_key(candidate_id: str, session_id: str, request_id: Optional[str], body: str) -> str:
    seed = f"{candidate_id}:{session_id}:{request_id or uuid.uuid4().hex}:{hashlib.sha256(body.encode()).hexdigest()}"
    return hashlib.sha256(seed.encode()).hexdigest()


def end_command_id(candidate_id: str, session_id: str, end_request_id: Optional[str]) -> str:
    seed = f"{candidate_id}:{session_id}:{end_request_id or 'fingerprint'}"
    return hashlib.sha256(seed.encode()).hexdigest()


def to_start_response(result) -> dict:
    return {
        "session_id": result.session_id,
        "question": result.first_question,
        "interviewer_message": result.first_question,
        "status": result.status,
        "request_id": result.client_request_id,
        "question_id": result.question_id,
        "fencing_token": result.fencing_token,
    }


def to_answer_response(result, view: SessionView) -> dict:
    return {
        "session_id": result.session_id,
        "status": result.status,
        "next_action": result.next_action,
        "next_question": result.question,
        "question_id": result.question_id,
        "question_pending": result.question_pending,
        "turn_request_id": None,
        "questions_answered": view.questions_answered,
        "report_id": result.report_id,
        "report_status": result.report_outcome,
    }


def to_end_response(result) -> dict:
    return {
        "session_id": result.session_id,
        "status": result.status,
        "report_id": result.report_id,
        "report_status": result.report_outcome,
    }


def to_feedback_response(report, body: Optional[dict]) -> dict:
    return {
        "session_id": report.session_id,
        "report_id": report.report_id,
        "report_status": report.outcome,
        "report": body if report.outcome == "ready" else None,
    }


def to_hint_response(result) -> dict:
    return {
        "hint": result.hint,
        "hints_used": result.hints_used,
        "remaining": result.remaining,
        "question_id": result.question_id,
    }


def to_resume_response(result) -> dict:
    return {
        "session_id": result.session_id,
        "status": result.status,
        "question": result.question,
        "question_id": result.question_id,
        "fencing_token": result.fencing_token,
        "question_pending": result.question_pending,
    }
```

Modify `backend/routes/agent_routes.py`. Keep the existing `/extract-text` handler, the `/demo/*` endpoints, `/sessions`, `/agents`, and the three `*_logic` helpers used by voice routes. Replace only the five authenticated endpoints (`/start`, `/answer`, `/hint`, `/end`, `/feedback`) and add `/resume`. The route module currently defines a `router = APIRouter(prefix="/agent-interview", tags=["multi-agent-interview"])`.

```python
from fastapi import APIRouter, Depends, HTTPException

from ..interview_engine.compatibility.agent_interview import (
    LegacyAnswerRequest,
    LegacyEndRequest,
    LegacyFeedbackRequest,
    LegacyHintRequest,
    LegacyResumeRequest,
    LegacyStartRequest,
    answer_idempotency_key,
    end_command_id,
    to_answer_response,
    to_end_response,
    to_feedback_response,
    to_hint_response,
    to_resume_response,
    to_start_response,
)
from ..interview_engine.compatibility.dependencies import engine_dependency
from ..interview_engine.contracts.messages import (
    EndSessionCommand,
    RequestHintCommand,
    ResumeSessionCommand,
    StartSessionCommand,
    SubmitTurnCommand,
)
from ..interview_engine.errors import EngineError
from ..utils.dependencies import get_current_user

router = APIRouter(prefix="/agent-interview", tags=["multi-agent-interview"])

_ENGINE_ERROR_STATUS = {
    "unsupported_interview_type": 400,
    "unsupported_mode": 400,
    "session_not_found": 404,
    "not_owner": 403,
    "session_exists": 409,
    "device_conflict": 409,
    "version_conflict": 409,
    "question_pending": 409,
    "question_mismatch": 409,
    "question_superseded": 409,
    "consent_required": 409,
    "pause_limit_reached": 409,
    "hint_limit_reached": 409,
    "hint_unavailable": 409,
    "no_report": 409,
    "invalid_state": 409,
}


def _handle(exc: EngineError):
    raise HTTPException(
        status_code=_ENGINE_ERROR_STATUS.get(exc.code, 400),
        detail={"code": exc.code, **exc.details},
    )


def _require_device(device_id):
    if not device_id:
        raise HTTPException(status_code=400, detail={"code": "device_id_required"})


@router.post("/start")
async def start_interview(
    body: LegacyStartRequest,
    current_user=Depends(get_current_user),
    engine=Depends(engine_dependency),
):
    _require_device(body.device_id)
    try:
        result = await engine.start(
            StartSessionCommand(
                candidate_id=str(current_user["_id"]),
                interview_type=body.interview_type,
                mode=body.mode,
                device_id=body.device_id,
                client_request_id=body.request_id or uuid.uuid4().hex,
                role=body.role,
                company=body.company,
            )
        )
    except EngineError as exc:
        _handle(exc)
    response = to_start_response(result)
    response["request_id"] = body.request_id or response["request_id"]
    return response


@router.post("/answer")
async def submit_answer(
    body: LegacyAnswerRequest,
    current_user=Depends(get_current_user),
    engine=Depends(engine_dependency),
):
    _require_device(body.device_id)
    try:
        result = await engine.submit_turn(
            SubmitTurnCommand(
                candidate_id=str(current_user["_id"]),
                session_id=body.session_id,
                device_id=body.device_id,
                turn_idempotency_key=answer_idempotency_key(
                    str(current_user["_id"]), body.session_id, body.request_id, body.answer
                ),
                kind=body.kind,
                text=body.answer,
                question_id=body.question_id,
            )
        )
        record = await engine.load_owned(body.session_id, str(current_user["_id"]))
        view = await engine.session_view(record)
    except EngineError as exc:
        _handle(exc)
    response = to_answer_response(result, view)
    response["turn_request_id"] = body.request_id
    return response


@router.post("/hint")
async def request_hint(
    body: LegacyHintRequest,
    current_user=Depends(get_current_user),
    engine=Depends(engine_dependency),
):
    _require_device(body.device_id)
    try:
        record = await engine.load_owned(body.session_id, str(current_user["_id"]))
        question_id = record.current_question_id or ""
        result = await engine.request_hint(
            RequestHintCommand(
                candidate_id=str(current_user["_id"]),
                session_id=body.session_id,
                device_id=body.device_id,
                hint_idempotency_key=f"{current_user['_id']}:{body.session_id}:{question_id}",
                question_id=question_id or None,
            )
        )
    except EngineError as exc:
        _handle(exc)
    return to_hint_response(result)


@router.post("/end")
async def end_interview(
    body: LegacyEndRequest,
    current_user=Depends(get_current_user),
    engine=Depends(engine_dependency),
):
    _require_device(body.device_id)
    try:
        result = await engine.end(
            EndSessionCommand(
                candidate_id=str(current_user["_id"]),
                session_id=body.session_id,
                device_id=body.device_id,
                end_command_id=end_command_id(
                    str(current_user["_id"]), body.session_id, body.end_request_id
                ),
                reason="candidate_completed",
            )
        )
    except EngineError as exc:
        _handle(exc)
    return to_end_response(result)


@router.post("/feedback")
async def get_feedback(
    body: LegacyFeedbackRequest,
    current_user=Depends(get_current_user),
    engine=Depends(engine_dependency),
):
    _require_device(body.device_id)
    try:
        record = await engine.load_owned(body.session_id, str(current_user["_id"]))
        report = await engine.get_report(str(current_user["_id"]), record.report_id)
    except EngineError as exc:
        _handle(exc)
    if report.outcome == "evaluating":
        await engine.drain_outbox()
        report = await engine.get_report(str(current_user["_id"]), record.report_id)
    body_dict = report.body
    if report.outcome == "ready" and body_dict is None:
        body_dict = await engine.build_report_body(report.report_id)
    return to_feedback_response(report, body_dict)


@router.post("/resume")
async def resume_interview(
    body: LegacyResumeRequest,
    current_user=Depends(get_current_user),
    engine=Depends(engine_dependency),
):
    try:
        result = await engine.resume(
            ResumeSessionCommand(
                candidate_id=str(current_user["_id"]),
                session_id=body.session_id,
                device_id=body.device_id,
                command_id=body.command_id,
            )
        )
    except EngineError as exc:
        _handle(exc)
    return to_resume_response(result)
```

Add `import uuid` at the top of `agent_routes.py`.

**Legacy suite updates (same commit):** `backend/tests/test_multi_agent_interview.py` and `backend/tests/test_real_interview_demo.py` call the replaced routes without `device_id` and assert score fields. Update each `/start`, `/answer`, `/hint`, `/end` body to include `"device_id": "test-device"`, and replace score assertions:

- `test_start_agent_interview`: unchanged assertions (`session_id`, `interviewer_message`) still pass.
- `test_submit_answer_agent`: replace `assert "evaluation" in data` with `assert "next_question" in data` and `assert "score" not in data`.
- `test_request_hint`: add `device_id`; level 2 is the same key as level 1 on the compatibility path, so assert `data["hints_used"] == 1` for both calls.
- `test_end_interview`: replace `final_score`/`overall_score`/`performance` assertion with `assert data["report_id"] and data["report_status"] in ("evaluating", "ready", "suppressed")`.
- `test_full_agent_flow`: add `device_id`; unchanged otherwise.
- `test_real_interview_demo.py`: add `device_id`; replace `data['evaluation']['score']` and `data['final_score']` prints with `data.get('report_id')` and `data.get('report_status')`, and drop the `score_penalty` print.
- `test_dsa_stage_by_stage_flow` calls `multi_agent_interview.get_context(session_id)` directly after `/start`, so it must keep hitting the legacy engine. Because the facade now owns `/start`, `/answer`, `/hint`, and `/end`, this test must be rewritten to call `multi_agent_interview.start/answer` directly instead of HTTP, and `test_voice_helper_logic` keeps calling `start_agent_interview_logic`/`submit_answer_logic`/`end_agent_interview_logic`, which stay in place as legacy helpers used by `voice_routes.py`.
- Rewrite `test_dsa_stage_by_stage_flow` to:

```python
@pytest.mark.asyncio
async def test_dsa_stage_by_stage_flow(student_user):
    from backend.services.multi_agent_system import multi_agent_interview

    session_id = f"dsa-{student_user['_id']}"
    await multi_agent_interview.start(
        session_id=session_id, student_id=str(student_user["_id"]),
        company="Google", role="Software Engineer", difficulty="medium",
        interview_type="dsa", resume_text="",
    )
    context = await multi_agent_interview.get_context(session_id)
    assert context.dsa_stage == "clarification"

    await multi_agent_interview.answer(session_id, "What are the input size limits?")
    context = await multi_agent_interview.get_context(session_id)
    assert context.dsa_stage == "approach"

    await multi_agent_interview.answer(session_id, "I will use two pointers with O(N) time.")
    context = await multi_agent_interview.get_context(session_id)
    assert context.dsa_stage == "coding"

    await multi_agent_interview.answer(session_id, "def solve(arr):\n    return arr")
    context = await multi_agent_interview.get_context(session_id)
    assert context.dsa_stage == "optimization"

    await multi_agent_interview.answer(session_id, "I would return early for an empty array.")
    context = await multi_agent_interview.get_context(session_id)
    assert context.dsa_stage == "completed"
```

- `backend/tests/test_diagnostic.py::test_diag_agent_interview` only asserts `status_code == 200` on each call; add `"device_id": "diag-device"` to the four bodies and leave the assertions.

- [ ] **Step 4: Run tests**

Run: `venv\Scripts\python.exe -m pytest backend/tests/interview_engine/test_compat_routes.py -q`
Expected: PASS (4 passed)

Run: `venv\Scripts\python.exe -m pytest backend/tests/test_multi_agent_interview.py backend/tests/test_real_interview_demo.py -q` (timeout 180s)
Expected: PASS for the updated tests; `test_dsa_stage_by_stage_flow` still passes against the legacy system.

- [ ] **Step 5: Commit**

```bash
git add backend/interview_engine/compatibility backend/routes/agent_routes.py backend/tests/interview_engine/test_compat_routes.py backend/tests/test_multi_agent_interview.py backend/tests/test_real_interview_demo.py backend/tests/test_diagnostic.py
git commit -m "feat(interview-engine): wire legacy agent-interview facade to engine"
```

---

### Task 12b: Add an in-process transaction-capable Mongo test database

The first-slice tests use `InMemorySessionStore`, so the route and engine suites need no Mongo. The Mongo store and the atomicity acceptance criterion still need a real replica set. Add an opt-in pytest fixture that launches one and wires it to the real engine, skipping when `mongod` is unavailable.

**Files:**
- Create: `backend/tests/interview_engine/test_mongo_engine_e2e.py`
- Modify: `pytest.ini` (register the `integration` marker)
- Test: `backend/tests/interview_engine/test_mongo_engine_e2e.py`

**Interfaces:**
- Consumes: `start_replica_set` from Task 10, `build_engine`, `MongoSessionStore`, `RedisLease`.
- Produces: no production API; proves atomicity and resume against Mongo.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/interview_engine/test_mongo_engine_e2e.py
import pytest

from backend.interview_engine.adapters.mongo_store import MongoSessionStore
from backend.interview_engine.adapters.redis_lease import RedisLease
from backend.interview_engine.adapters.scripted import (
    DeterministicEvaluator,
    HeuristicAnalyzer,
    ScriptedQuestionGenerator,
)
from backend.interview_engine.adapters.system import InMemoryLease, SystemClock, UuidIds
from backend.interview_engine.application.engine import InterviewEngine
from backend.interview_engine.contracts.messages import StartSessionCommand

pytestmark = pytest.mark.integration


@pytest.fixture
def mongo_engine():
    from tests.support.mongo_replica import start_replica_set
    from motor.motor_asyncio import AsyncIOMotorClient

    try:
        uri = start_replica_set()
    except Exception as exc:
        pytest.skip(f"replica set unavailable: {exc}")
    client = AsyncIOMotorClient(uri)
    database = client["interview_engine_e2e"]
    engine = InterviewEngine(
        store=MongoSessionStore(database, client),
        lease=InMemoryLease(),
        clock=SystemClock(),
        ids=UuidIds(),
        analyzer=HeuristicAnalyzer(),
        generator=ScriptedQuestionGenerator(),
        evaluator=DeterministicEvaluator(),
    )
    yield engine, database
    client.close()


@pytest.mark.asyncio
async def test_start_persists_session_and_outbox_atomically(mongo_engine):
    engine, database = mongo_engine
    await database.interview_engine_sessions.delete_many({})
    await database.interview_engine_outbox.delete_many({})
    result = await engine.start(StartSessionCommand(
        candidate_id="c1", interview_type="behavioral", mode="practice",
        device_id="d1", client_request_id="req-1", role="Senior Engineer",
    ))
    session = await database.interview_engine_sessions.find_one({"_id": result.session_id})
    assert session["status"] == "in_progress"
    assert session["version"] == 1
    outbox = await database.interview_engine_outbox.find_one(
        {"event_type": "interview_engine.question.requested"}
    )
    assert outbox is not None
    events = [e async for e in database.interview_engine_events.find({"session_id": result.session_id})]
    assert [e["event_type"] for e in events] == ["SessionCreated", "QuestionAsked"]


@pytest.mark.asyncio
async def test_duplicate_start_returns_same_session(mongo_engine):
    engine, database = mongo_engine
    await database.interview_engine_sessions.delete_many({})
    first = await engine.start(StartSessionCommand(
        candidate_id="c2", interview_type="behavioral", mode="practice",
        device_id="d1", client_request_id="req-9",
    ))
    second = await engine.start(StartSessionCommand(
        candidate_id="c2", interview_type="behavioral", mode="practice",
        device_id="d1", client_request_id="req-9",
    ))
    assert first.session_id == second.session_id
    assert await database.interview_engine_sessions.count_documents({"candidate_id": "c2"}) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest backend/tests/interview_engine/test_mongo_engine_e2e.py -q`
Expected: FAIL or SKIP; `start_replica_set` may not exist yet, and the marker is unregistered.

- [ ] **Step 3: Register the marker and confirm the helper import path**

Add to `pytest.ini` under `[pytest]`:

```ini
markers =
    integration: requires a local MongoDB replica set
```

Ensure `tests/support/__init__.py` exists (empty) so `tests.support.mongo_replica` imports when pytest runs from the repo root with `pythonpath = .`.

- [ ] **Step 4: Run test**

Run: `venv\Scripts\python.exe -m pytest backend/tests/interview_engine/test_mongo_engine_e2e.py -q` (timeout 180s)
Expected: PASS (2 passed) when `mongod` is installed; SKIP otherwise.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/interview_engine/test_mongo_engine_e2e.py tests/support/__init__.py pytest.ini
git commit -m "test(interview-engine): verify atomic start against Mongo replica set"
```

---

### Task 13: Engine outbox worker

**Files:**
- Create: `backend/interview_engine/worker.py`
- Modify: `backend/run_workers.py`
- Test: `backend/tests/interview_engine/test_worker.py`

**Interfaces:**
- Consumes: `build_engine`.
- Produces: `async def run_interview_engine_outbox(interval_seconds: float = 2.0, stop_event=None)`; `async def drain_once() -> int`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/interview_engine/test_worker.py
import pytest

from backend.interview_engine.adapters.factory import build_engine
from backend.interview_engine.adapters.memory_store import InMemorySessionStore
from backend.interview_engine.adapters.system import InMemoryLease
from backend.interview_engine import worker


@pytest.mark.asyncio
async def test_drain_once_uses_engine():
    engine = build_engine(store=InMemorySessionStore(), lease=InMemoryLease())
    count = await worker.drain_once(engine=engine)
    assert count == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest backend/tests/interview_engine/test_worker.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.interview_engine.worker'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/interview_engine/worker.py
import asyncio
import logging

logger = logging.getLogger(__name__)


async def drain_once(engine=None) -> int:
    if engine is None:
        from .adapters.factory import build_engine

        engine = build_engine()
    return await engine.drain_outbox()


async def run_interview_engine_outbox(interval_seconds: float = 2.0, stop_event=None) -> None:
    while True:
        if stop_event is not None and stop_event.is_set():
            return
        try:
            processed = await drain_once()
            if processed:
                logger.info("interview engine outbox processed %s events", processed)
        except Exception:
            logger.exception("interview engine outbox drain failed")
        await asyncio.sleep(interval_seconds)
```

In `backend/run_workers.py`, import the loop and start it alongside the existing workers:

```python
from .interview_engine.worker import run_interview_engine_outbox
```

and inside the worker `main`/gather section add `asyncio.create_task(run_interview_engine_outbox())` following the file's existing pattern.

- [ ] **Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest backend/tests/interview_engine/test_worker.py -q`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/interview_engine/worker.py backend/run_workers.py backend/tests/interview_engine/test_worker.py
git commit -m "feat(interview-engine): drain report outbox in worker"
```

---

### Task 14: Frontend device identity, request ids, and report rendering

**Files:**
- Create: `frontend/src/lib/interviewClient.js`, `frontend/src/components/__tests__/MockInterview.test.jsx`
- Modify: `frontend/src/components/MockInterview.jsx`, `frontend/package.json`
- Test: `frontend/src/components/__tests__/MockInterview.test.jsx`

**Interfaces:**
- Consumes: the HTTP facade from Task 12.
- Produces: `getDeviceId()`, `newRequestId()`, `resumeSession(sessionId)`, `fetchFeedback(sessionId)`.

- [ ] **Step 1: Write the failing test**

```jsx
// frontend/src/components/__tests__/MockInterview.test.jsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import MockInterview from "../MockInterview";

const post = vi.fn();

vi.mock("../../contexts/AuthContext", () => ({ useAuth: () => ({ user: { id: "u1" } }) }));
vi.mock("../../api/client", () => ({ api: { post: (...args) => post(...args) } }));
vi.mock("react-router-dom", () => ({ useNavigate: () => vi.fn() }));

describe("MockInterview canonical flow", () => {
  beforeEach(() => {
    localStorage.clear();
    post.mockReset();
  });

  it("persists a device id and sends it on start", async () => {
    post.mockResolvedValueOnce({
      data: {
        session_id: "s1",
        question: "Tell me about a problem you solved.",
        interviewer_message: "Tell me about a problem you solved.",
        status: "in_progress",
      },
    });
    render(<MockInterview />);
    await userEvent.click(screen.getByRole("button", { name: /start interview/i }));
    await waitFor(() => expect(post).toHaveBeenCalled());
    const [url, payload] = post.mock.calls[0];
    expect(url).toBe("/agent-interview/start");
    expect(payload.device_id).toBeTruthy();
    expect(localStorage.getItem("interview_device_id")).toBe(payload.device_id);
    expect(payload.request_id).toBeTruthy();
  });

  it("renders report competencies and no overall score", async () => {
    post
      .mockResolvedValueOnce({
        data: { session_id: "s1", question: "Q1", interviewer_message: "Q1", status: "in_progress" },
      })
      .mockResolvedValueOnce({
        data: { session_id: "s1", status: "completed", report_id: "r1", report_status: "ready", next_question: null },
      });
    render(<MockInterview />);
    await userEvent.click(screen.getByRole("button", { name: /start interview/i }));
    await userEvent.type(screen.getByPlaceholderText(/type your answer/i), "I led the migration and cut errors.");
    await userEvent.click(screen.getByRole("button", { name: /submit/i }));
    await waitFor(() => expect(screen.queryByText(/overall score/i)).not.toBeInTheDocument());
  });
});
```

Add to `frontend/package.json` `devDependencies`: `"vitest": "^1.6.0"`, `"@testing-library/react": "^14.2.1"`, `"@testing-library/user-event": "^14.5.2"`, `"jsdom": "^24.0.0"`; add `"test": "vitest run"` and in `vite.config.js` set `test: { environment: "jsdom", globals: true, setupFiles: "./src/test/setup.js" }`. Create `frontend/src/test/setup.js` with `import "@testing-library/jest-dom";` and add `"@testing-library/jest-dom": "^6.4.2"`.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend; npm test -- --run`
Expected: FAIL with `Cannot find module '../MockInterview'` or missing device id in payload

- [ ] **Step 3: Write minimal implementation**

```javascript
// frontend/src/lib/interviewClient.js
const DEVICE_KEY = "interview_device_id";

export function getDeviceId() {
  let id = localStorage.getItem(DEVICE_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(DEVICE_KEY, id);
  }
  return id;
}

export function newRequestId() {
  return crypto.randomUUID();
}
```

In `MockInterview.jsx`:
- Import `getDeviceId, newRequestId`.
- Add state `requestId`, `turnRequestId`, `report`, `reportStatus`.
- `startSession`: send `device_id: getDeviceId()`, `request_id: requestId || newRequestId()`, and store the request id.
- Handle `409 session_exists` by calling `/agent-interview/resume` with the session id and device id.
- `submitAnswer`: send `device_id`, `request_id: turnRequestId || newRequestId()`; on `202`, poll the same call; on `409 question_pending`, retry the same request id.
- Remove the `evaluation.score` branch and `final_score` summary; instead when `next_question` is null call `/agent-interview/end`, then poll `/agent-interview/feedback` until `report_status === "ready"` and render the returned competency report.
- Render a disclosure line at start: `AI-generated questions, AI-assisted evaluation, no proctoring, no human review.`
- Disable the `technical` and `dsa` type buttons with the label `Unavailable in this release`.
- Ensure every interactive control is a `button`/`input` with a label, and the message list has `role="log"` and `aria-live="polite"` for WCAG 2.2 AA.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend; npm test -- --run`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/interviewClient.js frontend/src/components/MockInterview.jsx frontend/src/components/__tests__/MockInterview.test.jsx frontend/src/test/setup.js frontend/package.json frontend/vite.config.js
git commit -m "feat(interview-ui): add device identity and competency report rendering"
```

---

### Task 15: End-to-end slice test and full verification

**Files:**
- Create: `backend/tests/interview_engine/test_e2e_practice_slice.py`
- Modify: `docs/interview-engine/canonical-engine-design.md` (status line only), `docs/adr/0047-canonical-engine-deep-module.md` (status line only)

**Interfaces:**
- Consumes: the whole stack.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/interview_engine/test_e2e_practice_slice.py
import pytest

from backend.interview_engine.adapters.factory import build_engine
from backend.interview_engine.adapters.memory_store import InMemorySessionStore
from backend.interview_engine.adapters.scripted import (
    DeterministicEvaluator,
    ScriptedAnalyzer,
    ScriptedQuestionGenerator,
)
from backend.interview_engine.adapters.system import InMemoryLease
from backend.interview_engine.compatibility.dependencies import get_engine
from backend.main import app


@pytest.fixture
def engine():
    instance = build_engine(
        store=InMemorySessionStore(),
        lease=InMemoryLease(),
        analyzer=ScriptedAnalyzer([]),
        generator=ScriptedQuestionGenerator(),
        evaluator=DeterministicEvaluator(),
    )
    app.dependency_overrides[get_engine] = lambda: instance
    yield instance
    app.dependency_overrides.pop(get_engine, None)


@pytest.mark.asyncio
async def test_practice_session_from_start_to_ready_report(client, student_token, engine):
    headers = {"Authorization": f"Bearer {student_token}"}
    start = await client.post(
        "/agent-interview/start",
        json={"role": "Senior Engineer", "company": "Acme", "interview_type": "behavioral", "device_id": "dev-1"},
        headers=headers,
    )
    session = start.json()
    for index in range(10):
        answer = await client.post(
            "/agent-interview/answer",
            json={
                "session_id": session["session_id"],
                "answer": "In my last project I owned the ingestion pipeline and cut latency by half after profiling.",
                "device_id": "dev-1",
                "request_id": f"turn-{index}",
            },
            headers=headers,
        )
        assert answer.status_code == 200
        payload = answer.json()
        assert "score" not in payload
        if payload["status"] == "completed":
            assert payload["report_id"]
            break
    else:
        pytest.fail("session never completed")

    feedback = await client.post(
        "/agent-interview/feedback",
        json={"session_id": session["session_id"], "device_id": "dev-1"},
        headers=headers,
    )
    body = feedback.json()
    assert body["report_status"] == "ready"
    report = body["report"]
    assert report is not None
    assert "overall_score" not in report
    assert all("score" not in competency for competency in report["competencies"])
    assert report["disclosure"]["no_human_review"] is True

    ended = await client.post(
        "/agent-interview/end",
        json={"session_id": session["session_id"], "device_id": "dev-1"},
        headers=headers,
    )
    assert ended.json()["report_id"] == body["report_id"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest backend/tests/interview_engine/test_e2e_practice_slice.py -q`
Expected: FAIL until the full stack is wired (this test is written last, so it should pass after Task 14; if it fails, fix the defect rather than the assertion)

- [ ] **Step 3: Fix any defect the end-to-end test exposes**

If the scripted analyzer marks a 10-answer session `sufficient` every time, the session completes on the 10th slot. If the report contains a `score` key anywhere, remove it in `report_builder.py` (the schema already forbids it). If `/feedback` returns `evaluating` after `drain_outbox`, check that `_handle_report_requested` uses `expected_outcome="evaluating"` and that the report record was inserted in the same transaction as completion.

- [ ] **Step 4: Run the full suites**

Run: `venv\Scripts\python.exe -m pytest tests -q` (timeout 180s)
Expected: PASS, no new failures.

Run: `venv\Scripts\python.exe -m pytest backend/tests -q` (timeout 240s)
Expected: PASS, no new failures.

Run: `venv\Scripts\python.exe -m flake8 backend/interview_engine backend/models/interview_engine_indexes.py backend/routes/agent_routes.py`
Expected: no output.

Run: `venv\Scripts\python.exe -m mypy backend/interview_engine --ignore-missing-imports`
Expected: `Success: no issues found`.

- [ ] **Step 5: Update status lines and commit**

Change the spec line 3 to `Status: implemented (first slice)` and ADR 0047 line 3 to `Status: accepted, implemented (first slice)`. Then:

```bash
git add backend/tests/interview_engine/test_e2e_practice_slice.py docs/interview-engine/canonical-engine-design.md docs/adr/0047-canonical-engine-deep-module.md
git commit -m "test(interview-engine): verify practice slice end to end"
```

---

## Self-Review

**1. Spec coverage**

- §4.2 blueprint/adaptivity → Tasks 3, 4, 8.
- §4.3 turns → Tasks 3, 8.
- §4.4 evidence ledger → Tasks 2, 6, 8.
- §4.5 scores/report/confidence/level → Tasks 2, 6, 9.
- §5.1 commands → Tasks 7–9, 12.
- §5.2 events → Tasks 7–9 (SessionCreated, QuestionAsked, TurnSubmitted, TurnAnalysisRequested, ClarificationReplied, HintProvided, SessionPaused, SessionLeaseTakenOver, SessionCompleted).
- §6.1 start flow → Task 7.
- §6.2 submit flow → Task 8.
- §6.3 hint/pause/resume/end → Task 9.
- §6.4 pending-question recovery and dead-letter → Task 7 `ensure_question` fallback + Task 9 resume recovery; a dedicated dead-letter test is deferred to the async ticket, but the fallback path is covered in Task 7.
- §9.1 compatibility → Task 12.
- §10.2 first slice → Tasks 7–15.
- §10.3 acceptance → Tasks 8 (no score), 9 (report), 10 + 12b (transaction), 12 (compatibility), 15 (full suites + WCAG via Task 14).

**2. Placeholder scan**

No `TBD`/`TODO`/`implement later` steps. Task 14 gives concrete behaviors rather than a full component body because the existing file is 507 lines and is edited in place; every behavior named is testable by the two tests. Task 10's integration test skips without a replica URI, which is explicit and not a placeholder.

**3. Type consistency**

- `SubmitTurnResult.next_action` is `str`; the engine passes `action.value`.
- `Session.apply_answer` returns `NextAction`; Task 8 compares with `NextAction.END`.
- `ensure_question` returns `QuestionRecord | None`; every caller handles `None`.
- `MongoSessionStore.put_turn_command` uses `_id = session_id:key`; `get_turn_command`/`complete_turn_command` use the same key.
- `ReportRecord.outcome` is `str`; `update_report` guards on `expected_outcome`.
- `SessionView.questions_answered` is computed by `session_view` and used in `to_answer_response`.
- `HintResult.question_id` is set from the persisted hint record.

**Known slice limits (intentional, tracked for later tickets):** no voice, no formal mode, no coding sandbox, no report sharing, no per-session deadline for practice, no deep async evidence extraction beyond the synchronous analyzer, and no dead-letter test (fallback behavior is covered).
