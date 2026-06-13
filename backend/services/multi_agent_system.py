"""
Multi-Agent Interview System
LangChain-based multi-agent framework for realistic interview simulation.
Agents: Interviewer, Evaluator, Hint Provider, Career Coach, Coordinator.
"""

import os
import json
import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class AgentRole(str, Enum):
    """Available agent roles in the interview system."""
    COORDINATOR = "coordinator"
    INTERVIEWER = "interviewer"
    EVALUATOR = "evaluator"
    HINT_PROVIDER = "hint_provider"
    CAREER_COACH = "career_coach"


@dataclass
class AgentMessage:
    """Message passed between agents."""
    from_agent: AgentRole
    to_agent: AgentRole
    content: str
    message_type: str = "request"  # request, response, broadcast
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class InterviewContext:
    """Shared context for all agents during an interview."""
    session_id: str
    student_id: str
    company: str
    role: str
    difficulty: str = "medium"
    interview_type: str = "mixed"          # behavioral | technical | mixed
    resume_text: str = ""                  # candidate resume for personalized Qs
    question_count: int = 0                # total questions asked so far
    current_question: Dict = field(default_factory=dict)
    questions_asked: List[Dict] = field(default_factory=list)
    answers_given: List[Dict] = field(default_factory=list)
    scores: List[float] = field(default_factory=list)
    hints_used: int = 0
    feedback_log: List[str] = field(default_factory=list)
    student_profile: Dict = field(default_factory=dict)
    tested_topics: List[str] = field(default_factory=list) # Checklist of areas covered
    current_topic_followups: int = 0                       # Avoid infinite deep dives
    job_description: str = ""                             # Role requirements
    dsa_stage: str = "clarification"                      # clarification | approach | coding | optimization | completed
    dsa_question_details: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        from dataclasses import asdict
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InterviewContext":
        import inspect
        sig = inspect.signature(cls)
        valid_keys = {k for k, v in sig.parameters.items()}
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered_data)


class BaseAgent:
    """Base class for all interview agents."""
    
    def __init__(self, role: AgentRole, name: str):
        self.role = role
        self.name = name
        self._llm_service = None
    
    def _get_llm(self):
        """Lazy load LLM service."""
        if self._llm_service is None:
            try:
                from .llm_service import llm_service
                self._llm_service = llm_service
            except Exception:
                self._llm_service = None
        return self._llm_service
    
    async def process(
        self, 
        message: AgentMessage, 
        context: InterviewContext
    ) -> AgentMessage:
        """Process incoming message and return response."""
        raise NotImplementedError("Agents must implement process()")
    
    def get_system_prompt(self) -> str:
        """Get agent-specific system prompt."""
        return f"You are {self.name}, a {self.role.value} in an interview system."


