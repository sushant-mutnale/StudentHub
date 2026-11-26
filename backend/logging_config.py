import json
import logging
import re

from .middleware.correlation import get_correlation_id

SENSITIVE_MARKERS = (
    "token",
    "secret",
    "password",
    "apikey",
    "authorization",
    "cookie",
    "credential",
)

_SENSITIVE_TEXT_PATTERN = re.compile(
    r"(?P<key>[\"']?[A-Za-z0-9_-]*(?:"
    + "|".join(SENSITIVE_MARKERS)
    + r")[A-Za-z0-9_-]*[\"']?\s*[:=]\s*)"
    r"(?:Bearer\s+)?[\"']?[^\s,;}\]\"']+[\"']?",
    re.IGNORECASE,
)

_installed_handlers = []


def redact_text(value):
    return _SENSITIVE_TEXT_PATTERN.sub(r"\g<key>[REDACTED]", str(value))


def _is_sensitive_key(key):
    normalized = "".join(char for char in str(key).lower() if char.isalnum())
    return any(marker in normalized for marker in SENSITIVE_MARKERS)


def redact(value, key=None):
    if key and _is_sensitive_key(key):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {name: redact(item, name) for name, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


class RedactingFilter(logging.Filter):
    def filter(self, record):
        if isinstance(record.msg, dict):
            record.msg = redact(record.msg)
        elif isinstance(record.msg, str):
            record.msg = redact_text(record.msg)
        if isinstance(record.args, dict):
            record.args = redact(record.args)
        elif isinstance(record.args, tuple):
            record.args = tuple(redact(arg) for arg in record.args)
        return True


class RedactingFormatter(logging.Formatter):
    def formatException(self, exc_info):
        return redact_text(super().formatException(exc_info))


class JsonFormatter(RedactingFormatter):
    def format(self, record):
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": redact_text(record.getMessage()),
            "correlation_id": get_correlation_id(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(app_env):
    root = logging.getLogger()
    for handler in list(_installed_handlers):
        root.removeHandler(handler)
    _installed_handlers.clear()

    handler = logging.StreamHandler()
    handler.addFilter(RedactingFilter())

    if app_env == "testing":
        handler.setFormatter(RedactingFormatter("%(levelname)s %(name)s %(message)s"))
    else:
        handler.setFormatter(JsonFormatter())

    root.addHandler(handler)
    _installed_handlers.append(handler)
    root.setLevel(logging.INFO)
