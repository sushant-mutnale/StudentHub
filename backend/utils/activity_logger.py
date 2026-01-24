from typing import Any, Dict, Optional
from ..models import activity as activity_model

async def log_activity(
    user_id: str, 
    event_type: str, 
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Utility wrapper to log activities.
    event_type: "POST_CREATED", "JOB_APPLIED", "INTERVIEW_ACCEPTED", "MESSAGE_SENT", etc.
    """
    try:
        await activity_model.log_activity(user_id, event_type, metadata)
    except Exception as e:
        # We don't want activity logging to break the main flow
        print(f"Error logging activity {event_type} for user {user_id}: {e}")
