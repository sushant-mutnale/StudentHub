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
