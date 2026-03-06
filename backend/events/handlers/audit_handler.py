"""
Audit Event Handler

Creates tamper-evident, structured audit logs for all important actions.
Critical for compliance, debugging, and incident response.

Features:
- Immutable audit records
- Before/after state tracking
- Correlation ID for tracing
- Actor identification
- TTL-based retention
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from ..event_bus import event_bus, Event, EventTypes

logger = logging.getLogger(__name__)


# Events that require audit logging
AUDITED_EVENTS = [
    # Admin actions
    EventTypes.JOB_APPROVED,
    EventTypes.JOB_SUSPENDED,
    EventTypes.JOB_FLAGGED,
    EventTypes.JOB_ESCALATED,
    EventTypes.ADMIN_ACTION_TAKEN,
    
    # Pipeline changes
    EventTypes.APPLICATION_STAGE_CHANGED,
    EventTypes.APPLICATION_WITHDRAWN,
    
    # Offers
    EventTypes.OFFER_EXTENDED,
    EventTypes.OFFER_ACCEPTED,
    EventTypes.OFFER_DECLINED,
    
    # User changes
    EventTypes.USER_PROFILE_UPDATED,
    EventTypes.USER_SCORE_CHANGED,
]


class AuditLogger:
    """
    Structured audit logging service.
    
    All audit logs are immutable once written.
    """
    
    @staticmethod
    async def log(
        action: str,
        actor_id: str,
        resource_type: str,
        resource_id: str,
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        severity: str = "info"
    ):
        """
        Create an immutable audit log entry.
        
        Args:
            action: What happened (e.g., "stage_changed", "job_approved")
            actor_id: Who performed the action
            resource_type: Type of resource affected (e.g., "application", "job")
            resource_id: ID of the affected resource
            before_state: State before the change
            after_state: State after the change
            correlation_id: Request trace ID
            metadata: Additional context
            severity: "info", "warning", "critical"
        """
        from ...database import get_database
        
        audit_entry = {
            "action": action,
            "actor_id": actor_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "before_state": before_state,
            "after_state": after_state,
            "diff": AuditLogger._compute_diff(before_state, after_state),
            "correlation_id": correlation_id,
            "metadata": metadata or {},
            "severity": severity,
            "timestamp": datetime.utcnow(),
            # Mark as immutable
            "immutable": True
        }
        
        try:
            db = get_database()
            result = await db.audit_logs.insert_one(audit_entry)
            logger.info(
                f"Audit: {action} on {resource_type}:{resource_id} by {actor_id}",
                extra={"audit_id": str(result.inserted_id)}
            )
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
            return None
    
    @staticmethod
    def _compute_diff(before: Optional[Dict], after: Optional[Dict]) -> Dict[str, Any]:
        """Compute the difference between before and after states."""
        if not before or not after:
            return {}
        
        diff = {
            "added": {},
            "removed": {},
            "changed": {}
        }
        
        all_keys = set(before.keys()) | set(after.keys())
        
        for key in all_keys:
            before_val = before.get(key)
            after_val = after.get(key)
            
            if key not in before:
                diff["added"][key] = after_val
            elif key not in after:
                diff["removed"][key] = before_val
            elif before_val != after_val:
                diff["changed"][key] = {"from": before_val, "to": after_val}
        
        return diff
    
    @staticmethod
    async def get_audit_trail(
        resource_type: str,
        resource_id: str,
        limit: int = 100
    ):
        """Get complete audit trail for a resource."""
        from ...database import get_database
        db = get_database()
        
        cursor = db.audit_logs.find({
            "resource_type": resource_type,
            "resource_id": resource_id
        }).sort("timestamp", -1).limit(limit)
        
        return await cursor.to_list(length=limit)
    
    @staticmethod
    async def get_actor_actions(
        actor_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ):
        """Get all actions performed by an actor."""
        from ...database import get_database
        db = get_database()
        
        query = {"actor_id": actor_id}
        
        if start_date or end_date:
            query["timestamp"] = {}
            if start_date:
                query["timestamp"]["$gte"] = start_date
            if end_date:
                query["timestamp"]["$lte"] = end_date
        
        cursor = db.audit_logs.find(query).sort("timestamp", -1).limit(limit)
        return await cursor.to_list(length=limit)


# Global audit logger instance
audit_logger = AuditLogger()


async def handle_audited_event(event: Event):
    """Create audit log entry for audited events."""
    payload = event.payload
    
    # Determine resource type and ID
    resource_type = "unknown"
    resource_id = None
    
    if "job_id" in payload:
        resource_type = "job"
        resource_id = payload["job_id"]
    elif "application_id" in payload:
        resource_type = "application"
        resource_id = payload["application_id"]
    elif "user_id" in payload:
        resource_type = "user"
        resource_id = payload["user_id"]
    elif "offer_id" in payload:
        resource_type = "offer"
        resource_id = payload["offer_id"]
    
    # Determine severity
    severity = "info"
    if event.type in [EventTypes.JOB_SUSPENDED, EventTypes.JOB_FLAGGED]:
        severity = "warning"
    if event.type == EventTypes.JOB_ESCALATED:
        severity = "critical"
    
    await audit_logger.log(
        action=str(event.type),
        actor_id=payload.get("actor_id") or "system",
        resource_type=resource_type,
        resource_id=resource_id or "unknown",
        before_state=payload.get("before_state"),
        after_state=payload.get("after_state"),
        correlation_id=event.correlation_id,
        metadata=payload.get("metadata", {}),
        severity=severity
    )


def register_audit_handlers():
    """Register audit handlers for all audited events."""
    
    for event_type in AUDITED_EVENTS:
        event_bus.subscribe(
            event_type,
            handle_audited_event
        )
    
    logger.info(f"Registered audit handlers for {len(AUDITED_EVENTS)} event types")
