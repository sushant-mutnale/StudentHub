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
_MAX_EXCERPTS = 3
_MIN_EXCERPTS = 2
_INSUFFICIENT = "insufficient_evidence"
_CONFLICTING = "conflicting_evidence"
_TIME_COVERAGE = "time_coverage"
_MODE_TECHNICAL = "mode_technical"
_HINT_ASSISTANCE = "hint_assistance"


def _sentences(text: str) -> List[str]:
    return [part.strip() for part in _SENTENCE_SPLIT.split(text.strip()) if part.strip()]


def sentence_excerpt(text: str, limit: int = 2) -> str:
    return " ".join(_sentences(text)[:limit])


def _ordered_items(items: Sequence[EvidenceRecord]) -> List[EvidenceRecord]:
    ordered: List[EvidenceRecord] = []
    seen = set()
    for item in items:
        if item.contradiction and item.signal != "off_topic" and item.turn_id not in seen:
            ordered.append(item)
            seen.add(item.turn_id)
    for item in items:
        if item.signal == "off_topic" or item.turn_id in seen:
            continue
        ordered.append(item)
        seen.add(item.turn_id)
    return ordered


def _excerpts_for(
    items: Sequence[EvidenceRecord], turns_by_id: Dict[str, TurnRecord]
) -> List[Excerpt]:
    usable = []
    for item in _ordered_items(items):
        turn = turns_by_id.get(item.turn_id)
        if turn is None:
            continue
        sentences = _sentences(turn.text)
        if sentences:
            usable.append((item, sentences))
    if not usable:
        return []
    if len(usable) == 1:
        item, sentences = usable[0]
        chunks = [sentences[0]] if len(sentences) == 1 else sentences[:_MIN_EXCERPTS]
        return [
            Excerpt(turn_id=item.turn_id, question_id=item.question_id, text=chunk)
            for chunk in chunks
        ]
    excerpts: List[Excerpt] = []
    for item, _ in usable[:_MAX_EXCERPTS]:
        text = sentence_excerpt(turns_by_id[item.turn_id].text)
        excerpts.append(
            Excerpt(turn_id=item.turn_id, question_id=item.question_id, text=text)
        )
    return excerpts


def _unique_limitations(limitations: Sequence[Limitation]) -> List[Limitation]:
    unique: List[Limitation] = []
    seen = set()
    for limitation in limitations:
        key = (limitation.category, limitation.detail)
        if key in seen:
            continue
        seen.add(key)
        unique.append(limitation)
    return unique


def build_report(
    record: SessionRecord,
    evidence: Sequence[EvidenceRecord],
    turns: Sequence[TurnRecord],
    evaluator_output: EvaluatorOutput,
) -> ReportBody:
    turns_by_id = {turn.turn_id: turn for turn in turns}
    ordered_competencies: List[str] = []
    for group in record.blueprint.groups:
        if group.competency not in ordered_competencies:
            ordered_competencies.append(group.competency)
    competencies: List[CompetencyReport] = []
    for competency in ordered_competencies:
        items = [item for item in evidence if item.competency == competency]
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
                    category=_INSUFFICIENT,
                    detail="No independent evidence was recorded for this competency.",
                )
            )
        else:
            excerpts = _excerpts_for(items, turns_by_id)
            if not excerpts:
                limitations.append(
                    Limitation(
                        category=_MODE_TECHNICAL,
                        detail="No transcript text was available for the recorded evidence, so no excerpt could be shown.",
                    )
                )
            if len(facts) == 1:
                limitations.append(
                    Limitation(
                        category=_INSUFFICIENT,
                        detail="Only one independent instance supports this score.",
                    )
                )
        if any(fact.contradiction for fact in facts):
            limitations.append(
                Limitation(
                    category=_CONFLICTING,
                    detail="A synchronously flagged contradiction caps confidence at low.",
                )
            )
        if any(item.signal == "off_topic" for item in items):
            limitations.append(
                Limitation(
                    category=_TIME_COVERAGE,
                    detail="An off-topic answer consumed part of the coverage available for this competency.",
                )
            )
        competencies.append(
            CompetencyReport(
                competency=competency,
                level=level.value,
                confidence=confidence.value,
                instance_count=len(facts),
                reasons=evaluator_output.reasons.get(competency, []),
                excerpts=excerpts,
                limitations=limitations,
            )
        )
    duration = 0
    if record.started_at and record.completed_at:
        duration = int((record.completed_at - record.started_at).total_seconds())
    body_limitations = _unique_limitations(
        [limitation for competency in competencies for limitation in competency.limitations]
    )
    if record.hint_count > 0:
        body_limitations.append(
            Limitation(
                category=_HINT_ASSISTANCE,
                detail=f"{record.hint_count} hint(s) were used during this session.",
            )
        )
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
        limitations=body_limitations,
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
