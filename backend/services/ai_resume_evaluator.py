"""
AI Resume Evaluator Service
Analyzes parsed resume data using an LLM to generate dynamic, intelligent insights, 
scores, strengths, and an actionable improvement plan.
"""

import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class AIResumeEvaluator:
    def __init__(self):
        self._llm_service = None

    def _get_llm(self):
        """Lazy load LLM service to avoid circular imports."""
        if self._llm_service is None:
            try:
                from .llm_service import llm_service
                self._llm_service = llm_service
            except Exception as e:
                logger.error(f"Failed to load LLM service: {e}")
                self._llm_service = None
        return self._llm_service

    async def evaluate_resume(self, parsed_data: Dict[str, Any], target_role: str = "General Tech Role") -> Optional[Dict[str, Any]]:
        """
        Evaluates a parsed resume and returns structured JSON feedback matching the UI's expected format.
        
        Args:
            parsed_data: The dictionary containing 'skills', 'experience', 'education', 'projects'
            target_role: The role the candidate is aiming for (default: General Tech Role)
            
        Returns:
            A dictionary containing 'summary', 'rating', 'strengths', 'issues', and 'action_plan',
            or None if the evaluation fails.
        """
        llm = self._get_llm()
        if not llm:
            logger.warning("LLM service is not available for resume evaluation.")
            return None

        # Prepare a concise summary of the parsed resume for the LLM prompt
        contact = parsed_data.get("contact", {})
        skills = parsed_data.get("skills", [])
        experience = parsed_data.get("experience", [])
        education = parsed_data.get("education", [])
        projects = parsed_data.get("projects", [])

        # Build a string representation of the resume
        resume_content = f"Candidate Name: {contact.get('name', 'Unknown')}\n\n"
        
        resume_content += f"Skills ({len(skills)}):\n"
        resume_content += ", ".join(skills[:30]) + ("..." if len(skills) > 30 else "") + "\n\n"
        
        resume_content += f"Experience ({len(experience)} entries):\n"
        for exp in experience[:5]:
            desc = exp.get("description", "")
            resume_content += f"- {exp.get('title')} at {exp.get('company')} ({exp.get('start_date')} to {exp.get('end_date')}): {desc[:200]}...\n"
        resume_content += "\n"
        
        resume_content += f"Education ({len(education)} entries):\n"
        for edu in education[:3]:
            resume_content += f"- {edu.get('degree')} at {edu.get('institution')} ({edu.get('year')}). GPA: {edu.get('gpa', 'N/A')}\n"
        resume_content += "\n"
        
        resume_content += f"Projects ({len(projects)} entries):\n"
        for proj in projects[:3]:
            technologies = ", ".join(proj.get("technologies", []))
            resume_content += f"- {proj.get('name')}: {proj.get('description', '')[:100]}... [Tech: {technologies}]\n"

        system_instruction = "You are an expert technical recruiter and resume reviewer at a top-tier tech company. Output ONLY strict JSON. No markdown backticks, no markdown formatting."

        prompt = f"""
Please evaluate the following extracted resume data for a candidate whose target role is approximately '{target_role}'.

=== EXTRACTED RESUME DATA ===
{resume_content}
=============================

Analyze this resume and provide highly specific, actionable, and insightful feedback. Do NOT use generic boilerplate text. Be critical but constructive.

Return ONLY a JSON object exactly matching this structure:
{{
  "summary": "A 2-3 sentence executive summary of the candidate's readiness, positioning, and overall competitiveness.",
  "rating": {{
    "overall": 8.5,
    "breakdown": [
      {{"aspect": "ATS Friendliness", "score": 8.0, "max": 10}},
      {{"aspect": "Technical Depth", "score": 8.5, "max": 10}},
      {{"aspect": "Clarity", "score": 7.0, "max": 10}},
      {{"aspect": "Impact Quantification", "score": 6.5, "max": 10}},
      {{"aspect": "Recruiter Readability", "score": 7.5, "max": 10}},
      {{"aspect": "Industry Alignment", "score": 9.0, "max": 10}}
    ]
  }},
  "strengths": [
    {{"title": "Short title 1 (e.g., Strong Backend Experience)", "description": "Specific detail from the resume about this strength."}},
    {{"title": "Short title 2", "description": "Specific detail."}},
    {{"title": "Short title 3", "description": "Specific detail."}}
  ],
  "issues": [
    {{"title": "Short title 1 (e.g., Lacks Quantified Metrics)", "description": "Specific explanation of what is missing."}},
    {{"title": "Short title 2", "description": "Specific explanation."}}
  ],
  "action_plan": [
    "Specific step 1 to improve the resume or profile.",
    "Specific step 2.",
    "Specific step 3.",
    "Specific step 4."
  ]
}}

Guidelines:
- "overall" score must be a logical average/aggregation of the breakdown scores (round to 1 decimal place).
- Breakdown scores must be between 1 and 10.
- Provide 2-4 strengths and 2-4 issues. Provide 3-5 action plan items.
- Reference specific technologies, project names, or companies from the resume in your analysis to prove you evaluated it deeply.
"""
        
        try:
            response_text = await llm.generate(prompt, system_instruction)
            
            # Clean possible markdown formatting
            clean_text = response_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            elif clean_text.startswith("```"):
                clean_text = clean_text[3:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()
                
            feedback = json.loads(clean_text)
            
            # Basic validation
            if "rating" in feedback and "overall" in feedback["rating"]:
                return feedback
            else:
                logger.error("LLM returned JSON, but it did not match the required schema.")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}\nResponse was:\n{response_text[:500]}...")
            return None
        except Exception as e:
            logger.error(f"Error during AI resume evaluation: {e}")
            return None

# Singleton instance
ai_resume_evaluator = AIResumeEvaluator()
