"""
Job Description Routes
API endpoints for JD parsing, saving, and skill matching.
"""

from datetime import datetime
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from ..database import get_database
from ..services.jd_parser import jd_parser
from ..schemas.jd_schema import (
    ParseJDRequest,
    ParseJDResponse,
    ParsedJobDescription,
    SalaryRange,
    JobLocation,
    SaveJDRequest,
    SaveJDResponse,
    SavedJD,
    MyJDsResponse,
    JDDetailResponse,
    SkillMatchRequest,
    SkillMatchResponse,
    SkillMatchResult,
    DeleteJDResponse,
)
from ..utils.dependencies import get_current_user


router = APIRouter(prefix="/jd", tags=["job-descriptions"])


def jd_collection():
    return get_database()["job_descriptions"]


def resumes_collection():
    return get_database()["resume_uploads"]


# ============ Parse JD ============

@router.post("/parse", response_model=ParseJDResponse)
async def parse_job_description(
    payload: ParseJDRequest,
    current_user=Depends(get_current_user)
):
    """
    Parse a job description text and extract structured data.
    
    - Extracts: job title, company, skills, experience level, responsibilities
    - Optionally uses AI for better extraction accuracy
    """
    parsed_data = await jd_parser.parse_jd(
        payload.jd_text,
        use_ai_enhancement=payload.use_ai_enhancement
    )
    
    if not parsed_data.get("success"):
        raise HTTPException(
            status_code=422,
            detail=parsed_data.get("error", "Failed to parse job description")
        )
    
    # Build response
    salary = parsed_data.get("salary_range", {})
    location = parsed_data.get("location", {})
    
    parsed_response = ParsedJobDescription(
        job_title=parsed_data.get("job_title", ""),
        company=parsed_data.get("company", ""),
        required_skills=parsed_data.get("required_skills", []),
        nice_to_have_skills=parsed_data.get("nice_to_have_skills", []),
        experience_level=parsed_data.get("experience_level", "not_specified"),
        responsibilities=parsed_data.get("responsibilities", []),
        qualifications=parsed_data.get("qualifications", []),
        salary_range=SalaryRange(**salary) if salary else None,
        location=JobLocation(**location) if location else None,
        parsing_confidence=parsed_data.get("parsing_confidence", 0),
        ai_enhanced=parsed_data.get("ai_enhanced", False),
    )
    
    return ParseJDResponse(
        parsed_data=parsed_response,
        parsing_confidence=parsed_data.get("parsing_confidence", 0),
        ai_enhanced=parsed_data.get("ai_enhanced", False),
        message=f"Parsed with {parsed_data.get('parsing_confidence', 0):.1f}% confidence"
    )


# ============ Save JD ============

@router.post("/save", response_model=SaveJDResponse)
async def save_job_description(
    payload: SaveJDRequest,
    current_user=Depends(get_current_user)
):
    """
    Save a job description for future reference.
    Parses if not already parsed.
    """
    student_id = str(current_user["_id"])
    
    # Parse if not provided
    if payload.parsed_data:
        parsed_data = payload.parsed_data.dict()
    else:
        result = await jd_parser.parse_jd(payload.jd_text, use_ai_enhancement=False)
        if not result.get("success"):
            raise HTTPException(status_code=422, detail="Failed to parse JD")
        parsed_data = result
    
    doc = {
        "student_id": ObjectId(student_id),
        "jd_text": payload.jd_text,
        "job_title": parsed_data.get("job_title", ""),
        "company": parsed_data.get("company", ""),
        "required_skills": parsed_data.get("required_skills", []),
        "nice_to_have_skills": parsed_data.get("nice_to_have_skills", []),
        "experience_level": parsed_data.get("experience_level", "not_specified"),
        "responsibilities": parsed_data.get("responsibilities", []),
        "qualifications": parsed_data.get("qualifications", []),
        "salary_range": parsed_data.get("salary_range"),
        "location": parsed_data.get("location"),
        "parsing_confidence": parsed_data.get("parsing_confidence", 0),
        "job_url": payload.job_url,
        "notes": payload.notes,
        "saved_at": datetime.utcnow(),
    }
    
    result = await jd_collection().insert_one(doc)
    
    return SaveJDResponse(
        jd_id=str(result.inserted_id),
        message="Job description saved successfully"
    )


# ============ List Saved JDs ============

@router.get("/my-jds", response_model=MyJDsResponse)
async def get_my_job_descriptions(current_user=Depends(get_current_user)):
    """Get all job descriptions saved by the current user."""
    student_id = str(current_user["_id"])
    
    cursor = jd_collection().find({
        "student_id": ObjectId(student_id)
    }).sort("saved_at", -1)
    
    docs = await cursor.to_list(length=50)
    
    jds = []
    for doc in docs:
        jds.append(SavedJD(
            id=str(doc["_id"]),
            student_id=str(doc["student_id"]),
            job_title=doc.get("job_title", ""),
            company=doc.get("company", ""),
            required_skills=doc.get("required_skills", []),
            experience_level=doc.get("experience_level", "not_specified"),
            parsing_confidence=doc.get("parsing_confidence", 0),
            job_url=doc.get("job_url"),
            saved_at=doc.get("saved_at", datetime.utcnow())
        ))
    
    return MyJDsResponse(
        job_descriptions=jds,
        total=len(jds)
    )


# ============ Get JD Detail ============