class InterviewerAgent(BaseAgent):
    """
    Conducts the interview by asking questions.
    Adapts difficulty based on student performance.
    """
    
    def __init__(self):
        super().__init__(AgentRole.INTERVIEWER, "Alex the Interviewer")
        self.question_bank = []
    
    def get_system_prompt(self) -> str:
        return """You are Alex, a Senior Technical Lead at a Tier-1 tech company. You are the INTERVIEWER.
        
Your persona:
- Elite, professional, but deeply curious. You are looking for a teammate, not just an employee.
- Adapt your tone to the COMPANY'S DNA. (e.g., if it's Google, focus on scalability; if it's a startup, focus on speed and ownership).
- NEVER identify as an AI or an assistant. You ARE the interviewer.
- Ask ONE targeted question at a time.
- If the candidate is vague, follow up with "Can you drill down into the specifics of [X]?"
- Keep your speech concise (under 50 words per turn) to respect the VOICE interface.
- Use natural conversational transitions/cues (e.g. "That makes sense. Let's dig deeper into...", "Got it. Moving to the next area...") to make the dialogue feel human and natural.

Your goal is to extract high-quality 'Signal' from the candidate's responses."""

    
    async def process(
        self, 
        message: AgentMessage, 
        context: InterviewContext
    ) -> AgentMessage:
        """Generate next question or follow-up based on context."""
        llm = self._get_llm()
        
        if message.message_type == "start_interview":
            # Generate opening question
            question = await self._generate_opening(context)
            return AgentMessage(
                from_agent=self.role,
                to_agent=AgentRole.COORDINATOR,
                content=question,
                message_type="question",
                metadata={"question_type": "opening", "difficulty": context.difficulty}
            )
        
        elif message.message_type == "dsa_transition":
            from_stage = message.metadata.get("from_stage")
            to_stage = message.metadata.get("to_stage")
            prompt = self._get_dsa_transition_prompt(context, from_stage, to_stage, message.content)
            response = None
            if llm:
                try:
                    response = await llm.generate(prompt, self.get_system_prompt())
                    response = response.strip()
                except Exception as e:
                    logger.warning(f"Failed to generate DSA transition: {e}")
            
            if not response:
                fallbacks = {
                    "approach": "Got it. Now that we've clarified the constraints, what high-level approach or algorithm do you propose to solve this problem? Please explain the complexity as well.",
                    "coding": "Makes sense. Let's move on to coding. Please write the complete code for your solution.",
                    "optimization": "Okay, the code is down. How would you test this? Are there any potential edge cases or bugs you can identify and optimize?",
                    "completed": "Perfect, we are all done with the coding portion. Thank you!"
                }
                response = fallbacks.get(to_stage, "Let's move to the next stage.")

            return AgentMessage(
                from_agent=self.role,
                to_agent=AgentRole.COORDINATOR,
                content=response,
                message_type="question",
                metadata={"question_type": f"dsa_{to_stage}", "difficulty": context.difficulty}
            )

        elif message.message_type == "continue":
            # Generate follow-up or next question based on performance
            avg_score = sum(context.scores) / len(context.scores) if context.scores else 50
            
            if avg_score >= 80:
                difficulty = "hard"
            elif avg_score >= 60:
                difficulty = "medium"
            else:
                difficulty = "medium"  # Stay at medium for struggling candidates
            
            question = await self._generate_question(context, difficulty)
            return AgentMessage(
                from_agent=self.role,
                to_agent=AgentRole.COORDINATOR,
                content=question,
                message_type="question",
                metadata={"question_type": "follow_up", "difficulty": difficulty}
            )
        
        elif message.message_type == "follow_up":
            # Ask clarifying question
            follow_up = await self._generate_follow_up(context, message.content)
            return AgentMessage(
                from_agent=self.role,
                to_agent=AgentRole.COORDINATOR,
                content=follow_up,
                message_type="clarification"
            )
        
        return AgentMessage(
            from_agent=self.role,
            to_agent=AgentRole.COORDINATOR,
            content="Thank you for your response.",
            message_type="acknowledgment"
        )
    
    async def _generate_vague_dsa_intro(self, question: Dict) -> str:
        llm = self._get_llm()
        if llm:
            try:
                prompt = f"""You are the interviewer. You want to present a coding problem to the candidate, but you want to do it vaguely to see if they ask clarifying questions.
                
Problem Title: {question.get('title')}
Full Description: {question.get('description')}

Write a 2-3 sentence verbal introduction. Tell them the name of the problem, give a very brief overview of the task, and ask them to raise any clarifying questions they have about inputs, outputs, constraints, or corner cases before we discuss the solution approach.
Do NOT show examples, constraints, or the ideal complexity. Keep it voice-friendly and concise."""
                response = await llm.generate(prompt, self.get_system_prompt())
                return response.strip()
            except Exception:
                pass
        
        # Fallback
        return f"Let's start with a coding problem: '{question.get('title', 'Coding Problem')}'. The task is: {question.get('description', '')[:150]}... Before writing code, what clarifying questions do you have about the inputs, outputs, or constraints?"

    def _get_dsa_transition_prompt(
        self,
        context: InterviewContext,
        from_stage: str,
        to_stage: str,
        prev_answer: str
    ) -> str:
        full_q = context.dsa_question_details
        
        prompt = f"""You are Alex, the senior tech lead and Interviewer at {context.company}.
We are conducting an interactive DSA interview for the {context.role} role.

Coding Problem: {full_q.get('title')}
Problem Description: {full_q.get('description')}
Constraints: {", ".join(full_q.get('constraints', []))}
Ideal Approach: {full_q.get('ideal_approach')}
Expected Complexity: Time {full_q.get('time_complexity')}, Space {full_q.get('space_complexity')}

TRANSITION PATH: {from_stage.upper()} -> {to_stage.upper()}
Candidate's response to the {from_stage} phase: "{prev_answer[:1000]}"

Your instructions for this transition:"""

        if from_stage == "clarification" and to_stage == "approach":
            prompt += """
1. Acknowledge and answer the candidate's clarifying questions based on the problem details (e.g. constraints, sorting properties). If they asked no questions or just started coding, politely guide them back.
2. Ask them to explain their proposed approach/strategy to solve this problem, and analyze both the Time and Space complexity (Big-O) of their approach.
3. Keep it voice-friendly and direct."""
        elif from_stage == "approach" and to_stage == "coding":
            prompt += """
1. Brief critique of their approach (e.g. confirm if it is optimal or suggest how to optimize it if it's suboptimal. If they proposed an O(N^2) solution when an O(N) is possible, suggest a pointer or hash map hint).
2. Prompt them to write the actual code solution for the problem.
3. Keep it encouraging and direct."""
        elif from_stage == "coding" and to_stage == "optimization":
            prompt += """
1. Check their code. Point out a potential bug, syntax issue, or edge case (e.g. empty arrays, large numbers, duplicates) that they should dry-run or verify.
2. Ask them how they would test this code or handle this specific edge case.
3. Keep it brief and focused."""
        elif from_stage == "optimization" and to_stage == "completed":
            prompt += """
1. Thank them for the solution. Inform them that we have wrapped up the coding portion of the interview.
2. Keep it warm and concise."""
            
        prompt += "\nWrite only what you (the interviewer, Alex) would say to the candidate."
        return prompt

    async def _generate_opening(self, context: InterviewContext) -> str:
        """Generate opening — warm intro, interview overview, ask candidate to introduce themselves."""
        
        # If it's a DSA interview, jump straight into the first coding question instead of intro
        if context.interview_type == "dsa":
            try:
                from .question_generator import question_generator
                question = await question_generator.generate_dsa_question(
                    difficulty=context.difficulty,
                    company=context.company
                )
                context.dsa_question_details = question
                context.dsa_stage = "clarification"
                return await self._generate_vague_dsa_intro(question)
            except Exception as e:
                logger.error(f"Error generating intro DSA question: {e}")
                pass
                
        llm = self._get_llm()
        if not llm:
            return self._get_fallback_opening(context)

        resume_snippet = ""
        if context.resume_text:
            text_to_show = context.resume_text
            if len(text_to_show) > 500:
                text_to_show = text_to_show[:500]
            resume_snippet = f"\nCANDIDATE RESUME SUMMARY (Snippet):\n{text_to_show}\nUse this to personalize your greeting — mention 1 specific skill or project you noticed.\n"

        interview_focus = ""
        if context.interview_type == "behavioral":
            interview_focus = "This will be a behavioral interview focusing on past experiences and soft skills."
        elif context.interview_type == "technical":
            interview_focus = "This will be a technical interview covering core technical concepts and depth of knowledge."
        else:
            interview_focus = "This will cover a brief intro, some behavioral scenarios, then technical questions."

        prompt = f"""CONTEXT: You are Alex, the INTERVIEWER at {context.company}. You are starting an interview with a candidate for the {context.role} position.
{resume_snippet}
Write your opening message to the CANDIDATE. Your message should:
1. Greet them warmly and say you are Alex, the interviewer from {context.company}
2. Mention: "{interview_focus}"
3. Ask the candidate to introduce themselves{" and mention any relevant projects" if context.resume_text else ""}

Write ONLY what you (the interviewer, Alex) would say. Do NOT write what the candidate says.
Keep it under 4 sentences. Natural conversational tone.

Example format: "Hi! I'm Alex from {context.company}. Thanks for joining us today for the {context.role} interview. {interview_focus} To kick off — could you tell me a bit about yourself?"

Your opening message:"""

        try:
            response = await llm.generate(prompt, self.get_system_prompt())
            return response.strip()
        except Exception:
            return self._get_fallback_opening(context)

    
    def _get_fallback_opening(self, context: InterviewContext) -> str:
        """Fallback opening — interviewer greets the candidate."""
        import random
        openings = [
            f"Hi there! Welcome to your {context.role} interview at {context.company}. I'm Alex, your interviewer today. We'll start with a quick intro, move into some behavioral questions, and then wrap up with technical topics. To kick things off — could you tell me a bit about yourself and your background?",
            f"Hello! Great to meet you. I'm Alex from {context.company}, and I'll be conducting your {context.role} interview today. We have about 45 minutes together — we'll cover introductions, a few behavioral scenarios, and then some technical questions. Let's start simply: could you walk me through your background and what draws you to this role?",
            f"Hi, welcome! I'm Alex, interviewing you for the {context.role} position at {context.company}. Thanks for making the time. Before we dive into the technical stuff, I'd love to hear a bit about you — what's your background, and what are you most excited to work on professionally?",
        ]
        return random.choice(openings)

    
    async def _generate_question(self, context: InterviewContext, difficulty: str) -> str:
        """Generate next question following: intro → behavioral → technical (discussion) → cross-questioning."""
        llm = self._get_llm()
        if not llm:
            return self._get_fallback_question(context.interview_type, difficulty)

        num_answered = len(context.answers_given)
        last_answer  = context.answers_given[-1]["answer"] if context.answers_given else ""
        previous_qs  = [q.get("content", q.get("title", "")) for q in context.questions_asked[-3:]]
        avg_score    = sum(context.scores) / len(context.scores) if context.scores else 50

        # --- Determine interview stage with Topic Pivoting ---
        is_behavioral_only = context.interview_type == "behavioral"
        is_technical_only  = context.interview_type == "technical"
        is_dsa_only        = context.interview_type == "dsa"

        # Check for deep-dive loop
        max_followups = 1
        should_pivot = False
        
        if context.current_topic_followups >= max_followups:
            should_pivot = True
            context.current_topic_followups = 0  # Reset for next topic
        else:
            context.current_topic_followups += 1

        if is_dsa_only:
            stage = "dsa_follow_up"
            safe_ans = last_answer
            if len(safe_ans) > 600:
                safe_ans = safe_ans[:600]
            instruction = f"""The candidate just submitted a code solution or answer. Answer: "{safe_ans}"
            
You are conducting a strict DSA (Data Structures and Algorithms) interview.
Ask ONE direct, targeted follow-up question about their solution.
Analyze complexity or point out an edge case.
One question only, conversational and direct."""

        elif num_answered <= 1:
            stage = "behavioral"
            context.tested_topics.append("Introduction")
            instruction = f"""The candidate explained their background. Now move to a BEHAVIORAL question.
- Pick a standard behavioral theme: teamwork, leadership, or handling failure.
- Frame it as "Tell me about a time when..."
- One question only, conversational tone."""

        elif (num_answered <= 3 and not is_behavioral_only) or (should_pivot and "Technical Core" not in context.tested_topics):
            stage = "technical_discussion"
            context.tested_topics.append("Technical Core")
            safe_ans = last_answer
            if len(safe_ans) > 300:
                safe_ans = safe_ans[:300]
            instruction = f"""PIVOT to Technical Discussion for a {context.role} at {context.company}.
This is a VOICE interview. Ask a conceptual or architectural question they can answer verbally.
Example: "How would you design X?" or "What are the tradeoffs of using Y for this role?"
Difficulty: {difficulty} (avg score so far: {avg_score:.0f}%)
One question only."""

        elif is_behavioral_only or (should_pivot and "Behavioral Deep" not in context.tested_topics):
            stage = "behavioral_deep"
            context.tested_topics.append("Behavioral Deep")
            instruction = f"""PIVOT to a deep behavioral scenario.
Focus on conflict resolution or mentoring.
One question only."""

        else:
            stage = "cross_question"
            safe_ans = last_answer
            if len(safe_ans) > 400:
                safe_ans = safe_ans[:400]
            instruction = f"""Final follow-up: Challenge an assumption or ask for a trade-off based on: "{safe_ans}"
Be direct. One question only."""

        resume_context = f"\nCandidate Resume Context:\n{context.resume_text}\n" if context.resume_text else ""
        jd_context = f"\nTarget Job Description:\n{context.job_description}\n" if context.job_description else ""

        prompt = f"""Company: {context.company} | Role: {context.role} | Stage: {stage}
{jd_context}
{resume_context}
Instructions for this turn:
{instruction}
- Start the response with a natural, conversational verbal transition or acknowledgment of their previous answer (if applicable) before asking the question.
- Keep the generated question voice-friendly and concise."""

        try:
            response = await llm.generate(prompt, self.get_system_prompt())
            return response.strip()
        except Exception:
            return self._get_fallback_question(context.interview_type, difficulty)

    
    def _get_fallback_question(self, interview_type: str = "mixed", difficulty: str = "medium") -> str:
        """Fallback questions — ALL voice-appropriate (no code writing)."""
        behavioral = [
            "Tell me about a time you had to work with a difficult team member. How did you handle it?",
            "Describe a project where you had to learn something new quickly. What was your approach?",
            "Tell me about a time something went wrong in a project. What did you do?",
            "How do you prioritize when you have multiple deadlines at once?",
            "Describe a situation where you disagreed with your manager or lead. How did you handle it?",
            "Tell me about a technical decision you're proud of. What made it the right choice?",
        ]
        technical = {
            "easy": [
                "Can you explain the difference between a stack and a queue, and give a real use case for each?",
                "How does HTTP differ from HTTPS? Why does it matter?",
                "What is the difference between SQL and NoSQL databases? When would you use each?",
            ],
            "medium": [
                "How would you design an API for a ride-sharing app like Uber? Walk me through the main endpoints.",
                "Explain how you'd approach caching in a high-traffic web application. What are the tradeoffs?",
                "Walk me through how you'd debug a slow database query in production.",
                "How would you ensure data consistency in a system with multiple microservices?",
            ],
            "hard": [
                "How would you design a distributed notification system that can handle millions of users?",
                "Walk me through your approach to designing Twitter's feed. What scalability challenges would you solve first?",
                "How would you architect a real-time collaborative editing system like Google Docs?",
            ]
        }
        import random
        if interview_type == "behavioral":
            return random.choice(behavioral)
        elif interview_type == "technical":
            return random.choice(technical.get(difficulty, technical["medium"]))
        else:
            # mixed: alternate between behavioral and technical
            pool = behavioral + technical.get(difficulty, technical["medium"])
            return random.choice(pool)


    async def _generate_follow_up(self, context: InterviewContext, answer: str) -> str:
        """Generate follow-up question based on answer."""
        llm = self._get_llm()
        if not llm:
            return "Can you tell me more about your approach? What's the time complexity?"
        
        resume_context = f"\nCandidate Resume Context:\n{context.resume_text}\n" if context.resume_text else ""
        jd_context = f"\nTarget Job Description:\n{context.job_description}\n" if context.job_description else ""

        prompt = f"""Company: {context.company} | Role: {context.role}
{jd_context}
{resume_context}
The candidate just answered: "{answer[:500]}"

Generate a brief follow-up question to dig deeper.
- Begin with a natural conversational cue (e.g. "That makes sense...", "Interesting point...") acknowledging their response.
- Ask a drill-down question about their approach (e.g., edge cases, time/space complexity, alternative approaches, design tradeoffs).
- Keep it concise (under 50 words) and voice-friendly."""
        
        try:
            response = await llm.generate(prompt, self.get_system_prompt())
            return response.strip()
        except Exception:
            return "Interesting approach! What's the time complexity of your solution?"


