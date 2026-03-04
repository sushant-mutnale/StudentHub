"""
Multi-Agent Interview System
LangChain-based multi-agent framework for realistic interview simulation.
Agents: Interviewer, Evaluator, Hint Provider, Career Coach, Coordinator.
"""

import os
import json
import asyncio
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum


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
        return """You are Alex, a senior software engineer at a top tech company. You are the INTERVIEWER.
The user (the person responding to you) is the CANDIDATE who is being interviewed.

Your responsibilities:
- Ask the candidate questions (you do NOT answer questions yourself)
- Evaluate their responses and decide the next question
- Be professional, encouraging, and conversational
- Ask ONE question at a time
- NEVER introduce yourself as the candidate or describe your own experience as a job-seeker

Remember: YOU ask questions. The CANDIDATE answers them."""

    
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
                
                # Format exactly like a Leetcode problem description
                formatted_question = f"### {question['title']}\n\n"
                formatted_question += f"**Description:**\n{question['description']}\n\n"
                
                if question.get('examples'):
                    formatted_question += "**Examples:**\n"
                    for i, ex in enumerate(question['examples'], 1):
                        formatted_question += f"*Example {i}:*\n"
                        formatted_question += f"Input: {ex.get('input', '')}\n"
                        formatted_question += f"Output: {ex.get('output', '')}\n\n"
                
                if question.get('constraints'):
                    formatted_question += "**Constraints:**\n"
                    for c in question['constraints']:
                        formatted_question += f"- {c}\n"
                        
                return formatted_question
            except Exception as e:
                print(f"Error generating intro DSA question: {e}")
                pass
                
        llm = self._get_llm()
        if not llm:
            return self._get_fallback_opening(context)

        resume_snippet = ""
        if context.resume_text:
            resume_snippet = f"\nCANDIDATE RESUME SUMMARY (first 500 chars):\n{context.resume_text[:500]}\nUse this to personalize your greeting — mention 1 specific skill or project you noticed.\n"

        interview_focus = ""
        if context.interview_type == "behavioral":
            interview_focus = "This will be a behavioral interview focusing on past experiences and soft skills."
        elif context.interview_type == "technical":
            interview_focus = "This will be a technical interview covering coding, system design, and technical depth."
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

        # --- Determine interview stage based on type and count ---
        is_behavioral_only = context.interview_type == "behavioral"
        is_technical_only  = context.interview_type == "technical"
        is_dsa_only        = context.interview_type == "dsa"

        if is_dsa_only:
            stage = "dsa_follow_up"
            instruction = f"""The candidate just submitted a code solution or answer. Answer: "{last_answer[:600]}"
            
You are conducting a strict DSA (Data Structures and Algorithms) interview. 
DO NOT ask open-ended system design questions. DO NOT ask behavioral questions.

Ask ONE direct, targeted follow-up question about their solution:
- Ask them to analyze the time and space complexity.
- Point out a potential edge case and ask how their code handles it (e.g., empty input, negative numbers).
- Ask if there's a more optimal way (e.g., O(N) instead of O(N^2)).

One question only, conversational and direct."""

        elif num_answered <= 1:
            stage = "behavioral"
            instruction = f"""The candidate just introduced themselves. Now ask ONE behavioral question.
- Use the STAR method context (Situation, Task, Action, Result)
- Reference something they shared in their intro if possible
- Themes: teamwork, handling failure, leadership, problem-solving under pressure
- One question only, conversational tone"""

        elif num_answered <= 3 and not is_behavioral_only:
            stage = "technical_discussion"
            instruction = f"""Move to a technical discussion question for a {context.role} at {context.company}.
Based on what they said: "{last_answer[:300]}"

IMPORTANT: This is a VOICE interview. Do NOT ask them to write code or implement anything.
Instead, ask a question they can ANSWER VERBALLY:
- System design: "How would you design X? Walk me through your approach."
- Architecture: "What database would you choose for X and why?"
- Concepts: "Explain how Y works and when you'd use it."
- Trade-offs: "What are the tradeoffs between approach A and B?"
- Experience: "Have you worked with X? Tell me about that experience."

Difficulty: {difficulty} (avg score so far: {avg_score:.0f}%)
Do NOT repeat these topics: {', '.join(previous_qs) or 'none yet'}

One question only. Start with a brief transition like "Let's explore some technical areas..."."""

        elif is_behavioral_only:
            stage = "behavioral_deep"
            instruction = f"""Continue behavioral questioning. Last answer: "{last_answer[:300]}"

Ask a follow-up behavioral question that:
- Digs into a different soft skill or situation type
- Could probe: conflict resolution, mentoring, receiving feedback, working under pressure, initiative
- References their answer if useful
- Is NOT a repeat of previous questions: {', '.join(previous_qs) or 'none yet'}

One question only."""

        else:
            stage = "cross_question"
            instruction = f"""Cross-question the candidate based on their last answer: "{last_answer[:400]}"

This is a VOICE interview — no code writing. Ask a verbal follow-up that:
- Challenges an assumption they made
- Asks for a concrete real-world example from their experience
- Explores edge cases or trade-offs they glossed over
- Asks how they'd handle a specific scenario related to what they said
- Probes technical depth without asking to write code

Be curious and direct. One follow-up question only."""

        prompt = f"""Company: {context.company} | Role: {context.role} | Stage: {stage}

{instruction}"""

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
        
        prompt = f"""The candidate just answered: "{answer[:500]}"

Generate a brief follow-up question to dig deeper. Could be about:
- Time/space complexity
- Edge cases
- Alternative approaches
- Real-world considerations

Keep it concise and natural."""
        
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
        return """You are Eva, an expert technical evaluator.

Your role:
- Provide fair, objective assessments
- Score based on correctness, clarity, and depth
- Identify specific strengths and weaknesses
- Give constructive, actionable feedback

Be encouraging but honest. Focus on helping candidates improve."""
    
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
        
        prompt = f"""Evaluate this interview answer:

QUESTION: {question.get('content', question.get('title', 'Unknown'))}
ANSWER: {answer[:1500]}
CONTEXT: {context.role} at {context.company}

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
        return """You are Charlie, an experienced career coach and mentor.

