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
