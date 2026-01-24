"""
AI Prompt Templates for Learning Module
Centralized prompts for gap analysis, recommendations, and learning paths.
"""

# System prompts
SKILL_ADVISOR_SYSTEM = """You are an expert career advisor and learning strategist for software engineering students.
You help students identify skill gaps and create personalized learning paths.
Be concise, specific, and actionable. Focus on practical advice.
Always recommend FREE resources when possible."""

LEARNING_COACH_SYSTEM = """You are a personalized learning coach for software engineering students.
You understand modern tech stacks, industry requirements, and effective learning strategies.
Your recommendations should be practical, time-efficient, and tailored to the student's background.
Focus on building skills that are most valuable for job readiness."""


# Gap Analysis Prompts
GAP_RECOMMENDATION_PROMPT = """Analyze this skill gap for a student seeking a tech job:

**Student's Current Skills:** {student_skills}
**Job Required Skills:** {required_skills}
**Missing Skills (High Priority):** {high_priority_gaps}
**Missing Skills (Medium Priority):** {medium_priority_gaps}
**Match Percentage:** {match_percentage}%

Provide a brief, actionable recommendation (2-3 sentences) that:
1. Acknowledges their strengths
2. Prioritizes which gaps to address first
3. Suggests a realistic timeline

Keep it encouraging but honest. Be specific about skill names."""


SKILL_SIMILARITY_PROMPT = """Given these two skills, determine if they are related or transferable:

Skill 1: {skill1}
Skill 2: {skill2}

Respond with ONLY one of these options:
- "SAME" - They are the same skill (just different names)
- "SIMILAR" - Related skills with transferable knowledge (e.g., React and Vue.js)
- "DIFFERENT" - Unrelated skills

Response:"""


# Learning Path Prompts
PERSONALIZED_PATH_PROMPT = """Create a personalized learning recommendation for this student:

**Skill to Learn:** {skill}
**Student's Background:**
- Current Skills: {current_skills}
- Experience Level: {experience_level}
- Available Time per Week: {hours_per_week} hours

**Gap Priority:** {priority}
**Target Proficiency:** From {current_level}% to {target_level}%

Provide:
1. Why this skill matters for their career (1 sentence)
2. Learning approach based on their background (1-2 sentences)
3. Key milestones to track progress (3 bullet points)
4. Estimated timeline

Keep response under 150 words. Be specific and practical."""


RESOURCE_RECOMMENDATION_PROMPT = """You are a course recommendation expert. Analyze these search results and recommend the best courses for the student.

**Skill to Learn:** {skill}

**Available Courses:**
{courses_list}

**Student Context:**
{student_context}

**Task:** Select the top {num_recommendations} courses from the list above. Consider:
1. Content quality (prefer well-known platforms and instructors)
2. Match with student's current level
3. Course type variety (mix of videos, courses, articles)
4. Relevance to the skill being learned

**Respond with:**
- The numbers of your top picks in order (e.g., 1, 4, 7, 3, 9)
- A brief reason for each pick (1 sentence)

Be concise. Focus on practical value for the student."""


LEARNING_ORDER_PROMPT = """Given these skills that a student needs to learn, suggest the optimal order:

**Skills to Learn:** {skills}
**Student's Current Skills:** {current_skills}

Consider:
- Prerequisites (what needs to be learned first)
- Synergy (skills that complement each other)
- Industry priority (most demanded first)

Respond with the skills in order, numbered 1-N, with a brief reason for each (1 sentence)."""


# Interview Prep Prompts (for later modules)
INTERVIEW_QUESTION_PROMPT = """Generate a technical interview question for:

**Company:** {company}
**Role:** {role}
**Topic:** {topic}
**Difficulty:** {difficulty}

The question should be:
- Realistic for the company's interview style
- Appropriate for the role level
- Clear and well-scoped

Provide:
1. The question
2. Key points the interviewer looks for (3-4 bullet points)
3. Common mistakes candidates make"""


ANSWER_EVALUATION_PROMPT = """Evaluate this interview answer:

**Question:** {question}
**Candidate's Answer:** {answer}
**Expected Key Points:** {key_points}

Provide:
1. Score (0-100)
2. Strengths (2-3 bullet points)
3. Areas to improve (2-3 bullet points)
4. Suggested better answer (if score < 80)

Be constructive and specific. Focus on actionable feedback."""

