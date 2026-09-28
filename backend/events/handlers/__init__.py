"""Event Handlers Package"""

from .notification_handler import register_notification_handlers
from .analytics_handler import register_analytics_handlers
from .audit_handler import register_audit_handlers
from .rag_handler import register_rag_handlers


def register_all_handlers():
    """Register all event handlers. Call at app startup."""
    register_notification_handlers()
    register_analytics_handlers()
    register_audit_handlers()
    register_rag_handlers()


__all__ = [
    "register_all_handlers",
    "register_notification_handlers",
    "register_analytics_handlers",
    "register_audit_handlers",
    "register_rag_handlers",
]
