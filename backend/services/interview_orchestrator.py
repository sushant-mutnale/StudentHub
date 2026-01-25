"""
Interview Session Orchestrator
The "brain" that manages interview flow, question selection, and adaptive difficulty.
Features: Session management, round progression, difficulty adaptation, AI evaluation.
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from enum import Enum
import asyncio
import random

from bson import ObjectId

from ..database import get_database
from .company_research import company_researcher


class SessionStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class RoundType(str, Enum):
    DSA = "dsa"
    BEHAVIORAL = "behavioral"
    SYSTEM_DESIGN = "system_design"
    CODING = "coding"
    HR = "hr"
    TECHNICAL = "technical"


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class InterviewOrchestrator:
    """
    Orchestrates interview sessions with adaptive questioning.
    """
    
    def __init__(self):
        self._llm_service = None
        self.questions_per_round = 2
        self.min_questions_per_round = 2
        self.max_questions_per_round = 4
    
    def _get_llm_service(self):
        """Lazy load LLM service."""
        if self._llm_service is None:
            try:
                from .llm_service import llm_service
                self._llm_service = llm_service
            except Exception:
                self._llm_service = None
        return self._llm_service
    
    def _sessions_collection(self):
        return get_database()["interview_sessions"]
    
    def _questions_collection(self):
        return get_database()["interview_questions"]
    
    def _answers_collection(self):
        return get_database()["interview_answers"]
    
    # ============ Session Management ============
    
    async def create_session(
        self,
        student_id: str,
        company: str,
        role: str,
        resume_id: Optional[str] = None,
        jd_text: Optional[str] = None,
        parsed_jd: Optional[Dict] = None,
        parsed_resume: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create a new interview session.
        Initializes rounds based on company interview pattern.
        """
        # Get company interview pattern
        company_pattern = await company_researcher.get_company_interview_pattern(company, role)
        
        # Build rounds from company pattern
        rounds = []
        for round_info in company_pattern.get("rounds", []):
            round_type = round_info.get("type", "coding")
            # Normalize round type
            if "dsa" in round_type.lower() or "coding" in round_type.lower():
                round_type = RoundType.DSA
            elif "behavioral" in round_type.lower() or "hr" in round_type.lower():
                round_type = RoundType.BEHAVIORAL
            elif "design" in round_type.lower():
                round_type = RoundType.SYSTEM_DESIGN
            else:
                round_type = RoundType.TECHNICAL
            
            rounds.append({
                "round_num": round_info.get("round", len(rounds)),
                "type": round_type,
                "name": round_info.get("name", f"Round {len(rounds) + 1}"),
                "duration_minutes": round_info.get("duration", 60),
                "questions_answered": 0,
                "questions": [],  # Will store question IDs
                "score": 0,
                "status": "pending"
            })
        
        # If no rounds from company, use default
        if not rounds:
            rounds = [
                {"round_num": 0, "type": RoundType.DSA, "name": "Coding Round", "duration_minutes": 60, "questions_answered": 0, "questions": [], "score": 0, "status": "pending"},
                {"round_num": 1, "type": RoundType.SYSTEM_DESIGN, "name": "System Design", "duration_minutes": 45, "questions_answered": 0, "questions": [], "score": 0, "status": "pending"},
                {"round_num": 2, "type": RoundType.BEHAVIORAL, "name": "Behavioral", "duration_minutes": 30, "questions_answered": 0, "questions": [], "score": 0, "status": "pending"},
            ]
        
        session_doc = {
            "student_id": ObjectId(student_id),
            "company": company,
            "role": role,
            "status": SessionStatus.NOT_STARTED,
            "current_round": 0,
            "current_difficulty": Difficulty.MEDIUM,
            "rounds": rounds,
            "total_rounds": len(rounds),
            "resume_id": ObjectId(resume_id) if resume_id else None,
            "parsed_resume": parsed_resume or {},
            "jd_text": jd_text or "",
            "parsed_jd": parsed_jd or {},
            "overall_score": 0,
            "total_questions_answered": 0,
            "total_time_spent_seconds": 0,
            "strengths": [],
            "weaknesses": [],
            "dsa_topics": company_pattern.get("dsa_topics", []),
            "behavioral_themes": company_pattern.get("behavioral_themes", []),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "started_at": None,
            "completed_at": None,
        }
        
        result = await self._sessions_collection().insert_one(session_doc)
        session_id = str(result.inserted_id)
        
        return {
            "session_id": session_id,
            "company": company,
            "role": role,
            "total_rounds": len(rounds),
            "rounds_preview": [{"name": r["name"], "type": r["type"]} for r in rounds],
            "status": SessionStatus.NOT_STARTED,
            "estimated_duration_minutes": sum(r["duration_minutes"] for r in rounds),
        }
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID."""
        if not ObjectId.is_valid(session_id):
            return None
        
        doc = await self._sessions_collection().find_one({"_id": ObjectId(session_id)})
        if doc:
            doc["_id"] = str(doc["_id"])
            doc["student_id"] = str(doc["student_id"])
            if doc.get("resume_id"):
                doc["resume_id"] = str(doc["resume_id"])
        return doc
    
    async def start_session(self, session_id: str) -> Dict[str, Any]:
        """
        Start an interview session.
        Returns the first question.
        """
        session = await self.get_session(session_id)
        if not session:
            return {"error": "Session not found"}
        
        if session["status"] == SessionStatus.COMPLETED:
            return {"error": "Session already completed"}
        
        # Update session status
        await self._sessions_collection().update_one(
            {"_id": ObjectId(session_id)},
            {
                "$set": {
                    "status": SessionStatus.IN_PROGRESS,
                    "started_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        # Get first question
        first_question = await self.get_next_question(session_id)
        
        return {
            "session_id": session_id,
            "status": SessionStatus.IN_PROGRESS,
            "current_round": session["rounds"][0]["name"],
            "first_question": first_question,
            "message": "Interview started. Good luck!"
        }
    
    # ============ Question Selection ============
    
    async def get_next_question(self, session_id: str) -> Dict[str, Any]:
        """
        Get the next question based on orchestrator logic.
        """
        session = await self.get_session(session_id)
        if not session:
            return {"error": "Session not found"}
        
        current_round = session["current_round"]
        total_rounds = session["total_rounds"]
        
        # Check if interview is complete
        if current_round >= total_rounds:
            return {
                "interview_completed": True,
                "message": "Interview completed! Generating report...",
                "next_action": "get_report"
            }
        
        round_data = session["rounds"][current_round]
        round_type = round_data["type"]
        difficulty = session.get("current_difficulty", Difficulty.MEDIUM)
        
        # Generate question based on round type
        question = await self._generate_question(
            session=session,
            round_type=round_type,
            difficulty=difficulty
        )
        
        # Store question
        question_doc = {
            "session_id": ObjectId(session_id),
            "round_num": current_round,
            "round_type": round_type,
            "difficulty": difficulty,
            "question_text": question["question"],
            "question_type": question.get("type", round_type),
            "hints": question.get("hints", []),
            "expected_answer_points": question.get("expected_points", []),
            "time_limit_seconds": question.get("time_limit", 1800),
            "created_at": datetime.utcnow(),
            "answered": False,
        }
        
        result = await self._questions_collection().insert_one(question_doc)
        question_id = str(result.inserted_id)
        
        # Update session with question
        await self._sessions_collection().update_one(
            {"_id": ObjectId(session_id)},
            {
                "$push": {f"rounds.{current_round}.questions": question_id},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        return {
            "question_id": question_id,
            "round": round_data["name"],
            "round_num": current_round,
            "question_type": round_type,
            "difficulty": difficulty,
            "question": question["question"],
            "hints": question.get("hints", []),
            "time_limit_seconds": question.get("time_limit", 1800),
            "questions_in_round": round_data["questions_answered"],
            "interview_completed": False
        }
    
    async def _generate_question(
        self,
        session: Dict[str, Any],
        round_type: str,
        difficulty: str
    ) -> Dict[str, Any]:
        """Generate a question using AI or templates."""
        company = session.get("company", "")
        role = session.get("role", "Software Engineer")
        dsa_topics = session.get("dsa_topics", [])
        behavioral_themes = session.get("behavioral_themes", [])
        resume_skills = session.get("parsed_resume", {}).get("skills", [])
        
        llm = self._get_llm_service()
        
        if llm:
            try:
                return await self._generate_ai_question(
                    round_type, difficulty, company, role,
                    dsa_topics, behavioral_themes, resume_skills
                )
            except Exception:
                pass
        
        # Fallback to template questions
        return self._get_template_question(round_type, difficulty, dsa_topics, behavioral_themes)
    
    async def _generate_ai_question(
        self,
        round_type: str,
        difficulty: str,
        company: str,
        role: str,
        dsa_topics: List[str],
        behavioral_themes: List[str],
        resume_skills: List[str]
    ) -> Dict[str, Any]:
        """Generate question using AI."""
        llm = self._get_llm_service()
        
        if round_type == RoundType.DSA or round_type == "dsa":
            topic = random.choice(dsa_topics) if dsa_topics else "arrays"
            prompt = f"""Generate a {difficulty} level coding/DSA interview question for {company} {role} position.