class EvaluatorAgent(BaseAgent):
    """
    Evaluates answers and provides scores.
    Tracks performance patterns.
    """
    
    def __init__(self):
        super().__init__(AgentRole.EVALUATOR, "Eva the Evaluator")
    
    def get_system_prompt(self) -> str:
        return """You are Eva, an Elite Technical Evaluator. Your judgment determines if someone gets hired at a top firm.

Your evaluation criteria:
1. Signal vs. Noise: Does the candidate give specific details or generic buzzwords?
2. Technical Rigor: Are they aware of complexity, tradeoffs, and edge cases?
3. Communication: Can they explain complex topics simply and clearly?
4. Problem Solving: How do they handle pressure and ambiguity?

Evaluation Tone: Objective, high-standards, and extremely precise. Identify exactly where they missed the mark."""
    
    async def process(
        self, 
        message: AgentMessage, 
        context: InterviewContext
    ) -> AgentMessage:
        """Evaluate answer and return score with feedback."""
        if message.message_type != "evaluate":
            return AgentMessage(
                from_agent=self.role,
                to_agent=AgentRole.COORDINATOR,
                content="No evaluation requested.",
                message_type="error"
            )
        
        answer = message.metadata.get("answer", "")
        question = message.metadata.get("question", context.current_question)
        dsa_stage = message.metadata.get("dsa_stage")
        
        if context.interview_type == "dsa" and dsa_stage:
            evaluation = await self._evaluate_dsa_stage(question, answer, dsa_stage, context)
        else:
            evaluation = await self._evaluate_answer(question, answer, context)
        
        return AgentMessage(
            from_agent=self.role,
            to_agent=AgentRole.COORDINATOR,
            content=evaluation.get("feedback", ""),
            message_type="evaluation",
            metadata={
                "score": evaluation.get("score", 50),
                "breakdown": evaluation.get("breakdown", {}),
                "strengths": evaluation.get("strengths", []),
                "improvements": evaluation.get("improvements", [])
            }
        )
    
    async def _evaluate_answer(
        self, 
        question: Dict, 
        answer: str, 
        context: InterviewContext
    ) -> Dict[str, Any]:
        """Evaluate answer using LLM or fallback."""
        llm = self._get_llm()
        
        if llm:
            try:
                return await self._llm_evaluate(question, answer, context)
            except Exception:
                pass
        
        return self._fallback_evaluate(answer)
    
    async def _llm_evaluate(
        self, 
        question: Dict, 
        answer: str, 
        context: InterviewContext
    ) -> Dict[str, Any]:
        """LLM-powered evaluation."""
        llm = self._get_llm()
        
        is_dsa = context.interview_type == "dsa"
        dsa_instructions = ""
        if is_dsa:
            dsa_instructions = "\nSPECIAL INSTRUCTIONS FOR DSA:\nEvaluate the code's time and space complexity, correctness, and edge case handling (e.g., empty inputs, negative numbers). Highlight any specific test cases where this code might fail."

        prompt = f"""Evaluate this interview answer:

QUESTION: {question.get('content', question.get('title', 'Unknown'))}
ANSWER: {answer[:2000]}
CONTEXT: {context.role} at {context.company}
{dsa_instructions}

Return JSON with this exact format:
{{
    "score": <0-100>,
    "feedback": "<2-3 sentences of constructive feedback>",
    "strengths": ["<strength1>", "<strength2>"],
    "improvements": ["<improvement1>", "<improvement2>"],
    "breakdown": {{
        "correctness": <0-100>,
        "clarity": <0-100>,
        "depth": <0-100>
    }}
}}

Be fair and constructive. Focus on specific, actionable feedback."""
        
        response = await llm.generate(prompt, self.get_system_prompt())
        
        # Parse JSON from response
        try:
            # Try to extract JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
        
        return self._fallback_evaluate(answer)
    
    def _fallback_evaluate(self, answer: str) -> Dict[str, Any]:
        """Fallback evaluation based on heuristics."""
        word_count = len(answer.split())
        
        # Basic scoring
        if word_count < 20:
            score = 40
            feedback = "Your answer was quite brief. Try to elaborate more on your approach."
        elif word_count < 50:
            score = 55
            feedback = "Good start! Consider adding more details about complexity and edge cases."
        elif word_count < 150:
            score = 70
            feedback = "Solid answer with good detail. You explained your approach clearly."
        else:
            score = 80
            feedback = "Comprehensive answer! You covered the topic thoroughly."
        
        return {
            "score": score,
            "feedback": feedback,
            "strengths": ["Attempted the question", "Showed engagement"],
            "improvements": ["Add more specific examples", "Discuss tradeoffs"],
            "breakdown": {
                "correctness": score,
                "clarity": min(score + 10, 100),
                "depth": max(score - 10, 30)
            }
        }

    async def _evaluate_dsa_stage(
        self,
        question: Dict,
        answer: str,
        dsa_stage: str,
        context: InterviewContext
    ) -> Dict[str, Any]:
        """Evaluate DSA answer for a specific stage (clarification, approach, coding, optimization)."""
        llm = self._get_llm()
        if llm:
            try:
                full_q = context.dsa_question_details
                prompt = f"""Evaluate this candidate answer for a specific stage of a DSA interview.
                
Coding Problem: {full_q.get('title')}
Problem Description: {full_q.get('description')}
Constraints: {", ".join(full_q.get('constraints', [])) if isinstance(full_q.get('constraints'), list) else full_q.get('constraints', '')}
Ideal Approach: {full_q.get('ideal_approach')}
Expected Complexity: Time {full_q.get('time_complexity')}, Space {full_q.get('space_complexity')}

CURRENT DSA STAGE: {dsa_stage.upper()}
Candidate's response for this stage: "{answer[:2000]}"

Criteria for {dsa_stage.upper()} stage:"""
                if dsa_stage == "clarification":
                    prompt += """
- Did the candidate ask clarifying questions about inputs, outputs, constraints, or corner cases?
- Did they confirm the problem statement and constraints?
- Score highly if they asked smart clarifying questions. Score lower if they just skipped to writing code or didn't ask anything."""
                elif dsa_stage == "approach":
                    prompt += """
- Did they describe a clear solution approach before coding?
- Did they analyze Time and Space complexity (Big-O)?
- Is the proposed approach correct and efficient?
- Score highly if they explained a correct approach with correct Big-O analysis."""
                elif dsa_stage == "coding":
                    prompt += """
- Did they write the actual code to implement the solution?
- Is the code structured, clean, and logical?
- Does it look like a valid attempt to solve the problem?
- Score highly if they wrote clean code that implements the approach."""
                elif dsa_stage == "optimization":
                    prompt += """
- Did they discuss edge cases (e.g. empty inputs, single element, negative numbers, duplicates)?
- Did they try to dry-run or verify the code?
- If the original approach was suboptimal, did they optimize it?
- Score highly if they addressed edge cases and verified correctness."""
                else:
                    prompt += """
- General DSA evaluation. Correctness, communication, and problem-solving."""

                prompt += """

Return JSON with this exact format:
{{
    "score": <0-100>,
    "feedback": "<2-3 sentences of constructive feedback for this stage>",
    "strengths": ["<strength1>", "<strength2>"],
    "improvements": ["<improvement1>", "<improvement2>"],
    "breakdown": {{
        "correctness": <0-100>,
        "clarity": <0-100>,
        "depth": <0-100>
    }}
}}

Be fair, constructive, and stage-appropriate. Return ONLY the JSON object."""
                response = await llm.generate(prompt, self.get_system_prompt())
                # Parse JSON
                import re
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    return json.loads(json_match.group())
            except Exception as e:
                logger.error(f"Error in LLM DSA stage evaluation: {e}")
                pass
                
        # Fallback evaluation for DSA stage
        return self._fallback_dsa_evaluate(answer, dsa_stage)

    def _fallback_dsa_evaluate(self, answer: str, dsa_stage: str) -> Dict[str, Any]:
        """Fallback evaluation for DSA stages based on simple heuristics."""
        word_count = len(answer.split())
        score = 50
        feedback = ""
        strengths = ["Responded to the interviewer"]
        improvements = []
        
        if dsa_stage == "clarification":
            # Check for question marks or key terms like "constraints", "input", "output", "null"
            has_questions = "?" in answer
            has_keywords = any(kw in answer.lower() for kw in ["constraint", "input", "output", "null", "empty", "limit", "edge"])
            if has_questions and has_keywords:
                score = 85
                feedback = "Great job asking clarifying questions and confirming constraints before jumping into code."
                strengths.append("Identified potential edge cases or constraints early")
            elif has_questions or has_keywords:
                score = 70
                feedback = "Good effort trying to clarify. Try to ask more specifically about inputs/outputs limits and corner cases."
                improvements.append("Ask more structured clarifying questions about constraints and null/empty states")
            else:
                score = 45
                feedback = "You proceeded without asking clarifying questions or confirming constraints. It's always best to clarify first."
                improvements.append("Always clarify inputs, outputs, constraints, and assumptions before planning")
                
        elif dsa_stage == "approach":
            # Check for Big-O notation, "time", "space", "complexity"
            has_big_o = any(o in answer for o in ["O(1)", "O(n)", "O(N)", "O(log", "O(n^2)", "O(N^2)"])
            has_complexity = "complexity" in answer.lower() or "time" in answer.lower() or "space" in answer.lower()
            if has_big_o and has_complexity:
                score = 80
                feedback = "Good explanation of your approach along with time and space complexity analysis."
                strengths.append("Analyzed Time/Space complexity upfront")
            elif has_complexity:
                score = 65
                feedback = "You described the approach, but make sure to state the exact Big-O Time and Space complexity explicitly."
                improvements.append("Explicitly state Big-O time and space complexity")
            else:
                score = 50
                feedback = "Please explain the algorithm/logic and analyze its Time and Space complexity before writing code."
                improvements.append("Describe your strategy and trace complexity before jumping into coding")
                
        elif dsa_stage == "coding":
            # Check if there is some code structure (def, class, function, return, variables, indentation/brackets)
            is_code_like = any(kw in answer for kw in ["def ", "class ", "return", "function", "var ", "const ", "let ", "{", "}", "="])
            if is_code_like and word_count > 15:
                score = 75
                feedback = "The code implementation has been provided. It matches the structure of a a standard code solution."
                strengths.append("Translated approach into code")
            else:
                score = 40
                feedback = "No code implementation was detected or the code was too brief. Please write out the full solution."
                improvements.append("Write a complete, structured code implementation of your approach")
                
        elif dsa_stage == "optimization":
            # Check for testing, edge cases, optimizations
            has_edge = any(kw in answer.lower() for kw in ["edge", "null", "empty", "zero", "bound", "negative", "test", "verify", "dry run"])
            if has_edge:
                score = 80
                feedback = "Solid analysis of edge cases and verification of the solution."
                strengths.append("Addressed corner cases and edge conditions")
            else:
                score = 55
                feedback = "Consider walking through specific test cases and edge cases (like empty/null inputs) to verify correctness."
                improvements.append("Verify code correctness against standard edge cases and dry-run code")
                
        return {
            "score": score,
            "feedback": feedback,
            "strengths": strengths,
            "improvements": improvements,
            "breakdown": {
                "correctness": score,
                "clarity": min(score + 10, 100),
                "depth": max(score - 10, 30)
            }
        }


