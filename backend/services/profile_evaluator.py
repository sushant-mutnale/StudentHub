"""
Profile Evaluator Service
When a student completes a full learning path (100%), this service:
1. Re-evaluates their competency in the skill via LLM
2. Updates user.skills with new proficiency level
3. Recalculates ai_profile scores
"""

import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from bson import ObjectId


class ProfileEvaluatorService:

    def __init__(self):
        self._llm_service = None

    def _get_llm(self):
        if self._llm_service is None:
            try:
                from .llm_service import llm_service
                self._llm_service = llm_service
            except Exception:
                self._llm_service = None
        return self._llm_service

    async def evaluate_on_completion(
        self,
        student_id: str,
        skill: str,
        stages: List[Dict[str, Any]],
        mcq_scores: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Called when a learning path reaches 100% completion.
        Updates user profile with new skill level.

        Args:
            student_id: MongoDB ObjectId string
            skill: Skill name
            stages: All completed stages with topics and resources
            mcq_scores: MCQ scores per stage (0-5 each) if available

        Returns:
            dict with new_skill_level, profile_updated, message
        """
        llm = self._get_llm()

        # Calculate estimated new level from MCQ performance
        avg_mcq = 0
        if mcq_scores:
            avg_mcq = sum(mcq_scores) / (len(mcq_scores) * 5) * 100  # % correct

        # Build stage summary for LLM
        stage_summary = "\n".join([
            f"- Stage {s.get('stage_number', i+1)}: {s.get('stage_name', '')} | Topics: {', '.join(s.get('topics', [])[:3])}"
            for i, s in enumerate(stages)
        ])

        if llm:
            system_instruction = """You are an Elite Skills Auditor and Certification Specialist. 
Your goal is to rigorously evaluate if a student has truly moved from one proficiency level to another. Reward high MCQ scores but look for consistency in the curriculum covered. 
Provide a summary that reads like a professional credential certification.
Output ONLY strict JSON."""

            prompt = f"""A student just completed a comprehensive '{skill}' learning path. 
            
=== CURRICULUM COVERED ===
{stage_summary}

=== QUANTITATIVE PERFORMANCE ===
MCQ Avg Score: {round(avg_mcq)}%

Task:
Perform a final competency audit.
1. Assign a new proficiency level (beginner, intermediate, advanced, expert).
2. Assign a numerical competency score (0-100).
3. Provide a professional 'Achievement Summary' (max 20 words).

Return ONLY JSON:
{{{{
  "proficiency": "...",
  "score": ...,
  "summary": "..."
}}}}"""
            try:
                resp = await llm.generate(prompt, system_instruction)
                clean = resp.strip().replace("```json", "").replace("```", "").strip()
                result = json.loads(clean)
                new_proficiency = result.get("proficiency", new_proficiency)
                proficiency_score = result.get("score", proficiency_score)
                ai_summary = result.get("summary", ai_summary)
            except Exception as e:
                print(f"Profile eval LLM error: {e}")

        # Update user skills in MongoDB
        from ..database import get_database
        db = get_database()

        user = await db.users.find_one({"_id": ObjectId(student_id)})
        if not user:
            return {"profile_updated": False, "message": "User not found"}

        skills = user.get("skills", [])
        skill_lower = skill.lower()

        # Find existing skill or create new entry
        updated = False
        for s in skills:
            s_name = s.get("name", "").lower() if isinstance(s, dict) else str(s).lower()
            if s_name == skill_lower:
                s["proficiency"] = new_proficiency
                s["level"] = proficiency_score
                s["last_updated"] = datetime.utcnow().isoformat()
                updated = True
                break

        if not updated:
            skills.append({
                "name": skill,
                "proficiency": new_proficiency,
                "level": proficiency_score,
                "last_updated": datetime.utcnow().isoformat()
            })

        # Update AI profile learning score estimate
        current_ai_profile = user.get("ai_profile", {})
        current_learning_score = current_ai_profile.get("learning_score", 50)
        new_learning_score = min(100, round(current_learning_score * 0.8 + proficiency_score * 0.2))

        await db.users.update_one(
            {"_id": ObjectId(student_id)},
            {
                "$set": {
                    "skills": skills,
                    "ai_profile.learning_score": new_learning_score,
                    "updated_at": datetime.utcnow()
                }
            }
        )

        return {
            "profile_updated": True,
            "skill": skill,
            "new_proficiency": new_proficiency,
            "new_score": proficiency_score,
            "new_learning_score": new_learning_score,
            "summary": ai_summary,
            "message": f"🎉 {skill} skill updated to {new_proficiency} ({proficiency_score}/100)!"
        }


# Singleton
profile_evaluator = ProfileEvaluatorService()
