"""
Next-Best-Action Routes

Determines the single most impactful next step for a student based on their
profile completeness, skill gaps, and top matching opportunities.
"""

from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from ..models import user as user_model
from ..utils.dependencies import get_current_user
from ..services.recommendation_engine import recommendation_engine

router = APIRouter(prefix="/next-action", tags=["next-action"])


class ActionTarget(BaseModel):
    """Reference to the object an action points at (job, skill, page)."""
    id: Optional[str] = None
    title: Optional[str] = None
    url: Optional[str] = None


class NextAction(BaseModel):
    id: str
    priority: str  # "high" | "medium" | "low"
    type: str  # e.g. apply_to_job, close_skill_gap, complete_onboarding, ...
    title: str
    description: str
    cta: str
    target: ActionTarget = Field(default_factory=ActionTarget)


class NextBestActionResponse(BaseModel):
    student_id: str
    action: NextAction
    context: dict = Field(default_factory=dict)


def _skills_names(user: dict) -> List[str]:
    names = []
    for s in user.get("skills", []):
        if isinstance(s, dict):
            names.append(s.get("name", ""))
        else:
            names.append(str(s))
    return [n for n in names if n]


async def _top_matching_job(student, rank: int = 0):
    """Return the (rank)th best matching job for the student, or None."""
    try:
        result = await recommendation_engine.recommend_jobs(
            student_id=str(student["_id"]),
            limit=max(rank + 1, 5),
        )
        recs = result.get("recommendations", [])
        if rank < len(recs):
            item = recs[rank]
            job = item.get("job", item)
            return job, item.get("score", 0), item.get("match_details", {})
    except Exception:
        pass
    return None


@router.get("", response_model=NextBestActionResponse)
async def get_next_best_action(
    current_user=Depends(get_current_user),
):
    """Compute and return the single next best action for the student."""
    student_id = str(current_user["_id"])

    # 1. Profile / onboarding completeness gates
    if current_user.get("role") != "student":
        return NextBestActionResponse(
            student_id=student_id,
            action=NextAction(
                id="recruiter_dashboard",
                priority="high",
                type="none",
                title="Manage your pipeline",
                description="Review your job postings and candidate pipeline.",
                cta="Go to dashboard",
                target=ActionTarget(url="/dashboard/recruiter"),
            ),
        )

    if not current_user.get("onboarding_completed"):
        return NextBestActionResponse(
            student_id=student_id,
            action=NextAction(
                id="complete_onboarding",
                priority="high",
                type="complete_onboarding",
                title="Finish setting up your profile",
                description="Complete onboarding so we can start matching you with great opportunities.",
                cta="Complete onboarding",
                target=ActionTarget(url="/onboarding"),
            ),
        )

    skills = _skills_names(current_user)
    if not skills:
        return NextBestActionResponse(
            student_id=student_id,
            action=NextAction(
                id="add_skills",
                priority="high",
                type="add_skills",
                title="Add your skills",
                description="Tell us what you know so we can find the best matches for you.",
                cta="Edit profile",
                target=ActionTarget(url="/profile/student"),
            ),
        )

    # 2. Top matching job — suggest applying to the best one
    top = await _top_matching_job(current_user, rank=0)
    if top:
        job, score, match_details = top
        job_id = str(job.get("_id") or job.get("id")) if isinstance(job, dict) else None
        return NextBestActionResponse(
            student_id=student_id,
            action=NextAction(
                id=f"apply_to_job_{job_id}",
                priority="high" if (score or 0) >= 70 else "medium",
                type="apply_to_job",
                title=f"Apply to {job.get('title')}",
                description=(
                    f"{job.get('company_name') or 'Company'} — {score:.0f}% match with your profile. "
                    f"You look like a strong fit."
                ),
                cta="View job and apply",
                target=ActionTarget(
                    id=job_id,
                    title=job.get("title"),
                    url=f"/jobs/{job_id}",
                ),
            ),
            context={"match_score": score, "match_details": match_details},
        )

    # 3. Fallback: explore opportunities
    return NextBestActionResponse(
        student_id=student_id,
        action=NextAction(
            id="explore_opportunities",
            priority="medium",
            type="explore",
            title="Explore opportunities",
            description="We haven't found a top match yet. Browse open jobs to get started.",
            cta="Browse opportunities",
            target=ActionTarget(url="/opportunities"),
        ),
    )