class HintProviderAgent(BaseAgent):
    """
    Provides hints when students are stuck.
    Tracks hint usage for scoring adjustments.
    """
    
    def __init__(self):
        super().__init__(AgentRole.HINT_PROVIDER, "Hannah the Hint Provider")
        self.hints_given: Dict[str, List[str]] = {}
    
    def get_system_prompt(self) -> str:
        return """You are Hannah, a helpful tutor providing hints during interviews.

Your approach:
- Give progressive hints (small nudge first, then more specific)
- Don't give away the answer
- Ask guiding questions when appropriate
- Encourage the candidate to think through the problem

Be supportive and educational."""
    
    async def process(
        self, 
        message: AgentMessage, 
        context: InterviewContext
    ) -> AgentMessage:
        """Provide appropriate hint based on hint level."""
        if message.message_type != "request_hint":
            return AgentMessage(
                from_agent=self.role,
                to_agent=AgentRole.COORDINATOR,
                content="No hint requested.",
                message_type="error"
            )
        
        hint_level = message.metadata.get("hint_level", 1)
        question = context.current_question
        
        hint = await self._generate_hint(question, hint_level, context)
        
        return AgentMessage(
            from_agent=self.role,
            to_agent=AgentRole.COORDINATOR,
            content=hint,
            message_type="hint",
            metadata={
                "hint_level": hint_level,
                "penalty": self._get_hint_penalty(hint_level)
            }
        )
    
    async def _generate_hint(
        self, 
        question: Dict, 
        level: int, 
        context: InterviewContext
    ) -> str:
        """Generate progressive hints."""
        llm = self._get_llm()
        
        if llm:
            try:
                return await self._llm_hint(question, level)
            except Exception:
                pass
        
        return self._fallback_hint(level)
    
    async def _llm_hint(self, question: Dict, level: int) -> str:
        """LLM-powered hint generation."""
        llm = self._get_llm()
        
        level_descriptions = {
            1: "a very small nudge - just point in the right direction",
            2: "a moderate hint - suggest the approach or data structure",
            3: "a significant hint - explain the key insight needed"
        }
        
        prompt = f"""The candidate is stuck on this question:
{question.get('content', question.get('title', ''))}

Provide {level_descriptions.get(level, level_descriptions[2])}.

Do NOT give away the answer. Be helpful but let them figure it out.
Keep it to 1-2 sentences."""
        
        response = await llm.generate(prompt, self.get_system_prompt())
        return response.strip()
    
    def _fallback_hint(self, level: int) -> str:
        """Fallback hints by level."""
        hints = {
            1: "Think about what data structure would help you access elements quickly.",
            2: "Consider using a hash map to store values you've seen. What would you use as keys?",
            3: "A common pattern is to store (target - current) in a hash map as you iterate."
        }
        return hints.get(level, hints[2])
    
    def _get_hint_penalty(self, level: int) -> float:
        """Score penalty for using hints."""
        penalties = {1: 0.05, 2: 0.10, 3: 0.15}
        return penalties.get(level, 0.10)


