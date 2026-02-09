"""
Gap Analysis Agent

Compares Student Profile vs Job Description.
Identifies missing skills and retrieves COURSE recommendations via RAG.
"""

import logging
import json
from typing import List, Dict, Any, Optional

from backend.services.rag_manager import rag_manager
from backend.config import settings

logger = logging.getLogger(__name__)

class GapAnalysisAgent:
    """
    Advanced Agent that performs 3-step analysis:
    1. Compare (LLM): Student Skills vs Job Description
    2. Retrieve (RAG): Find courses for missing skills
    3. Plan (Logic): Structure a learning path
    """
    
    async def analyze(self, student_skills: List[str], job_description: str) -> Dict[str, Any]:
        """
        Main entry point for the agent.
        """
        logger.info("Starting Gap Analysis...")
        
        # Step 1: LLM Comparison via Helper
        from .llm_service import llm_service
        
        # Prepare Prompt
        prompt = f"""
        Compare the Student's Skills against the Job Description.
        
        Student Skills: {", ".join(student_skills)}
        
        Job Description:
        {job_description[:3000]}
        
        Identify:
        1. Missing critical technical skills (High Priority).
        2. Missing nice-to-have skills (Medium/Low Priority).
        
        Return ONLY a JSON list of objects:
        [
            {{"skill": "Skill Name", "priority": "High|Medium|Low", "reason": "Why it is missing"}}
        ]
        """
        
        system_prompt = "You are an expert Career Coach and Technical Recruiter. Output strictly valid JSON."
        
        try:
            llm_response = await llm_service.generate(prompt, system_prompt)
            # Simple cleanup if LLM adds markdown blocks
            clean_json = llm_response.replace("```json", "").replace("```", "").strip()
            missing_analysis = json.loads(clean_json)
        except Exception as e:
            logger.error(f"Gap Analysis LLM Failed: {e}")
            # Fallback to naive
            missing_analysis = []
            common_tech = ["python", "react", "docker", "kubernetes", "aws", "fastapi", "mongodb", "sql", "git"]
            student_set = {s.lower() for s in student_skills}
            for tech in common_tech:
                if tech in job_description.lower() and tech not in student_set:
                    missing_analysis.append({"skill": tech, "priority": "High", "reason": "Detected in JD"})

        missing_skills = [item["skill"] for item in missing_analysis]
        logger.info(f"Identified gaps: {missing_skills}")
        
        # Step 2: RAG Retrieval (The new "Brain" power)
        recommendations = []
        for item in missing_analysis:
            skill = item["skill"]
            priority = item.get("priority", "High")
            
            # Query the RAG Manager
            courses = await rag_manager.search_public(f"{skill} course tutorial", limit=2)
            
            # Format recommendations
            skill_recs = []
            for doc in courses:
                meta = doc.metadata or {}
                skill_recs.append({
                    "title": meta.get("title", f"Learn {skill}"),
                    "type": meta.get("type", "resource"),
                    "url": meta.get("url", f"https://www.google.com/search?q={skill}+tutorial"),
                    "relevance": doc.score
                })
            
            # If no RAG results, add a fallback Google link
            if not skill_recs:
                skill_recs.append({
                    "title": f"{skill} Documentation",
                    "type": "search",
                    "url": f"https://www.google.com/search?q={skill}+documentation",
                    "relevance": 1.0
                })
            
            recommendations.append({
                "skill": skill,
                "priority": priority,
                "reason": item.get("reason", "Required for role"),
                "resources": skill_recs
            })
            
        return {
            "missing_skills": missing_skills,
            "recommendations": recommendations,
            "analysis_summary": f"Identified {len(missing_skills)} missing skills using AI Analysis."
        }

gap_analysis_agent = GapAnalysisAgent()
