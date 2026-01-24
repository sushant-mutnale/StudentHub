"""
Learning Path Builder Service
Generates personalized learning roadmaps based on skill gaps.
Now with AI-powered personalization via LangChain.
"""

import json
import os
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional


class LearningPathBuilder:
    """
    Builds personalized learning paths from skill gaps.
    Uses AI for personalized coaching when available.
    """
    
    def __init__(self, use_ai: bool = True):
        self.resources_path = os.path.join(
            os.path.dirname(__file__), 
            "..", 
            "data", 
            "learning_resources.json"
        )
        self._resources_cache = None
        self.use_ai = use_ai
        self._llm_service = None
    
    def _get_llm_service(self):
        """Lazy load LLM service."""
        if self._llm_service is None:
            try:
                from .llm_service import llm_service
                self._llm_service = llm_service
            except Exception:
                self._llm_service = None
        return self._llm_service
    
    def _load_resources(self) -> Dict[str, Any]:
        """Load learning resources from JSON file."""
        if self._resources_cache is not None:
            return self._resources_cache
        
        try:
            with open(self.resources_path, "r", encoding="utf-8") as f:
                self._resources_cache = json.load(f)
        except FileNotFoundError:
            self._resources_cache = {}
        
        return self._resources_cache
    
    def fetch_resources(
        self, 
        skill: str, 
        level: str = "beginner"
    ) -> List[Dict[str, Any]]:
        """
        Fetch resources for a skill at a given level.
        """
        resources_db = self._load_resources()
        skill_lower = skill.lower().replace("-", "_").replace(" ", "_")
        
        if skill_lower not in resources_db:
            return [{
                "resource_id": str(uuid.uuid4()),
                "type": "article",
                "title": f"Learn {skill.title()} - Getting Started",
                "url": f"https://www.google.com/search?q=learn+{skill}+tutorial",
                "duration_minutes": 30,
                "source": "Google Search",
                "level": level,
                "completed": False,
                "completed_at": None
            }]
        
        skill_data = resources_db[skill_lower]
        level_resources = skill_data.get(level, [])
        
        enriched = []
        for res in level_resources:
            enriched.append({
                "resource_id": str(uuid.uuid4()),
                "type": res.get("type", "article"),
                "title": res.get("title", "Learning Resource"),
                "url": res.get("url", ""),
                "duration_minutes": res.get("duration_minutes", 30),
                "source": res.get("source", "Unknown"),
                "level": level,
                "completed": False,
                "completed_at": None
            })
        
        return enriched if enriched else [{
            "resource_id": str(uuid.uuid4()),
            "type": "article",
            "title": f"Learn {skill.title()} - {level.title()}",
            "url": f"https://www.google.com/search?q={skill}+{level}+tutorial",
            "duration_minutes": 30,
            "source": "Google Search",
            "level": level,
            "completed": False,
            "completed_at": None
        }]
    
    def fetch_topics(self, skill: str, level: str = "beginner") -> List[str]:
        """Fetch topics for a skill at a given level."""
        resources_db = self._load_resources()
        skill_lower = skill.lower().replace("-", "_").replace(" ", "_")
        
        if skill_lower not in resources_db:
            return [f"Introduction to {skill.title()}", f"{skill.title()} Basics"]
        
        skill_data = resources_db[skill_lower]
        topics = skill_data.get("topics", {})
        
        return topics.get(level, [f"Learn {skill.title()} - {level.title()}"])
    
    def estimate_duration(self, current_level: int, target_level: int) -> int:
        """Estimate total weeks needed to close the gap."""
        gap = target_level - current_level
        
        if gap <= 0:
            return 0
        elif gap < 30:
            return 2
        elif gap < 50:
            return 4
        elif gap < 70:
            return 6
        else:
            return 8
    
    def determine_stages(self, current_level: int, target_level: int) -> List[str]:
        """Determine which stages are needed based on gap."""
        gap = target_level - current_level
        
        if gap <= 0:
            return []
        elif gap < 30:
            if current_level < 30:
                return ["beginner"]
            elif current_level < 60:
                return ["intermediate"]
            else:
                return ["advanced"]
        elif gap < 60:
            if current_level < 30:
                return ["beginner", "intermediate"]
            else:
                return ["intermediate", "advanced"]
        else:
            return ["beginner", "intermediate", "advanced"]
    
    async def _generate_ai_personalization(
        self,
        skill: str,
        current_skills: List[str],
        current_level: int,
        target_level: int,
        priority: str
    ) -> Dict[str, Any]:
        """Generate AI-powered personalization for a learning path."""
        llm = self._get_llm_service()
        
        if llm is None:
            return self._generate_rule_personalization(skill, priority)
        
        try:
            from .ai_prompts import PERSONALIZED_PATH_PROMPT, LEARNING_COACH_SYSTEM
            
            prompt = PERSONALIZED_PATH_PROMPT.format(
                skill=skill,
                current_skills=", ".join(current_skills) if current_skills else "Not specified",
                experience_level="Beginner" if current_level < 30 else "Intermediate" if current_level < 60 else "Advanced",
                hours_per_week=10,  # Default assumption
                priority=priority,
                current_level=current_level,
                target_level=target_level
            )
            
            response = await llm.generate(prompt, LEARNING_COACH_SYSTEM)
            
            if response and not response.startswith("Error"):
                return {
                    "ai_advice": response.strip(),
                    "ai_powered": True
                }
            else:
                return self._generate_rule_personalization(skill, priority)
                
        except Exception:
            return self._generate_rule_personalization(skill, priority)
    
    def _generate_rule_personalization(self, skill: str, priority: str) -> Dict[str, Any]:
        """Generate rule-based personalization (fallback)."""
        advice = f"Learning {skill.title()} will significantly boost your career prospects. "
        
        if priority == "HIGH":
            advice += "This is a high-priority skill for your target role. Dedicate focused time daily."
        elif priority == "MEDIUM":
            advice += "This skill will complement your existing expertise nicely."
        else:
            advice += "This is a nice-to-have skill that can set you apart from other candidates."
        
        return {
            "ai_advice": advice,
            "ai_powered": False
        }
    
    async def build_path(
        self,
        skill: str,
        current_level: int = 0,
        target_level: int = 80,
        priority: str = "HIGH",
        student_id: Optional[str] = None,
        current_skills: Optional[List[str]] = None,
        use_ai: bool = True
    ) -> Dict[str, Any]:
        """
        Build a complete learning path for a skill.
        
        Args:
            skill: Skill name (normalized)
            current_level: Current proficiency (0-100)
            target_level: Target proficiency (0-100)
            priority: Gap priority
            student_id: Optional student ID
            current_skills: Student's existing skills for context
            use_ai: Whether to use AI personalization
        """
        stage_levels = self.determine_stages(current_level, target_level)
        total_weeks = self.estimate_duration(current_level, target_level)
        
        if not stage_levels:
            return {
                "student_id": student_id,
                "skill": skill,
                "current_level": current_level,
                "target_level": target_level,
                "gap_priority": priority,
                "stages": [],
                "progress": {
                    "current_stage": 0,
                    "completion_percentage": 100.0,
                    "time_spent_minutes": 0,
                    "estimated_completion_date": None
                },
                "estimated_completion_weeks": 0,
                "ai_advice": "You already have this skill covered!",
                "ai_powered": False,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        
        # Generate AI personalization
        if use_ai and self.use_ai:
            personalization = await self._generate_ai_personalization(
                skill=skill,
                current_skills=current_skills or [],
                current_level=current_level,
                target_level=target_level,
                priority=priority
            )
        else:
            personalization = self._generate_rule_personalization(skill, priority)
        
        weeks_per_stage = max(1, total_weeks // len(stage_levels))
        
        stages = []
        stage_names = {
            "beginner": "Foundation",
            "intermediate": "Core Concepts",
            "advanced": "Advanced Skills"
        }
        
        for i, level in enumerate(stage_levels, start=1):
            resources = self.fetch_resources(skill, level)
            topics = self.fetch_topics(skill, level)
            
            stage = {
                "stage_number": i,
                "stage_name": stage_names.get(level, level.title()),
                "level": level,
                "duration_weeks": weeks_per_stage,
                "topics": topics,
                "resources": resources,
                "assessment": {
                    "type": "quiz",
                    "questions_count": 10,
                    "passing_score": 70
                },
                "status": "not_started",
                "completed_at": None
            }
            stages.append(stage)
        
        completion_date = datetime.utcnow() + timedelta(weeks=total_weeks)
        
        return {
            "student_id": student_id,
            "skill": skill,
            "current_level": current_level,
            "target_level": target_level,
            "gap_priority": priority,
            "stages": stages,
            "progress": {
                "current_stage": 0,
                "completion_percentage": 0.0,
                "time_spent_minutes": 0,
                "estimated_completion_date": completion_date.isoformat()
            },
            "estimated_completion_weeks": total_weeks,
            "ai_advice": personalization.get("ai_advice", ""),
            "ai_powered": personalization.get("ai_powered", False),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    
    async def build_paths_from_gaps(
        self,
        gaps: List[Dict[str, Any]],
        student_id: str,
        current_skills: Optional[List[str]] = None,
        use_ai: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Build learning paths for multiple skill gaps.
        """
        paths = []
        
        for gap in gaps:
            path = await self.build_path(
                skill=gap.get("skill", "unknown"),
                current_level=gap.get("current_level", 0),
                target_level=gap.get("target_level", 80),
                priority=gap.get("priority", "MEDIUM"),
                student_id=student_id,
                current_skills=current_skills,
                use_ai=use_ai
            )
            paths.append(path)
        
        # Sort by priority (HIGH first)
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        paths.sort(key=lambda x: priority_order.get(x["gap_priority"], 2))
        
        return paths


# Singleton instance
learning_path_builder = LearningPathBuilder()
