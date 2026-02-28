"""
MCQ Generator Service
Generates 5-question multiple choice quizzes for learning path stage evaluation.
Uses LLM to create topic-specific questions and evaluate answers.
"""

import json
from typing import List, Dict, Any, Optional


class MCQGeneratorService:
    """Generates and evaluates MCQs for learning path stages."""

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

    async def generate_mcqs(
        self,
        skill: str,
        stage_name: str,
        subtopics: List[Dict[str, Any]],
        difficulty: str = "intermediate",
        goal_level: str = "Job-ready"
    ) -> List[Dict[str, Any]]:
        """
        Generate 5 MCQs for a specific learning path stage based on subtopics.
        """
        llm = self._get_llm()
        if not llm:
            return self._fallback_mcqs(skill, stage_name)

        subtopics_text = ""
        for s in subtopics[:4]:
            ac = ", ".join(s.get("acceptance_criteria", []))
            subtopics_text += f"- {s.get('title', 'Topic')} (Focus: {ac})\n"
            
        if not subtopics_text:
            subtopics_text = f"- {skill} fundamentals"

        prompt = f"""You are an elite technical interviewer creating a rigorous quiz to test student knowledge.

Skill: {skill}
Stage: {stage_name}
Subtopics & Acceptance Criteria Covered:
{subtopics_text}
Target Goal Level: {goal_level}
Difficulty: {difficulty}

Generate EXACTLY 5 multiple-choice questions to test deep understanding of the above stage.
If the Target Goal Level is 'Job-ready' or 'Intermediate', you MUST include scenario-based questions, practical class/code usage questions, and debugging questions (e.g., identifying why styling failed, fixing a broken component).

Rules:
- 5 questions exactly.
- Each question must have exactly 4 options (A, B, C, D).
- Only one option is correct.
- Questions MUST test applied conceptual understanding, NOT raw repetition or trivia. Vary the difficulty.
- Include a brief explanation for the correct answer, PLUS a feedback/improvement suggestion for the learner.
- Difficulty should be rigorously calibrated to '{difficulty}' and '{goal_level}'.

Output ONLY valid JSON in this exact format:
{{
  "questions": [
    {{
      "id": 1,
      "question": "Scenario/Debugging/Concept Question text here?",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_index": 0,
      "explanation": "Brief explanation why this is correct. Feedback: Recommendation on what to review."
    }}
  ]
}}"""

        try:
            response = await llm.generate(prompt, "You are a technical quiz generator. Output strict JSON only.")
            clean = response.strip()
            # Strip markdown code blocks if present
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            data = json.loads(clean.strip())
            questions = data.get("questions", [])
            # Ensure exactly 5 questions
            if len(questions) < 5:
                questions += self._fallback_mcqs(skill, stage_name)[len(questions):]
            return questions[:5]
        except Exception as e:
            print(f"MCQ Generation failed: {e}")
            return self._fallback_mcqs(skill, stage_name)

    def evaluate_answers(
        self,
        questions: List[Dict[str, Any]],
        submitted_answers: List[int]  # list of selected option indices (0-3)
    ) -> Dict[str, Any]:
        """
        Evaluate submitted MCQ answers.

        Returns:
            score (int 0-5), passed (bool >=3/5), per-question feedback
        """
        if len(questions) != len(submitted_answers):
            return {"score": 0, "passed": False, "feedback": [], "error": "Answer count mismatch"}

        feedback = []
        score = 0

        for i, (q, ans) in enumerate(zip(questions, submitted_answers)):
            correct = q.get("correct_index", 0)
            is_correct = ans == correct
            if is_correct:
                score += 1
            feedback.append({
                "question_id": q.get("id", i + 1),
                "question": q.get("question", ""),
                "your_answer": q.get("options", [])[ans] if 0 <= ans < len(q.get("options", [])) else "Invalid",
                "correct_answer": q.get("options", [])[correct] if 0 <= correct < len(q.get("options", [])) else "N/A",
                "is_correct": is_correct,
                "explanation": q.get("explanation", "")
            })

        passed = score >= 3  # Must get 3 or more out of 5

        return {
            "score": score,
            "total": 5,
            "percentage": round(score / 5 * 100),
            "passed": passed,
            "feedback": feedback,
            "message": (
                f"✅ Passed! You scored {score}/5. Stage marked as complete."
                if passed
                else f"❌ Not quite. You scored {score}/5. Review the material and try again."
            )
        }

    def _fallback_mcqs(self, skill: str, stage_name: str) -> List[Dict[str, Any]]:
        """Fallback MCQs when LLM fails."""
        return [
            {
                "id": i + 1,
                "question": f"Which of the following best describes a key concept in {skill} related to {stage_name}?",
                "options": [
                    f"It is a core component of modern {skill} workflows",
                    f"It is unrelated to {skill}",
                    f"It applies only to legacy {skill} systems",
                    f"It is optional and rarely used"
                ],
                "correct_index": 0,
                "explanation": f"Core concepts in {skill} are foundational to modern development workflows."
            }
            for i in range(5)
        ]


# Singleton
mcq_generator = MCQGeneratorService()
