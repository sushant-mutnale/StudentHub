"""
Audit Log Model

Tracks critical system actions for compliance and security.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from bson import ObjectId
from ..database import get_database

def audit_collection():
    return get_database()["audit_logs"]

class AuditLog:
    """
    Represents a single audit log entry.
    """
    
    ACTION_CREATE = "create"
    ACTION_UPDATE = "update"
    ACTION_DELETE = "delete"
    ACTION_LOGIN = "login"
    ACTION_APPROVE = "approve"
    ACTION_REJECT = "reject"
    
    ENTITY_USER = "user"
    ENTITY_JOB = "job"
    ENTITY_APPLICATION = "application"
    
    @classmethod
    async def log(
        cls,
        action: str,
        entity_type: str,
        entity_id: str,
        actor_id: str,
        changes: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ):
        """
        Create a new audit log entry.
        """
        doc = {
            "action": action,
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "actor_id": str(actor_id),
            "changes": changes or {},
            "metadata": metadata or {},
            "ip_address": ip_address,
            "timestamp": datetime.utcnow()
        }
        
        await audit_collection().insert_one(doc)

async def ensure_audit_indexes():
    """Create indexes for audit logs."""
    collection = audit_collection()
    await collection.create_index("entity_id")
    await collection.create_index("actor_id")
    await collection.create_index("action")
    await collection.create_index("timestamp")
