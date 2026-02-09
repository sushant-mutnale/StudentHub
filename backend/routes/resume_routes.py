"""
Resume Routes
API endpoints for resume upload, parsing, and management.
"""

import os
import shutil
from datetime import datetime
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query

from ..database import get_database
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


router = APIRouter(prefix="/resume", tags=["resume"])

# Constants
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_EXTENSIONS = {".pdf"}
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads", "resumes")


def resumes_collection():
    return get_database()["resume_uploads"]


def ensure_upload_dir():
    """Ensure upload directory exists."""
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    return UPLOAD_DIR


def get_resume_path(student_id: str, filename: str) -> str:
    """Generate unique file path for resume."""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")
    return os.path.join(
        ensure_upload_dir(),
        f"{student_id}_{timestamp}_{safe_filename}"
    )


# ============ Upload Endpoint ============

@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(
    file: UploadFile = File(...),
    use_ai_enhancement: bool = Query(False, description="Use AI to enhance parsing"),
    current_user=Depends(get_current_user)
):
    """
    Upload and parse a resume PDF.
    
    - Stores file permanently with student_id + timestamp
    - Extracts structured data: contact, skills, experience, education, projects
    - Optionally uses AI to improve extraction accuracy
    """
    student_id = str(current_user["_id"])
    
    # Validate file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Read file content
    content = await file.read()
    
    # Validate file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    # Calculate file hash for deduplication
    file_hash = resume_parser.get_file_hash_from_bytes(content) if hasattr(resume_parser, 'get_file_hash_from_bytes') else None
    
    # Check for duplicate
    if file_hash:
        existing = await resumes_collection().find_one({
            "student_id": ObjectId(student_id),
            "file_hash": file_hash
        })
        if existing:
            # [FIX] Return success for duplicate upload to refine UX
            return ResumeUploadResponse(
                resume_id=str(existing["_id"]),
                file_name=existing.get("file_name", file.filename),
                parsed_data=ParsedResume(
                    contact=ParsedContact(**existing.get("parsed_data", {}).get("contact", {})),
                    skills=existing.get("parsed_data", {}).get("skills", []),
                    experience=[ParsedExperience(**e) for e in existing.get("parsed_data", {}).get("experience", [])],
                    education=[ParsedEducation(**e) for e in existing.get("parsed_data", {}).get("education", [])],
                    projects=[ParsedProject(**p) for p in existing.get("parsed_data", {}).get("projects", [])],
                    parsing_confidence=existing.get("parsing_confidence", 0),
                    ai_enhanced=existing.get("ai_enhanced", False),
                    extraction_method=existing.get("extraction_method", ""),
                ),
                parsing_confidence=existing.get("parsing_confidence", 0),
                ai_enhanced=existing.get("ai_enhanced", False),
                message="Resume already exists. Retrieved existing data."
            )
    
    # Save file
    file_path = get_resume_path(student_id, file.filename)
    with open(file_path, "wb") as f:
        f.write(content)
    
    try:
        # Parse resume
        parsed_data = await resume_parser.parse_resume(
            file_path,
            use_ai_enhancement=use_ai_enhancement
        )
        
        if not parsed_data.get("success"):
            # Clean up file on parsing failure
            os.remove(file_path)
            raise HTTPException(
                status_code=422,
                detail=parsed_data.get("error", "Failed to parse resume")
            )
        
        # Store in MongoDB
        doc = {
            "student_id": ObjectId(student_id),
            "file_name": file.filename,
            "file_path": file_path,
            "file_hash": file_hash or "",
            "parsed_data": {
                "contact": parsed_data.get("contact", {}),
                "skills": parsed_data.get("skills", []),
                "experience": parsed_data.get("experience", []),
                "education": parsed_data.get("education", []),
                "projects": parsed_data.get("projects", []),
            },
            "raw_text": parsed_data.get("raw_text", "")[:10000],  # Limit stored text
            "parsing_confidence": parsed_data.get("parsing_confidence", 0),
            "ai_enhanced": parsed_data.get("ai_enhanced", False),
            "extraction_method": parsed_data.get("extraction_method", ""),
            "uploaded_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        
        result = await resumes_collection().insert_one(doc)
        resume_id = str(result.inserted_id)
        
        # Build response
        parsed_response = ParsedResume(
            contact=ParsedContact(**parsed_data.get("contact", {})),
            skills=parsed_data.get("skills", []),
            experience=[ParsedExperience(**e) for e in parsed_data.get("experience", [])],
            education=[ParsedEducation(**e) for e in parsed_data.get("education", [])],
            projects=[ParsedProject(**p) for p in parsed_data.get("projects", [])],
            parsing_confidence=parsed_data.get("parsing_confidence", 0),
            ai_enhanced=parsed_data.get("ai_enhanced", False),
            extraction_method=parsed_data.get("extraction_method", ""),
        )
        
        return ResumeUploadResponse(
            resume_id=resume_id,
            file_name=file.filename,
            parsed_data=parsed_response,
            parsing_confidence=parsed_data.get("parsing_confidence", 0),
            ai_enhanced=parsed_data.get("ai_enhanced", False),
            message=f"Resume parsed with {parsed_data.get('parsing_confidence', 0):.1f}% confidence"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # Clean up file on error
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Parsing error: {str(e)}")


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
            uploaded_at=doc.get("uploaded_at", datetime.utcnow())
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
    
    return ResumeDetailResponse(
        id=str(doc["_id"]),
        file_name=doc.get("file_name", ""),
        file_url=None,  # Can add file serving later
        parsed_data=ParsedResume(
            contact=ParsedContact(**parsed_data.get("contact", {})),
            skills=parsed_data.get("skills", []),
            experience=[ParsedExperience(**e) for e in parsed_data.get("experience", [])],
            education=[ParsedEducation(**e) for e in parsed_data.get("education", [])],
            projects=[ParsedProject(**p) for p in parsed_data.get("projects", [])],
            parsing_confidence=doc.get("parsing_confidence", 0),
            ai_enhanced=doc.get("ai_enhanced", False),
            extraction_method=doc.get("extraction_method", ""),
        ),
        uploaded_at=doc.get("uploaded_at", datetime.utcnow()),
        updated_at=doc.get("updated_at")
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
    
    # Update in MongoDB
    await resumes_collection().update_one(
        {"_id": ObjectId(resume_id)},
        {
            "$set": {
                "parsed_data": new_data,
                "parsing_confidence": parsed_data.get("parsing_confidence", 0),
                "ai_enhanced": parsed_data.get("ai_enhanced", False),
                "updated_at": datetime.utcnow(),
            }
        }
    )
    
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
    
    # Delete file
    file_path = doc.get("file_path", "")
    if file_path and os.path.exists(file_path):
        os.remove(file_path)
    
    # Delete from MongoDB
    await resumes_collection().delete_one({"_id": ObjectId(resume_id)})
    
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
