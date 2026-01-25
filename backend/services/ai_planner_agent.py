"""
AI Planner Agent
Creates personalized study plans based on gap analysis + target company.
Uses LLM with fallback chain: OpenRouter → Gemini → Groq → Ollama
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from bson import ObjectId
import json
import re

from ..database import get_database
from .llm_service import llm_service


class AIPlannerAgent:
    """
    AI-powered study planner that creates personalized preparation schedules.
    Builds on gap analysis output and company interview patterns.
    """
    
    def __init__(self):
        self.llm = llm_service
    
    def _plans_collection(self):
        return get_database()["study_plans"]
    
    def _tasks_collection(self):
        return get_database()["study_tasks"]
    
    async def create_study_plan(
        self,
        student_id: str,
        gaps: Dict[str, Any],
        target_company: str,
        target_role: str = "Software Engineer",
        prep_weeks: int = 8,
        hours_per_day: float = 2.0,
        preferred_days: List[str] = None
    ) -> Dict[str, Any]:
        """
        Create a personalized study plan.
        
        Args:
            student_id: Student's ID
            gaps: Output from gap_analysis_service (missing skills, proficiency)
            target_company: Company they're preparing for
            target_role: Role they want
            prep_weeks: Number of weeks to prepare
            hours_per_day: Available hours per day
            preferred_days: Which days can study (default: all)
        
        Returns:
            Complete study plan with weekly breakdown
        """
        if preferred_days is None:
            preferred_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        # Get company interview patterns
        from .company_research import company_researcher
        company_pattern = await company_researcher.get_company_interview_pattern(target_company, target_role)
        
        # Build context for AI
        system_prompt = """You are an expert interview preparation coach. 
Create detailed, actionable study plans based on the student's gaps and target company requirements.
Be specific with resources (LeetCode problems, video topics, reading materials).
Format response as valid JSON."""

        prompt = f"""Create a {prep_weeks}-week study plan for a student targeting {target_company} {target_role}.

STUDENT'S SKILL GAPS:
{json.dumps(gaps.get('missing_skills', [])[:10], indent=2)}

PROFICIENCY LEVELS (needs improvement):
{json.dumps({k: v for k, v in gaps.get('proficiency', {}).items() if v < 60}[:5] if isinstance(gaps.get('proficiency'), dict) else {}, indent=2)}

COMPANY INTERVIEW PATTERN:
- DSA Topics: {', '.join(company_pattern.get('dsa_topics', ['arrays', 'trees', 'graphs'])[:5])}
- Behavioral Themes: {', '.join(company_pattern.get('behavioral_themes', ['leadership', 'teamwork'])[:3])}
- Rounds: {len(company_pattern.get('rounds', []))} rounds

AVAILABLE TIME:
- {hours_per_day} hours per day
- Days available: {', '.join(preferred_days)}
- Total weeks: {prep_weeks}

