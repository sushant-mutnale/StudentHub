"""
Learning Path Builder Service
Generates personalized learning roadmaps based on skill gaps.
Now with AI-powered personalization via LangChain.
"""

import json
import os
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional


class ResourceCuratorAgent:
    """
    Agent 2: Searches Tavily for real, free, high-quality resources
    for each week topic in a learning path.
    """

    def __init__(self):
        self._tavily_client = None
        self._llm = None

    def _get_tavily(self):
        if self._tavily_client is None:
            try:
                from tavily import TavilyClient
                api_key = os.getenv("TAVILY_API_KEY", "")
                if api_key:
                    self._tavily_client = TavilyClient(api_key=api_key)
            except Exception:
                self._tavily_client = None
        return self._tavily_client

    def _get_llm(self):
        if self._llm is None:
            try:
                from .llm_service import llm_service
                self._llm = llm_service
            except Exception:
                self._llm = None
        return self._llm

    async def curate_resources_for_subtopic(self, skill: str, topic: str, subtopic: str) -> List[Dict[str, Any]]:
        """
        Search Tavily for 3 distinct resources: video, documentation, and exercise/repository.
        """
        tavily = self._get_tavily()
        if not tavily:
            return self._default_subtopic_resources(skill, subtopic)

        resources = []
        try:
            # 1. Video
            res_video = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: tavily.search(query=f"{skill} {subtopic} tutorial video site:youtube.com", max_results=1, search_depth="basic")
            )
            for r in res_video.get("results", []):
                resources.append({
                    "resource_id": str(uuid.uuid4()),
                    "type": "video",
                    "title": r.get("title", f"{skill} - {subtopic} Video")[:100],
                    "url": r.get("url", ""),
                    "duration_minutes": 30,
                    "source": "YouTube",
                    "completed": False,
                    "completed_at": None
                })
        except Exception:
            resources.append({
                "resource_id": str(uuid.uuid4()),
                "type": "video",
                "title": f"{skill} - {subtopic} Video Tutorial",
                "url": f"https://www.youtube.com/results?search_query={skill.replace(' ', '+')}+{subtopic.replace(' ', '+')}",
                "duration_minutes": 30,
                "source": "YouTube",
                "completed": False,
                "completed_at": None
            })

        try:
            # 2. Documentation
            res_docs = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: tavily.search(query=f"{skill} {subtopic} official documentation OR tutorial site:docs.python.org OR site:developer.mozilla.org OR site:freecodecamp.org OR site:react.dev OR site:geeksforgeeks.org", max_results=1, search_depth="basic")
            )
            for r in res_docs.get("results", []):
                resources.append({
                    "resource_id": str(uuid.uuid4()),
                    "type": "documentation",
                    "title": r.get("title", f"{skill} - {subtopic} Docs")[:100],
                    "url": r.get("url", ""),
                    "duration_minutes": 20,
                    "source": r.get("url", "").split("/")[2] if "/" in r.get("url", "") else "Web",
                    "completed": False,
                    "completed_at": None
                })
        except Exception:
            resources.append({
                "resource_id": str(uuid.uuid4()),
                "type": "documentation",
                "title": f"{skill} {subtopic} Official Documentation",
                "url": f"https://www.google.com/search?q={skill.replace(' ', '+')}+{subtopic.replace(' ', '+')}+documentation",
                "duration_minutes": 20,
                "source": "Google",
                "completed": False,
                "completed_at": None
            })

        try:
            # 3. Exercise/Repository
            res_repo = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: tavily.search(query=f"{skill} {subtopic} example project OR exercise site:github.com OR site:hackerrank.com OR site:leetcode.com", max_results=1, search_depth="basic")
            )
            for r in res_repo.get("results", []):
                resources.append({
                    "resource_id": str(uuid.uuid4()),
                    "type": "repository",
                    "title": r.get("title", f"{skill} - {subtopic} Exercise")[:100],
                    "url": r.get("url", ""),
                    "duration_minutes": 45,
                    "source": r.get("url", "").split("/")[2] if "/" in r.get("url", "") else "Web",
                    "completed": False,
                    "completed_at": None
                })
        except Exception:
            resources.append({
                "resource_id": str(uuid.uuid4()),
                "type": "repository",
                "title": f"{skill} - {subtopic} GitHub Repository",
                "url": f"https://github.com/search?q={skill.replace(' ', '+')}+{subtopic.replace(' ', '+')}&type=repositories",
                "duration_minutes": 45,
                "source": "GitHub",
                "completed": False,
                "completed_at": None
            })

        return resources

    def _default_subtopic_resources(self, skill: str, subtopic: str) -> List[Dict[str, Any]]:
        """Minimal fallback when Tavily unavailable."""
        return [
            {
                "resource_id": str(uuid.uuid4()),
                "type": "documentation",
                "title": f"{skill} {subtopic} Official Documentation",
                "url": f"https://roadmap.sh/search?q={skill.lower().replace(' ', '-')}",
                "duration_minutes": 30,
                "source": "roadmap.sh",
                "completed": False,
                "completed_at": None
            }
        ]


