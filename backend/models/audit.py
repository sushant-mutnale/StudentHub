"""
Audit Models - Immutable audit logging for governance and debugging.

This module provides append-only audit logging for:
- Recruiter actions (job create/edit, candidate moves)
- Admin actions (verification, moderation)
- System events (auto-transitions, scheduled jobs)
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from bson import ObjectId

from ..database import get_database


def audit_logs_collection():
    return get_database()["audit_logs"]


# Actor types
ACTOR_USER = "user"
ACTOR_ADMIN = "admin"
ACTOR_SYSTEM = "system"

# Action categories
ACTION_JOB_CREATED = "job_created"
ACTION_JOB_EDITED = "job_edited"
ACTION_JOB_DELETED = "job_deleted"
ACTION_JOB_FLAGGED = "job_flagged"
ACTION_JOB_APPROVED = "job_approved"
ACTION_JOB_REJECTED = "job_rejected"
ACTION_JOB_PUBLISHED = "job_published"

ACTION_RECRUITER_CREATED = "recruiter_created"
ACTION_RECRUITER_VERIFIED = "recruiter_verified"
ACTION_RECRUITER_SUSPENDED = "recruiter_suspended"
ACTION_RECRUITER_UNSUSPENDED = "recruiter_unsuspended"
ACTION_RECRUITER_FLAGGED = "recruiter_flagged"

ACTION_APPLICATION_CREATED = "application_created"
ACTION_APPLICATION_STAGE_CHANGED = "application_stage_changed"
ACTION_APPLICATION_WITHDRAWN = "application_withdrawn"

ACTION_INTERVIEW_CREATED = "interview_created"
ACTION_INTERVIEW_COMPLETED = "interview_completed"

ACTION_OFFER_CREATED = "offer_created"
ACTION_OFFER_ACCEPTED = "offer_accepted"
ACTION_OFFER_REJECTED = "offer_rejected"

ACTION_SCORECARD_SUBMITTED = "scorecard_submitted"

ACTION_ADMIN_LOGIN = "admin_login"
ACTION_ADMIN_ACTION = "admin_action"


async def log_audit(
    action: str,
    entity_type: str,
    entity_id: str,
    actor_id: Optional[str] = None,
    actor_type: str = ACTOR_USER,
    before: Optional[Dict] = None,
    after: Optional[Dict] = None,
    metadata: Optional[Dict] = None,
    reason: Optional[str] = None
) -> dict:
    """
    Create an immutable audit log entry.
    
    This function ONLY inserts - no updates or deletes allowed.
    """
    now = datetime.utcnow()
    
    log_entry = {
        "timestamp": now,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "actor_id": ObjectId(actor_id) if actor_id else None,
        "actor_type": actor_type,
        "before": before,
        "after": after,
        "metadata": metadata or {},
        "reason": reason
    }
    
    result = await audit_logs_collection().insert_one(log_entry)
    log_entry["_id"] = result.inserted_id
    return log_entry


async def get_audit_logs_for_entity(
    entity_type: str,
    entity_id: str,
    limit: int = 100
) -> List[dict]:
    """Get all audit logs for a specific entity."""
    cursor = audit_logs_collection().find({
        "entity_type": entity_type,
        "entity_id": entity_id
    }).sort("timestamp", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def get_audit_logs_by_actor(
    actor_id: str,
    limit: int = 100
) -> List[dict]:
    """Get all audit logs by a specific actor."""
    cursor = audit_logs_collection().find({
        "actor_id": ObjectId(actor_id)
    }).sort("timestamp", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def get_audit_logs_by_action(
    action: str,
    limit: int = 100,
    since: Optional[datetime] = None
) -> List[dict]:
    """Get audit logs for a specific action type."""
    query: Dict[str, Any] = {"action": action}
    if since:
        query["timestamp"] = {"$gte": since}
    
    cursor = audit_logs_collection().find(query).sort("timestamp", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def get_recent_audit_logs(
    limit: int = 100,
    entity_type: Optional[str] = None,
    actions: Optional[List[str]] = None
) -> List[dict]:
    """Get recent audit logs with optional filters."""
    query: Dict[str, Any] = {}
    if entity_type:
        query["entity_type"] = entity_type
    if actions:
        query["action"] = {"$in": actions}
    
    cursor = audit_logs_collection().find(query).sort("timestamp", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def count_actions_by_actor(
    actor_id: str,
    action: Optional[str] = None,
    since: Optional[datetime] = None
) -> int:
    """Count actions by an actor (useful for rate limiting/suspicious detection)."""
    query: Dict[str, Any] = {"actor_id": ObjectId(actor_id)}
    if action:
        query["action"] = action
    if since:
        query["timestamp"] = {"$gte": since}
    
    return await audit_logs_collection().count_documents(query)


async def ensure_audit_indexes():
    """Create indexes for audit logs. Note: No unique indexes to allow duplicates."""
    col = audit_logs_collection()
    await col.create_index("timestamp")
    await col.create_index([("entity_type", 1), ("entity_id", 1)])
    await col.create_index("actor_id")
    await col.create_index("action")
    await col.create_index([("actor_id", 1), ("timestamp", -1)])