Create a JSON response with this EXACT structure:
{{
    "plan_title": "8-Week Prep Plan for {target_company}",
    "total_weeks": {prep_weeks},
    "weekly_focus": [
        {{
            "week": 1,
            "focus_area": "Foundations & Arrays",
            "goals": ["Goal 1", "Goal 2"],
            "topics": ["arrays", "hashmaps"]
        }}
    ],
    "daily_schedule": {{
        "coding_minutes": 60,
        "behavioral_minutes": 20,
        "system_design_minutes": 30,
        "review_minutes": 10
    }},
    "key_resources": [
        {{"type": "course", "name": "Course Name", "url": "optional_url"}},
        {{"type": "practice", "name": "LeetCode Easy Problems", "count": 50}}
    ],
    "milestones": [
        {{"week": 2, "milestone": "Complete 30 easy problems"}},
        {{"week": 4, "milestone": "Start medium problems"}}
    ]
}}"""

        # Generate plan using LLM with fallback
        response = await self.llm.generate(prompt, system_prompt)
        
        # Parse JSON from response
        plan_data = self._parse_plan_response(response, target_company, prep_weeks)
        
        # Generate detailed daily tasks
        daily_tasks = await self._generate_daily_tasks(
            plan_data,
            prep_weeks,
            hours_per_day,
            preferred_days,
            gaps,
            company_pattern
        )
        
        # Save plan to database
        plan_doc = {
            "student_id": ObjectId(student_id),
            "target_company": target_company,
            "target_role": target_role,
            "prep_weeks": prep_weeks,
            "hours_per_day": hours_per_day,
            "preferred_days": preferred_days,
            "plan_data": plan_data,
            "daily_tasks": daily_tasks,
            "status": "active",
            "progress": {
                "tasks_completed": 0,
                "total_tasks": len(daily_tasks),
                "current_week": 1,
                "current_day": 1
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = await self._plans_collection().insert_one(plan_doc)
        plan_id = str(result.inserted_id)
        
        return {
            "success": True,
            "plan_id": plan_id,
            "plan_title": plan_data.get("plan_title", f"{prep_weeks}-Week Plan for {target_company}"),
            "total_weeks": prep_weeks,
            "weekly_focus": plan_data.get("weekly_focus", []),
            "first_week_tasks": daily_tasks[:7] if daily_tasks else [],
            "milestones": plan_data.get("milestones", []),
            "estimated_total_hours": prep_weeks * 7 * hours_per_day,
            "message": f"Study plan created! Start with Week 1 today."
        }
    
    def _parse_plan_response(self, response: str, company: str, weeks: int) -> Dict[str, Any]:
        """Parse LLM response to extract plan JSON."""
        # Try to extract JSON from response
        try:
            # Find JSON block in response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except (json.JSONDecodeError, AttributeError):
            pass
        
        # Fallback: create default structure
        return {
            "plan_title": f"{weeks}-Week Prep Plan for {company}",
            "total_weeks": weeks,
            "weekly_focus": [
                {"week": 1, "focus_area": "Foundations: Arrays & Strings", "goals": ["Complete 15 easy problems"], "topics": ["arrays", "strings"]},
                {"week": 2, "focus_area": "Hash Maps & Two Pointers", "goals": ["Complete 15 medium problems"], "topics": ["hashmaps", "two-pointers"]},
                {"week": 3, "focus_area": "Linked Lists & Stacks", "goals": ["Master pointer techniques"], "topics": ["linked-lists", "stacks"]},
                {"week": 4, "focus_area": "Trees & Binary Search", "goals": ["Tree traversals mastery"], "topics": ["trees", "binary-search"]},
                {"week": 5, "focus_area": "Graphs & BFS/DFS", "goals": ["Graph problems confidence"], "topics": ["graphs", "bfs", "dfs"]},
                {"week": 6, "focus_area": "Dynamic Programming", "goals": ["DP patterns recognition"], "topics": ["dp", "memoization"]},
                {"week": 7, "focus_area": "System Design Basics", "goals": ["Design 3 systems"], "topics": ["system-design"]},
                {"week": 8, "focus_area": "Behavioral + Mock Interviews", "goals": ["3 mock interviews"], "topics": ["behavioral", "mock"]}
            ][:weeks],
            "daily_schedule": {
                "coding_minutes": 60,
                "behavioral_minutes": 15,
                "system_design_minutes": 30,
                "review_minutes": 15
            },
            "key_resources": [
                {"type": "practice", "name": "LeetCode Problems", "count": 100},
                {"type": "course", "name": "System Design Primer", "url": "github.com/donnemartin/system-design-primer"}
            ],
            "milestones": [
                {"week": 2, "milestone": "30 problems completed"},
                {"week": 4, "milestone": "50 problems + medium difficulty"},
                {"week": 6, "milestone": "75 problems + DP basics"},
                {"week": weeks, "milestone": "Interview ready!"}
            ]
        }
    
    async def _generate_daily_tasks(
        self,
        plan_data: Dict[str, Any],
        prep_weeks: int,
        hours_per_day: float,
        preferred_days: List[str],
        gaps: Dict[str, Any],
        company_pattern: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate specific daily tasks based on the plan."""
        daily_tasks = []
        start_date = datetime.utcnow().date()
        
        # LeetCode problem suggestions by topic
        leetcode_by_topic = {
            "arrays": ["Two Sum", "Best Time to Buy and Sell Stock", "Contains Duplicate", "Product of Array Except Self"],
            "strings": ["Valid Anagram", "Valid Palindrome", "Longest Substring Without Repeating"],
            "hashmaps": ["Two Sum", "Group Anagrams", "Top K Frequent Elements"],
            "linked-lists": ["Reverse Linked List", "Merge Two Sorted Lists", "Linked List Cycle"],
            "trees": ["Maximum Depth of Binary Tree", "Invert Binary Tree", "Level Order Traversal"],
            "graphs": ["Number of Islands", "Clone Graph", "Course Schedule"],
            "dp": ["Climbing Stairs", "House Robber", "Coin Change"],
            "stacks": ["Valid Parentheses", "Min Stack", "Daily Temperatures"],
            "two-pointers": ["Container With Most Water", "3Sum", "Trapping Rain Water"],
            "binary-search": ["Binary Search", "Search in Rotated Array", "Find Minimum in Rotated Array"]
        }
        
        weekly_focus = plan_data.get("weekly_focus", [])
        schedule = plan_data.get("daily_schedule", {})
        
        day_number = 0
        for week_num in range(1, prep_weeks + 1):
            week_data = weekly_focus[week_num - 1] if week_num <= len(weekly_focus) else weekly_focus[-1]
            topics = week_data.get("topics", ["arrays"])
            
            for day_in_week in range(7):
                current_date = start_date + timedelta(days=day_number)
                day_name = current_date.strftime("%A")
                
                # Skip days not in preferred days
                if day_name not in preferred_days:
                    day_number += 1
                    continue
                
                # Get problems for this day's topics
                topic = topics[day_in_week % len(topics)] if topics else "arrays"
                problems = leetcode_by_topic.get(topic, ["Practice problem"])
                
                tasks_for_day = []
                
                # Coding task
                coding_mins = schedule.get("coding_minutes", 60)
                if coding_mins > 0:
                    problem = problems[day_in_week % len(problems)]
                    tasks_for_day.append({
                        "type": "leetcode",
                        "title": f"Solve: {problem}",
                        "topic": topic,
                        "difficulty": "easy" if week_num <= 2 else "medium" if week_num <= 5 else "hard",
                        "estimated_minutes": coding_mins,
                        "completed": False
                    })
                
                # Behavioral task (every other day)
                if day_in_week % 2 == 0:
                    behavioral_mins = schedule.get("behavioral_minutes", 15)
                    themes = company_pattern.get("behavioral_themes", ["leadership"])
                    theme = themes[day_in_week % len(themes)] if themes else "teamwork"
                    tasks_for_day.append({
                        "type": "behavioral",
                        "title": f"Prepare STAR story: {theme}",
                        "topic": theme,
                        "estimated_minutes": behavioral_mins,
                        "completed": False
                    })
                
                # System design (weekends or week 6+)
                if week_num >= 5 or day_name in ["Saturday", "Sunday"]:
                    design_mins = schedule.get("system_design_minutes", 30)
                    tasks_for_day.append({
                        "type": "system_design",
                        "title": "Study: URL Shortener design" if week_num == 5 else "Study: Chat App design",
                        "estimated_minutes": design_mins,
                        "completed": False
                    })
                
                daily_tasks.append({
                    "day_number": len(daily_tasks) + 1,
                    "date": current_date.isoformat(),
                    "week": week_num,
                    "day_name": day_name,
                    "focus_topic": topic,
                    "tasks": tasks_for_day,
                    "total_minutes": sum(t["estimated_minutes"] for t in tasks_for_day),
                    "completed": False
                })
                
                day_number += 1
        
        return daily_tasks
    
    async def get_today_tasks(self, plan_id: str) -> Dict[str, Any]:
        """Get tasks for today."""
        plan = await self._plans_collection().find_one({"_id": ObjectId(plan_id)})
        if not plan:
            return {"error": "Plan not found"}
        
        today = datetime.utcnow().date().isoformat()
        
        for day_data in plan.get("daily_tasks", []):
            if day_data.get("date") == today:
                return {
                    "success": True,
                    "date": today,
                    "day_number": day_data["day_number"],
                    "week": day_data["week"],
                    "focus_topic": day_data["focus_topic"],
                    "tasks": day_data["tasks"],
                    "total_minutes": day_data["total_minutes"]
                }
        
        # If no exact match, get next uncompleted day
        for day_data in plan.get("daily_tasks", []):
            if not day_data.get("completed", False):
                return {
                    "success": True,
                    "date": day_data["date"],
                    "day_number": day_data["day_number"],
                    "week": day_data["week"],
                    "focus_topic": day_data["focus_topic"],
                    "tasks": day_data["tasks"],
                    "total_minutes": day_data["total_minutes"],
                    "note": "Showing next uncompleted day"
                }
        
        return {"success": True, "message": "All tasks completed! 🎉"}
    
    async def mark_task_complete(
        self,
        plan_id: str,
        day_number: int,
        task_index: int
    ) -> Dict[str, Any]:
        """Mark a specific task as complete."""
        plan = await self._plans_collection().find_one({"_id": ObjectId(plan_id)})
        if not plan:
            return {"error": "Plan not found"}
        
        daily_tasks = plan.get("daily_tasks", [])
        
        for i, day_data in enumerate(daily_tasks):
            if day_data["day_number"] == day_number:
                if 0 <= task_index < len(day_data["tasks"]):
                    daily_tasks[i]["tasks"][task_index]["completed"] = True
                    
                    # Check if all day's tasks are completed
                    all_done = all(t.get("completed", False) for t in daily_tasks[i]["tasks"])
                    if all_done:
                        daily_tasks[i]["completed"] = True
                    
                    # Update progress
                    completed_count = sum(
                        1 for d in daily_tasks 
                        for t in d.get("tasks", []) 
                        if t.get("completed", False)
                    )
                    
                    await self._plans_collection().update_one(
                        {"_id": ObjectId(plan_id)},
                        {
                            "$set": {
                                "daily_tasks": daily_tasks,
                                "progress.tasks_completed": completed_count,
                                "updated_at": datetime.utcnow()
                            }
                        }
                    )
                    
                    return {
                        "success": True,
                        "message": "Task marked complete!",
                        "day_completed": all_done,
                        "total_completed": completed_count
                    }
        
        return {"error": "Task not found"}
    
    async def get_progress(self, plan_id: str) -> Dict[str, Any]:
        """Get overall progress for a plan."""
        plan = await self._plans_collection().find_one({"_id": ObjectId(plan_id)})
        if not plan:
            return {"error": "Plan not found"}
        
        daily_tasks = plan.get("daily_tasks", [])
        
        total_tasks = sum(len(d.get("tasks", [])) for d in daily_tasks)
        completed_tasks = sum(
            1 for d in daily_tasks 
            for t in d.get("tasks", []) 
            if t.get("completed", False)
        )
        
        days_completed = sum(1 for d in daily_tasks if d.get("completed", False))
        total_days = len(daily_tasks)
        
        # Current week calculation
        current_day = next(
            (d for d in daily_tasks if not d.get("completed", False)),
            daily_tasks[-1] if daily_tasks else {"week": 1}
        )
        
        return {
            "success": True,
            "plan_id": plan_id,
            "target_company": plan.get("target_company"),
            "progress": {
                "tasks_completed": completed_tasks,
                "total_tasks": total_tasks,
                "completion_percent": round((completed_tasks / total_tasks) * 100, 1) if total_tasks > 0 else 0,
                "days_completed": days_completed,
                "total_days": total_days,
                "current_week": current_day.get("week", 1)
            },
            "milestones": plan.get("plan_data", {}).get("milestones", [])
        }
    
    async def adjust_plan(
        self,
        plan_id: str,
        new_hours_per_day: Optional[float] = None,
        extend_weeks: Optional[int] = None,
        skip_days: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Adjust an existing plan."""
        plan = await self._plans_collection().find_one({"_id": ObjectId(plan_id)})
        if not plan:
            return {"error": "Plan not found"}
        
        updates = {"updated_at": datetime.utcnow()}
        
        if new_hours_per_day:
            updates["hours_per_day"] = new_hours_per_day
        
        if extend_weeks:
            updates["prep_weeks"] = plan.get("prep_weeks", 8) + extend_weeks
        
        if skip_days:
            current_days = plan.get("preferred_days", [])
            updates["preferred_days"] = [d for d in current_days if d not in skip_days]
        
        await self._plans_collection().update_one(
            {"_id": ObjectId(plan_id)},
            {"$set": updates}
        )
        
        return {
            "success": True,
            "message": "Plan adjusted",
            "updates": updates
        }
    
    async def get_student_plans(self, student_id: str) -> List[Dict[str, Any]]:
        """Get all plans for a student."""
        cursor = self._plans_collection().find(
            {"student_id": ObjectId(student_id)}
        ).sort("created_at", -1)
        
        plans = await cursor.to_list(20)
        
        return [
            {
                "plan_id": str(p["_id"]),
                "target_company": p.get("target_company"),
                "target_role": p.get("target_role"),
                "prep_weeks": p.get("prep_weeks"),
                "status": p.get("status"),
                "progress": p.get("progress", {}),
                "created_at": p.get("created_at")
            }
            for p in plans
        ]


# Singleton instance
ai_planner = AIPlannerAgent()
