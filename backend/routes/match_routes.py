from fastapi import APIRouter, Depends, HTTPException

from ..models import job as job_model
from ..models import user as user_model
from ..schemas.user_schema import UserPublic, MatchResult, MatchExplanation
from ..utils.dependencies import get_current_recruiter

router = APIRouter()

SYNONYM_MAP = {
    "reactjs": "react",
    "react.js": "react",
    "nodejs": "node",
    "node.js": "node",
    "mongodb": "mongo",
    "postgresql": "postgres",
    "js": "javascript",
    "py": "python",
}


def normalize_skill(skill: str) -> str:
    s = skill.lower().strip()
    return SYNONYM_MAP.get(s, s)


def calculate_match_explanation(student: dict, required_skills: list[str]) -> MatchExplanation:
    """Calculate detailed weighted match scores."""
    if not required_skills:
        return MatchExplanation(
            matched_skills=[],
            missing_skills=[],
            skill_match_score=0,
            proficiency_score=0,
            activity_score=0,
            completeness_score=0,
            total_score=0
        )

    # Get student skills as objects (handle migration-on-the-fly)
    student_skills = student.get("skills", [])
    student_skills_dict = {normalize_skill(s["name"]): s for s in student_skills}
    normalized_required = [normalize_skill(s) for s in required_skills]
    
    matched_skills = []
    missing_skills = []
    skill_match_sum = 0
    proficiency_sum = 0
    
    for req in normalized_required:
        if req in student_skills_dict:
            matched_skills.append(req)
            skill_match_sum += 1
            # Add proficiency weight (normalize level 0-100 to 0-1)
            proficiency_sum += (student_skills_dict[req].get("level", 50) / 100)
        else:
            missing_skills.append(req)
            
    # Component Scores (0.0 to 1.0)
    skill_match_score = skill_match_sum / len(normalized_required)
    proficiency_score = proficiency_sum / skill_match_sum if skill_match_sum else 0
    
    # AI Profile signals
    ai_profile = student.get("ai_profile") or {}
    activity_score = ai_profile.get("activity_score", 0.0)
    completeness_score = ai_profile.get("profile_completeness", 0.0)
    
    # Weighted Result
    total_score = (
        (skill_match_score * 0.5) +
        (proficiency_score * 0.2) +
        (activity_score * 0.15) +
        (completeness_score * 0.15)
    )
    
    return MatchExplanation(
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        skill_match_score=round(skill_match_score, 2),
        proficiency_score=round(proficiency_score, 2),
        activity_score=round(activity_score, 2),
        completeness_score=round(completeness_score, 2),
        total_score=round(total_score, 2)
    )


def db_user_to_match_result(db_user: dict, explanation: MatchExplanation) -> MatchResult:
    """Convert MongoDB user doc and explanation to MatchResult."""
    user_id = str(db_user.get("_id") or db_user.get("id"))
    public_user = UserPublic(
        id=user_id,
        role=db_user["role"],
        username=db_user["username"],
        email=db_user["email"],
        full_name=db_user.get("full_name"),
        prn=db_user.get("prn"),
        college=db_user.get("college"),
        branch=db_user.get("branch"),
        year=db_user.get("year"),
        company_name=db_user.get("company_name"),
        contact_number=db_user.get("contact_number"),
        website=db_user.get("website"),
        company_description=db_user.get("company_description"),
        avatar_url=db_user.get("avatar_url"),
        bio=db_user.get("bio"),
        skills=db_user.get("skills") or [],
        ai_profile=db_user.get("ai_profile"),
        created_at=db_user.get("created_at"),
        updated_at=db_user.get("updated_at"),
    )
    return MatchResult(
        **public_user.model_dump(),
        match_score=explanation.total_score,
        explanation=explanation
    )


@router.get("/{job_id}/matches", response_model=list[MatchResult])
async def job_matches(job_id: str, recruiter=Depends(get_current_recruiter)):
    job = await job_model.get_job(job_id)
    if not job or str(job["recruiter_id"]) != str(recruiter["_id"]):
        raise HTTPException(status_code=404, detail="Job not found")

    required_skills = job.get("skills_required", [])
    students = await user_model.list_students_by_skill_matches(required_skills)

    results = []
    for student in students:
        explanation = calculate_match_explanation(student, required_skills)
        results.append(db_user_to_match_result(student, explanation))

    # Sort by total score descending
    sorted_results = sorted(
        results, key=lambda x: x.match_score, reverse=True
    )
    return sorted_results


