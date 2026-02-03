"""
Code Sandbox Service
Executes student code safely using Piston API (free, no setup required).
Features: Multi-language support, test case validation, resource limits.
"""

import aiohttp
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json
import re


@dataclass
class ExecutionResult:
    """Result of code execution."""
    success: bool
    output: str
    error: str
    run_time_ms: int
    memory_kb: int
    exit_code: int


class CodeSandbox:
    """
    Safe code execution using Piston API.
    Supports: Python, JavaScript, Java, C++, Go, Rust, etc.
    """
    
    # Piston API endpoint (free, public)
    PISTON_API = "https://emkc.org/api/v2/piston"
    
    # Language mappings
    LANGUAGES = {
        "python": {"language": "python", "version": "3.10"},
        "python3": {"language": "python", "version": "3.10"},
        "javascript": {"language": "javascript", "version": "18.15.0"},
        "js": {"language": "javascript", "version": "18.15.0"},
        "java": {"language": "java", "version": "15.0.2"},
        "cpp": {"language": "c++", "version": "10.2.0"},
        "c++": {"language": "c++", "version": "10.2.0"},
        "c": {"language": "c", "version": "10.2.0"},
        "go": {"language": "go", "version": "1.16.2"},
        "rust": {"language": "rust", "version": "1.68.2"},
        "typescript": {"language": "typescript", "version": "5.0.3"},
    }
    
    # Execution limits
    MAX_TIMEOUT_MS = 10000  # 10 seconds
    MAX_MEMORY_KB = 256000  # 256 MB
    
    def __init__(self):
        self._session = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def execute_code(
        self,
        code: str,
        language: str = "python",
        stdin: str = "",
        timeout_ms: int = 5000
    ) -> ExecutionResult:
        """
        Execute code and return result.
        
        Args:
            code: Source code to execute
            language: Programming language
            stdin: Standard input for the code
            timeout_ms: Execution timeout in milliseconds
            
        Returns:
            ExecutionResult with output, errors, timing
        """
        # Get language config
        lang_config = self.LANGUAGES.get(language.lower())
        if not lang_config:
            return ExecutionResult(
                success=False,
                output="",
                error=f"Unsupported language: {language}. Supported: {list(self.LANGUAGES.keys())}",
                run_time_ms=0,
                memory_kb=0,
                exit_code=-1
            )
        
        # Prepare request
        payload = {
            "language": lang_config["language"],
            "version": lang_config["version"],
            "files": [{"content": code}],
            "stdin": stdin,
            "run_timeout": min(timeout_ms, self.MAX_TIMEOUT_MS),
            "compile_memory_limit": self.MAX_MEMORY_KB * 1000,
            "run_memory_limit": self.MAX_MEMORY_KB * 1000
        }
        
        try:
            session = await self._get_session()
            async with session.post(
                f"{self.PISTON_API}/execute",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return ExecutionResult(
                        success=False,
                        output="",
                        error=f"API Error: {response.status} - {error_text[:200]}",
                        run_time_ms=0,
                        memory_kb=0,
                        exit_code=-1
                    )
                
                result = await response.json()
                
                run_data = result.get("run", {})
                compile_data = result.get("compile", {})
                
                # Check for compile errors
                if compile_data.get("stderr"):
                    return ExecutionResult(
                        success=False,
                        output=compile_data.get("stdout", ""),
                        error=compile_data.get("stderr", "Compilation failed"),
                        run_time_ms=0,
                        memory_kb=0,
                        exit_code=compile_data.get("code", 1)
                    )
                
                # Runtime result
                stdout = run_data.get("stdout", "").strip()
                stderr = run_data.get("stderr", "").strip()
                exit_code = run_data.get("code", 0)
                
                return ExecutionResult(
                    success=exit_code == 0 and not stderr,
                    output=stdout,
                    error=stderr,
                    run_time_ms=0,  # Piston doesn't return timing
                    memory_kb=0,
                    exit_code=exit_code
                )
                
        except asyncio.TimeoutError:
            return ExecutionResult(
                success=False,
                output="",
                error="Execution timed out",
                run_time_ms=timeout_ms,
                memory_kb=0,
                exit_code=-1
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                output="",
                error=f"Execution error: {str(e)}",
                run_time_ms=0,
                memory_kb=0,
                exit_code=-1
            )
    
    async def run_test_cases(
        self,
        code: str,
        test_cases: List[Dict[str, Any]],
        language: str = "python"
    ) -> Dict[str, Any]:
        """
        Run code against multiple test cases.
        
        Args:
            code: Source code (must read from stdin and print to stdout)
            test_cases: List of {"input": ..., "expected": ...}
            language: Programming language
            
        Returns:
            {
                "passed": int,
                "total": int,
                "results": [...],
                "score": float (0-100)
            }
        """
        if not test_cases:
            return {"passed": 0, "total": 0, "results": [], "score": 0}
        
        results = []
        passed = 0
        
        for i, test in enumerate(test_cases):
            # Prepare input
            test_input = test.get("input", "")
            if isinstance(test_input, list):
                test_input = "\n".join(str(x) for x in test_input)
            elif not isinstance(test_input, str):
                test_input = str(test_input)
            
            # Expected output
            expected = test.get("expected", "")
            if not isinstance(expected, str):
                expected = str(expected)
            expected = expected.strip()
            
            # Execute
            result = await self.execute_code(code, language, test_input)
            
            # Compare output
            actual = result.output.strip()
            is_correct = self._compare_outputs(actual, expected)
            
            if is_correct:
                passed += 1
            
            results.append({
                "test_case": i + 1,
                "input": test_input[:100] + "..." if len(test_input) > 100 else test_input,
                "expected": expected[:100] + "..." if len(expected) > 100 else expected,
                "actual": actual[:100] + "..." if len(actual) > 100 else actual,
                "passed": is_correct,
                "error": result.error if not result.success else None
            })
        
        total = len(test_cases)
        score = (passed / total) * 100 if total > 0 else 0
        
        return {
            "passed": passed,
            "total": total,
            "results": results,
            "score": round(score, 1),
            "all_passed": passed == total
        }
    
    def _compare_outputs(self, actual: str, expected: str) -> bool:
        """Compare outputs with some flexibility."""
        # Exact match
        if actual == expected:
            return True
        
        # Normalize whitespace
        actual_normalized = " ".join(actual.split())
        expected_normalized = " ".join(expected.split())
        if actual_normalized == expected_normalized:
            return True
        
        # Try parsing as JSON/list for array problems
        try:
            actual_parsed = json.loads(actual.replace("'", '"'))
            expected_parsed = json.loads(expected.replace("'", '"'))
            if actual_parsed == expected_parsed:
                return True
            # For lists, check sorted equality (order might not matter)
            if isinstance(actual_parsed, list) and isinstance(expected_parsed, list):
                if sorted(str(x) for x in actual_parsed) == sorted(str(x) for x in expected_parsed):
                    return True
        except (json.JSONDecodeError, TypeError):
            pass
        
        return False
    
    async def validate_solution(
        self,
        code: str,
        problem_id: str,
        language: str = "python"
    ) -> Dict[str, Any]:
        """
        Validate a solution against a known problem's test cases.
        
        Args:
            code: Student's solution code
            problem_id: Problem identifier to get test cases
            language: Programming language
        """
        # Get test cases for the problem
        test_cases = self._get_problem_test_cases(problem_id)
        
        if not test_cases:
            return {
                "success": False,
                "error": f"No test cases found for problem: {problem_id}",
                "score": 0
            }
        
        # Run tests
        result = await self.run_test_cases(code, test_cases, language)
        
        return {
            "success": True,
            "problem_id": problem_id,
            **result
        }
    
    def _get_problem_test_cases(self, problem_id: str) -> List[Dict[str, Any]]:
        """Get test cases for common problems."""
        # Built-in test cases for common problems
        PROBLEM_TESTS = {
            "two_sum": [
                {"input": "[2,7,11,15]\n9", "expected": "[0, 1]"},
                {"input": "[3,2,4]\n6", "expected": "[1, 2]"},
                {"input": "[3,3]\n6", "expected": "[0, 1]"}
            ],
            "valid_parentheses": [
                {"input": "()", "expected": "True"},
                {"input": "()[]{}", "expected": "True"},
                {"input": "(]", "expected": "False"},
                {"input": "([)]", "expected": "False"}
            ],
            "reverse_string": [
                {"input": "hello", "expected": "olleh"},
                {"input": "world", "expected": "dlrow"}
            ],
            "fizzbuzz": [
                {"input": "15", "expected": "1\n2\nFizz\n4\nBuzz\nFizz\n7\n8\nFizz\nBuzz\n11\nFizz\n13\n14\nFizzBuzz"}
            ],
            "palindrome": [
                {"input": "racecar", "expected": "True"},
                {"input": "hello", "expected": "False"}
            ]
        }
        
        return PROBLEM_TESTS.get(problem_id.lower(), [])
    
    async def get_supported_languages(self) -> List[str]:
        """Get list of supported languages."""
        return list(self.LANGUAGES.keys())
    
    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()


# Singleton instance
code_sandbox = CodeSandbox()


# Integration with answer evaluator
async def evaluate_code_with_sandbox(
    code: str,
    test_cases: List[Dict[str, Any]],
    language: str = "python"
) -> Dict[str, Any]:
    """
    Helper function to evaluate code with sandbox.
    Used by answer_evaluator.py
    """
    result = await code_sandbox.run_test_cases(code, test_cases, language)
    return {
        "correctness_score": result["score"],
        "tests_passed": result["passed"],
        "tests_total": result["total"],
        "all_passed": result["all_passed"],
        "results": result["results"]
    }
