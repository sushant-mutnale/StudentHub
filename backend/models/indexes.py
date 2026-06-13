from .thread import ensure_message_indexes
from .interview import ensure_interview_indexes
from .offer import ensure_offer_indexes
from .job import ensure_job_indexes
from .pipeline import ensure_pipeline_indexes
from .application import ensure_application_indexes
from .scorecard import ensure_scorecard_indexes
from .audit import ensure_audit_indexes
from .user import ensure_user_indexes
from .notification import ensure_notification_indexes
from .outbox import ensure_outbox_indexes
from .post import ensure_post_indexes


async def ensure_database_indexes():
    await ensure_message_indexes()
    await ensure_interview_indexes()
    await ensure_offer_indexes()
    await ensure_job_indexes()
    # Module 5 indexes
    await ensure_pipeline_indexes()
    await ensure_application_indexes()
    await ensure_scorecard_indexes()
    await ensure_audit_indexes()
    
    # New indexes
    await ensure_user_indexes()
    await ensure_notification_indexes()
    await ensure_outbox_indexes()
    await ensure_post_indexes()

