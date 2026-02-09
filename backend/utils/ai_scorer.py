from datetime import datetime
from ..models import user as user_model
from ..models import activity as activity_model
from ..models.interview import interviews_collection
from ..models.offer import offers_collection
from bson import ObjectId

async def calculate_student_scores(user_id: str):
    """
    Calculate AI Career Profile scores for a student based on their platform data.
    """
    if not ObjectId.is_valid(user_id):
        return None
        
    student = await user_model.get_user_by_id(user_id)
    if not student or student.get("role") != "student":
        return None

    # 1. Skill Score (Average of skill levels)
    skills = student.get("skills", [])
    skill_score = 0.0
    if skills:
        skill_score = sum(s.get("level", 50) for s in skills) / len(skills)
    
    # 2. Activity Score (Based on activity logs)
    # For now, a simple count of activities in last 30 days
    activities = await activity_model.get_user_activities(user_id, limit=100)
    activity_score = min(len(activities) * 2, 100.0) # Cap at 100

    # 3. Interview Score (Average ratings)
    cursor = interviews_collection().find({
        "candidate_id": ObjectId(user_id),
        "feedback.rating": {"$exists": True}
    })
    interviews = await cursor.to_list(length=None)
    
    interview_score = 0.0
    ratings = []
    for interview in interviews:
        for f in interview.get("feedback", []):
            if "rating" in f:
                ratings.append(f["rating"])
    
    if ratings:
        # Normalize 1-5 rating to 0-100
        interview_score = (sum(ratings) / len(ratings)) * 20
    else:
        # Default starting score if no interviews yet
        interview_score = 0.0

    # 4. Profile Completeness
    required_fields = ["full_name", "bio", "avatar_url", "college", "branch", "year", "prn"]
    filled_count = sum(1 for field in required_fields if student.get(field))
    profile_completeness = (filled_count / len(required_fields)) * 100

    # 5. Overall Score (Weighted)
    # BOOSTED FOR DEMO: Higher weight on recent activity to show immediate changes
    overall_score = (
        (skill_score * 0.35) +
        (interview_score * 0.25) +
        (activity_score * 0.3) +  # Increased weight
        (profile_completeness * 0.1)
    )

    return {
        "overall_score": round(overall_score, 2),
        "skill_score": round(skill_score, 2),
        "learning_score": 0.0, # Placholder for future module
        "interview_score": round(interview_score, 2),
        "activity_score": round(activity_score, 2),
        "profile_completeness": round(profile_completeness, 2),
        "last_computed_at": datetime.utcnow()
    }

async def update_student_ai_profile(student_id: str):
    """Recalculate and save the student's AI profile."""
    new_scores = await calculate_student_scores(student_id)
    if new_scores:
        await user_model.update_user(student_id, {"ai_profile": new_scores})
        return new_scores
    return None