class CareerCoachAgent(BaseAgent):
    """
    Provides career advice and interview tips.
    Gives end-of-interview feedback.
    """
    
    def __init__(self):
        super().__init__(AgentRole.CAREER_COACH, "Charlie the Career Coach")
    
    def get_system_prompt(self) -> str:
        return """You are Charlie, a High-Performance Career Strategist and Mentor to industry leaders.

Your motive:
- Turn every 'failure' into a strategic growth point.
- Provide actionable 'Career Roadmap' advice.
- Don't just give feedback; give a competitive edge.
- Tone: Inspirational, strategic, and direct.

Ask yourself: "What is the one insight this candidate needs to land their dream job tomorrow?" """
    
    async def process(
        self, 
        message: AgentMessage, 
        context: InterviewContext
    ) -> AgentMessage:
        """Provide coaching feedback."""
        if message.message_type == "end_interview":
            coaching = await self._generate_final_coaching(context)
            return AgentMessage(
                from_agent=self.role,
                to_agent=AgentRole.COORDINATOR,
                content=coaching,
                message_type="coaching",
                metadata={"type": "final_feedback"}
            )
        
        elif message.message_type == "quick_tip":
            tip = await self._generate_quick_tip(context)
            return AgentMessage(
                from_agent=self.role,
                to_agent=AgentRole.COORDINATOR,
                content=tip,
                message_type="tip"
            )
        
        return AgentMessage(
            from_agent=self.role,
            to_agent=AgentRole.COORDINATOR,
            content="Keep practicing! You're doing great.",
            message_type="encouragement"
        )
    
    async def _generate_final_coaching(self, context: InterviewContext) -> str:
        """Generate comprehensive end-of-interview feedback."""
        llm = self._get_llm()
        
        avg_score = sum(context.scores) / len(context.scores) if context.scores else 50
        
        if llm:
            try:
                prompt = f"""Generate final interview coaching for:

PERFORMANCE SUMMARY:
- Questions answered: {len(context.answers_given)}
- Average score: {avg_score:.1f}%
- Hints used: {context.hints_used}
- Company: {context.company}
- Role: {context.role}

Write 3-4 sentences of personalized coaching:
1. What they did well
2. Key area to improve
3. Specific practice recommendation
4. Encouragement

Be specific and actionable."""
                
                response = await llm.generate(prompt, self.get_system_prompt())
                return response.strip()
            except Exception:
                pass
        
        return self._fallback_coaching(avg_score)
    
    def _fallback_coaching(self, avg_score: float) -> str:
        """Fallback coaching based on score."""
        if avg_score >= 80:
            return """Excellent interview performance! You demonstrated strong problem-solving skills and communicated your thoughts clearly. 
Keep practicing system design questions to prepare for senior roles. You're well-prepared for real interviews - stay confident!"""
        elif avg_score >= 60:
            return """Good job on the interview! You showed solid foundational knowledge. 
Focus on practicing medium-hard LeetCode problems daily and work on explaining your thought process out loud. 
You're making great progress - keep at it!"""
        else:
            return """Thanks for completing the practice interview! Every attempt is a learning opportunity. 
I recommend focusing on core data structures (arrays, hash maps, trees) and practicing pattern-based problems. 
Try the 'Blind 75' problem set and don't hesitate to use hints while learning. You've got this!"""
    
    async def _generate_quick_tip(self, context: InterviewContext) -> str:
        """Generate a quick tip based on current context."""
        tips = [
            "Remember to think out loud - interviewers want to see your thought process!",
            "Always clarify the problem before coding. Ask about edge cases and constraints.",
            "It's okay to start with a brute force solution and then optimize.",
            "Consider time and space complexity early - it shows maturity.",
            "If stuck, try working through a simple example step by step."
        ]
        import random
        return random.choice(tips)


