import re
from typing import List, Sequence

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
