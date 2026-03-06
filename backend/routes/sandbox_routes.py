"""
Code Sandbox Routes
API endpoints for code execution and validation.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..services.code_sandbox import code_sandbox
from ..utils.dependencies import get_current_user


router = APIRouter(prefix="/sandbox", tags=["code-sandbox"])


# ============ Request/Response Models ============

class ExecuteCodeRequest(BaseModel):
    """Request to execute code."""
    code: str = Field(..., min_length=1, description="Source code to execute")
    language: str = Field(default="python", description="Programming language")
    stdin: str = Field(default="", description="Standard input")
    timeout_ms: int = Field(default=5000, ge=1000, le=10000)


class TestCase(BaseModel):
    """Single test case."""
    input: str
    expected: str


class RunTestsRequest(BaseModel):
    """Request to run code against test cases."""
    code: str = Field(..., min_length=1)
    test_cases: List[TestCase]
    language: str = Field(default="python")


class ValidateSolutionRequest(BaseModel):
    """Request to validate against known problem."""
    code: str = Field(..., min_length=1)
    problem_id: str = Field(..., description="Problem identifier (e.g., 'two_sum')")
    language: str = Field(default="python")


# ============ Execute Code ============

@router.post("/execute")
async def execute_code(
    payload: ExecuteCodeRequest,
    current_user=Depends(get_current_user)
):
    """
    Execute code and return output.
    
    Supported languages: python, javascript, java, cpp, go, rust
    """
    result = await code_sandbox.execute_code(
        code=payload.code,
        language=payload.language,
        stdin=payload.stdin,
        timeout_ms=payload.timeout_ms
    )
    
    return {
        "status": "success" if result.success else "error",
        "output": result.output,
        "error": result.error if result.error else None,
        "exit_code": result.exit_code
    }


# ============ Run Test Cases ============

@router.post("/test")
async def run_test_cases(
    payload: RunTestsRequest,
    current_user=Depends(get_current_user)
):
    """
    Run code against multiple test cases.
    
    Returns pass/fail for each test and overall score.
    """
    test_cases = [{"input": t.input, "expected": t.expected} for t in payload.test_cases]
    
    result = await code_sandbox.run_test_cases(
        code=payload.code,
        test_cases=test_cases,
        language=payload.language
    )
    
    return {
        "status": "success",
        "passed": result["passed"],
        "total": result["total"],
        "score": result["score"],
        "all_passed": result["all_passed"],
        "results": result["results"]
    }


# ============ Validate Known Problem ============

@router.post("/validate")
async def validate_solution(
    payload: ValidateSolutionRequest,
    current_user=Depends(get_current_user)
):
    """
    Validate solution against a known problem's test cases.
    
    Supported problems: two_sum, valid_parentheses, reverse_string, fizzbuzz, palindrome
    """
    result = await code_sandbox.validate_solution(
        code=payload.code,
        problem_id=payload.problem_id,
        language=payload.language
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


# ============ Get Supported Languages ============

@router.get("/languages")
async def get_languages():
    """Get list of supported programming languages."""
    languages = await code_sandbox.get_supported_languages()
    return {"status": "success", "languages": languages}


# ============ Quick Test (Demo) ============

@router.post("/quick-test")
async def quick_test(
    code: str,
    language: str = "python"
):
    """Quick code execution test (no auth required for demo)."""
    # Limit code size for demo
    if len(code) > 5000:
        raise HTTPException(status_code=400, detail="Code too long for demo (max 5000 chars)")
    
    result = await code_sandbox.execute_code(
        code=code,
        language=language,
        stdin="",
        timeout_ms=3000
    )
    
    return {
        "output": result.output[:1000],
        "error": result.error[:500] if result.error else None,
        "success": result.success
    }
