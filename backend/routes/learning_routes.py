"""
Learning Routes
APIs for Gap Analysis, Learning Path Generation, and Progress Tracking
"""

from datetime import datetime
from typing import List

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from ..database import get_database
from ..services.gap_analyzer import skill_gap_analyzer
from ..services.learning_path_builder import learning_path_builder
from ..schemas.learning_schema import (
    GapAnalysisRequest,
    GapAnalysisResponse,
    GeneratePathRequest,
    GeneratePathResponse,
    MarkProgressRequest,
    MarkProgressResponse,
    MyPathsResponse,
    LearningPath,
    LearningPathProgress,
    SkillGap,
)
from ..utils.dependencies import get_current_user


router = APIRouter(prefix="/learning", tags=["learning"])


def learning_paths_collection():
    return get_database()["learning_paths"]


def gap_analyses_collection():
    return get_database()["gap_analyses"]


# ============ Gap Analysis Endpoints ============

@router.post("/analyze-gap", response_model=GapAnalysisResponse)
async def analyze_gap(
    payload: GapAnalysisRequest,
    current_user=Depends(get_current_user)
):
    """
    Analyze skill gaps between student skills and job requirements.
    Returns gaps with priorities and recommendations.
    """
    student_id = payload.student_id or str(current_user["_id"])
    
    # Get student skills from profile if not provided
    student_skills = payload.student_skills
    if not student_skills:
        user_skills = current_user.get("skills", [])
        if isinstance(user_skills, list):
            student_skills = [
                s.get("name") if isinstance(s, dict) else str(s) 
                for s in user_skills
            ]
    
    # Perform gap analysis (async for AI recommendations)
    analysis = await skill_gap_analyzer.analyze_gap(
        student_skills=student_skills,
        job_required_skills=payload.job_required_skills,
        job_nice_to_have_skills=payload.job_nice_to_have_skills,
        student_id=student_id,
        job_id=payload.job_id,
        use_ai_recommendations=True
    )
    
    # Store in MongoDB
    doc = {
        **analysis,
        "student_id": ObjectId(student_id) if ObjectId.is_valid(student_id) else student_id,
        "created_at": datetime.utcnow()
    }
    await gap_analyses_collection().insert_one(doc)
    
    # Convert gaps to SkillGap objects for response
    gaps = [SkillGap(**g) for g in analysis["gaps"]]
    
    return GapAnalysisResponse(
        status="success",
        student_id=student_id,
        job_id=payload.job_id,
        analyzed_at=analysis["analyzed_at"],
        student_skills=analysis["student_skills"],
        job_required_skills=analysis["job_required_skills"],
        job_nice_to_have=analysis["job_nice_to_have"],
        gaps=gaps,
        match_percentage=analysis["match_percentage"],
        gap_score=analysis["gap_score"],
        recommendations=analysis["recommendations"],
        high_priority_count=analysis["high_priority_count"],
        total_gaps=analysis["total_gaps"]
    )


# ============ Learning Path Endpoints ============

@router.post("/generate-path", response_model=GeneratePathResponse)
async def generate_learning_paths(
    payload: GeneratePathRequest,
    current_user=Depends(get_current_user)
):
    """
    Generate personalized learning paths from skill gaps.
    Now with AI-powered personalization!
    """
    student_id = payload.student_id or str(current_user["_id"])
    
    # Get student's current skills for AI context
    user_skills = current_user.get("skills", [])
    current_skills = [
        s.get("name") if isinstance(s, dict) else str(s)
        for s in user_skills
        if s
    ]
    
    # Convert gaps to dicts
    gaps_dicts = [g.dict() for g in payload.gaps]
    
    # Build learning paths with AI personalization (async)
    paths = await learning_path_builder.build_paths_from_gaps(
        gaps=gaps_dicts,
        student_id=student_id,
        current_skills=current_skills,
        use_ai=True
    )
    
    # Store each path in MongoDB
    stored_paths = []
    total_weeks = 0
    ai_powered_count = 0
    
    for path in paths:
        path["student_id"] = ObjectId(student_id) if ObjectId.is_valid(student_id) else student_id
        result = await learning_paths_collection().insert_one(path)
        path["_id"] = result.inserted_id
        path["id"] = str(result.inserted_id)
        total_weeks += path.get("estimated_completion_weeks", 0)
        if path.get("ai_powered", False):
            ai_powered_count += 1
        stored_paths.append(path)
    
    # Convert to response model
    response_paths = []
    for p in stored_paths:
        response_paths.append(LearningPath(
            id=str(p.get("_id") or p.get("id")),
            student_id=str(p["student_id"]),
            skill=p["skill"],
            current_level=p["current_level"],
            target_level=p["target_level"],
            gap_priority=p["gap_priority"],
            stages=p["stages"],
            progress=LearningPathProgress(**p["progress"]),
            estimated_completion_weeks=p["estimated_completion_weeks"],
            ai_advice=p.get("ai_advice", ""),
            ai_powered=p.get("ai_powered", False),
            created_at=p.get("created_at"),
            updated_at=p.get("updated_at")
        ))
    
    return GeneratePathResponse(
        status="success",
        learning_paths=response_paths,
        total_estimated_weeks=total_weeks,
        ai_powered_paths=ai_powered_count
    )


