async def ensure_interview_engine_indexes(database=None):
    if database is None:
        from ..database import get_database
        database = get_database()

    sessions = database.interview_engine_sessions
    await sessions.create_index("candidate_id")
    await sessions.create_index(
        [("candidate_id", 1), ("client_request_id", 1)],
        unique=True,
        partialFilterExpression={"client_request_id": {"$exists": True, "$type": "string"}},
    )
    await sessions.create_index([("candidate_id", 1), ("status", 1)])

    events = database.interview_engine_events
    await events.create_index([("session_id", 1), ("event_sequence", 1)], unique=True)

    turns = database.interview_engine_turns
    await turns.create_index([("session_id", 1), ("sequence", 1)], unique=True)
    await turns.create_index([("session_id", 1), ("idempotency_key", 1)], unique=True)

    evidence = database.interview_engine_evidence
    await evidence.create_index([("session_id", 1), ("competency", 1)])

    questions = database.interview_engine_questions
    await questions.create_index([("session_id", 1)])
    await questions.create_index(
        [("session_id", 1), ("question_generation_key", 1)], unique=True, background=True
    )

    hints = database.interview_engine_hints
    await hints.create_index(
        [("session_id", 1), ("hint_idempotency_key", 1)], unique=True, background=True
    )

    commands = database.interview_engine_turn_commands
    await commands.create_index([("session_id", 1), ("idempotency_key", 1)], unique=True)

    reports = database.interview_engine_reports
    await reports.create_index("session_id")

    outbox = database.interview_engine_outbox
    await outbox.create_index("outbox_id", unique=True, background=True)
    await outbox.create_index([("status", 1), ("created_at", 1)], background=True)