class CoordinatorAgent(BaseAgent):
    """
    Orchestrates the multi-agent interview.
    Routes messages and manages interview flow.
    """
    
    def __init__(self):
        super().__init__(AgentRole.COORDINATOR, "The Coordinator")
        self.agents: Dict[AgentRole, BaseAgent] = {}
        self._initialize_agents()
    
    def _initialize_agents(self):
        """Initialize all sub-agents."""
        self.agents = {
            AgentRole.INTERVIEWER: InterviewerAgent(),
            AgentRole.EVALUATOR: EvaluatorAgent(),
            AgentRole.HINT_PROVIDER: HintProviderAgent(),
            AgentRole.CAREER_COACH: CareerCoachAgent()
        }
    
    async def process(
        self, 
        message: AgentMessage, 
        context: InterviewContext
    ) -> AgentMessage:
        """Route message to appropriate agent."""
        target = message.to_agent
        
        if target in self.agents:
            return await self.agents[target].process(message, context)
        
        return AgentMessage(
            from_agent=self.role,
            to_agent=message.from_agent,
            content="Unknown agent target",
            message_type="error"
        )
    
    async def start_interview(self, context: InterviewContext) -> Dict[str, Any]:
        """Start a new interview session."""
        message = AgentMessage(
            from_agent=AgentRole.COORDINATOR,
            to_agent=AgentRole.INTERVIEWER,
            content="Start the interview",
            message_type="start_interview"
        )
        
        response = await self.agents[AgentRole.INTERVIEWER].process(message, context)
        
        return {
            "session_id": context.session_id,
            "question": response.content,
            "question_type": response.metadata.get("question_type", "coding"),
            "agent": "interviewer"
        }
    
    async def submit_answer(
        self, 
        context: InterviewContext, 
        answer: str
    ) -> Dict[str, Any]:
        """Process answer submission through evaluation and follow-up."""
        # First, evaluate the answer
        eval_metadata = {
            "answer": answer,
            "question": context.current_question
        }
        if context.interview_type == "dsa":
            eval_metadata["dsa_stage"] = context.dsa_stage

        eval_message = AgentMessage(
            from_agent=AgentRole.COORDINATOR,
            to_agent=AgentRole.EVALUATOR,
            content="Evaluate this answer",
            message_type="evaluate",
            metadata=eval_metadata
        )
        
        eval_response = await self.agents[AgentRole.EVALUATOR].process(eval_message, context)
        
        # Store score
        score = eval_response.metadata.get("score", 50)
        context.scores.append(score)
        context.answers_given.append({
            "answer": answer[:500],
            "score": score,
            "question_id": len(context.questions_asked)
        })
        
        if context.interview_type == "dsa":
            from_stage = context.dsa_stage
            
            # clarification -> approach -> coding -> optimization -> completed
            stage_order = ["clarification", "approach", "coding", "optimization", "completed"]
            try:
                current_idx = stage_order.index(from_stage)
                to_stage = stage_order[current_idx + 1]
            except (ValueError, IndexError):
                to_stage = "completed"
                
            context.dsa_stage = to_stage
            
            # Send transition message to interviewer
            next_message = AgentMessage(
                from_agent=AgentRole.COORDINATOR,
                to_agent=AgentRole.INTERVIEWER,
                content=answer,
                message_type="dsa_transition",
                metadata={
                    "from_stage": from_stage,
                    "to_stage": to_stage
                }
            )
            
            next_response = await self.agents[AgentRole.INTERVIEWER].process(next_message, context)
            next_question_content = next_response.content if to_stage != "completed" else ""
            
            return {
                "evaluation": {
                    "score": score,
                    "feedback": eval_response.content,
                    "breakdown": eval_response.metadata.get("breakdown", {}),
                    "strengths": eval_response.metadata.get("strengths", []),
                    "improvements": eval_response.metadata.get("improvements", [])
                },
                "next_question": next_question_content,
                "agent": "evaluator",
                "dsa_stage": to_stage
            }
            
        else:
            # Determine whether to ask a follow-up (drill-down) or pivot to a new topic (continue)
            is_technical = context.interview_type in ("technical", "mixed")
            if is_technical and context.current_topic_followups == 0:
                context.current_topic_followups = 1
                msg_type = "follow_up"
            else:
                context.current_topic_followups = 0
                msg_type = "continue"

            # Get next question
            next_message = AgentMessage(
                from_agent=AgentRole.COORDINATOR,
                to_agent=AgentRole.INTERVIEWER,
                content=answer,
                message_type=msg_type
            )
            
            next_response = await self.agents[AgentRole.INTERVIEWER].process(next_message, context)
            
            return {
                "evaluation": {
                    "score": score,
                    "feedback": eval_response.content,
                    "breakdown": eval_response.metadata.get("breakdown", {}),
                    "strengths": eval_response.metadata.get("strengths", []),
                    "improvements": eval_response.metadata.get("improvements", [])
                },
                "next_question": next_response.content,
                "agent": "evaluator"
            }
    
    async def request_hint(
        self, 
        context: InterviewContext, 
        hint_level: int = 1
    ) -> Dict[str, Any]:
        """Request a hint for current question."""
        message = AgentMessage(
            from_agent=AgentRole.COORDINATOR,
            to_agent=AgentRole.HINT_PROVIDER,
            content="Need a hint",
            message_type="request_hint",
            metadata={"hint_level": hint_level}
        )
        
        response = await self.agents[AgentRole.HINT_PROVIDER].process(message, context)
        context.hints_used += 1
        
        return {
            "hint": response.content,
            "hint_level": hint_level,
            "penalty": response.metadata.get("penalty", 0.05),
            "hints_used": context.hints_used,
            "agent": "hint_provider"
        }
    
    async def end_interview(self, context: InterviewContext) -> Dict[str, Any]:
        """End interview and get final coaching."""
        message = AgentMessage(
            from_agent=AgentRole.COORDINATOR,
            to_agent=AgentRole.CAREER_COACH,
            content="Interview complete",
            message_type="end_interview"
        )
        
        coaching_response = await self.agents[AgentRole.CAREER_COACH].process(message, context)
        
        # Calculate final stats
        avg_score = sum(context.scores) / len(context.scores) if context.scores else 0
        hint_penalty = context.hints_used * 0.05
        final_score = max(0, avg_score * (1 - hint_penalty))
        
        return {
            "final_score": round(final_score, 1),
            "questions_answered": len(context.answers_given),
            "hints_used": context.hints_used,
            "coaching": coaching_response.content,
            "performance_breakdown": {
                "raw_avg": round(avg_score, 1),
                "hint_penalty": f"-{hint_penalty*100:.0f}%",
                "final": round(final_score, 1)
            },
            "agent": "career_coach"
        }


