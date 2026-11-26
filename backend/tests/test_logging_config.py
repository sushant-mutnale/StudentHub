import json
import logging

from backend.logging_config import JsonFormatter, RedactingFilter, redact
from backend.middleware.correlation import correlation_id_ctx


def test_redact_nested_sensitive_fields():
    result = redact(
        {
            "token": "abc",
            "nested": {"password": "def"},
            "authorization": "Bearer abc",
            "safe": "ok",
        }
    )

    assert result == {
        "token": "[REDACTED]",
        "nested": {"password": "[REDACTED]"},
        "authorization": "[REDACTED]",
        "safe": "ok",
    }


def test_redacting_filter_redacts_log_args():
    record = logging.LogRecord(
        "test",
        logging.INFO,
        __file__,
        1,
        "event=%s",
        ({"secret": "abc"},),
        None,
    )

    assert RedactingFilter().filter(record) is True
    assert record.getMessage() == "event={'secret': '[REDACTED]'}"


def test_json_formatter_includes_correlation_id():
    token = correlation_id_ctx.set("cid-123")
    try:
        record = logging.LogRecord(
            "test",
            logging.INFO,
            __file__,
            1,
            {"event": "request.completed", "status": 200},
            None,
            None,
        )
        payload = json.loads(JsonFormatter().format(record))
    finally:
        correlation_id_ctx.reset(token)

    assert payload["correlation_id"] == "cid-123"
    assert payload["message"] == "{'event': 'request.completed', 'status': 200}"