Your role:
- Provide actionable career advice
- Help candidates improve their interview skills
- Give motivating, honest feedback
- Suggest specific resources and practice areas

Be encouraging and supportive while being constructive."""
    
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
        eval_message = AgentMessage(
            from_agent=AgentRole.COORDINATOR,
            to_agent=AgentRole.EVALUATOR,
            content="Evaluate this answer",
            message_type="evaluate",
            metadata={
                "answer": answer,
                "question": context.current_question
            }
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
        
        # Get next question
        next_message = AgentMessage(
            from_agent=AgentRole.COORDINATOR,
            to_agent=AgentRole.INTERVIEWER,
            content=answer,
            message_type="continue"
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

class MultiAgentInterviewService:
    """
    High-level service for multi-agent interviews.
    Manages sessions and provides API-friendly interface.
    """
    
    def __init__(self):
        self.coordinator = CoordinatorAgent()
        self.active_contexts: Dict[str, InterviewContext] = {}
    
    def create_context(
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
        self.active_contexts[session_id] = context
        return context
    
    def get_context(self, session_id: str) -> Optional[InterviewContext]:
        """Get existing context."""
        return self.active_contexts.get(session_id)
    
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
        context = self.create_context(
            session_id, student_id, company, role, difficulty,
            interview_type, resume_text
        )
        result = await self.coordinator.start_interview(context)

        # Store current question & increment counter
        context.current_question = {"content": result["question"]}
        context.questions_asked.append(context.current_question)
        context.question_count += 1

        return result
    
    async def answer(self, session_id: str, answer: str) -> Dict[str, Any]:
        """Submit answer for current question."""
        context = self.get_context(session_id)
        if not context:
            return {"error": "Session not found"}

        result = await self.coordinator.submit_answer(context, answer)

        # Update current question & counter
        context.current_question = {"content": result["next_question"]}
        context.questions_asked.append(context.current_question)
        context.question_count += 1

        return result
    
    async def hint(self, session_id: str, level: int = 1) -> Dict[str, Any]:
        """Request hint for current question."""
        context = self.get_context(session_id)
        if not context:
            return {"error": "Session not found"}
        
        return await self.coordinator.request_hint(context, level)
    
    async def finish(self, session_id: str) -> Dict[str, Any]:
        """End interview and get final results."""
        context = self.get_context(session_id)
        if not context:
            return {"error": "Session not found"}

        result = await self.coordinator.end_interview(context)
        result["question_count"] = context.question_count

        # Keep context briefly for feedback call (don't delete immediately)
        # It will be cleaned up in feedback() or after 30 min
        return result

    async def feedback(self, session_id: str) -> Dict[str, Any]:
        """Generate structured 7-dimension feedback from full conversation."""
        context = self.get_context(session_id)
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

    def cleanup(self, session_id: str):
        """Remove session context."""
        self.active_contexts.pop(session_id, None)

    def get_active_sessions(self) -> List[str]:
        """Get list of active session IDs."""
        return list(self.active_contexts.keys())


# Singleton instance
multi_agent_interview = MultiAgentInterviewService()
