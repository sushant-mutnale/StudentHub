from .thread import ensure_message_indexes
from .interview import ensure_interview_indexes
from .offer import ensure_offer_indexes
from .job import ensure_job_indexes
from .pipeline import ensure_pipeline_indexes
from .application import ensure_application_indexes
from .scorecard import ensure_scorecard_indexes
from .audit import ensure_audit_indexes


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
