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
