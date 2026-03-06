"""
Skill Gap Analyzer Service
Compares student skills vs job requirements, outputs gaps with priorities.
Now with AI-powered recommendations via LangChain.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
import re
import asyncio


# Skill synonym mapping for normalization
SKILL_SYNONYMS = {
    "reactjs": "react",
    "react.js": "react",
    "react native": "react-native",
    "nodejs": "node",
    "node.js": "node",
    "javascript": "javascript",
    "js": "javascript",
    "typescript": "typescript",
    "ts": "typescript",
    "python3": "python",
    "py": "python",
    "mongodb": "mongodb",
    "mongo": "mongodb",
    "postgresql": "postgres",
    "psql": "postgres",
    "mysql": "mysql",
    "sql": "sql",
    "amazon web services": "aws",
    "docker container": "docker",
    "kubernetes": "kubernetes",
    "k8s": "kubernetes",
    "machine learning": "ml",
    "artificial intelligence": "ai",
    "data structures": "dsa",
    "algorithms": "dsa",
    "data structures and algorithms": "dsa",
    "system design": "system-design",
    "git": "git",
    "github": "git",
    "c++": "cpp",
    "cplusplus": "cpp",
    "c#": "csharp",
    "golang": "go",
    "rest api": "rest",
    "restful": "rest",
    "graphql": "graphql",
    "ci/cd": "cicd",
    "continuous integration": "cicd",
    "html5": "html",
    "css3": "css",
    "tailwind": "tailwindcss",
    "tailwind css": "tailwindcss",
    "next.js": "nextjs",
    "next js": "nextjs",
    "vue.js": "vue",
    "vuejs": "vue",
    "angular.js": "angular",
    "angularjs": "angular",
    "express.js": "express",
    "expressjs": "express",
    "fastapi": "fastapi",
    "flask": "flask",
    "django": "django",
    "spring boot": "spring",
    "springboot": "spring",
}


class SkillGapAnalyzer:
    """
    Analyzes skill gaps between student profile and job requirements.
    Uses AI for smart recommendations when available.
    """
    
    def __init__(self, use_ai: bool = True):
        self.synonyms = SKILL_SYNONYMS
        self.use_ai = use_ai
        self._llm_service = None
    
    def _get_llm_service(self):
        """Lazy load LLM service to avoid import errors if not configured."""
        if self._llm_service is None:
            try:
                from .llm_service import llm_service
                self._llm_service = llm_service
            except Exception:
                self._llm_service = None
        return self._llm_service
    
    def normalize_skill(self, skill: str) -> str:
        """
        Normalize a single skill name.
        - Lowercase
        - Remove extra whitespace
        - Apply synonym mapping
        """
        if not skill:
            return ""
        
        # Lowercase and strip
        normalized = skill.lower().strip()
        
        # Remove extra spaces
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Check synonym mapping
        if normalized in self.synonyms:
            normalized = self.synonyms[normalized]
        
        return normalized
    
    def normalize_skills(self, skills: List) -> set:
        """
        Normalize a list of skills.
        Handles both string skills and structured skill objects.
        """
        normalized = set()
        
        for skill in skills:
            if isinstance(skill, dict):
                # Structured skill object from Module 2
                skill_name = skill.get("name", "")
            else:
                skill_name = str(skill)
            
            norm = self.normalize_skill(skill_name)
            if norm:
                normalized.add(norm)
        
        return normalized
    
    def calculate_priority(
        self, 
        skill: str, 
        is_required: bool, 
        student_has_similar: bool = False
    ) -> str:
        """
        Calculate priority level for a missing skill.
        
        Returns: "HIGH", "MEDIUM", or "LOW"
        """
        if is_required and not student_has_similar:
            return "HIGH"
        elif is_required and student_has_similar:
            return "MEDIUM"
        elif not is_required:  # Nice-to-have
            return "MEDIUM"
        else:
            return "LOW"
    
    def find_similar_skills(self, skill: str, student_skills: set) -> bool:
        """
        Check if student has a similar skill.
        Example: Student has "React Native" and job needs "React"
        """
        skill_root = skill.split("-")[0] if "-" in skill else skill
        
        for student_skill in student_skills:
            if skill_root in student_skill or student_skill in skill_root:
                return True
        
        return False
    
    async def analyze_gap(
        self,
        student_skills: List,
        job_required_skills: List[str],
        job_nice_to_have_skills: Optional[List[str]] = None,
        student_id: Optional[str] = None,
        job_id: Optional[str] = None,
        use_ai_recommendations: bool = True
    ) -> Dict[str, Any]:
        """
        Perform full gap analysis with optional AI-powered recommendations.
        
        Args:
            student_skills: List of student skills (strings or skill objects)
            job_required_skills: List of required skill names
            job_nice_to_have_skills: Optional list of nice-to-have skills
            student_id: Optional student ObjectId string
            job_id: Optional job ObjectId string
            use_ai_recommendations: Whether to use AI for recommendations
            
        Returns:
            Gap analysis dictionary with gaps, scores, and recommendations
        """
        if job_nice_to_have_skills is None:
            job_nice_to_have_skills = []
        
        # Normalize all skills
        student_normalized = self.normalize_skills(student_skills)
        required_normalized = self.normalize_skills(
            [{"name": s} for s in job_required_skills]
        )
        nice_normalized = self.normalize_skills(
            [{"name": s} for s in job_nice_to_have_skills]
        )
        
        # Find missing skills
        missing_required = required_normalized - student_normalized
        missing_nice = nice_normalized - student_normalized
        
        # Build gap list
        gaps = []
        
        for skill in missing_required:
            has_similar = self.find_similar_skills(skill, student_normalized)
            priority = self.calculate_priority(
                skill, 
                is_required=True, 
                student_has_similar=has_similar
            )
            gaps.append({
                "skill": skill,
                "priority": priority,
                "reason": "Required but missing" if not has_similar 
                          else "Required - has similar skill",
                "current_level": 0,
                "target_level": 80,
                "is_required": True
            })
        
        for skill in missing_nice:
            # Don't duplicate if already in required
            if skill not in missing_required:
                has_similar = self.find_similar_skills(skill, student_normalized)
                priority = self.calculate_priority(
                    skill, 
                    is_required=False, 
                    student_has_similar=has_similar
                )
                gaps.append({
                    "skill": skill,
                    "priority": priority,
                    "reason": "Nice-to-have but missing",
                    "current_level": 0,
                    "target_level": 60,
                    "is_required": False
                })
        
        # Sort gaps by priority (HIGH first, then MEDIUM)
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        gaps.sort(key=lambda x: priority_order.get(x["priority"], 2))
        
        # Calculate match percentage
        if len(required_normalized) > 0:
            matched_required = required_normalized.intersection(student_normalized)
            match_percentage = round(
                (len(matched_required) / len(required_normalized)) * 100, 1
            )
        else:
            match_percentage = 100.0
        
        gap_score = round(100 - match_percentage, 1)
        
        # Generate recommendations (AI or rule-based)
        if use_ai_recommendations and self.use_ai:
            recommendations = await self._generate_ai_recommendations(
                student_skills=list(student_normalized),
                required_skills=list(required_normalized),
                gaps=gaps,
                match_percentage=match_percentage
            )
        else:
            recommendations = self._generate_rule_recommendations(gaps, gap_score)
        
        return {
            "student_id": student_id,
            "job_id": job_id,
            "analyzed_at": datetime.utcnow().isoformat(),
            "student_skills": list(student_normalized),
            "job_required_skills": list(required_normalized),
            "job_nice_to_have": list(nice_normalized),
            "gaps": gaps,
            "match_percentage": match_percentage,
            "gap_score": gap_score,
            "recommendations": recommendations,
            "high_priority_count": len([g for g in gaps if g["priority"] == "HIGH"]),
            "total_gaps": len(gaps),
            "ai_powered": use_ai_recommendations and self.use_ai
        }
    
    async def _generate_ai_recommendations(
        self,
        student_skills: List[str],
        required_skills: List[str],
        gaps: List[Dict],
        match_percentage: float
    ) -> str:
        """Generate AI-powered personalized recommendations."""
        llm = self._get_llm_service()
        
        if llm is None:
            return self._generate_rule_recommendations(gaps, 100 - match_percentage)
        
        try:
            from .ai_prompts import GAP_RECOMMENDATION_PROMPT, SKILL_ADVISOR_SYSTEM
            
            high_priority = [g["skill"] for g in gaps if g["priority"] == "HIGH"]
            medium_priority = [g["skill"] for g in gaps if g["priority"] == "MEDIUM"]
            
            prompt = GAP_RECOMMENDATION_PROMPT.format(
                student_skills=", ".join(student_skills) or "None specified",
                required_skills=", ".join(required_skills),
                high_priority_gaps=", ".join(high_priority) or "None",
                medium_priority_gaps=", ".join(medium_priority) or "None",
                match_percentage=match_percentage
            )
            
            response = await llm.generate(prompt, SKILL_ADVISOR_SYSTEM)
            
            # Clean up response
            if response and not response.startswith("Error"):
                return response.strip()
            else:
                return self._generate_rule_recommendations(gaps, 100 - match_percentage)
                
        except Exception as e:
            # Fallback to rule-based on any error
            return self._generate_rule_recommendations(gaps, 100 - match_percentage)
    
    def _generate_rule_recommendations(
        self, 
        gaps: List[Dict], 
        gap_score: float
    ) -> str:
        """Generate rule-based recommendations (fallback)."""
        if not gaps:
            return "Great! You have all the required skills. Consider strengthening your expertise."
        
        high_priority = [g["skill"] for g in gaps if g["priority"] == "HIGH"]
        
        if gap_score >= 75:
            prefix = "Significant gap detected. "
        elif gap_score >= 50:
            prefix = "Moderate gap found. "
        else:
            prefix = "You're close! "
        
        if high_priority:
            skills_str = ", ".join(high_priority[:3])
            if len(high_priority) > 3:
                skills_str += f" (+{len(high_priority) - 3} more)"
            return f"{prefix}Focus on learning: {skills_str}"
        else:
            return f"{prefix}Consider brushing up on the nice-to-have skills."


# Singleton instance for easy import
skill_gap_analyzer = SkillGapAnalyzer()