@router.get("/my-paths", response_model=MyPathsResponse)
async def get_my_learning_paths(current_user=Depends(get_current_user)):
    """
    Get all active learning paths for the current user.
    """
    student_id = str(current_user["_id"])
    
    cursor = learning_paths_collection().find({
        "student_id": ObjectId(student_id)
    }).sort("created_at", -1)
    
    docs = await cursor.to_list(length=None)
    
    paths = []
    total_progress = 0.0
    
    for doc in docs:
        progress = doc.get("progress", {})
        total_progress += progress.get("completion_percentage", 0)
        
        paths.append(LearningPath(
            id=str(doc["_id"]),
            student_id=str(doc["student_id"]),
            skill=doc["skill"],
            current_level=doc["current_level"],
            target_level=doc["target_level"],
            gap_priority=doc["gap_priority"],
            stages=doc["stages"],
            progress=LearningPathProgress(**progress),
            estimated_completion_weeks=doc.get("estimated_completion_weeks", 0),
            ai_advice=doc.get("ai_advice", ""),
            ai_powered=doc.get("ai_powered", False),
            created_at=doc.get("created_at"),
            updated_at=doc.get("updated_at")
        ))
    
    overall = (total_progress / len(docs)) if docs else 0.0
    
    return MyPathsResponse(
        status="success",
        learning_paths=paths,
        total_paths=len(paths),
        overall_progress=round(overall, 1)
    )


@router.post("/mark-progress", response_model=MarkProgressResponse)
async def mark_progress(
    payload: MarkProgressRequest,
    current_user=Depends(get_current_user)
):
    """
    Mark a learning resource as completed and update progress.
    """
    student_id = str(current_user["_id"])
    
    if not ObjectId.is_valid(payload.learning_path_id):
        raise HTTPException(status_code=400, detail="Invalid learning path ID")
    
    # Find the learning path
    path = await learning_paths_collection().find_one({
        "_id": ObjectId(payload.learning_path_id),
        "student_id": ObjectId(student_id)
    })
    
    if not path:
        raise HTTPException(status_code=404, detail="Learning path not found")
    
    stages = path.get("stages", [])
    
    # Find the stage
    stage_idx = None
    for i, stage in enumerate(stages):
        if stage.get("stage_number") == payload.stage_number:
            stage_idx = i
            break
    
    if stage_idx is None:
        raise HTTPException(status_code=404, detail="Stage not found")
    
    stage = stages[stage_idx]
    resources = stage.get("resources", [])
    
    if payload.resource_index < 0 or payload.resource_index >= len(resources):
        raise HTTPException(status_code=404, detail="Resource not found")
    
    # Mark resource as completed
    resources[payload.resource_index]["completed"] = True
    resources[payload.resource_index]["completed_at"] = datetime.utcnow().isoformat()
    
    # Check if all resources in stage are completed
    all_completed = all(r.get("completed", False) for r in resources)
    if all_completed:
        stages[stage_idx]["status"] = "completed"
        stages[stage_idx]["completed_at"] = datetime.utcnow().isoformat()
    else:
        stages[stage_idx]["status"] = "in_progress"
    
    # Calculate overall progress
    total_resources = sum(len(s.get("resources", [])) for s in stages)
    completed_resources = sum(
        sum(1 for r in s.get("resources", []) if r.get("completed", False))
        for s in stages
    )
    
    completion_percentage = round(
        (completed_resources / total_resources * 100) if total_resources > 0 else 0,
        1
    )
    
    # Find current stage (first incomplete)
    current_stage = 0
    for i, s in enumerate(stages):
        if s.get("status") != "completed":
            current_stage = i
            break
        current_stage = i + 1
    
    # Update in MongoDB
    progress = {
        "current_stage": current_stage,
        "completion_percentage": completion_percentage,
        "time_spent_minutes": path.get("progress", {}).get("time_spent_minutes", 0),
        "estimated_completion_date": path.get("progress", {}).get("estimated_completion_date")
    }
    
    await learning_paths_collection().update_one(
        {"_id": ObjectId(payload.learning_path_id)},
        {
            "$set": {
                "stages": stages,
                "progress": progress,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return MarkProgressResponse(
        status="success",
        learning_path_id=payload.learning_path_id,
        new_completion_percentage=completion_percentage,
        stage_status=stages[stage_idx]["status"],
        message=f"Progress updated! {completion_percentage}% complete."
    )


@router.get("/path/{path_id}")
async def get_learning_path(path_id: str, current_user=Depends(get_current_user)):
    """
    Get a specific learning path by ID.
    """
    if not ObjectId.is_valid(path_id):
        raise HTTPException(status_code=400, detail="Invalid path ID")
    
    path = await learning_paths_collection().find_one({
        "_id": ObjectId(path_id)
    })
    
    if not path:
        raise HTTPException(status_code=404, detail="Learning path not found")
    
    # Verify ownership or admin
    if str(path["student_id"]) != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return LearningPath(
        id=str(path["_id"]),
        student_id=str(path["student_id"]),
        skill=path["skill"],
        current_level=path["current_level"],
        target_level=path["target_level"],
        gap_priority=path["gap_priority"],
        stages=path["stages"],
        progress=LearningPathProgress(**path.get("progress", {})),
        estimated_completion_weeks=path.get("estimated_completion_weeks", 0),
        ai_advice=path.get("ai_advice", ""),
        ai_powered=path.get("ai_powered", False),
        created_at=path.get("created_at"),
        updated_at=path.get("updated_at")
    )
