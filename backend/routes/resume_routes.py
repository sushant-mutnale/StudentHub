"""
Resume Routes
API endpoints for resume upload, parsing, and management.
"""

import os
import shutil
import logging
from datetime import datetime
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, BackgroundTasks

logger = logging.getLogger(__name__)

from ..database import get_database
from ..models import user as user_model
from ..services.resume_parser import resume_parser
from ..schemas.resume_schema import (
    ResumeUploadResponse,
    MyResumesResponse,
    ResumeListItem,
    ResumeDetailResponse,
    ParsedResume,
    ParsedContact,
    ParsedExperience,
    ParsedEducation,
    ParsedProject,
    ReparseRequest,
    ReparseResponse,
    DeleteResponse,
)
from ..utils.dependencies import get_current_user
from ..services.ai_resume_evaluator import ai_resume_evaluator


router = APIRouter(prefix="/resume", tags=["resume"])

# Constants
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_EXTENSIONS = {".pdf"}
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads", "resumes")


def resumes_collection():
    return get_database()["resume_uploads"]


def resume_cache_collection():
    return get_database()["resume_cache"]


def ensure_upload_dir():
    """Ensure upload directory exists."""
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    return UPLOAD_DIR


def get_resume_path(student_id: str, filename: str) -> str:
    """Generate unique file path for resume."""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")
    final_path = os.path.join(
        ensure_upload_dir(),
        f"{student_id}_{timestamp}_{safe_filename}"
    )
    final_path = os.path.abspath(final_path)
    base_dir = os.path.abspath(UPLOAD_DIR)
    if not final_path.startswith(base_dir + os.sep):
        raise HTTPException(status_code=400, detail="Invalid filename")
    return final_path


# ============ Upload Endpoint ============

async def parse_resume_background_task(
    resume_id: str,
    file_path: str,
    file_hash: str,
    use_ai_enhancement: bool,
    student_id: str
):
    """Background task to parse resume and update MongoDB collections."""
    try:
        # 1. Parse resume file
        parsed_data = await resume_parser.parse_resume(
            file_path,
            use_ai_enhancement=use_ai_enhancement
        )
        
        if not parsed_data.get("success"):
            # Clean up file on failure
            if os.path.exists(file_path):
                os.remove(file_path)
            error_msg = parsed_data.get("error", "Failed to parse resume")
            await resumes_collection().update_one(
                {"_id": ObjectId(resume_id)},
                {"$set": {
                    "status": "failed",
                    "error_message": error_msg,
                    "updated_at": datetime.utcnow()
                }}
            )
            return

        # 2. Evaluate resume with AI
        parsed_data_struct = {
            "contact": parsed_data.get("contact", {}),
            "skills": parsed_data.get("skills", []),
            "experience": parsed_data.get("experience", []),
            "education": parsed_data.get("education", []),
            "projects": parsed_data.get("projects", [])
        }
        ai_feedback = await ai_resume_evaluator.evaluate_resume(parsed_data=parsed_data_struct)
        
        # 3. Save to global cache
        cache_doc = {
            "file_hash": file_hash,
            "parsed_data": parsed_data_struct,
            "feedback": ai_feedback or {},
            "raw_text": parsed_data.get("raw_text", ""),
            "parsing_confidence": parsed_data.get("parsing_confidence", 0.0),
            "ai_enhanced": parsed_data.get("ai_enhanced", False),
            "extraction_method": parsed_data.get("extraction_method", ""),
            "created_at": datetime.utcnow()
        }
        await resume_cache_collection().update_one(
            {"file_hash": file_hash},
            {"$set": cache_doc},
            upsert=True
        )

        # 4. Update the uploaded resume document
        await resumes_collection().update_one(
            {"_id": ObjectId(resume_id)},
            {"$set": {
                "parsed_data": parsed_data_struct,
                "feedback": ai_feedback or {},
                "raw_text": parsed_data.get("raw_text", "")[:10000],
                "parsing_confidence": parsed_data.get("parsing_confidence", 0.0),
                "ai_enhanced": parsed_data.get("ai_enhanced", False),
                "extraction_method": parsed_data.get("extraction_method", ""),
                "status": "completed",
                "updated_at": datetime.utcnow()
            }}
        )

        # 5. Merge skills into user profile for Gap Analysis
        if parsed_data.get("skills"):
            user = await user_model.get_user_by_id(student_id)
            if user:
                user_skills = user.get("skills", [])
                existing_skill_names = set(
                    s.get("name", "").lower() if isinstance(s, dict) else str(s).lower() 
                    for s in user_skills
                )
                
                new_skills = []
                for skill in parsed_data["skills"]:
                    if isinstance(skill, str) and skill.lower() not in existing_skill_names:
                        new_skills.append(skill)
                        existing_skill_names.add(skill.lower())
                
                if new_skills:
                    all_skills = [
                        s.get("name") if isinstance(s, dict) else str(s)
                        for s in user_skills
                    ] + new_skills
                    await user_model.update_user(student_id, {"skills": all_skills})

    except Exception as e:
        logger.error(f"Error in background resume parsing task for {resume_id}: {e}", exc_info=True)
        # Clean up file
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
        await resumes_collection().update_one(
            {"_id": ObjectId(resume_id)},
            {"$set": {
                "status": "failed",
                "error_message": str(e),
                "updated_at": datetime.utcnow()
            }}
        )