resource_curator = ResourceCuratorAgent()


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
    
    async def normalize_skill_input(self, raw_input: str) -> str:
        """
        Agent 0: Normalize and correct misspelled skill names via LLM.
        e.g. 'dokcer' → 'Docker', 'reactjs' → 'React'
        """
        llm = self._get_llm_service()
        if not llm:
            return raw_input.strip()

        prompt = f"""The user typed this skill name: "{raw_input}"

If it has a typo or informal name, return the correct, standard skill name.
If it's already correct, return it as-is.
Return ONLY the corrected skill name — nothing else. No explanation.

Examples:
- 'dokcer' → 'Docker'
- 'reactjs' → 'React'
- 'machne lernin' → 'Machine Learning'
- 'Python' → 'Python'"""

        try:
            result = await llm.generate(prompt, "You are a skill name corrector. Return only the corrected name.")
            corrected = result.strip().strip('"').strip("'")
            return corrected if corrected else raw_input.strip()
        except Exception:
            return raw_input.strip()

    async def generate_curriculum(
        self,
        skill: str,
        current_level: int,
        target_level: int,
        current_skills: List[str],
        available_time: str = "4 weeks",
        goal_level: str = "Job-ready"
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive Stage-by-Stage Learning Curriculum using LLM.
        Includes subtopics, daily tasks, acceptance criteria, and time estimates.
        """
        llm = self._get_llm_service()
        if not llm:
            return None

        prompt = f"""
        Act as a Senior Technical Mentor. Create a highly detailed, dependency-based Learning Roadmap for '{skill}'.
        
        User Context:
        - Current Level: {current_level}/100
        - Target Level: {target_level}/100
        - Available Time: {available_time}
        - Goal Level: {goal_level}
        - Existing Skills: {", ".join(current_skills)}
        
        Requirements:
        1. Break down the curriculum into logical, sequential Stages or Weeks.
        2. Ensure a strict dependency-based learning order (fundamentals first, advanced later).
        3. For each stage, provide:
           - 'week': The stage number
           - 'topic': Stage overarching theme
           - 'goal': A concrete milestone for this stage (e.g., "Build a responsive landing page", "Final project: Full dashboard UI")
        4. Inside each stage, provide 3-5 structured 'subtopics'.
        5. For each subtopic, provide:
           - 'title': Clearly defined concept (e.g., "Flexbox & Grid Layouts")
           - 'estimated_time_minutes': Integer duration (e.g., 60, 120, 150)
           - 'acceptance_criteria': Array of 3 explicit tasks representing the Definition of Done (e.g., "Build a responsive navbar", "Create a reusable card component", "Explain mobile-first design verbally")
        
        Ensure a mix of conceptual and practical learning. There should be no repetitive topics. Provide a logical progression.
        
        Output JSON Format ONLY:
        {{
            "weeks": [
                {{
                    "week": 1,
                    "topic": "Topic Name",
                    "goal": "Stage/Milestone Goal",
                    "subtopics": [
                        {{
                            "title": "Subtopic 1",
                            "estimated_time_minutes": 120,
                            "acceptance_criteria": ["Practical Task 1", "Verbal check 2", "Code task 3"]
                        }}
                    ]
                }}
            ]
        }}
        """
        
        try:
            response = await llm.generate(prompt, "You are an elite curriculum developer. Output strict JSON only.")
            clean_json = response.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_json)
        except Exception as e:
            # logger.error(f"Curriculum Generation Failed: {e}")
            return None

    async def _generate_ai_personalization(
        self,
        skill: str,
        current_skills: List[str],
        current_level: int,
        target_level: int,
        priority: str,
        available_time: str = "4 weeks",
        goal_level: str = "Job-ready"
    ) -> Dict[str, Any]:
        """
        Generate AI-powered personalization for a learning path.
        NOW ENHANCED to use generate_curriculum for structure.
        """
        # Try to generate full curriculum
        curriculum = await self.generate_curriculum(skill, current_level, target_level, current_skills, available_time, goal_level)
        
        if curriculum and "weeks" in curriculum:
            return {
                "ai_advice": f"I've created a custom {len(curriculum['weeks'])}-week plan for you to master {skill}.",
                "ai_powered": True,
                "curriculum": curriculum # Pass this through to the path builder
            }
            
        # Fallback to old simple advice if curriculum fails
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
        use_ai: bool = True,
        available_time: str = "4 weeks",
        goal_level: str = "Job-ready"
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
            available_time: User's available time to complete
            goal_level: Desired depth of knowledge
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
                "available_time": available_time,
                "goal_level": goal_level,
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
                priority=priority,
                available_time=available_time,
                goal_level=goal_level
            )
        else:
            personalization = self._generate_rule_personalization(skill, priority)
        
        stages = []
        
        # [NEW] specific logic for AI Curriculum
        if personalization.get("curriculum"):
            curriculum = personalization["curriculum"]
            weeks = curriculum.get("weeks", [])
            total_weeks = len(weeks)

            for i, week in enumerate(weeks, start=1):
                # Use Tavily to get REAL resources for each subtopic
                topic = week.get("topic", skill)
                subtopics_data = week.get("subtopics", [])
                built_subtopics = []
                
                for sub in subtopics_data:
                    sub_title = sub.get("title", "Concept")
                    try:
                        resources = await resource_curator.curate_resources_for_subtopic(skill, topic, sub_title)
                    except Exception as e:
                        print(f"Error curating resources for subtopic: {e}")
                        resources = resource_curator._default_subtopic_resources(skill, sub_title)
                        
                    built_subtopics.append({
                        "title": sub_title,
                        "estimated_time_minutes": sub.get("estimated_time_minutes", 60),
                        "acceptance_criteria": sub.get("acceptance_criteria", []),
                        "resources": resources,
                        "completed": False,
                        "completed_at": None
                    })

                stages.append({
                    "stage_number": week.get("week", i),
                    "stage_name": f"Stage {week.get('week', i)}: {week.get('topic', 'Topic')}",
                    "level": "intermediate",
                    "duration_weeks": 1,
                    "topics": [],
                    "subtopics": built_subtopics,
                    "resources": [],
                    "goal": week.get("goal", ""),
                    "status": "not_started",
                    "completed_at": None
                })
        else:
            # Fallback to old logic
            current_stage_levels = self.determine_stages(current_level, target_level) # Renamed to avoid confusion
            weeks_per_stage = max(1, total_weeks // len(current_stage_levels)) if current_stage_levels else 1
            
            stage_names = {
                "beginner": "Foundation",
                "intermediate": "Core Concepts",
                "advanced": "Advanced Skills"
            }
            
            for i, level in enumerate(current_stage_levels, start=1):
                resources = self.fetch_resources(skill, level)
                topics = self.fetch_topics(skill, level)
                
                stages.append({
                    "stage_number": i,
                    "stage_name": stage_names.get(level, level.title()),
                    "level": level,
                    "duration_weeks": weeks_per_stage,
                    "topics": topics,
                    "resources": resources,
                    "status": "not_started",
                    "completed_at": None
                })

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
            "available_time": available_time,
            "goal_level": goal_level,
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
        use_ai: bool = True,
        available_time: str = "4 weeks",
        goal_level: str = "Job-ready"
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
                use_ai=use_ai,
                available_time=available_time,
                goal_level=goal_level
            )
            paths.append(path)
        
        # Sort by priority (HIGH first)
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        paths.sort(key=lambda x: priority_order.get(x["gap_priority"], 2))
        
        return paths


# Singleton instance
learning_path_builder = LearningPathBuilder()