Topic: {topic}
Candidate knows: {', '.join(resume_skills[:5]) if resume_skills else 'general programming'}

Respond in this EXACT format:
QUESTION: [The complete question with examples]
HINTS: [Hint 1] | [Hint 2]
EXPECTED_POINTS: [Key point 1] | [Key point 2] | [Key point 3]
TIME_LIMIT: [time in seconds, e.g., 1800]"""

        elif round_type == RoundType.BEHAVIORAL or round_type == "behavioral":
            theme = random.choice(behavioral_themes) if behavioral_themes else "teamwork"
            prompt = f"""Generate a behavioral interview question for {company} {role} position.

Focus theme: {theme}
Company values: {', '.join(behavioral_themes[:3]) if behavioral_themes else 'general values'}

Respond in this EXACT format:
QUESTION: [The behavioral question using STAR method prompt]
HINTS: [What to focus on] | [Example structure]
EXPECTED_POINTS: [Key point 1] | [Key point 2] | [Key point 3]
TIME_LIMIT: [time in seconds, e.g., 600]"""

        else:  # System design
            prompt = f"""Generate a {difficulty} system design question for {company} {role} position.

Respond in this EXACT format:
QUESTION: [The system design question with scope and requirements]
HINTS: [Hint 1] | [Hint 2]
EXPECTED_POINTS: [Key point 1] | [Key point 2] | [Key point 3]
TIME_LIMIT: [time in seconds, e.g., 2700]"""

        response = await llm.generate(prompt)
        return self._parse_ai_question_response(response, round_type, difficulty)
    
    def _parse_ai_question_response(
        self,
        response: str,
        round_type: str,
        difficulty: str
    ) -> Dict[str, Any]:
        """Parse AI-generated question response."""
        question = {
            "question": "",
            "type": round_type,
            "difficulty": difficulty,
            "hints": [],
            "expected_points": [],
            "time_limit": 1800
        }
        
        lines = response.split("\n")
        for line in lines:
            line = line.strip()
            
            if line.upper().startswith("QUESTION:"):
                question["question"] = line[9:].strip()
            elif line.upper().startswith("HINTS:"):
                hints = line[6:].strip().split("|")
                question["hints"] = [h.strip() for h in hints if h.strip()]
            elif line.upper().startswith("EXPECTED_POINTS:"):
                points = line[16:].strip().split("|")
                question["expected_points"] = [p.strip() for p in points if p.strip()]
            elif line.upper().startswith("TIME_LIMIT:"):
                try:
                    question["time_limit"] = int(line[11:].strip())
                except ValueError:
                    pass
        
        # Fallback if parsing failed
        if not question["question"]:
            question["question"] = response[:500]
        
        return question
    
    def _get_template_question(
        self,
        round_type: str,
        difficulty: str,
        dsa_topics: List[str],
        behavioral_themes: List[str]
    ) -> Dict[str, Any]:
        """Get a template question as fallback."""
        
        if round_type == RoundType.DSA or round_type == "dsa":
            questions = {
                "easy": [
                    {"question": "Given an array of integers, find two numbers that add up to a target sum. Return their indices.", "hints": ["Use a hash map", "One pass solution exists"], "expected_points": ["Hash map approach", "O(n) time complexity", "Handle edge cases"], "time_limit": 1200},
                    {"question": "Reverse a linked list iteratively.", "hints": ["Use three pointers", "Think about what changes at each step"], "expected_points": ["Pointer manipulation", "Iterative approach", "Handle empty list"], "time_limit": 900},
                ],
                "medium": [
                    {"question": "Given a binary tree, return the level order traversal of its nodes' values.", "hints": ["BFS approach", "Use a queue"], "expected_points": ["BFS implementation", "Queue usage", "Level separation"], "time_limit": 1500},
                    {"question": "Implement an LRU Cache with get and put operations in O(1) time.", "hints": ["Hash map + doubly linked list", "OrderedDict in Python"], "expected_points": ["Data structure choice", "O(1) operations", "Eviction logic"], "time_limit": 1800},
                ],
                "hard": [
                    {"question": "Given a string, find the length of the longest substring without repeating characters.", "hints": ["Sliding window", "Hash set for tracking"], "expected_points": ["Sliding window technique", "Hash set usage", "Optimal O(n) solution"], "time_limit": 1800},
                    {"question": "Serialize and deserialize a binary tree.", "hints": ["Use preorder traversal", "Handle null nodes"], "expected_points": ["Traversal choice", "Null handling", "Reconstruct logic"], "time_limit": 2400},
                ]
            }
            pool = questions.get(difficulty, questions["medium"])
            
        elif round_type == RoundType.BEHAVIORAL or round_type == "behavioral":
            questions = [
                {"question": "Tell me about a time when you had to work with a difficult team member. How did you handle it?", "hints": ["Use STAR method", "Focus on resolution"], "expected_points": ["Situation clarity", "Actions taken", "Positive outcome"], "time_limit": 600},
                {"question": "Describe a project where you had to learn something new quickly. How did you approach it?", "hints": ["Be specific", "Show learning process"], "expected_points": ["Learning strategy", "Adaptation", "Result achieved"], "time_limit": 600},
                {"question": "Tell me about a time you failed. What did you learn from it?", "hints": ["Be honest", "Focus on learning"], "expected_points": ["Honest failure", "Learning identified", "Applied lessons"], "time_limit": 600},
            ]
            pool = questions
            
        else:  # System design
            questions = [
                {"question": "Design a URL shortening service like bit.ly.", "hints": ["Consider scale", "Hash function choice"], "expected_points": ["Hash generation", "Database design", "Scalability"], "time_limit": 2700},
                {"question": "Design a real-time chat application.", "hints": ["WebSockets vs polling", "Message storage"], "expected_points": ["Real-time communication", "Message persistence", "Scalability"], "time_limit": 2700},
                {"question": "Design a rate limiter for an API.", "hints": ["Token bucket vs sliding window", "Distributed considerations"], "expected_points": ["Algorithm choice", "Storage", "Distributed handling"], "time_limit": 2400},
            ]
            pool = questions
        
        return random.choice(pool)
    
    # ============ Answer Evaluation ============
    
    async def submit_answer(
        self,
        session_id: str,
        question_id: str,
        answer: str,
        time_taken_seconds: int,
        code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit and evaluate an answer.
        Decides next action (next question, next round, or complete).
        """
        session = await self.get_session(session_id)
        if not session:
            return {"error": "Session not found"}
        
        if session["status"] == SessionStatus.COMPLETED:
            return {"error": "Session already completed"}
        
        # Get question
        question_doc = await self._questions_collection().find_one(
            {"_id": ObjectId(question_id)}
        )
        if not question_doc:
            return {"error": "Question not found"}
        
        # Evaluate answer
        evaluation = await self._evaluate_answer(
            question=question_doc,
            answer=answer,
            code=code,
            session=session
        )
        
        # Store answer
        answer_doc = {
            "session_id": ObjectId(session_id),
            "question_id": ObjectId(question_id),
            "answer_text": answer,
            "code": code,
            "time_taken_seconds": time_taken_seconds,
            "score": evaluation["score"],
            "feedback": evaluation["feedback"],
            "strengths": evaluation.get("strengths", []),
            "improvements": evaluation.get("improvements", []),
            "created_at": datetime.utcnow()
        }
        await self._answers_collection().insert_one(answer_doc)
        
        # Mark question as answered
        await self._questions_collection().update_one(
            {"_id": ObjectId(question_id)},
            {"$set": {"answered": True, "score": evaluation["score"]}}
        )
        
        # Update session
        current_round = session["current_round"]
        await self._sessions_collection().update_one(
            {"_id": ObjectId(session_id)},
            {
                "$inc": {
                    f"rounds.{current_round}.questions_answered": 1,
                    "total_questions_answered": 1,
                    "total_time_spent_seconds": time_taken_seconds
                },
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        # Adapt difficulty
        new_difficulty = self._adapt_difficulty(evaluation["score"], session.get("current_difficulty", Difficulty.MEDIUM))
        if new_difficulty != session.get("current_difficulty"):
            await self._sessions_collection().update_one(
                {"_id": ObjectId(session_id)},
                {"$set": {"current_difficulty": new_difficulty}}
            )
        
        # Decide next action
        next_action = await self._decide_next_action(session_id)
        
        return {
            "evaluation": evaluation,
            "next_action": next_action,
            "new_difficulty": new_difficulty
        }
    
    async def _evaluate_answer(
        self,
        question: Dict[str, Any],
        answer: str,
        code: Optional[str],
        session: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate an answer using AI or rule-based logic."""
        llm = self._get_llm_service()
        
        if llm:
            try:
                return await self._ai_evaluate_answer(question, answer, code)
            except Exception:
                pass
        
        # Fallback: simple rule-based evaluation
        return self._rule_based_evaluate(question, answer, code)
    
    async def _ai_evaluate_answer(
        self,
        question: Dict[str, Any],
        answer: str,
        code: Optional[str]
    ) -> Dict[str, Any]:
        """AI-powered answer evaluation."""
        llm = self._get_llm_service()
        
        expected_points = question.get("expected_answer_points", [])
        
        prompt = f"""Evaluate this interview answer.

QUESTION: {question.get('question_text', '')}

CANDIDATE'S ANSWER:
{answer}

{f'CODE PROVIDED: {code[:1000]}' if code else ''}

EXPECTED KEY POINTS: {', '.join(expected_points) if expected_points else 'General correctness and clarity'}

Evaluate and respond in EXACTLY this format:
SCORE: [0-100]
FEEDBACK: [2-3 sentences of overall feedback]
STRENGTHS: [strength 1] | [strength 2]
IMPROVEMENTS: [improvement 1] | [improvement 2]"""

        response = await llm.generate(prompt)
        return self._parse_evaluation_response(response)
    
    def _parse_evaluation_response(self, response: str) -> Dict[str, Any]:
        """Parse AI evaluation response."""
        result = {
            "score": 50,
            "feedback": "",
            "strengths": [],
            "improvements": []
        }
        
        lines = response.split("\n")
        for line in lines:
            line = line.strip()
            
            if line.upper().startswith("SCORE:"):
                try:
                    score = int(line[6:].strip().replace("%", ""))
                    result["score"] = min(100, max(0, score))
                except ValueError:
                    pass
            elif line.upper().startswith("FEEDBACK:"):
                result["feedback"] = line[9:].strip()
            elif line.upper().startswith("STRENGTHS:"):
                strengths = line[10:].strip().split("|")
                result["strengths"] = [s.strip() for s in strengths if s.strip()]
            elif line.upper().startswith("IMPROVEMENTS:"):
                improvements = line[13:].strip().split("|")
                result["improvements"] = [i.strip() for i in improvements if i.strip()]
        
        return result
    
    def _rule_based_evaluate(
        self,
        question: Dict[str, Any],
        answer: str,
        code: Optional[str]
    ) -> Dict[str, Any]:
        """Simple rule-based evaluation as fallback."""
        score = 50
        feedback = ""
        strengths = []
        improvements = []
        
        # Check answer length
        if len(answer) > 200:
            score += 10
            strengths.append("Detailed answer")
        elif len(answer) < 50:
            score -= 10
            improvements.append("Provide more detail")
        
        # Check for code if DSA question
        if question.get("round_type") in ["dsa", RoundType.DSA]:
            if code and len(code) > 50:
                score += 15
                strengths.append("Provided code solution")
            else:
                improvements.append("Include working code")
        
        # Check for expected points
        expected = question.get("expected_answer_points", [])
        matched = 0
        for point in expected:
            if point.lower() in answer.lower():
                matched += 1
        
        if expected:
            match_rate = matched / len(expected)
            score += int(match_rate * 30)
            if match_rate > 0.5:
                strengths.append("Covered key points")
            else:
                improvements.append("Address more key concepts")
        
        score = min(100, max(0, score))
        feedback = f"Your answer scored {score}%. " + ("Great job!" if score >= 70 else "There's room for improvement.")
        
        return {
            "score": score,
            "feedback": feedback,
            "strengths": strengths,
            "improvements": improvements
        }
    
    def _adapt_difficulty(self, score: int, current_difficulty: str) -> str:
        """Adapt difficulty based on performance."""
        if score >= 80:
            if current_difficulty == Difficulty.EASY:
                return Difficulty.MEDIUM
            elif current_difficulty == Difficulty.MEDIUM:
                return Difficulty.HARD
        elif score < 50:
            if current_difficulty == Difficulty.HARD:
                return Difficulty.MEDIUM
            elif current_difficulty == Difficulty.MEDIUM:
                return Difficulty.EASY
        
        return current_difficulty
    
    # ============ Round & Session Progression ============
    
    async def _decide_next_action(self, session_id: str) -> Dict[str, Any]:
        """Decide what happens next: next question, next round, or complete."""
        session = await self.get_session(session_id)
        if not session:
            return {"action": "error", "message": "Session not found"}
        
        current_round = session["current_round"]
        total_rounds = session["total_rounds"]
        rounds = session["rounds"]
        
        if current_round >= total_rounds:
            # Complete interview
            await self._complete_session(session_id)
            return {
                "action": "interview_completed",
                "message": "Interview completed! View your report."
            }
        
        questions_in_round = rounds[current_round]["questions_answered"]
        
        if questions_in_round >= self.min_questions_per_round:
            # Move to next round
            if current_round + 1 >= total_rounds:
                await self._complete_session(session_id)
                return {
                    "action": "interview_completed",
                    "message": "Interview completed! View your report."
                }
            
            # Update round score before moving
            await self._calculate_round_score(session_id, current_round)
            
            # Advance to next round
            await self._sessions_collection().update_one(
                {"_id": ObjectId(session_id)},
                {
                    "$set": {
                        f"rounds.{current_round}.status": "completed",
                        "current_round": current_round + 1,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            next_round = rounds[current_round + 1] if current_round + 1 < len(rounds) else None
            return {
                "action": "next_round",
                "message": f"Moving to next round: {next_round['name'] if next_round else 'Final'}",
                "next_round": next_round["name"] if next_round else None,
                "next_round_type": next_round["type"] if next_round else None
            }
        else:
            return {
                "action": "next_question",
                "message": "Get the next question",
                "questions_remaining": self.min_questions_per_round - questions_in_round
            }
    
    async def _calculate_round_score(self, session_id: str, round_num: int):
        """Calculate and update round score."""
        # Get all answers for this round
        answers = await self._answers_collection().find({
            "session_id": ObjectId(session_id)
        }).to_list(100)
        
        # Get questions for this round
        session = await self.get_session(session_id)
        round_questions = session["rounds"][round_num].get("questions", [])
        
        # Calculate average score for round
        round_scores = []
        for answer in answers:
            if str(answer["question_id"]) in round_questions:
                round_scores.append(answer.get("score", 0))
        
        avg_score = sum(round_scores) / len(round_scores) if round_scores else 0
        
        await self._sessions_collection().update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {f"rounds.{round_num}.score": round(avg_score, 1)}}
        )
    
    async def _complete_session(self, session_id: str):
        """Mark session as completed and calculate final scores."""
        session = await self.get_session(session_id)
        if not session:
            return
        
        # Calculate overall score
        total_score = 0
        scored_rounds = 0
        
        for round_data in session["rounds"]:
            if round_data.get("score", 0) > 0:
                total_score += round_data["score"]
                scored_rounds += 1
        
        overall_score = total_score / scored_rounds if scored_rounds > 0 else 0
        
        # Get all answers to analyze strengths/weaknesses
        answers = await self._answers_collection().find({
            "session_id": ObjectId(session_id)
        }).to_list(100)
        
        strengths = []
        weaknesses = []
        
        for answer in answers:
            strengths.extend(answer.get("strengths", []))
            weaknesses.extend(answer.get("improvements", []))
        
        # Deduplicate and limit
        strengths = list(set(strengths))[:5]
        weaknesses = list(set(weaknesses))[:5]
        
        await self._sessions_collection().update_one(
            {"_id": ObjectId(session_id)},
            {
                "$set": {
                    "status": SessionStatus.COMPLETED,
                    "overall_score": round(overall_score, 1),
                    "strengths": strengths,
                    "weaknesses": weaknesses,
                    "completed_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )
    
    # ============ Report Generation ============
    
    async def generate_report(self, session_id: str) -> Dict[str, Any]:
        """Generate comprehensive interview report."""
        session = await self.get_session(session_id)
        if not session:
            return {"error": "Session not found"}
        
        if session["status"] != SessionStatus.COMPLETED:
            return {"error": "Interview not yet completed"}
        
        # Get all questions and answers
        questions = await self._questions_collection().find({
            "session_id": ObjectId(session_id)
        }).to_list(100)
        
        answers = await self._answers_collection().find({
            "session_id": ObjectId(session_id)
        }).to_list(100)
        
        # Build Q&A pairs
        qa_pairs = []
        answer_map = {str(a["question_id"]): a for a in answers}
        
        for q in questions:
            q_id = str(q["_id"])
            a = answer_map.get(q_id, {})
            qa_pairs.append({
                "question": q.get("question_text", ""),
                "question_type": q.get("round_type", ""),
                "difficulty": q.get("difficulty", ""),
                "answer": a.get("answer_text", ""),
                "code": a.get("code"),
                "score": a.get("score", 0),
                "feedback": a.get("feedback", ""),
                "strengths": a.get("strengths", []),
                "improvements": a.get("improvements", []),
                "time_taken": a.get("time_taken_seconds", 0)
            })
        
        # Calculate per-round breakdown
        round_breakdown = []
        for r in session["rounds"]:
            round_breakdown.append({
                "round_name": r["name"],
                "round_type": r["type"],
                "questions_answered": r["questions_answered"],
                "score": r.get("score", 0),
                "status": r.get("status", "pending")
            })
        
        report = {
            "session_id": session_id,
            "company": session["company"],
            "role": session["role"],
            "status": session["status"],
            "overall_score": session["overall_score"],
            "total_questions": len(questions),
            "total_time_minutes": session["total_time_spent_seconds"] // 60,
            "started_at": session.get("started_at"),
            "completed_at": session.get("completed_at"),
            "round_breakdown": round_breakdown,
            "questions_and_answers": qa_pairs,
            "strengths": session.get("strengths", []),
            "areas_to_improve": session.get("weaknesses", []),
            "recommendations": await self._generate_recommendations(session, qa_pairs)
        }
        
        return report
    
    async def _generate_recommendations(
        self,
        session: Dict[str, Any],
        qa_pairs: List[Dict]
    ) -> List[str]:
        """Generate personalized recommendations."""
        llm = self._get_llm_service()
        
        if not llm:
            # Default recommendations based on score
            score = session.get("overall_score", 0)
            if score >= 80:
                return [
                    "Excellent performance! You're well-prepared.",
                    "Consider practicing more system design for well-rounded skills.",
                    "Keep maintaining your strong fundamentals."
                ]
            elif score >= 60:
                return [
                    "Good foundation. Focus on the weak areas identified.",
                    "Practice more coding problems to improve speed.",
                    "Review feedback for each question to identify patterns."
                ]
            else:
                return [
                    "Focus on fundamentals before advanced topics.",
                    "Practice data structures: arrays, trees, graphs.",
                    "Work through the improvements suggested for each question."
                ]
        
        try:
            # AI-generated recommendations
            weaknesses = session.get("weaknesses", [])
            low_scores = [qa for qa in qa_pairs if qa.get("score", 0) < 60]
            
            prompt = f"""Based on this interview performance, give 3 specific actionable recommendations.

Company: {session['company']}
Role: {session['role']}
Overall Score: {session['overall_score']}%
Weak Areas: {', '.join(weaknesses[:3]) if weaknesses else 'None identified'}
Low Score Questions: {len(low_scores)} out of {len(qa_pairs)}

Give 3 SHORT, SPECIFIC recommendations. One per line, no numbering."""

            response = await llm.generate(prompt)
            recommendations = [r.strip() for r in response.split("\n") if r.strip()]
            return recommendations[:3]
        
        except Exception:
            return ["Review your weak areas", "Practice more problems", "Work on time management"]


# Singleton instance
interview_orchestrator = InterviewOrchestrator()
