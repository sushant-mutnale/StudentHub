"""
Answer Evaluator Service
Evaluates interview answers with type-specific scoring and constructive feedback.
Features: DSA code analysis, STAR format detection, design component checking, AI feedback.
"""

from typing import Dict, List, Any, Optional, Tuple
import re
import math


class AnswerEvaluator:
    """
    Evaluates interview answers based on question type.
    Uses weighted scoring formulas and generates constructive feedback.
    """
    
    def __init__(self):
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
    
    # ============ Main Evaluation Entry ============
    
    async def evaluate(
        self,
        question: Dict[str, Any],
        answer: str,
        code: Optional[str] = None,
        time_taken_seconds: int = 0,
        expected_time_seconds: int = 1800
    ) -> Dict[str, Any]:
        """
        Evaluate an answer based on question type.
        
        Returns:
            {
                "score": 0-100,
                "breakdown": {component scores},
                "feedback": "constructive feedback string",
                "strengths": ["list", "of", "strengths"],
                "improvements": ["list", "of", "improvements"],
                "grade": "A/B/C/D/F"
            }
        """
        question_type = question.get("type", "dsa")
        
        if question_type == "dsa":
            return await self.evaluate_dsa(question, answer, code, time_taken_seconds, expected_time_seconds)
        elif question_type == "behavioral":
            return await self.evaluate_behavioral(question, answer, time_taken_seconds)
        elif question_type == "system_design":
            return await self.evaluate_design(question, answer, time_taken_seconds)
        elif question_type == "technical":
            return await self.evaluate_technical(question, answer, time_taken_seconds)
        else:
            return await self.evaluate_generic(question, answer)
    
    # ============ DSA Evaluation ============
    
    async def evaluate_dsa(
        self,
        question: Dict[str, Any],
        answer: str,
        code: Optional[str],
        time_taken: int,
        expected_time: int
    ) -> Dict[str, Any]:
        """
        Evaluate DSA/coding answer.
        
        Scoring formula:
        overall = (correctness * 0.4) + (code_quality * 0.3) + (efficiency * 0.2) + (speed * 0.1)
        """
        breakdown = {}
        strengths = []
        improvements = []
        
        # 1. Correctness (40%)
        correctness = await self._evaluate_dsa_correctness(question, answer, code)
        breakdown["correctness"] = correctness
        if correctness >= 80:
            strengths.append("Correct solution approach")
        elif correctness < 50:
            improvements.append("Review the problem requirements and edge cases")
        
        # 2. Code Quality (30%)
        code_quality = self._evaluate_code_quality(code or answer)
        breakdown["code_quality"] = code_quality
        if code_quality >= 80:
            strengths.append("Clean, readable code")
        elif code_quality < 50:
            improvements.append("Improve code structure and naming")
        
        # 3. Efficiency (20%)
        efficiency = await self._evaluate_efficiency(question, answer, code)
        breakdown["efficiency"] = efficiency
        if efficiency >= 80:
            strengths.append("Optimal time/space complexity")
        elif efficiency < 50:
            improvements.append("Consider more efficient algorithms or data structures")
        
        # 4. Speed (10%)
        speed = self._evaluate_speed(time_taken, expected_time)
        breakdown["speed"] = speed
        if speed >= 80:
            strengths.append("Completed within expected time")
        elif speed < 50:
            improvements.append("Practice to improve problem-solving speed")
        
        # Calculate overall score
        overall = (
            correctness * 0.4 +
            code_quality * 0.3 +
            efficiency * 0.2 +
            speed * 0.1
        )
        
        # Generate feedback
        feedback = await self._generate_dsa_feedback(question, answer, code, breakdown)
        
        return {
            "score": round(overall, 1),
            "breakdown": breakdown,
            "feedback": feedback,
            "strengths": strengths[:3],
            "improvements": improvements[:3],
            "grade": self._score_to_grade(overall)
        }
    
    async def _evaluate_dsa_correctness(
        self,
        question: Dict[str, Any],
        answer: str,
        code: Optional[str],
        language: str = "python"
    ) -> float:
        """
        Evaluate correctness of DSA answer.
        Uses sandbox execution when test cases are available.
        """
        score = 50  # Base score
        
        ideal_approach = question.get("ideal_approach", "").lower()
        expected_complexity = question.get("time_complexity", "").lower()
        
        text = (answer + " " + (code or "")).lower()
        
        # Check if mentions key concepts from ideal approach
        approach_keywords = ["hash", "map", "set", "two pointer", "sliding", "dp", "dynamic", 
                           "recursion", "bfs", "dfs", "binary search", "sort", "stack", "queue",
                           "tree", "graph", "heap", "trie"]
        
        mentioned_concepts = sum(1 for kw in approach_keywords if kw in text)
        score += min(20, mentioned_concepts * 5)
        
        # Check if has code
        if code and len(code) > 50:
            score += 15
            
            # Check for function definition
            if re.search(r'def\s+\w+\(|function\s+\w+|public\s+\w+|const\s+\w+\s*=', code):
                score += 5
            
            # Check for loops/logic
            if re.search(r'for\s|while\s|if\s', code):
                score += 5
        
        # TRY SANDBOX EXECUTION (NEW - Most accurate!)
        sandbox_score = await self._sandbox_evaluate_code(question, code, language)
        if sandbox_score is not None:
            # Sandbox result is highly reliable - give it 60% weight
            score = (score * 0.4) + (sandbox_score * 0.6)
            return min(100, score)
        
        # Fallback to LLM evaluation if sandbox not available
        llm = self._get_llm_service()
        if llm and code:
            try:
                ai_score = await self._ai_evaluate_correctness(question, code)
                # Blend AI score with rule-based
                score = (score + ai_score) / 2
            except Exception:
                pass
        
        return min(100, score)
    
    async def _sandbox_evaluate_code(
        self, 
        question: Dict[str, Any], 
        code: Optional[str],
        language: str = "python"
    ) -> Optional[float]:
        """
        Execute code in sandbox against test cases.
        Returns score 0-100 based on test pass rate, or None if sandbox unavailable.
        """
        if not code or len(code) < 30:
            return None
        
        # Get test cases from question
        test_cases = question.get("test_cases", [])
        
        # If no test cases, try the problem's built-in ones
        if not test_cases:
            problem_id = question.get("id", "")
            if problem_id:
                test_cases = self._get_builtin_test_cases(problem_id)
        
        if not test_cases:
            return None  # No test cases available
        
        try:
            from .code_sandbox import code_sandbox
            
            result = await code_sandbox.run_test_cases(
                code=code,
                test_cases=test_cases,
                language=language
            )
            
            # Calculate score based on test results
            if result["total"] > 0:
                base_score = result["score"]  # Already 0-100
                
                # Bonus for all tests passing
                if result["all_passed"]:
                    base_score = min(100, base_score + 5)
                
                return base_score
            
            return None
            
        except Exception as e:
            # Sandbox not available or failed
            return None
    
    def _get_builtin_test_cases(self, problem_id: str) -> List[Dict[str, str]]:
        """Get built-in test cases for known problems."""
        # These mirror the test cases in code_sandbox.py
        test_case_db = {
            "two_sum": [
                {"input": "[2,7,11,15]\n9", "expected": "[0, 1]"},
                {"input": "[3,2,4]\n6", "expected": "[1, 2]"},
                {"input": "[3,3]\n6", "expected": "[0, 1]"}
            ],
            "valid_parentheses": [
                {"input": "()", "expected": "True"},
                {"input": "()[]{}", "expected": "True"},
                {"input": "(]", "expected": "False"}
            ],
            "reverse_string": [
                {"input": "hello", "expected": "olleh"},
                {"input": "world", "expected": "dlrow"}
            ],
            "fizzbuzz": [
                {"input": "3", "expected": "Fizz"},
                {"input": "5", "expected": "Buzz"},
                {"input": "15", "expected": "FizzBuzz"},
                {"input": "7", "expected": "7"}
            ],
            "palindrome": [
                {"input": "racecar", "expected": "True"},
                {"input": "hello", "expected": "False"},
                {"input": "A man a plan a canal Panama", "expected": "True"}
            ]
        }
        return test_case_db.get(problem_id, [])
    
    async def _ai_evaluate_correctness(self, question: Dict, code: str) -> float:
        """Use AI to evaluate code correctness."""
        llm = self._get_llm_service()
        if not llm:
            return 50
        
        prompt = f"""Evaluate this code solution for correctness.

PROBLEM: {question.get('title', '')}
{question.get('description', '')[:500]}

CODE:
{code[:1500]}

Rate correctness from 0-100 considering:
- Does it solve the problem correctly?
- Does it handle edge cases?
- Is the logic sound?

Respond with ONLY a number between 0-100."""

        try:
            response = await llm.generate(prompt)
            score = int(re.search(r'\d+', response).group())
            return min(100, max(0, score))
        except Exception:
            return 50
    
    def _evaluate_code_quality(self, code: str) -> float:
        """Evaluate code quality (naming, structure, readability)."""
        if not code or len(code) < 20:
            return 30
        
        score = 50
        
        # Length check (too short = incomplete, too long = potentially messy)
        if 100 < len(code) < 2000:
            score += 10
        
        # Has meaningful variable names (not just single letters everywhere)
        meaningful_vars = len(re.findall(r'\b[a-z]{3,15}\b', code.lower()))
        if meaningful_vars >= 5:
            score += 10
        
        # Has comments
        if re.search(r'#|//|/\*', code):
            score += 10
        
        # Consistent indentation
        lines = code.split('\n')
        indented = sum(1 for l in lines if l.startswith('    ') or l.startswith('\t'))
        if indented > len(lines) * 0.3:
            score += 10
        
        # No extremely long lines
        long_lines = sum(1 for l in lines if len(l) > 100)
        if long_lines < len(lines) * 0.1:
            score += 5
        
        # Has return statement
        if 'return ' in code:
            score += 5
        
        return min(100, score)
    
    async def _evaluate_efficiency(
        self,
        question: Dict[str, Any],
        answer: str,
        code: Optional[str]
    ) -> float:
        """Evaluate time/space complexity awareness."""
        score = 50
        
        text = (answer + " " + (code or "")).lower()
        expected = question.get("time_complexity", "").lower()
        
        # Check if mentions complexity
        complexity_patterns = [
            r'o\(1\)', r'o\(n\)', r'o\(log\s*n\)', r'o\(n\s*log\s*n\)',
            r'o\(n\^?2\)', r'o\(n\^?3\)', r'constant', r'linear', r'logarithmic'
        ]
        
        for pattern in complexity_patterns:
            if re.search(pattern, text):
                score += 15
                break
        
        # Check if optimal based on expected
        if expected:
            if expected in text or any(e in text for e in expected.split()):
                score += 20
        
        # Penalize obviously inefficient patterns
        if re.search(r'for.*for.*for', code or ""):  # Triple nested loops
            score -= 10
        
        return min(100, max(0, score))
    
    def _evaluate_speed(self, time_taken: int, expected_time: int) -> float:
        """Evaluate completion speed."""
        if expected_time <= 0:
            return 70  # Default if no expected time
        
        ratio = time_taken / expected_time
        
        if ratio <= 0.5:
            return 100  # Very fast
        elif ratio <= 0.75:
            return 90
        elif ratio <= 1.0:
            return 80
        elif ratio <= 1.25:
            return 70
        elif ratio <= 1.5:
            return 60
        elif ratio <= 2.0:
            return 50
        else:
            return 30
    
    async def _generate_dsa_feedback(
        self,
        question: Dict[str, Any],
        answer: str,
        code: Optional[str],
        breakdown: Dict[str, float]
    ) -> str:
        """Generate constructive feedback for DSA answer."""
        llm = self._get_llm_service()
        
        if llm:
            try:
                prompt = f"""Generate brief, constructive feedback for this coding interview answer.

Problem: {question.get('title', '')}
Code provided: {'Yes' if code else 'No'}
Scores: Correctness={breakdown.get('correctness', 0):.0f}%, Quality={breakdown.get('code_quality', 0):.0f}%, Efficiency={breakdown.get('efficiency', 0):.0f}%

Write 2-3 sentences of specific, encouraging feedback. Mention what was good and one improvement."""

                response = await llm.generate(prompt)
                return response.strip()[:300]
            except Exception:
                pass
        
        # Fallback feedback
        avg = sum(breakdown.values()) / len(breakdown)
        if avg >= 80:
            return "Excellent solution! Your approach demonstrates strong problem-solving skills. Keep practicing to maintain this level."
        elif avg >= 60:
            return "Good attempt! Your solution shows understanding of the core concepts. Focus on optimizing time complexity and handling edge cases."
        else:
            return "Keep practicing! Try breaking down the problem into smaller steps. Consider the data structures that might help solve this efficiently."
    
    # ============ Behavioral Evaluation ============
    
    async def evaluate_behavioral(
        self,
        question: Dict[str, Any],
        answer: str,
        time_taken: int
    ) -> Dict[str, Any]:
        """
        Evaluate behavioral answer.
        
        Scoring formula:
        overall = (STAR_score * 0.4) + (depth_score * 0.3) + (relevance * 0.3)
        """
        breakdown = {}
        strengths = []
        improvements = []
        
        # 1. STAR Format (40%)
        star_score, star_details = self._evaluate_star_format(answer)
        breakdown["star_format"] = star_score
        if star_score >= 80:
            strengths.append("Excellent STAR format structure")
        elif star_score < 50:
            improvements.append("Structure your answer using STAR: Situation, Task, Action, Result")
        
        # 2. Depth/Detail (30%)
        depth_score = self._evaluate_answer_depth(answer)
        breakdown["depth"] = depth_score
        if depth_score >= 80:
            strengths.append("Detailed with specific examples")
        elif depth_score < 50:
            improvements.append("Add more specific details, metrics, and examples")
        
        # 3. Relevance (30%)
        relevance = self._evaluate_behavioral_relevance(question, answer)
        breakdown["relevance"] = relevance
        if relevance >= 80:
            strengths.append("Directly addressed the question theme")
        elif relevance < 50:
            improvements.append("Focus more on the specific theme being asked about")
        
        # Calculate overall
        overall = (star_score * 0.4) + (depth_score * 0.3) + (relevance * 0.3)
        
        # Generate feedback
        feedback = await self._generate_behavioral_feedback(question, answer, breakdown, star_details)
        
        return {
            "score": round(overall, 1),
            "breakdown": breakdown,
            "feedback": feedback,
            "strengths": strengths[:3],
            "improvements": improvements[:3],
            "grade": self._score_to_grade(overall),
            "star_analysis": star_details
        }
    
    def _evaluate_star_format(self, answer: str) -> Tuple[float, Dict[str, bool]]:
        """Check if answer follows STAR format."""
        answer_lower = answer.lower()
        
        star_components = {
            "situation": False,
            "task": False,
            "action": False,
            "result": False
        }
        
        # Situation indicators
        situation_patterns = [
            r'situation', r'context', r'background', r'there was', r'when i was',
            r'at my', r'in my previous', r'while working', r'during'
        ]
        if any(re.search(p, answer_lower) for p in situation_patterns):
            star_components["situation"] = True
        
        # Task indicators
        task_patterns = [
            r'task', r'goal', r'objective', r'needed to', r'had to', r'responsible',
            r'my role', r'challenge was', r'problem was'
        ]
        if any(re.search(p, answer_lower) for p in task_patterns):
            star_components["task"] = True
        
        # Action indicators
        action_patterns = [
            r'action', r'i did', r'i took', r'i decided', r'i implemented',
            r'i created', r'i led', r'i developed', r'i worked', r'approach'
        ]
        if any(re.search(p, answer_lower) for p in action_patterns):
            star_components["action"] = True
        
        # Result indicators
        result_patterns = [
            r'result', r'outcome', r'impact', r'achieved', r'delivered',
            r'improved', r'increased', r'reduced', r'led to', r'successfully',
            r'\d+%', r'metric'
        ]
        if any(re.search(p, answer_lower) for p in result_patterns):
            star_components["result"] = True
        
        # Calculate score
        components_present = sum(star_components.values())
        score = (components_present / 4) * 100
        
        # Bonus for explicit STAR labels
        if 'situation:' in answer_lower or 'task:' in answer_lower:
            score = min(100, score + 10)
        
        return score, star_components
    
    def _evaluate_answer_depth(self, answer: str) -> float:
        """Evaluate answer depth and detail."""
        score = 50
        
        word_count = len(answer.split())
        
        # Word count scoring
        if word_count >= 200:
            score += 20
        elif word_count >= 100:
            score += 10
        elif word_count < 50:
            score -= 20
        
        # Check for specifics
        # Numbers/metrics
        if re.search(r'\d+', answer):
            score += 10
        
        # Specific examples (names, tools, technologies)
        proper_nouns = len(re.findall(r'\b[A-Z][a-z]+\b', answer))
        if proper_nouns >= 3:
            score += 10
        
        # Multiple actions (and, then, also, additionally)
        connectors = len(re.findall(r'\band\b|\bthen\b|\balso\b|\badditionally\b', answer.lower()))
        if connectors >= 2:
            score += 5
        
        return min(100, max(0, score))
    
    def _evaluate_behavioral_relevance(self, question: Dict[str, Any], answer: str) -> float:
        """Evaluate if answer is relevant to question theme."""
        theme = question.get("theme", "").lower()
        key_points = question.get("key_points", [])
        
        score = 60  # Base
        answer_lower = answer.lower()
        
        # Check for theme keywords
        if theme and theme in answer_lower:
            score += 15
        
        # Check for key points mentioned
        for point in key_points:
            if any(word in answer_lower for word in point.lower().split()):
                score += 10
        
        return min(100, score)
    
    async def _generate_behavioral_feedback(
        self,
        question: Dict[str, Any],
        answer: str,
        breakdown: Dict[str, float],
        star_details: Dict[str, bool]
    ) -> str:
        """Generate feedback for behavioral answer."""
        missing_star = [k for k, v in star_details.items() if not v]
        
        if breakdown.get("star_format", 0) >= 80:
            feedback = "Excellent use of STAR format! Your answer was well-structured. "
        else:
            feedback = f"Consider adding clearer {', '.join(missing_star)} sections. "
        
        if breakdown.get("depth", 0) >= 80:
            feedback += "Great specific details and metrics. "
        else:
            feedback += "Add more specific examples and quantifiable results. "
        
        return feedback[:300]
    
    # ============ System Design Evaluation ============
    
    async def evaluate_design(
        self,
        question: Dict[str, Any],
        answer: str,
        time_taken: int
    ) -> Dict[str, Any]:
        """
        Evaluate system design answer.
        
        Scoring:
        overall = (architecture * 0.35) + (scalability * 0.25) + (tradeoffs * 0.25) + (clarity * 0.15)
        """
        breakdown = {}
        strengths = []
        improvements = []
        
        expected_components = question.get("expected_components", [])
        discussion_points = question.get("discussion_points", [])
        
        # 1. Architecture (35%)
        architecture = self._evaluate_architecture(answer, expected_components)
        breakdown["architecture"] = architecture
        if architecture >= 80:
            strengths.append("Comprehensive architecture discussion")
        elif architecture < 50:
            improvements.append("Discuss more components: database, cache, load balancer, etc.")
        
        # 2. Scalability (25%)
        scalability = self._evaluate_scalability(answer)
        breakdown["scalability"] = scalability
        if scalability >= 80:
            strengths.append("Good scalability considerations")
        elif scalability < 50:
            improvements.append("Address how the system handles scale and high traffic")
        
        # 3. Tradeoffs (25%)
        tradeoffs = self._evaluate_tradeoffs(answer, discussion_points)
        breakdown["tradeoffs"] = tradeoffs
        if tradeoffs >= 80:
            strengths.append("Discussed important tradeoffs")
        elif tradeoffs < 50:
            improvements.append("Discuss tradeoffs between different design choices")
        
        # 4. Clarity (15%)
        clarity = self._evaluate_clarity(answer)
        breakdown["clarity"] = clarity
        if clarity >= 80:
            strengths.append("Clear and organized explanation")
        elif clarity < 50:
            improvements.append("Structure your answer with clear sections")
        
        overall = (
            architecture * 0.35 +
            scalability * 0.25 +
            tradeoffs * 0.25 +
            clarity * 0.15
        )
        
        feedback = await self._generate_design_feedback(question, answer, breakdown)
        
        return {
            "score": round(overall, 1),
            "breakdown": breakdown,
            "feedback": feedback,
            "strengths": strengths[:3],
            "improvements": improvements[:3],
            "grade": self._score_to_grade(overall)
        }
    
    def _evaluate_architecture(self, answer: str, expected_components: List[str]) -> float:
        """Evaluate architecture discussion."""
        score = 40
        answer_lower = answer.lower()
        
        # General architecture keywords
        architecture_keywords = [
            "database", "cache", "redis", "cdn", "load balancer", "api", "server",
            "frontend", "backend", "microservice", "queue", "message", "storage",
            "partition", "replica", "shard", "index"
        ]
        
        found = sum(1 for kw in architecture_keywords if kw in answer_lower)
        score += min(30, found * 5)
        
        # Check expected components
        if expected_components:
            found_expected = sum(1 for c in expected_components if c.lower() in answer_lower)
            score += (found_expected / len(expected_components)) * 30
        
        return min(100, score)
    
    def _evaluate_scalability(self, answer: str) -> float:
        """Evaluate scalability discussion."""
        answer_lower = answer.lower()
        score = 40
        
        scalability_keywords = [
            "scale", "million", "billion", "concurrent", "throughput", "latency",
            "horizontal", "vertical", "partition", "shard", "replica", "cache",
            "distributed", "load balance", "bottleneck", "traffic"
        ]
        
        found = sum(1 for kw in scalability_keywords if kw in answer_lower)
        score += min(60, found * 10)
        
        return min(100, score)
    
    def _evaluate_tradeoffs(self, answer: str, discussion_points: List[str]) -> float:
        """Evaluate tradeoff discussion."""
        answer_lower = answer.lower()
        score = 40
        
        tradeoff_keywords = [
            "tradeoff", "trade-off", "vs", "versus", "however", "but", "alternatively",
            "pros and cons", "advantage", "disadvantage", "consider", "depend"
        ]
        
        found = sum(1 for kw in tradeoff_keywords if kw in answer_lower)
        score += min(30, found * 10)
        
        # Check discussion points
        if discussion_points:
            found_points = sum(1 for p in discussion_points if any(w in answer_lower for w in p.lower().split()))
            score += (found_points / len(discussion_points)) * 30
        
        return min(100, score)
    
    def _evaluate_clarity(self, answer: str) -> float:
        """Evaluate clarity and organization."""
        score = 50
        
        # Length check
        word_count = len(answer.split())
        if 200 <= word_count <= 1000:
            score += 15
        
        # Has structure (numbered points, sections)
        if re.search(r'\d[\.\):]|\n-|\n\*|step|first|second|then|finally', answer.lower()):
            score += 20
        
        # Not too many run-on sentences
        sentences = answer.split('.')
        avg_sentence_length = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
        if avg_sentence_length <= 25:
            score += 15
        
        return min(100, score)
    
    async def _generate_design_feedback(
        self,
        question: Dict[str, Any],
        answer: str,
        breakdown: Dict[str, float]
    ) -> str:
        """Generate design feedback."""
        avg = sum(breakdown.values()) / len(breakdown)
        
        if avg >= 80:
            return "Excellent system design! You covered architecture, scalability, and tradeoffs comprehensively."
        elif avg >= 60:
            return "Good design approach! Consider diving deeper into scalability challenges and discussing more tradeoffs."
        else:
            return "Focus on the high-level architecture first, then discuss how each component scales and what tradeoffs you made."
    
    # ============ Technical Evaluation ============
    
    async def evaluate_technical(
        self,
        question: Dict[str, Any],
        answer: str,
        time_taken: int
    ) -> Dict[str, Any]:
        """
        Evaluate technical/project-based answer.
        
        Scoring:
        overall = (clarity * 0.35) + (depth * 0.35) + (accuracy * 0.30)
        """
        breakdown = {}
        strengths = []
        improvements = []
        
        # 1. Clarity (35%)
        clarity = self._evaluate_clarity(answer)
        breakdown["clarity"] = clarity
        if clarity >= 80:
            strengths.append("Clear explanation")
        elif clarity < 50:
            improvements.append("Explain concepts more clearly")
        
        # 2. Technical Depth (35%)
        depth = self._evaluate_technical_depth(answer)
        breakdown["depth"] = depth
        if depth >= 80:
            strengths.append("Good technical depth")
        elif depth < 50:
            improvements.append("Go deeper into technical details")
        
        # 3. Accuracy (30%)
        accuracy = self._evaluate_technical_accuracy(answer)
        breakdown["accuracy"] = accuracy
        if accuracy >= 80:
            strengths.append("Accurate technical terminology")
        elif accuracy < 50:
            improvements.append("Verify technical terms and concepts")
        
        overall = (clarity * 0.35) + (depth * 0.35) + (accuracy * 0.30)
        
        feedback = f"Your explanation demonstrates {'strong' if overall >= 70 else 'developing'} technical knowledge. "
        if overall < 70:
            feedback += "Practice explaining your projects to others to improve clarity."
        
        return {
            "score": round(overall, 1),
            "breakdown": breakdown,
            "feedback": feedback,
            "strengths": strengths[:3],
            "improvements": improvements[:3],
            "grade": self._score_to_grade(overall)
        }
    
    def _evaluate_technical_depth(self, answer: str) -> float:
        """Evaluate technical depth of answer."""
        score = 50
        answer_lower = answer.lower()
        
        # Technical terms
        tech_terms = [
            "api", "database", "cache", "server", "client", "http", "rest", "graphql",
            "authentication", "authorization", "encryption", "hash", "algorithm",
            "framework", "library", "architect", "deploy", "docker", "kubernetes",
            "aws", "azure", "gcp", "microservice", "monolith", "queue", "async"
        ]
        
        found = sum(1 for t in tech_terms if t in answer_lower)
        score += min(30, found * 5)
        
        # Multiple levels of detail
        word_count = len(answer.split())
        if word_count >= 150:
            score += 20
        elif word_count >= 100:
            score += 10
        
        return min(100, score)
    
    def _evaluate_technical_accuracy(self, answer: str) -> float:
        """Estimate technical accuracy (heuristic)."""
        # This is a simplified check - in production, use AI
        score = 60
        
        # Check for code or technical specifics
        if re.search(r'\b(function|class|api|http|json|sql)\b', answer.lower()):
            score += 15
        
        # Check for frameworks/tools mentioned
        if re.search(r'\b(react|node|python|java|spring|django|flask)\b', answer.lower()):
            score += 15
        
        # Check for numbers/metrics
        if re.search(r'\d+', answer):
            score += 10
        
        return min(100, score)
    
    # ============ Generic Evaluation ============
    
    async def evaluate_generic(
        self,
        question: Dict[str, Any],
        answer: str
    ) -> Dict[str, Any]:
        """Fallback generic evaluation."""
        depth = self._evaluate_answer_depth(answer)
        clarity = self._evaluate_clarity(answer)
        
        overall = (depth + clarity) / 2
        
        return {
            "score": round(overall, 1),
            "breakdown": {"depth": depth, "clarity": clarity},
            "feedback": "Thank you for your response. Consider adding more specific examples and structure.",
            "strengths": ["Provided a response"],
            "improvements": ["Add more detail", "Use specific examples"],
            "grade": self._score_to_grade(overall)
        }
    
    # ============ Helpers ============
    
    def _score_to_grade(self, score: float) -> str:
        """Convert score to letter grade."""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"


# Singleton instance
answer_evaluator = AnswerEvaluator()
