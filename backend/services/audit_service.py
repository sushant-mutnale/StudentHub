"""
Audit Service

Centralized service for logging audit events.
"""

from typing import Optional, Dict, Any
from enum import Enum

from ..models.audit import AuditLog

class AuditAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    APPROVE = "approve"
    REJECT = "reject"
    VERIFY = "verify"

class AuditService:
    """ Service for creating audit logs. """
    
    async def log_event(
        self,
        action: str,
        entity_type: str,
        entity_id: str,
        actor_id: str,
        changes: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        request = None
    ):
        """
        Log an event.
        Optional: extract IP from request if provided.
        """
        ip_address = None
        if request:
            ip_address = request.client.host
            
        await AuditLog.log(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=actor_id,
            changes=changes,
            metadata=metadata,
            ip_address=ip_address
        )

audit_service = AuditService()
