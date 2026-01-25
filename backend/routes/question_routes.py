"""
Question Routes
API endpoints for question generation and answer evaluation.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..services.question_generator import question_generator
from ..services.answer_evaluator import answer_evaluator
from ..utils.dependencies import get_current_user


router = APIRouter(prefix="/questions", tags=["question-generation"])


# ============ Request/Response Models ============

class GenerateQuestionRequest(BaseModel):
    """Request to generate a question."""
    question_type: str = Field(..., description="dsa, behavioral, system_design, or technical")
    difficulty: str = Field(default="medium", description="easy, medium, or hard")
    company: Optional[str] = None
    topics: Optional[List[str]] = Field(default=None, description="DSA topics")
    themes: Optional[List[str]] = Field(default=None, description="Behavioral themes")
    resume_data: Optional[dict] = Field(default=None, description="For technical questions")


class QuestionResponse(BaseModel):
    """Generated question response."""
    status: str = "success"
    question: dict
    message: str = "Question generated successfully"


class EvaluateAnswerRequest(BaseModel):
    """Request to evaluate an answer."""
    question: dict = Field(..., description="The question that was asked")
    answer: str = Field(..., min_length=10, description="Student's answer")
    code: Optional[str] = Field(default=None, description="Code if DSA question")
    time_taken_seconds: int = Field(default=0, ge=0)


class EvaluationResponse(BaseModel):
    """Answer evaluation response."""
    status: str = "success"
    score: float
    grade: str
    breakdown: dict
    feedback: str
    strengths: List[str]
    improvements: List[str]


# ============ Generate Questions ============

@router.post("/generate", response_model=QuestionResponse)
async def generate_question(
    payload: GenerateQuestionRequest,
    current_user=Depends(get_current_user)
):
    """
    Generate an interview question based on type.
    
    Types:
    - dsa: Coding/algorithm question
    - behavioral: STAR format question
    - system_design: Architecture question
    - technical: Resume-based question
    """
    question = await question_generator.generate_question(
        question_type=payload.question_type,
        difficulty=payload.difficulty,
        company=payload.company,
        themes=payload.themes,
        topics=payload.topics,
        resume_data=payload.resume_data
    )
    
    return QuestionResponse(
        question=question,
        message=f"Generated {payload.question_type} question"
    )


@router.get("/dsa")
async def get_dsa_question(
    difficulty: str = Query("medium", description="easy, medium, hard"),
    topic: Optional[str] = Query(None, description="arrays, trees, graphs, etc."),
    company: Optional[str] = Query(None),
    current_user=Depends(get_current_user)
):
    """Generate a DSA coding question."""
    topics = [topic] if topic else None
    question = await question_generator.generate_dsa_question(difficulty, topics, company)
    return {"status": "success", "question": question}


@router.get("/behavioral")
async def get_behavioral_question(
    theme: Optional[str] = Query(None, description="leadership, ownership, teamwork, etc."),
    company: Optional[str] = Query(None),
    current_user=Depends(get_current_user)
):
    """Generate a behavioral question."""
    themes = [theme] if theme else None
    question = await question_generator.generate_behavioral_question(themes, company)
    return {"status": "success", "question": question}


@router.get("/design")
async def get_design_question(
    difficulty: str = Query("medium", description="medium or hard"),
    current_user=Depends(get_current_user)
):
    """Generate a system design question."""
    question = await question_generator.generate_design_question(difficulty)
    return {"status": "success", "question": question}


@router.post("/technical")
async def get_technical_question(
    resume_data: dict,
    current_user=Depends(get_current_user)
):
    """Generate a technical question based on resume."""
    question = await question_generator.generate_technical_question(resume_data)
    return {"status": "success", "question": question}


# ============ Evaluate Answers ============

@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_answer(
    payload: EvaluateAnswerRequest,
    current_user=Depends(get_current_user)
):
    """
    Evaluate an answer with type-specific scoring.
    
    Returns:
    - Score (0-100)
    - Grade (A-F)
    - Breakdown by component
    - Constructive feedback
    - Strengths and improvements
    """
    result = await answer_evaluator.evaluate(
        question=payload.question,
        answer=payload.answer,
        code=payload.code,
        time_taken_seconds=payload.time_taken_seconds
    )
    
    return EvaluationResponse(
        score=result["score"],
        grade=result["grade"],
        breakdown=result["breakdown"],
        feedback=result["feedback"],
        strengths=result["strengths"],
        improvements=result["improvements"]
    )


# ============ Quick Endpoints (Demo/Testing) ============

@router.get("/quick/dsa")
async def quick_dsa():
    """Quick DSA question (no auth)."""
    question = await question_generator.generate_dsa_question()
    return {"question": question["title"], "description": question["description"][:300]}


@router.get("/quick/behavioral")
async def quick_behavioral():
    """Quick behavioral question (no auth)."""
    question = await question_generator.generate_behavioral_question()
    return {"question": question["question"], "theme": question["theme"]}


@router.get("/quick/design")
async def quick_design():
    """Quick design question (no auth)."""
    question = await question_generator.generate_design_question()
    return {"title": question["title"], "description": question["description"][:300]}


# ============ Question Bank Stats ============

@router.get("/stats")
async def get_question_stats(current_user=Depends(get_current_user)):
    """Get statistics about the question bank."""
    from ..services.question_generator import DSA_QUESTION_BANK, BEHAVIORAL_QUESTION_TEMPLATES, SYSTEM_DESIGN_QUESTIONS
    
    dsa_by_difficulty = {}
    for q in DSA_QUESTION_BANK:
        diff = q.get("difficulty", "medium")
        dsa_by_difficulty[diff] = dsa_by_difficulty.get(diff, 0) + 1
    
    behavioral_by_theme = {}
    for q in BEHAVIORAL_QUESTION_TEMPLATES:
        theme = q.get("theme", "other")
        behavioral_by_theme[theme] = behavioral_by_theme.get(theme, 0) + 1
    
    return {
        "status": "success",
        "stats": {
            "total_dsa": len(DSA_QUESTION_BANK),
            "dsa_by_difficulty": dsa_by_difficulty,
            "total_behavioral": len(BEHAVIORAL_QUESTION_TEMPLATES),
            "behavioral_by_theme": behavioral_by_theme,
            "total_design": len(SYSTEM_DESIGN_QUESTIONS)
        }
    }
