from .thread import ensure_message_indexes
from .interview import ensure_interview_indexes
from .offer import ensure_offer_indexes
from .job import ensure_job_indexes


async def ensure_database_indexes():
    await ensure_message_indexes()
    await ensure_interview_indexes()
    await ensure_offer_indexes()
    await ensure_job_indexes()