# ============ Service Interface ============

from ..redis_client import get_redis

def _serialize_context(ctx) -> str:
    """Serialize InterviewContext to JSON for Redis storage."""
    def default(o):
        if hasattr(o, '__dict__'):
            return o.__dict__
        if hasattr(o, 'value'):
            return o.value  # Enum
        if isinstance(o, datetime):
            return o.isoformat()
        return str(o)
    data = ctx.to_dict() if hasattr(ctx, 'to_dict') else (ctx.__dict__ if hasattr(ctx, '__dict__') else ctx)
    return json.dumps(data, default=default)

def _deserialize_context(data_str: str) -> Optional[InterviewContext]:
    """Deserialize JSON string to InterviewContext."""
    try:
        data = json.loads(data_str)
        return InterviewContext.from_dict(data)
    except Exception as e:
        logger.error(f"Failed to deserialize InterviewContext: {e}")
        return None

class MultiAgentInterviewService:
    """
    High-level service for multi-agent interviews.
    Manages sessions with L1 (in-memory) and L2 (Redis) caching.
    """
    
    def __init__(self):
        self.coordinator = CoordinatorAgent()
        self.active_contexts: Dict[str, InterviewContext] = {}
        self.last_accessed: Dict[str, datetime] = {}
        self._eviction_task_started = False
    
    def _start_eviction_task_if_needed(self):
        if not self._eviction_task_started:
            try:
                loop = asyncio.get_running_loop()
                if loop.is_running():
                    loop.create_task(self._periodic_evict_sessions())
                    self._eviction_task_started = True
            except RuntimeError:
                pass

    async def _periodic_evict_sessions(self):
        """Evict in-memory sessions that haven't been accessed in 30 minutes."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                now = datetime.utcnow()
                to_evict = []
                for session_id, last_time in list(self.last_accessed.items()):
                    if (now - last_time).total_seconds() > 1800:  # 30 minutes
                        to_evict.append(session_id)
                for session_id in to_evict:
                    logger.info(f"Evicting idle in-memory session {session_id} from L1 cache")
                    self.active_contexts.pop(session_id, None)
                    self.last_accessed.pop(session_id, None)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in session eviction task: {e}")

    async def _save_to_redis(self, context: InterviewContext):
        """Write session to Redis with 1 hour TTL."""
        try:
            redis_client = get_redis()
            if redis_client:
                key = f"interview:session:{context.session_id}"
                serialized = _serialize_context(context)
                await redis_client.set(key, serialized, ex=3600)
        except Exception as e:
            logger.warning(f"Redis write failed, falling back to L1 cache only: {e}")

    async def _get_from_redis(self, session_id: str) -> Optional[InterviewContext]:
        """Read session from Redis."""
        try:
            redis_client = get_redis()
            if redis_client:
                key = f"interview:session:{session_id}"
                data_str = await redis_client.get(key)
                if data_str:
                    return _deserialize_context(data_str)
        except Exception as e:
            logger.warning(f"Redis read failed, falling back to L1 cache only: {e}")
        return None

    async def _delete_from_redis(self, session_id: str):
        """Delete session from Redis."""
        try:
            redis_client = get_redis()
            if redis_client:
                key = f"interview:session:{session_id}"
                await redis_client.delete(key)
        except Exception as e:
            logger.warning(f"Redis delete failed: {e}")

    async def create_context(
        self,
        session_id: str,
        student_id: str,
        company: str = "Tech Company",
        role: str = "Software Engineer",
        difficulty: str = "medium",
        interview_type: str = "mixed",
        resume_text: str = ""
    ) -> InterviewContext:
        """Create new interview context."""
        context = InterviewContext(
            session_id=session_id,
            student_id=student_id,
            company=company,
            role=role,
            difficulty=difficulty,
            interview_type=interview_type,
            resume_text=resume_text
        )
        await self.update_context(context)
        return context

    async def create_session(self, *args, **kwargs) -> InterviewContext:
        """Alias for create_context to support alternative naming conventions."""
        return await self.create_context(*args, **kwargs)
    
    async def get_context(self, session_id: str) -> Optional[InterviewContext]:
        """Get existing context, checking L1 first, then L2 Redis."""
        self.last_accessed[session_id] = datetime.utcnow()
        self._start_eviction_task_if_needed()

        if session_id in self.active_contexts:
            return self.active_contexts[session_id]

        context = await self._get_from_redis(session_id)
        if context:
            self.active_contexts[session_id] = context
            return context

        return None

    async def get_session(self, session_id: str) -> Optional[InterviewContext]:
        """Alias for get_context to support alternative naming conventions."""
        return await self.get_context(session_id)

    async def update_context(self, context: InterviewContext):
        """Update context in both L1 (in-memory) and L2 (Redis)."""
        session_id = context.session_id
        self.last_accessed[session_id] = datetime.utcnow()
        self._start_eviction_task_if_needed()

        self.active_contexts[session_id] = context
        await self._save_to_redis(context)
    
    async def start(
        self,
        session_id: str,
        student_id: str,
        company: str = "Tech Company",
        role: str = "Software Engineer",
        difficulty: str = "medium",
        interview_type: str = "mixed",
        resume_text: str = ""
    ) -> Dict[str, Any]:
        """Start new multi-agent interview."""
        context = await self.create_context(
            session_id, student_id, company, role, difficulty,
            interview_type, resume_text
        )
        result = await self.coordinator.start_interview(context)

        # Store current question & increment counter
        context.current_question = {"content": result["question"]}
        context.questions_asked.append(context.current_question)
        context.question_count += 1

        await self.update_context(context)
        return result
    
    async def answer(self, session_id: str, answer: str) -> Dict[str, Any]:
        """Submit answer for current question."""
        context = await self.get_context(session_id)
        if not context:
            return {"error": "Session not found"}

        result = await self.coordinator.submit_answer(context, answer)

        # Update current question & counter
        context.current_question = {"content": result["next_question"]}
        context.questions_asked.append(context.current_question)
        context.question_count += 1

        await self.update_context(context)
        return result
    
    async def hint(self, session_id: str, level: int = 1) -> Dict[str, Any]:
        """Request hint for current question."""
        context = await self.get_context(session_id)
        if not context:
            return {"error": "Session not found"}
        
        result = await self.coordinator.request_hint(context, level)
        await self.update_context(context)
        return result
    
    async def finish(self, session_id: str) -> Dict[str, Any]:
        """End interview and get final results."""
        context = await self.get_context(session_id)
        if not context:
            return {"error": "Session not found"}

        result = await self.coordinator.end_interview(context)
        result["question_count"] = context.question_count

        await self.update_context(context)
        return result

    async def feedback(self, session_id: str) -> Dict[str, Any]:
        """Generate structured 7-dimension feedback from full conversation."""
        context = await self.get_context(session_id)
        if not context:
            return {"error": "Session not found"}

        llm = None
        try:
            from .llm_service import llm_service
            llm = llm_service
        except Exception:
            pass

        # Build conversation transcript
        transcript = []
        qs = context.questions_asked
        ans = context.answers_given
        for i, a in enumerate(ans):
            q_text = qs[i]["content"] if i < len(qs) else "(question)"
            transcript.append(f"Q{i+1}: {q_text}")
            transcript.append(f"A{i+1}: {a.get('answer', '')}")
        transcript_str = "\n".join(transcript) or "No answers recorded."

        avg_score = sum(context.scores) / len(context.scores) if context.scores else 50

        if llm:
            try:
                prompt = f"""You are an expert interview evaluator. Analyze this interview transcript and return ONLY a JSON object.

