"""
Recommendation Engine Service
Intelligent ranking system that matches opportunities to students based on
AI profile, skills, learning gaps, and preferences.

Week 2 Module 4: Personalized recommendation system with 6 scoring components.
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import math

from ..database import get_database


# ============ Collections ============

def opportunities_jobs_collection():
    return get_database()["opportunities_jobs"]


def opportunities_hackathons_collection():
    return get_database()["opportunities_hackathons"]


def opportunities_content_collection():
    return get_database()["opportunities_content"]


def recommendation_feedback_collection():
    return get_database()["recommendation_feedback"]


def users_collection():
    return get_database()["users"]


def learning_paths_collection():
    return get_database()["learning_paths"]


# ============ Skill Normalization ============

SKILL_SYNONYMS = {
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "react.js": "react",
    "reactjs": "react",
    "react native": "react-native",
    "node": "nodejs",
    "node.js": "nodejs",
    "express.js": "express",
    "mongo": "mongodb",
    "postgres": "postgresql",
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "dl": "deep learning",
    "aws": "amazon web services",
    "gcp": "google cloud platform",
    "k8s": "kubernetes",
}


def normalize_skill(skill: str) -> str:
    """Normalize skill name for consistent matching."""
    normalized = skill.lower().strip()
    return SKILL_SYNONYMS.get(normalized, normalized)


def normalize_skills(skills: List[str]) -> List[str]:
    """Normalize list of skills."""
    return [normalize_skill(s) for s in skills]


# ============ Scoring Components ============

class ScoringEngine:
    """
    Calculates recommendation scores based on 6 components:
    - Skill Match (40%)
    - Proficiency Fit (20%)
    - Freshness (15%)
    - Location Match (10%)
    - Career Alignment (10%)
    - AI Profile Readiness (5%)
    """
    
    WEIGHTS = {
        "skill_match": 0.40,
        "proficiency_fit": 0.20,
        "freshness": 0.15,
        "location_match": 0.10,
        "career_alignment": 0.10,
        "ai_readiness": 0.05
    }
    
    @staticmethod
    def calculate_skill_match(
        student_skills: List[Dict],
        required_skills: List[str]
    ) -> Dict[str, Any]:
        """
        Calculate skill match score (0-100).
        Considers which required skills student has.
        """
        if not required_skills:
            return {"score": 50, "matched": [], "missing": [], "reason": "No skills required"}
        
        student_skill_names = normalize_skills([s.get("name", s) if isinstance(s, dict) else s for s in student_skills])
        required_normalized = normalize_skills(required_skills)
        
        matched = []
        missing = []
        
        for req_skill in required_normalized:
            if req_skill in student_skill_names:
                matched.append(req_skill)
            else:
                missing.append(req_skill)
        
        match_percentage = (len(matched) / len(required_normalized)) * 100
        
        # Bonus for high proficiency in matched skills
        proficiency_bonus = 0
        for skill in student_skills:
            if isinstance(skill, dict):
                skill_name = normalize_skill(skill.get("name", ""))
                if skill_name in matched:
                    level = skill.get("level", 50)
                    if level >= 70:
                        proficiency_bonus += 3
                    elif level >= 50:
                        proficiency_bonus += 1
        
        final_score = min(match_percentage + proficiency_bonus, 100)
        
        return {
            "score": round(final_score, 1),
            "matched": matched,
            "missing": missing,
            "reason": f"{len(matched)} of {len(required_normalized)} skills matched"
        }
    
    @staticmethod
    def calculate_proficiency_fit(
        student_skills: List[Dict],
        experience_required: str = "0-1 years"
    ) -> Dict[str, Any]:
        """
        Calculate proficiency fit score (0-100).
        Checks if student is over/under/perfectly qualified.
        """
        # Calculate average student proficiency
        if not student_skills:
            avg_proficiency = 30
        else:
            levels = []
            for skill in student_skills:
                if isinstance(skill, dict):
                    levels.append(skill.get("level", 50))
                else:
                    levels.append(50)
            avg_proficiency = sum(levels) / len(levels) if levels else 30
        
        # Determine expected range
        exp_lower = experience_required.lower() if experience_required else "0-1 years"
        
        if "0" in exp_lower or "fresher" in exp_lower or "entry" in exp_lower:
            # Entry level: 20-60 proficiency is perfect
            if avg_proficiency < 20:
                score = 40  # Underqualified
                reason = "May need more preparation"
            elif avg_proficiency <= 60:
                score = 100  # Perfect fit
                reason = "Perfect match for entry level"
            else:
                score = 70  # Overqualified
                reason = "Might be overqualified"
        elif "1-3" in exp_lower or "mid" in exp_lower:
            # Mid level: 50-80 proficiency is perfect
            if avg_proficiency < 50:
                score = 50
                reason = "May need more experience"
            elif avg_proficiency <= 80:
                score = 100
                reason = "Perfect match for mid level"
            else:
                score = 80
                reason = "Slightly overqualified"
        else:
            # Senior level: 70+ proficiency expected
            if avg_proficiency < 70:
                score = 40
                reason = "May be underqualified"
            else:
                score = 100
                reason = "Good match for senior level"
        
        return {
            "score": score,
            "avg_proficiency": round(avg_proficiency, 1),
            "reason": reason
        }
    
    @staticmethod
    def calculate_freshness(posted_at: datetime) -> Dict[str, Any]:
        """
        Calculate freshness score (0-100).
        Newer opportunities score higher.
        """
        if not posted_at:
            return {"score": 50, "days_old": None, "reason": "Unknown posting date"}
        
        days_old = (datetime.utcnow() - posted_at).days
        
        if days_old <= 1:
            score = 100
            reason = "Posted today"
        elif days_old <= 3:
            score = 90
            reason = f"Posted {days_old} days ago"
        elif days_old <= 7:
            score = 75
            reason = f"Posted {days_old} days ago"
        elif days_old <= 14:
            score = 55
            reason = f"Posted {days_old} days ago"
        elif days_old <= 30:
            score = 35
            reason = f"Posted {days_old} days ago"
        else:
            score = 20
            reason = f"Posted {days_old} days ago (old)"
        
        return {
            "score": score,
            "days_old": days_old,
            "reason": reason
        }
    
    @staticmethod
    def calculate_location_match(
        student_location: str,
        job_location: str,
        work_mode: str
    ) -> Dict[str, Any]:
        """
        Calculate location match score (0-100).
        Remote jobs always match.
        """
        work_mode_lower = (work_mode or "").lower()
        student_loc = (student_location or "").lower()
        job_loc = (job_location or "").lower()
        
        if work_mode_lower == "remote" or "remote" in job_loc or "wfh" in job_loc:
            return {"score": 100, "reason": "Remote/WFH - location doesn't matter"}
        
        if not student_loc or not job_loc:
            return {"score": 60, "reason": "Location info incomplete"}
        
        # Check exact city match
        if student_loc in job_loc or job_loc in student_loc:
            return {"score": 100, "reason": "Same city"}
        
        # Check common Indian cities/regions
        major_cities = {
            "bangalore": ["bengaluru", "blr"],
            "mumbai": ["bombay"],
            "delhi": ["new delhi", "ncr", "gurgaon", "gurugram", "noida", "ghaziabad"],
            "chennai": ["madras"],
            "hyderabad": ["hyd"],
            "pune": [],
            "kolkata": ["calcutta"]
        }
        
        for city, aliases in major_cities.items():
            student_match = student_loc == city or any(a in student_loc for a in aliases)
            job_match = city in job_loc or any(a in job_loc for a in aliases)
            
            if student_match and job_match:
                return {"score": 95, "reason": f"Same metro area"}
        
        if work_mode_lower == "hybrid":
            return {"score": 50, "reason": "Hybrid - some relocation may be needed"}
        
        return {"score": 20, "reason": "Different location - relocation needed"}
    
    @staticmethod
    def calculate_career_alignment(
        student_interests: List[str],
        student_learning_gaps: List[str],
        job_title: str,
        job_skills: List[str]
    ) -> Dict[str, Any]:
        """
        Calculate career alignment score (0-100).
        Higher if job matches interests or helps fill learning gaps.
        """
        score = 50  # Base score
        reasons = []
        
        interests_normalized = normalize_skills(student_interests or [])
        gaps_normalized = normalize_skills(student_learning_gaps or [])
        job_skills_normalized = normalize_skills(job_skills or [])
        title_lower = (job_title or "").lower()
        
        # Check interest match
        for interest in interests_normalized:
            if interest in title_lower or interest in job_skills_normalized:
                score += 15
                reasons.append(f"Matches interest: {interest}")
        
        # Check if job helps fill learning gaps (valuable!)
        gaps_covered = []
        for gap in gaps_normalized:
            if gap in job_skills_normalized:
                score += 10
                gaps_covered.append(gap)
        
        if gaps_covered:
            reasons.append(f"Covers learning gaps: {', '.join(gaps_covered)}")
        
        final_score = min(score, 100)
        reason = "; ".join(reasons) if reasons else "No specific alignment detected"
        
        return {
            "score": final_score,
            "gaps_covered": gaps_covered,
            "reason": reason
        }
    
    @staticmethod
    def calculate_ai_readiness(ai_profile: Dict) -> Dict[str, Any]:
        """
        Calculate AI profile readiness score (0-100).
        Students with higher AI profile are more competitive.
        """
        if not ai_profile:
            return {"score": 50, "reason": "No AI profile data"}
        
        overall = ai_profile.get("overall_score", 50)
        interview_score = ai_profile.get("interview_score", 50)
        learning_score = ai_profile.get("learning_score", 50)
        
        # Base readiness from overall score
        readiness = overall
        
        # Bonus for strong interview skills
        if interview_score >= 70:
            readiness += 10
        
        # Bonus for active learning
        if learning_score >= 60:
            readiness += 5
        
        final_score = min(readiness, 100)
        
        return {
            "score": round(final_score, 1),
            "overall": overall,
            "interview": interview_score,
            "learning": learning_score,
            "reason": f"Overall AI profile: {overall}%"
        }
    
    @classmethod
    def calculate_job_score(
        cls,
        student: Dict,
        job: Dict
    ) -> Dict[str, Any]:
        """
        Calculate total job recommendation score.
        Returns score breakdown with explanations.
        """
        # Extract student data
        student_skills = student.get("skills", [])
        student_location = student.get("location", student.get("college_location", ""))
        student_interests = student.get("interests", [])
        ai_profile = student.get("ai_profile", {})
        
        # Get learning gaps
        learning_gaps = []
        learning_paths = student.get("learning_paths", [])
        for path in learning_paths:
            if path.get("gap_priority") in ["HIGH", "MEDIUM"]:
                learning_gaps.append(path.get("skill", ""))
        
        # Calculate each component
        skill_match = cls.calculate_skill_match(
            student_skills,
            job.get("skills_required", [])
        )
        
        proficiency_fit = cls.calculate_proficiency_fit(
            student_skills,
            job.get("experience_required", "0-1 years")
        )
        
        freshness = cls.calculate_freshness(job.get("posted_at"))
        
        location_match = cls.calculate_location_match(
            student_location,
            job.get("location", ""),
            job.get("work_mode", "")
        )
        
        career_alignment = cls.calculate_career_alignment(
            student_interests,
            learning_gaps,
            job.get("title", ""),
            job.get("skills_required", [])
        )
        
        ai_readiness = cls.calculate_ai_readiness(ai_profile)
        
        # Calculate weighted total
        total_score = (
            skill_match["score"] * cls.WEIGHTS["skill_match"] +
            proficiency_fit["score"] * cls.WEIGHTS["proficiency_fit"] +
            freshness["score"] * cls.WEIGHTS["freshness"] +
            location_match["score"] * cls.WEIGHTS["location_match"] +
            career_alignment["score"] * cls.WEIGHTS["career_alignment"] +
            ai_readiness["score"] * cls.WEIGHTS["ai_readiness"]
        )
        
        return {
            "total_score": round(total_score, 1),
            "breakdown": {
                "skill_match": {
                    "weight": "40%",
                    **skill_match
                },
                "proficiency_fit": {
                    "weight": "20%",
                    **proficiency_fit
                },
                "freshness": {
                    "weight": "15%",
                    **freshness
                },
                "location_match": {
                    "weight": "10%",
                    **location_match
                },
                "career_alignment": {
                    "weight": "10%",
                    **career_alignment
                },
                "ai_readiness": {
                    "weight": "5%",
                    **ai_readiness
                }
            },
            "recommendation": cls._generate_recommendation(
                total_score,
                skill_match["missing"],
                career_alignment.get("gaps_covered", [])
            )
        }
    
    @staticmethod
    def _generate_recommendation(
        total_score: float,
        missing_skills: List[str],
        gaps_covered: List[str]
    ) -> str:
        """Generate actionable recommendation based on score."""
        if total_score >= 85:
            rec = "Excellent match! Apply soon."
        elif total_score >= 70:
            rec = "Good match. Worth applying."
        elif total_score >= 55:
            rec = "Moderate match. Consider carefully."
        else:
            rec = "Low match. Keep improving your profile."
        
        if missing_skills:
            rec += f" Consider learning: {', '.join(missing_skills[:3])}."
        
        if gaps_covered:
            rec += f" This job helps build: {', '.join(gaps_covered[:2])}."
        
        return rec
    
    @classmethod
    def calculate_hackathon_score(
        cls,
        student: Dict,
        hackathon: Dict
    ) -> Dict[str, Any]:
        """Calculate hackathon recommendation score."""
        student_skills = student.get("skills", [])
        student_interests = student.get("interests", [])
        ai_profile = student.get("ai_profile", {})
        
        # Theme match
        student_skill_names = normalize_skills([
            s.get("name", s) if isinstance(s, dict) else s 
            for s in student_skills
        ])
        theme_tags = normalize_skills(hackathon.get("theme_tags", []))
        tech_tags = normalize_skills(hackathon.get("tech_stack_tags", []))
        
        theme_matches = sum(1 for t in theme_tags if t in student_skill_names or t in student_interests)
        tech_matches = sum(1 for t in tech_tags if t in student_skill_names)
        
        theme_score = min((theme_matches + tech_matches) * 20, 100)
        
        # Freshness (time to deadline)
        reg_deadline = hackathon.get("registration_deadline") or hackathon.get("start_date")
        if reg_deadline:
            days_until = (reg_deadline - datetime.utcnow()).days
            if days_until <= 3:
                freshness_score = 100  # Urgent
            elif days_until <= 7:
                freshness_score = 85
            elif days_until <= 14:
                freshness_score = 70
            elif days_until <= 30:
                freshness_score = 55
            else:
                freshness_score = 40
        else:
            freshness_score = 50
        
        # Difficulty match
        difficulty = hackathon.get("difficulty_level", "intermediate").lower()
        overall = ai_profile.get("overall_score", 50)
        
        if difficulty == "beginner" and overall < 50:
            difficulty_score = 100
        elif difficulty == "intermediate" and 40 <= overall <= 75:
            difficulty_score = 100
        elif difficulty == "advanced" and overall >= 65:
            difficulty_score = 100
        else:
            difficulty_score = 60
        
        total_score = (
            theme_score * 0.50 +
            freshness_score * 0.25 +
            difficulty_score * 0.25
        )
        
        return {
            "total_score": round(total_score, 1),
            "breakdown": {
                "theme_match": {"score": theme_score, "weight": "50%"},
                "urgency": {"score": freshness_score, "weight": "25%"},
                "difficulty_fit": {"score": difficulty_score, "weight": "25%"}
            }
        }
    
    @classmethod
    def calculate_content_score(
        cls,
        student: Dict,
        content: Dict
    ) -> Dict[str, Any]:
        """Calculate content recommendation score."""
        student_skills = student.get("skills", [])
        student_interests = student.get("interests", [])
        learning_gaps = []
        
        for path in student.get("learning_paths", []):
            learning_gaps.append(path.get("skill", ""))
        
        # Topic relevance
        topic = (content.get("topic") or "").lower()
        all_interests = normalize_skills(student_interests + [
            s.get("name", s) if isinstance(s, dict) else s 
            for s in student_skills
        ] + learning_gaps)
        
        if topic in all_interests:
            relevance_score = 100
        elif any(topic in i or i in topic for i in all_interests):
            relevance_score = 80
        else:
            relevance_score = 40
        
        # Recency
        published_at = content.get("published_at")
        if published_at:
            hours_old = (datetime.utcnow() - published_at).total_seconds() / 3600
            if hours_old <= 6:
                recency_score = 100
            elif hours_old <= 24:
                recency_score = 85
            elif hours_old <= 72:
                recency_score = 65
            else:
                recency_score = 40
        else:
            recency_score = 50
        
        total_score = (
            relevance_score * 0.60 +
            recency_score * 0.40
        )
        
        return {
            "total_score": round(total_score, 1),
            "breakdown": {
                "relevance": {"score": relevance_score, "weight": "60%"},
                "recency": {"score": recency_score, "weight": "40%"}
            }
        }


# ============ Recommendation Engine ============

def recommendations_offline_collection():
    """Get the recommendations_offline collection."""
    return get_database()["recommendations_offline"]


class RecommendationEngine:
    """
    Main recommendation engine that orchestrates scoring,
    filtering, and ranking of opportunities.
    """
    
    def __init__(self):
        self.scoring = ScoringEngine()
    
    async def get_student_profile(self, student_id: str) -> Optional[Dict]:
        """Fetch student profile with all relevant data."""
        from bson import ObjectId
        
        user = await users_collection().find_one({"_id": ObjectId(student_id)})
        if not user:
            return None
        
        # Get learning paths for gaps
        learning_paths = await learning_paths_collection().find(
            {"student_id": ObjectId(student_id)}
        ).to_list(length=20)
        
        user["learning_paths"] = learning_paths
        user["_id"] = str(user["_id"])
        
        return user
    
    async def compute_and_store_recommendations(self, student_id: str) -> bool:
        """
        Compute recommendations offline (batch mode) and store them.
        """
        try:
            # Re-use existing logic
            result = await self.recommend_jobs(student_id, limit=50, use_offline=False)
            if "recommendations" in result:
                doc = {
                    "student_id": student_id,
                    "type": "jobs",
                    "recommendations": result["recommendations"],
                    "updated_at": datetime.utcnow()
                }
                await recommendations_offline_collection().replace_one(
                    {"student_id": student_id, "type": "jobs"},
                    doc,
                    upsert=True
                )
                return True
            return False
        except Exception as e:
            logger.error(f"Offline computation failed: {e}")
            return False

    async def recommend_jobs(
        self,
        student_id: str,
        limit: int = 20,
        filters: Dict = None,
        use_offline: bool = True
    ) -> Dict[str, Any]:
        """
        Get personalized job recommendations for a student.
        Tries offline store first for speed, falls back to live compute.
        """
        # 1. Try Offline Store
        if use_offline and not filters: # Filters require live re-ranking mostly
            cached = await recommendations_offline_collection().find_one(
                {"student_id": student_id, "type": "jobs"}
            )
            if cached:
                # Check freshness (e.g., 24 hours)
                if (datetime.utcnow() - cached["updated_at"]).total_seconds() < 86400:
                    return {
                        "status": "success",
                        "source": "offline",
                        "student_id": student_id,
                        "recommendations": cached["recommendations"][:limit],
                        "total_available": len(cached["recommendations"]),
                        "filters_applied": {}
                    }

        # 2. Live Compute (Online)
        student = await self.get_student_profile(student_id)
        if not student:
            return {"error": "Student not found", "recommendations": []}
        
        # Build query
        query = {"is_active": True}
        
        if filters:
            if filters.get("location"):
                query["location"] = {"$regex": filters["location"], "$options": "i"}
            if filters.get("work_mode"):
                query["work_mode"] = filters["work_mode"]
            if filters.get("min_stipend"):
                # This needs stipend parsing logic
                pass
        
        # Fetch active jobs
        jobs = await opportunities_jobs_collection().find(query).to_list(length=200)
        
        # Score each job
        scored_jobs = []
        for job in jobs:
            score_result = self.scoring.calculate_job_score(student, job)
            job["_id"] = str(job["_id"])
            
            scored_jobs.append({
                "job": job,
                "score": score_result["total_score"],
                "match_details": score_result["breakdown"],
                "recommendation": score_result["recommendation"]
            })
        
        # Sort by score descending
        scored_jobs.sort(key=lambda x: x["score"], reverse=True)
        
        # Apply feedback adjustments
        scored_jobs = await self._apply_feedback_adjustments(
            student_id, scored_jobs, "job"
        )
        
        return {
            "status": "success",
            "source": "live",
            "student_id": student_id,
            "recommendations": scored_jobs[:limit],
            "total_available": len(scored_jobs),
            "filters_applied": filters or {}
        }
    
    async def recommend_hackathons(
        self,
        student_id: str,
        limit: int = 10,
        filters: Dict = None
    ) -> Dict[str, Any]:
        """
        Get personalized hackathon recommendations for a student.
        """
        student = await self.get_student_profile(student_id)
        if not student:
            return {"error": "Student not found", "recommendations": []}
        
        # Build query
        query = {"status": {"$in": ["open", "upcoming"]}}
        
        if filters:
            if filters.get("theme"):
                query["theme_tags"] = {"$regex": filters["theme"], "$options": "i"}
            if filters.get("eligibility"):
                query["eligibility"] = filters["eligibility"]
        
        hackathons = await opportunities_hackathons_collection().find(query).to_list(length=100)
        
        scored_hackathons = []
        for hackathon in hackathons:
            score_result = self.scoring.calculate_hackathon_score(student, hackathon)
            hackathon["_id"] = str(hackathon["_id"])
            
            scored_hackathons.append({
                "hackathon": hackathon,
                "score": score_result["total_score"],
                "match_details": score_result["breakdown"]
            })
        
        scored_hackathons.sort(key=lambda x: x["score"], reverse=True)
        
        return {
            "status": "success",
            "student_id": student_id,
            "recommendations": scored_hackathons[:limit],
            "total_available": len(scored_hackathons)
        }
    
    async def recommend_content(
        self,
        student_id: str,
        limit: int = 15,
        filters: Dict = None
    ) -> Dict[str, Any]:
        """
        Get personalized content recommendations for a student.
        """
        student = await self.get_student_profile(student_id)
        if not student:
            return {"error": "Student not found", "recommendations": []}
        
        # Build query
        query = {}
        if filters:
            if filters.get("topic"):
                query["topic"] = filters["topic"]
        
        content = await opportunities_content_collection().find(query).sort(
            "published_at", -1
        ).to_list(length=100)
        
        scored_content = []
        for article in content:
            score_result = self.scoring.calculate_content_score(student, article)
            article["_id"] = str(article["_id"])
            
            scored_content.append({
                "article": article,
                "score": score_result["total_score"],
                "match_details": score_result["breakdown"]
            })
        
        scored_content.sort(key=lambda x: x["score"], reverse=True)
        
        return {
            "status": "success",
            "student_id": student_id,
            "recommendations": scored_content[:limit],
            "total_available": len(scored_content)
        }
    
    async def _apply_feedback_adjustments(
        self,
        student_id: str,
        scored_items: List[Dict],
        opportunity_type: str
    ) -> List[Dict]:
        """
        Adjust scores based on past user feedback.
        Boost items similar to what user engaged with.
        Reduce items similar to what user ignored.
        """
        from bson import ObjectId
        
        # Get past feedback
        feedback = await recommendation_feedback_collection().find({
            "student_id": ObjectId(student_id),
            "opportunity_type": opportunity_type
        }).sort("timestamp", -1).to_list(length=50)
        
        if not feedback:
            return scored_items
        
        # Count positive/negative actions
        positive_actions = {"clicked", "saved", "applied"}
        negative_actions = {"ignored", "dismissed"}
        
        positive_skills = []
        negative_skills = []
        
        for fb in feedback:
            skills = fb.get("opportunity_skills", [])
            if fb.get("action") in positive_actions:
                positive_skills.extend(skills)
            elif fb.get("action") in negative_actions:
                negative_skills.extend(skills)
        
        # Adjust scores
        for item in scored_items:
            opp = item.get("job") or item.get("hackathon") or item.get("article")
            opp_skills = opp.get("skills_required", []) or opp.get("theme_tags", [])
            
            boost = 0
            for skill in opp_skills:
                if skill.lower() in [s.lower() for s in positive_skills]:
                    boost += 2
                if skill.lower() in [s.lower() for s in negative_skills]:
                    boost -= 3
            
            item["score"] = max(0, min(100, item["score"] + boost))
        
        # Re-sort after adjustments
        scored_items.sort(key=lambda x: x["score"], reverse=True)
        
        return scored_items
    
    async def record_feedback(
        self,
        student_id: str,
        opportunity_id: str,
        opportunity_type: str,
        action: str,
        recommendation_score: float = None,
        recommendation_rank: int = None
    ) -> Dict[str, Any]:
        """
        Record user interaction with a recommendation.
        Used to improve future recommendations.
        """
        from bson import ObjectId
        
        # Get opportunity details for context
        if opportunity_type == "job":
            opp = await opportunities_jobs_collection().find_one(
                {"_id": ObjectId(opportunity_id)}
            )
            skills = opp.get("skills_required", []) if opp else []
        elif opportunity_type == "hackathon":
            opp = await opportunities_hackathons_collection().find_one(
                {"_id": ObjectId(opportunity_id)}
            )
            skills = opp.get("theme_tags", []) if opp else []
        else:
            opp = await opportunities_content_collection().find_one(
                {"_id": ObjectId(opportunity_id)}
            )
            skills = [opp.get("topic")] if opp else []
        
        feedback = {
            "student_id": ObjectId(student_id),
            "opportunity_id": ObjectId(opportunity_id),
            "opportunity_type": opportunity_type,
            "opportunity_skills": skills,
            "action": action,
            "recommendation_score": recommendation_score,
            "recommendation_rank": recommendation_rank,
            "timestamp": datetime.utcnow()
        }
        
        await recommendation_feedback_collection().insert_one(feedback)
        
        return {
            "status": "recorded",
            "action": action,
            "opportunity_id": opportunity_id
        }
    
    async def get_recommendation_stats(self, student_id: str) -> Dict[str, Any]:
        """Get statistics about recommendations for a student."""
        from bson import ObjectId
        
        feedback = await recommendation_feedback_collection().find({
            "student_id": ObjectId(student_id)
        }).to_list(length=200)
        
        stats = {
            "total_interactions": len(feedback),
            "by_action": {},
            "by_type": {},
            "engagement_rate": 0
        }
        
        for fb in feedback:
            action = fb.get("action", "unknown")
            opp_type = fb.get("opportunity_type", "unknown")
            
            stats["by_action"][action] = stats["by_action"].get(action, 0) + 1
            stats["by_type"][opp_type] = stats["by_type"].get(opp_type, 0) + 1
        
        # Calculate engagement rate
        positive = stats["by_action"].get("clicked", 0) + stats["by_action"].get("applied", 0)
        if stats["total_interactions"] > 0:
            stats["engagement_rate"] = round(positive / stats["total_interactions"] * 100, 1)
        
        return stats


# Singleton instance
recommendation_engine = RecommendationEngine()
