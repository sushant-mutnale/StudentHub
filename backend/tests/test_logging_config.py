import json
import logging
import sys

from backend import logging_config
from backend.logging_config import (
    JsonFormatter,
    RedactingFilter,
    configure_logging,
    redact,
)
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


def test_redact_covers_common_sensitive_key_variants():
    result = redact(
        {
            "refresh_token": "abc",
            "access_token": "def",
            "apiKey": "ghi",
            "client_secret": "jkl",
            "nested": {"api_key": "mno"},
            "safe": "ok",
        }
    )

    assert result == {
        "refresh_token": "[REDACTED]",
        "access_token": "[REDACTED]",
        "apiKey": "[REDACTED]",
        "client_secret": "[REDACTED]",
        "nested": {"api_key": "[REDACTED]"},
        "safe": "ok",
    }


def test_redacting_filter_scrubs_sensitive_text_in_error_messages():
    record = logging.LogRecord(
        "test",
        logging.ERROR,
        __file__,
        1,
        {"event": "request.failed", "error": "token=abc and Authorization: Bearer def"},
        None,
        None,
    )

    assert RedactingFilter().filter(record) is True
    assert record.getMessage() == (
        "{'event': 'request.failed', "
        "'error': 'token=[REDACTED] and Authorization: [REDACTED]'}"
    )


def test_formatters_redact_exception_and_traceback_text():
    try:
        raise RuntimeError("apiKey=ghi failed")
    except RuntimeError:
        record = logging.LogRecord(
            "test", logging.ERROR, __file__, 1, "failed", None, sys.exc_info()
        )

    payload = json.loads(JsonFormatter().format(record))
    assert "apiKey=ghi" not in payload["exception"]
    assert "apiKey=[REDACTED]" in payload["exception"]

    text = logging_config.RedactingFormatter("%(levelname)s %(message)s").format(record)
    assert "apiKey=ghi" not in text
    assert "apiKey=[REDACTED]" in text


def test_configure_logging_preserves_host_handlers_and_avoids_duplicates():
    root = logging.getLogger()
    original_handlers = list(root.handlers)
    original_level = root.level
    sentinel = logging.NullHandler()
    root.addHandler(sentinel)
    try:
        configure_logging("testing")
        assert sentinel in root.handlers
        installed = [
            handler
            for handler in root.handlers
            if any(isinstance(item, RedactingFilter) for item in handler.filters)
        ]
        assert len(installed) == 1

        configure_logging("testing")
        assert sentinel in root.handlers
        installed = [
            handler
            for handler in root.handlers
            if any(isinstance(item, RedactingFilter) for item in handler.filters)
        ]
        assert len(installed) == 1
    finally:
        root.handlers = original_handlers
        root.setLevel(original_level)
