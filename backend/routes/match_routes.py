from fastapi import APIRouter, Depends, HTTPException

from ..models import job as job_model
from ..models import user as user_model
from ..schemas.user_schema import UserPublic
from ..utils.dependencies import get_current_recruiter

router = APIRouter()


def db_user_to_public(db_user: dict) -> UserPublic:
    """Convert MongoDB user document to UserPublic response model."""
    user_id = str(db_user.get("_id") or db_user.get("id"))
    return UserPublic(
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
        created_at=db_user.get("created_at"),
        updated_at=db_user.get("updated_at"),
    )


@router.get("/{job_id}/matches", response_model=list[UserPublic])
async def job_matches(job_id: str, recruiter=Depends(get_current_recruiter)):
    job = await job_model.get_job(job_id)
    if not job or str(job["recruiter_id"]) != str(recruiter["_id"]):
        raise HTTPException(status_code=404, detail="Job not found")

    students = await user_model.list_students_by_skill_matches(job["skills_required"])

    def match_score(student):
        student_skills = set(student.get("skills", []))
        return len(student_skills.intersection(set(job["skills_required"])))

    sorted_students = sorted(
        students, key=match_score, reverse=True
    )
    return [db_user_to_public(student) for student in sorted_students]


