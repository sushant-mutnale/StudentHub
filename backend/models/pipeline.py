"""
Pipeline Models - Customizable hiring pipelines with versioning.

Collections:
- pipeline_templates: Company-specific pipeline configurations
- pipeline_stages: Stage definitions (embedded in templates)
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from bson import ObjectId
import uuid

from ..database import get_database


def pipeline_templates_collection():
    return get_database()["pipeline_templates"]


# Default stage types
STAGE_TYPE_APPLIED = "applied"
STAGE_TYPE_SCREENING = "screening"
STAGE_TYPE_INTERVIEW = "interview"
STAGE_TYPE_OFFER = "offer"
STAGE_TYPE_HIRED = "hired"
STAGE_TYPE_REJECTED = "rejected"
STAGE_TYPE_WITHDRAWN = "withdrawn"

TERMINAL_STAGE_TYPES = {STAGE_TYPE_HIRED, STAGE_TYPE_REJECTED, STAGE_TYPE_WITHDRAWN}


def get_default_pipeline_stages() -> List[Dict[str, Any]]:
    """Returns the default pipeline stages for new companies."""
    return [
        {
            "id": str(uuid.uuid4()),
            "name": "Applied",
            "order": 1,
            "type": STAGE_TYPE_APPLIED,
            "color": "#3b82f6",
            "auto_trigger": "on_apply",
            "requires_scorecard": False,
            "student_visible_name": "Application Received"
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Resume Screening",
            "order": 2,
            "type": STAGE_TYPE_SCREENING,
            "color": "#8b5cf6",
            "auto_trigger": None,
            "requires_scorecard": False,
            "student_visible_name": "Under Review"
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Phone Screen",
            "order": 3,
            "type": STAGE_TYPE_INTERVIEW,
            "color": "#06b6d4",
            "auto_trigger": "on_interview_schedule",
            "requires_scorecard": True,
            "student_visible_name": "Phone Interview"
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Technical Round 1",
            "order": 4,
            "type": STAGE_TYPE_INTERVIEW,
            "color": "#10b981",
            "auto_trigger": "on_interview_schedule",
            "requires_scorecard": True,
            "student_visible_name": "Technical Interview"
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Technical Round 2",
            "order": 5,
            "type": STAGE_TYPE_INTERVIEW,
            "color": "#10b981",
            "auto_trigger": "on_interview_schedule",
            "requires_scorecard": True,
            "student_visible_name": "Technical Interview"
        },
        {
            "id": str(uuid.uuid4()),
            "name": "HR Round",
            "order": 6,
            "type": STAGE_TYPE_INTERVIEW,
            "color": "#f59e0b",
            "auto_trigger": "on_interview_schedule",
            "requires_scorecard": True,
            "student_visible_name": "Final Interview"
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Offer Extended",
            "order": 7,
            "type": STAGE_TYPE_OFFER,
            "color": "#ec4899",
            "auto_trigger": "on_offer_create",
            "requires_scorecard": False,
            "student_visible_name": "Offer Received"
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Hired",
            "order": 8,
            "type": STAGE_TYPE_HIRED,
            "color": "#22c55e",
            "auto_trigger": "on_offer_accept",
            "requires_scorecard": False,
            "student_visible_name": "Hired"
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Rejected",
            "order": 9,
            "type": STAGE_TYPE_REJECTED,
            "color": "#ef4444",
            "auto_trigger": None,
            "requires_scorecard": False,
            "student_visible_name": "Not Selected"
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Withdrawn",
            "order": 10,
            "type": STAGE_TYPE_WITHDRAWN,
            "color": "#6b7280",
            "auto_trigger": "on_withdraw",
            "requires_scorecard": False,
            "student_visible_name": "Withdrawn"
        }
    ]


def generate_default_transitions(stages: List[Dict]) -> List[Dict[str, Any]]:
    """Generate default forward transitions between stages."""
    transitions = []
    non_terminal = [s for s in stages if s["type"] not in TERMINAL_STAGE_TYPES]
    terminal_stages = {s["type"]: s["id"] for s in stages if s["type"] in TERMINAL_STAGE_TYPES}
    
    for i, stage in enumerate(non_terminal[:-1]):
        # Forward to next stage
        transitions.append({
            "from_stage_id": stage["id"],
            "to_stage_id": non_terminal[i + 1]["id"],
            "allowed_by": ["recruiter", "admin"]
        })
        # Allow rejection from any non-terminal stage
        if STAGE_TYPE_REJECTED in terminal_stages:
            transitions.append({
                "from_stage_id": stage["id"],
                "to_stage_id": terminal_stages[STAGE_TYPE_REJECTED],
                "allowed_by": ["recruiter", "admin"]
            })
        # Allow withdrawal from any non-terminal stage
        if STAGE_TYPE_WITHDRAWN in terminal_stages:
            transitions.append({
                "from_stage_id": stage["id"],
                "to_stage_id": terminal_stages[STAGE_TYPE_WITHDRAWN],
                "allowed_by": ["student"]
            })
    
    return transitions


async def create_default_pipeline_for_company(company_id: str, company_name: str) -> dict:
    """Create the default pipeline template for a new company."""
    stages = get_default_pipeline_stages()
    transitions = generate_default_transitions(stages)
    
    now = datetime.utcnow()
    template = {
        "company_id": ObjectId(company_id),
        "company_name": company_name,
        "name": "Default Hiring Pipeline",
        "version": 1,
        "active": True,
        "is_default": True,
        "stages": stages,
        "transitions": transitions,
        "created_at": now,
        "updated_at": now,
        "created_by": ObjectId(company_id)
    }
    
    result = await pipeline_templates_collection().insert_one(template)
    return await pipeline_templates_collection().find_one({"_id": result.inserted_id})


async def get_active_pipeline(company_id: str) -> Optional[dict]:
    """Get the active pipeline template for a company."""
    return await pipeline_templates_collection().find_one({
        "company_id": ObjectId(company_id),
        "active": True
    })


async def get_pipeline_by_id(pipeline_id: str) -> Optional[dict]:
    """Get a specific pipeline template by ID."""
    return await pipeline_templates_collection().find_one({"_id": ObjectId(pipeline_id)})


async def list_company_pipelines(company_id: str) -> List[dict]:
    """List all pipeline templates for a company (including inactive versions)."""
    cursor = pipeline_templates_collection().find({
        "company_id": ObjectId(company_id)
    }).sort("version", -1)
    return await cursor.to_list(length=100)


async def create_pipeline_template(
    company_id: str,
    name: str,
    stages: List[Dict],
    transitions: List[Dict],
    created_by: str
) -> dict:
    """Create a new custom pipeline template."""
    # Validate stages
    validate_pipeline_stages(stages)
    
    # Get current max version
    existing = await pipeline_templates_collection().find_one(
        {"company_id": ObjectId(company_id), "name": name},
        sort=[("version", -1)]
    )
    version = (existing.get("version", 0) + 1) if existing else 1
    
    # Deactivate old versions with same name
    await pipeline_templates_collection().update_many(
        {"company_id": ObjectId(company_id), "name": name},
        {"$set": {"active": False}}
    )
    
    now = datetime.utcnow()
    template = {
        "company_id": ObjectId(company_id),
        "name": name,
        "version": version,
        "active": True,
        "is_default": False,
        "stages": stages,
        "transitions": transitions,
        "created_at": now,
        "updated_at": now,
        "created_by": ObjectId(created_by)
    }
    
    result = await pipeline_templates_collection().insert_one(template)
    return await pipeline_templates_collection().find_one({"_id": result.inserted_id})


async def update_pipeline_template(
    pipeline_id: str,
    updates: Dict[str, Any],
    updated_by: str
) -> Optional[dict]:
    """Update a pipeline template, creating a new version."""
    existing = await get_pipeline_by_id(pipeline_id)
    if not existing:
        return None
    
    # Create new version instead of updating in place
    new_version = existing["version"] + 1
    
    # Deactivate current version
    await pipeline_templates_collection().update_one(
        {"_id": ObjectId(pipeline_id)},
        {"$set": {"active": False}}
    )
    
    # Create new version
    now = datetime.utcnow()
    new_template = {
        "company_id": existing["company_id"],
        "name": existing["name"],
        "version": new_version,
        "active": True,
        "is_default": existing.get("is_default", False),
        "stages": updates.get("stages", existing["stages"]),
        "transitions": updates.get("transitions", existing["transitions"]),
        "created_at": now,
        "updated_at": now,
        "created_by": ObjectId(updated_by),
        "previous_version_id": ObjectId(pipeline_id)
    }
    
    if "stages" in updates:
        validate_pipeline_stages(updates["stages"])
    
    result = await pipeline_templates_collection().insert_one(new_template)
    return await pipeline_templates_collection().find_one({"_id": result.inserted_id})


def validate_pipeline_stages(stages: List[Dict]) -> bool:
    """Validate that pipeline stages meet requirements."""
    stage_types = [s.get("type") for s in stages]
    
    # Must have exactly one 'applied' stage
    if stage_types.count(STAGE_TYPE_APPLIED) != 1:
        raise ValueError("Pipeline must have exactly one 'applied' stage")
    
    # Must have at least one interview stage
    if STAGE_TYPE_INTERVIEW not in stage_types:
        raise ValueError("Pipeline must have at least one 'interview' stage")
    
    # Must have terminal stages
    if STAGE_TYPE_HIRED not in stage_types:
        raise ValueError("Pipeline must have a 'hired' terminal stage")
    if STAGE_TYPE_REJECTED not in stage_types:
        raise ValueError("Pipeline must have a 'rejected' terminal stage")
    
    return True


def get_stage_by_id(pipeline: dict, stage_id: str) -> Optional[dict]:
    """Get a stage from a pipeline by its ID."""
    for stage in pipeline.get("stages", []):
        if stage.get("id") == stage_id:
            return stage
    return None


def get_stage_by_type(pipeline: dict, stage_type: str) -> Optional[dict]:
    """Get the first stage of a given type."""
    for stage in pipeline.get("stages", []):
        if stage.get("type") == stage_type:
            return stage
    return None


def get_next_stage(pipeline: dict, current_stage_id: str) -> Optional[dict]:
    """Get the next stage in order after the current stage."""
    stages = sorted(pipeline.get("stages", []), key=lambda s: s.get("order", 0))
    for i, stage in enumerate(stages):
        if stage.get("id") == current_stage_id and i < len(stages) - 1:
            next_stage = stages[i + 1]
            # Skip terminal stages for auto-advance
            if next_stage.get("type") not in TERMINAL_STAGE_TYPES:
                return next_stage
    return None


def can_transition(pipeline: dict, from_stage_id: str, to_stage_id: str, actor_role: str) -> bool:
    """Check if a transition is allowed."""
    for transition in pipeline.get("transitions", []):
        if (transition.get("from_stage_id") == from_stage_id and 
            transition.get("to_stage_id") == to_stage_id):
            allowed = transition.get("allowed_by", [])
            return actor_role in allowed or "admin" in allowed
    return False


async def ensure_pipeline_indexes():
    """Create indexes for pipeline templates."""
    col = pipeline_templates_collection()
    await col.create_index("company_id")
    await col.create_index([("company_id", 1), ("active", 1)])
    await col.create_index([("company_id", 1), ("name", 1), ("version", -1)])