@router.get("/{jd_id}", response_model=JDDetailResponse)
async def get_job_description(jd_id: str, current_user=Depends(get_current_user)):
    """Get detailed job description by ID."""
    if not ObjectId.is_valid(jd_id):
        raise HTTPException(status_code=400, detail="Invalid JD ID")
    
    doc = await jd_collection().find_one({"_id": ObjectId(jd_id)})
    
    if not doc:
        raise HTTPException(status_code=404, detail="Job description not found")
    
    # Verify ownership
    if str(doc["student_id"]) != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Access denied")
    
    salary = doc.get("salary_range")
    location = doc.get("location")
    
    return JDDetailResponse(
        id=str(doc["_id"]),
        jd_text=doc.get("jd_text", ""),
        parsed_data=ParsedJobDescription(
            job_title=doc.get("job_title", ""),
            company=doc.get("company", ""),
            required_skills=doc.get("required_skills", []),
            nice_to_have_skills=doc.get("nice_to_have_skills", []),
            experience_level=doc.get("experience_level", "not_specified"),
            responsibilities=doc.get("responsibilities", []),
            qualifications=doc.get("qualifications", []),
            salary_range=SalaryRange(**salary) if salary else None,
            location=JobLocation(**location) if location else None,
            parsing_confidence=doc.get("parsing_confidence", 0),
        ),
        job_url=doc.get("job_url"),
        notes=doc.get("notes"),
        saved_at=doc.get("saved_at", datetime.utcnow())
    )


# ============ Delete JD ============

@router.delete("/{jd_id}", response_model=DeleteJDResponse)
async def delete_job_description(jd_id: str, current_user=Depends(get_current_user)):
    """Delete a saved job description."""
    if not ObjectId.is_valid(jd_id):
        raise HTTPException(status_code=400, detail="Invalid JD ID")
    
    doc = await jd_collection().find_one({"_id": ObjectId(jd_id)})
    
    if not doc:
        raise HTTPException(status_code=404, detail="Job description not found")
    
    # Verify ownership
    if str(doc["student_id"]) != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Access denied")
    
    await jd_collection().delete_one({"_id": ObjectId(jd_id)})
    
    return DeleteJDResponse(message="Job description deleted successfully")


# ============ Match Skills ============

@router.post("/match-skills", response_model=SkillMatchResponse)
async def match_skills(
    payload: SkillMatchRequest,
    current_user=Depends(get_current_user)
):
    """
    Match skills between a parsed resume and job description.
    Returns matched, missing required, and missing nice-to-have skills.
    """
    student_id = str(current_user["_id"])
    
    # Get resume
    if not ObjectId.is_valid(payload.resume_id):
        raise HTTPException(status_code=400, detail="Invalid resume ID")
    
    resume_doc = await resumes_collection().find_one({
        "_id": ObjectId(payload.resume_id)
    })
    
    if not resume_doc:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    if str(resume_doc["student_id"]) != student_id:
        raise HTTPException(status_code=403, detail="Access denied to resume")
    
    # Get JD
    if not ObjectId.is_valid(payload.jd_id):
        raise HTTPException(status_code=400, detail="Invalid JD ID")
    
    jd_doc = await jd_collection().find_one({
        "_id": ObjectId(payload.jd_id)
    })
    
    if not jd_doc:
        raise HTTPException(status_code=404, detail="Job description not found")
    
    if str(jd_doc["student_id"]) != student_id:
        raise HTTPException(status_code=403, detail="Access denied to JD")
    
    # Extract skills
    resume_skills = set(
        s.lower() for s in resume_doc.get("parsed_data", {}).get("skills", [])
    )
    required_skills = set(s.lower() for s in jd_doc.get("required_skills", []))
    nice_to_have = set(s.lower() for s in jd_doc.get("nice_to_have_skills", []))
    
    # Calculate matches
    matched = resume_skills & required_skills
    matched_nice = resume_skills & nice_to_have
    missing_required = required_skills - resume_skills
    missing_nice = nice_to_have - resume_skills
    
    # Calculate match percentage
    if required_skills:
        match_pct = (len(matched) / len(required_skills)) * 100
    else:
        match_pct = 100 if not required_skills else 0
    
    # Generate recommendation
    if match_pct >= 80:
        recommendation = "Excellent match! You have most of the required skills."
    elif match_pct >= 60:
        recommendation = "Good match. Consider highlighting transferable skills and learning the missing ones."
    elif match_pct >= 40:
        recommendation = "Moderate match. Focus on acquiring the missing required skills before applying."
    else:
        recommendation = "Low match. This role requires significant upskilling. Consider it as a stretch goal."
    
    return SkillMatchResponse(
        result=SkillMatchResult(
            matched_skills=sorted(matched | matched_nice),
            missing_required=sorted(missing_required),
            missing_nice_to_have=sorted(missing_nice),
            match_percentage=round(match_pct, 1),
            recommendation=recommendation
        )
    )


# ============ Quick Parse (No Auth) ============

@router.post("/quick-parse")
async def quick_parse_jd(
    jd_text: str = Query(..., min_length=50, description="JD text to parse"),
    use_ai: bool = Query(False)
):
    """
    Quick parse a JD without authentication.
    For demo/testing purposes.
    """
    parsed = await jd_parser.parse_jd(jd_text, use_ai_enhancement=use_ai)
    
    if not parsed.get("success"):
        raise HTTPException(status_code=422, detail="Failed to parse")
    
    return {
        "status": "success",
        "job_title": parsed.get("job_title"),
        "company": parsed.get("company"),
        "required_skills": parsed.get("required_skills"),
        "experience_level": parsed.get("experience_level"),
        "parsing_confidence": parsed.get("parsing_confidence"),
    }