CANDIDATE: {context.role} at {context.company}
TRANSCRIPT:
{transcript_str[:3000]}

Return ONLY this JSON (no markdown, no explanation):
{{
  "communication_clarity": <0-100>,
  "technical_depth": <0-100>,
  "confidence": <0-100>,
  "overall_rating": <1.0-5.0>,
  "strengths": ["<strength1>", "<strength2>", "<strength3>"],
  "improvements": ["<area1>", "<area2>", "<area3>"],
  "suggested_answers": {{
    "best_moment": "<which answer was strongest and why>",
    "improve_this": "<which answer needed work and a better version>"
  }},
  "summary": "<2-3 sentence overall assessment>"
}}"""
                raw = await llm.generate(prompt, "You are an expert interview coach. Return ONLY valid JSON.")
                import re, json as _json
                m = re.search(r'\{[\s\S]*\}', raw)
                if m:
                    return _json.loads(m.group())
            except Exception:
                pass

        # Graceful fallback
        rating = round(1 + (avg_score / 100) * 4, 1)
        return {
            "communication_clarity": int(avg_score),
            "technical_depth": max(30, int(avg_score) - 5),
            "confidence": min(100, int(avg_score) + 5),
            "overall_rating": rating,
            "strengths": ["Attempted all questions", "Showed engagement", "Communicated clearly"],
            "improvements": ["Add more specific examples", "Discuss complexity tradeoffs", "Structure answers with STAR method"],
            "suggested_answers": {
                "best_moment": "Your introductory answer showed good self-awareness.",
                "improve_this": "Technical answers could benefit from concrete code examples or system diagrams."
            },
            "summary": f"Overall performance: {avg_score:.0f}/100. You completed {context.question_count} questions. Keep practicing to build confidence and depth."
        }

    async def cleanup(self, session_id: str):
        """Remove session context from L1 and L2."""
        self.active_contexts.pop(session_id, None)
        self.last_accessed.pop(session_id, None)
        await self._delete_from_redis(session_id)

    async def cleanup_session(self, session_id: str):
        """Alias for cleanup to support alternative naming conventions."""
        await self.cleanup(session_id)

    def get_active_sessions(self) -> List[str]:
        """Get list of active session IDs."""
        return list(self.active_contexts.keys())


# Singleton instance
multi_agent_interview = MultiAgentInterviewService()