# ============ Upload Endpoint ============

@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    use_ai_enhancement: bool = Query(False, description="Use AI to enhance parsing"),
    current_user=Depends(get_current_user)
):
    """
    Upload and parse a resume PDF asynchronously.
    
    - Computes SHA-256 hash
    - Checks global cache; if exists, returns immediately
    - Otherwise, saves file and initiates background parsing task
    """
    student_id = str(current_user["_id"])
    
    # Validate file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Pre-read size check
    if hasattr(file, 'size') and file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"File too large. Max size is {MAX_FILE_SIZE // (1024*1024)}MB")
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"File too large. Max size is {MAX_FILE_SIZE // (1024*1024)}MB")
    
    # Calculate file hash for deduplication
    file_hash = resume_parser.get_file_hash_from_bytes(content)
    
    # 1. Check global resume cache first
    cache_hit = await resume_cache_collection().find_one({"file_hash": file_hash})
    if cache_hit:
        parsed_data = cache_hit.get("parsed_data", {})
        ai_feedback = cache_hit.get("feedback", {})
        
        # Save cache hit as a new document for this student in resume_uploads
        doc = {
            "student_id": ObjectId(student_id),
            "file_name": file.filename,
            "file_path": None,  # No new local file saved
            "file_hash": file_hash,
            "parsed_data": parsed_data,
            "feedback": ai_feedback,
            "raw_text": cache_hit.get("raw_text", ""),
            "parsing_confidence": cache_hit.get("parsing_confidence", 0.0),
            "ai_enhanced": cache_hit.get("ai_enhanced", False),
            "extraction_method": cache_hit.get("extraction_method", ""),
            "status": "completed",
            "uploaded_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        result = await resumes_collection().insert_one(doc)
        resume_id = str(result.inserted_id)
        
        # Merge skills to user profile
        if parsed_data.get("skills"):
            user = await user_model.get_user_by_id(student_id)
            if user:
                user_skills = user.get("skills", [])
                existing_skill_names = set(
                    s.get("name", "").lower() if isinstance(s, dict) else str(s).lower() 
                    for s in user_skills
                )
                
                new_skills = []
                for skill in parsed_data["skills"]:
                    if isinstance(skill, str) and skill.lower() not in existing_skill_names:
                        new_skills.append(skill)
                        existing_skill_names.add(skill.lower())
                
                if new_skills:
                    all_skills = [
                        s.get("name") if isinstance(s, dict) else str(s)
                        for s in user_skills
                    ] + new_skills
                    await user_model.update_user(student_id, {"skills": all_skills})
                    
        return ResumeUploadResponse(
            status="completed",
            resume_id=resume_id,
            file_name=file.filename,
            overall_score=ai_feedback.get("overall_score", 0.0),
            category_scores=ai_feedback.get("category_scores", {}),
            executive_summary=ai_feedback.get("executive_summary", ""),
            strengths=ai_feedback.get("strengths", []),
            improvements=ai_feedback.get("improvements", []),
            action_plan=ai_feedback.get("action_plan", []),
            extracted_skills=parsed_data.get("skills", []),
            experience=[ParsedExperience(**e) for e in parsed_data.get("experience", [])],
            education=[ParsedEducation(**e) for e in parsed_data.get("education", [])],
            contact=ParsedContact(**parsed_data.get("contact", {})),
            projects=[ParsedProject(**p) for p in parsed_data.get("projects", [])],
            parsing_confidence=cache_hit.get("parsing_confidence", 0.0),
            ai_enhanced=cache_hit.get("ai_enhanced", False),
            message="Retrieved existing parsed resume from cache."
        )

    # 2. Check for student-specific upload duplicate
    existing = await resumes_collection().find_one({
        "student_id": ObjectId(student_id),
        "file_hash": file_hash
    })
    if existing:
        ai_feedback = existing.get("feedback", {})
        parsed_data = existing.get("parsed_data", {})
        status = existing.get("status", "completed")
        
        return ResumeUploadResponse(
            status=status,
            resume_id=str(existing["_id"]),
            file_name=existing.get("file_name", file.filename),
            overall_score=ai_feedback.get("overall_score", 0.0),
            category_scores=ai_feedback.get("category_scores", {}),
            executive_summary=ai_feedback.get("executive_summary", ""),
            strengths=ai_feedback.get("strengths", []),
            improvements=ai_feedback.get("improvements", []),
            action_plan=ai_feedback.get("action_plan", []),
            extracted_skills=parsed_data.get("skills", []),
            experience=[ParsedExperience(**e) for e in parsed_data.get("experience", [])],
            education=[ParsedEducation(**e) for e in parsed_data.get("education", [])],
            contact=ParsedContact(**parsed_data.get("contact", {})),
            projects=[ParsedProject(**p) for p in parsed_data.get("projects", [])],
            parsing_confidence=existing.get("parsing_confidence", 0),
            ai_enhanced=existing.get("ai_enhanced", False),
            message=f"Resume already exists for this student. Status: {status}",
            error_message=existing.get("error_message")
        )
    
    # Save file
    file_path = get_resume_path(student_id, file.filename)
    with open(file_path, "wb") as f:
        f.write(content)
        
    # Store in MongoDB with "processing" status
    doc = {
        "student_id": ObjectId(student_id),
        "file_name": file.filename,
        "file_path": file_path,
        "file_hash": file_hash,
        "status": "processing",
        "uploaded_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    result = await resumes_collection().insert_one(doc)
    resume_id = str(result.inserted_id)
    
    # Dispatch background task
    background_tasks.add_task(
        parse_resume_background_task,
        resume_id=resume_id,
        file_path=file_path,
        file_hash=file_hash,
        use_ai_enhancement=use_ai_enhancement,
        student_id=student_id
    )
    
    return ResumeUploadResponse(
        status="processing",
        resume_id=resume_id,
        file_name=file.filename,
        message="Resume uploaded successfully. Parsing in progress."
    )


# ============ List Resumes ============

@router.get("/my-resumes", response_model=MyResumesResponse)
async def get_my_resumes(current_user=Depends(get_current_user)):
    """Get all resumes uploaded by the current user."""
    student_id = str(current_user["_id"])
    
    cursor = resumes_collection().find({
        "student_id": ObjectId(student_id)
    }).sort("uploaded_at", -1)
    
    docs = await cursor.to_list(length=50)
    
    resumes = []
    for doc in docs:
        contact = doc.get("parsed_data", {}).get("contact", {})
        resumes.append(ResumeListItem(
            id=str(doc["_id"]),
            file_name=doc.get("file_name", ""),
            name=contact.get("name"),
            parsing_confidence=doc.get("parsing_confidence", 0),
            skills_count=len(doc.get("parsed_data", {}).get("skills", [])),
            uploaded_at=doc.get("uploaded_at", datetime.utcnow()),
            status=doc.get("status", "completed")
        ))
    
    return MyResumesResponse(
        resumes=resumes,
        total=len(resumes)
    )


# ============ Get Resume Detail ============

@router.get("/{resume_id}", response_model=ResumeDetailResponse)
async def get_resume(resume_id: str, current_user=Depends(get_current_user)):
    """Get detailed parsed resume by ID."""
    if not ObjectId.is_valid(resume_id):
        raise HTTPException(status_code=400, detail="Invalid resume ID")
    
    doc = await resumes_collection().find_one({
        "_id": ObjectId(resume_id)
    })
    
    if not doc:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    # Verify ownership
    if str(doc["student_id"]) != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Access denied")
    
    parsed_data = doc.get("parsed_data", {})
    ai_feedback = doc.get("feedback", {})
    
    return ResumeDetailResponse(
        status=doc.get("status", "completed"),
        id=str(doc["_id"]),
        file_name=doc.get("file_name", ""),
        file_url=None,  # Can add file serving later
        
        # AI fields
        overall_score=ai_feedback.get("overall_score", 0.0),
        category_scores=ai_feedback.get("category_scores", {}),
        executive_summary=ai_feedback.get("executive_summary", ""),
        strengths=ai_feedback.get("strengths", []),
        improvements=ai_feedback.get("improvements", []),
        action_plan=ai_feedback.get("action_plan", []),
        
        # Parsed fields
        extracted_skills=parsed_data.get("skills", []),
        experience=[ParsedExperience(**e) for e in parsed_data.get("experience", [])],
        education=[ParsedEducation(**e) for e in parsed_data.get("education", [])],
        contact=ParsedContact(**parsed_data.get("contact", {})),
        projects=[ParsedProject(**p) for p in parsed_data.get("projects", [])],
        
        uploaded_at=doc.get("uploaded_at", datetime.utcnow()),
        updated_at=doc.get("updated_at"),
        error_message=doc.get("error_message")
    )


# ============ Reparse with AI ============

@router.post("/reparse/{resume_id}", response_model=ReparseResponse)
async def reparse_resume(
    resume_id: str,
    payload: ReparseRequest,
    current_user=Depends(get_current_user)
):
    """
    Reparse an existing resume with AI enhancement.
    User can choose to enable/disable AI for the reparse.
    """
    if not ObjectId.is_valid(resume_id):
        raise HTTPException(status_code=400, detail="Invalid resume ID")
    
    doc = await resumes_collection().find_one({
        "_id": ObjectId(resume_id)
    })
    
    if not doc:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    # Verify ownership
    if str(doc["student_id"]) != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Access denied")
    
    file_path = doc.get("file_path", "")
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Resume file not found on disk")
    
    previous_confidence = doc.get("parsing_confidence", 0)
    
    # Reparse with AI
    parsed_data = await resume_parser.parse_resume(
        file_path,
        use_ai_enhancement=payload.use_ai
    )
    
    if not parsed_data.get("success"):
        raise HTTPException(
            status_code=422,
            detail=parsed_data.get("error", "Failed to reparse resume")
        )
    
    # Track changes
    changes = []
    old_data = doc.get("parsed_data", {})
    new_data = {
        "contact": parsed_data.get("contact", {}),
        "skills": parsed_data.get("skills", []),
        "experience": parsed_data.get("experience", []),
        "education": parsed_data.get("education", []),
        "projects": parsed_data.get("projects", []),
    }
    
    if old_data.get("contact", {}).get("name") != new_data["contact"].get("name"):
        changes.append(f"Name: {new_data['contact'].get('name')}")
    if set(old_data.get("skills", [])) != set(new_data["skills"]):
        changes.append(f"Skills updated ({len(new_data['skills'])} found)")
    if len(old_data.get("experience", [])) != len(new_data["experience"]):
        changes.append(f"Experience entries: {len(new_data['experience'])}")
    
    # Generate New AI Feedback based on reparsed data
    ai_feedback = await ai_resume_evaluator.evaluate_resume(
        parsed_data=new_data
    )
    
    # Update in MongoDB
    update_data = {
        "parsed_data": new_data,
        "parsing_confidence": parsed_data.get("parsing_confidence", 0),
        "ai_enhanced": parsed_data.get("ai_enhanced", False),
        "updated_at": datetime.utcnow(),
    }
    if ai_feedback:
        update_data["feedback"] = ai_feedback
        changes.append("AI Profile Evaluator generated fresh feedback and actionable insights.")

    await resumes_collection().update_one(
        {"_id": ObjectId(resume_id)},
        {"$set": update_data}
    )
    
    # Merge skills into user profile for Gap Analysis
    if new_data.get("skills"):
        user = await user_model.get_user_by_id(str(doc["student_id"]))
        if user:
            user_skills = user.get("skills", [])
            existing_skill_names = set(
                s.get("name", "").lower() if isinstance(s, dict) else str(s).lower() 
                for s in user_skills
            )
            
            new_skills = []
            for skill in new_data["skills"]:
                if isinstance(skill, str) and skill.lower() not in existing_skill_names:
                    new_skills.append(skill)
                    existing_skill_names.add(skill.lower())
            
            if new_skills:
                all_skills = [
                    s.get("name") if isinstance(s, dict) else str(s)
                    for s in user_skills
                ] + new_skills
                await user_model.update_user(str(doc["student_id"]), {"skills": all_skills})
    
    return ReparseResponse(
        resume_id=resume_id,
        previous_confidence=previous_confidence,
        new_confidence=parsed_data.get("parsing_confidence", 0),
        ai_enhanced=parsed_data.get("ai_enhanced", False),
        changes_made=changes if changes else ["No significant changes detected"]
    )


# ============ Delete Resume ============

@router.delete("/{resume_id}", response_model=DeleteResponse)
async def delete_resume(resume_id: str, current_user=Depends(get_current_user)):
    """Delete a resume and its file."""
    if not ObjectId.is_valid(resume_id):
        raise HTTPException(status_code=400, detail="Invalid resume ID")
    
    doc = await resumes_collection().find_one({
        "_id": ObjectId(resume_id)
    })
    
    if not doc:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    # Verify ownership
    if str(doc["student_id"]) != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Access denied")
    
    file_path = doc.get("file_path", "")
    # Delete DB record first (atomic), then file
    await resumes_collection().delete_one({"_id": ObjectId(resume_id)})
    try:
        if file_path:
            os.remove(file_path)
    except OSError as e:
        logger.warning(f"Could not delete file {file_path}: {e}")
    
    return DeleteResponse(message="Resume deleted successfully")


# ============ Get Skills from Resume ============

@router.get("/{resume_id}/skills")
async def get_resume_skills(resume_id: str, current_user=Depends(get_current_user)):
    """Get just the skills from a parsed resume."""
    if not ObjectId.is_valid(resume_id):
        raise HTTPException(status_code=400, detail="Invalid resume ID")
    
    doc = await resumes_collection().find_one({
        "_id": ObjectId(resume_id)
    })
    
    if not doc:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    # Verify ownership
    if str(doc["student_id"]) != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Access denied")
    
    skills = doc.get("parsed_data", {}).get("skills", [])
    
    return {
        "status": "success",
        "resume_id": resume_id,
        "skills": skills,
        "count": len(skills)
    }
