"""
Projection Handler (CQRS)

Updates read models (views) asynchronously in response to domain events.
Example: Updating the Pipeline Board View when an application stage changes.
"""

import logging
from datetime import datetime
from typing import Dict, Any

from . import register_handler
from ..event_bus import Event, EventTypes, event_bus
from ..database import get_database
from ..models.views import PipelineBoardView, PipelineBoardColumnView, PipelineBoardCandidateView
from ..models.pipeline import get_pipeline_by_id
from ..models import user as user_model
from ..models import application as application_model
from ..models import job as job_model

logger = logging.getLogger(__name__)

def view_pipeline_boards():
    return get_database()["view_pipeline_boards"]


@register_handler(EventTypes.APPLICATION_STAGE_CHANGED)
async def update_pipeline_board_view(event: Event):
    """
    Update the denormalized pipeline board view when an application moves stages.
    This creates/updates the pre-aggregated document for fast reads.
    """
    payload = event.payload
    application_id = payload.get("application_id")
    job_id = payload.get("job_id")
    
    if not job_id or not application_id:
        return

    logger.info(f"Updating pipeline board view for job {job_id}")
    
    # In a full CQRS system, we might compute just the delta.
    # For simplicity and robustness here, we'll re-aggregate the board for this job.
    # This is still much better than doing it on every read.
    
    try:
        # Get Job & Pipeline info
        job = await job_model.get_job(job_id)
        if not job:
            return
            
        pipeline_id = payload.get("pipeline_id") # Usually passed in event, or lookup
        if not pipeline_id:
            # Fallback lookup
            # In a real app, job would link to pipeline explicitly
            pass 

        # We actually need the pipeline ID to structure the board
        # Assuming we can find it or it's standard
        # For now, let's fetch the Recruiter's active pipeline
        recruiter_id = str(job["recruiter_id"])
        
        # This part assumes we know WHICH pipeline applies. 
        # If we don't have it in the event, we might need to fetch the board to see which one was used,
        # or just fetch the active one.
        col = view_pipeline_boards()
        existing_view = await col.find_one({"job_id": job_id})
        
        pipeline = None
        if existing_view:
            pipeline_id = existing_view["pipeline_id"]
            pipeline = await get_pipeline_by_id(pipeline_id)
        else:
            # First time creation? Or fetch active
            pass # We'll need the pipeline logic here similar to the route
            
        if not pipeline:
           from ..models.pipeline import get_active_pipeline
           pipeline = await get_active_pipeline(recruiter_id)
           
        if not pipeline:
            logger.warning(f"No pipeline found for job {job_id}, cannot update view")
            return

        pipeline_id = str(pipeline["_id"])

        # Re-build the board data
        columns = []
        total_candidates = 0
        
        for stage in sorted(pipeline.get("stages", []), key=lambda s: s.get("order", 0)):
            stage_id = stage["id"]
            
            # Fetch fresh apps for this stage
            apps = await application_model.list_applications_by_company_stage(
                company_id=recruiter_id,
                stage_id=stage_id,
                job_id=job_id
            )
            
            candidates = []
            for app in apps:
                student = await user_model.get_user_by_id(str(app["student_id"]))
                if student:
                    candidates.append(PipelineBoardCandidateView(
                        application_id=str(app["_id"]),
                        student_id=str(app["student_id"]),
                        student_name=student.get("full_name") or student.get("username", "Unknown"),
                        student_avatar=student.get("avatar_url"),
                        applied_at=app["applied_at"],
                        last_activity=app.get("updated_at"),
                        overall_score=app.get("rating_summary", {}).get("overall_score"),
                        tags=app.get("tags", [])
                    ))
            
            columns.append(PipelineBoardColumnView(
                stage_id=stage_id,
                stage_name=stage["name"],
                stage_type=stage["type"],
                color=stage.get("color", "#3b82f6"),
                order=stage.get("order", 0),
                candidates=candidates,
                count=len(candidates)
            ))
            total_candidates += len(candidates)

        # Create View Object
        view = PipelineBoardView(
            id=job_id, # Using job_id as the view ID for direct lookup
            job_id=job_id,
            job_title=job.get("title", "Unknown"),
            pipeline_id=pipeline_id,
            pipeline_name=pipeline["name"],
            company_id=recruiter_id,
            columns=columns,
            total_candidates=total_candidates,
            updated_at=datetime.utcnow()
        )
        
        # Upsert
        await col.replace_one(
            {"job_id": job_id},
            view.dict(by_alias=True),
            upsert=True
        )
        
        logger.info(f"Pipeline Board View updated for job {job_id}")

    except Exception as e:
        logger.error(f"Failed to update pipeline board view: {e}")
