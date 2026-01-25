# Module 3 Advanced: AI-Powered Enhancements
## Week 9-12 Implementation Plan

---

## Technology Stack

### Already Using (No Changes Needed)
- FastAPI, MongoDB, Pydantic, Gemini API (llm_service.py)

### New Libraries to Install
```bash
pip install langchain langchain-google-genai docker beautifulsoup4 apscheduler
```

---

## WEEK 9: AI Planner Agent

### What You're Building
An intelligent agent that creates personalized study plans based on:
- Gap analysis results
- Target company interview patterns
- Available preparation time
- Learning style preference

### How It Connects to Current System
```
gap_analysis_service.py → AI Planner Agent → Personalized Day-by-Day Plan
```

### Step 1: Create Planner Agent Service
**File:** `backend/services/ai_planner_agent.py`

What it does:
1. Takes gap analysis output (missing skills, proficiency levels)
2. Gets company interview patterns from company_research.py
3. Uses LLM to create structured study plan
4. Returns week-by-week, day-by-day schedule

Key Functions:
- `create_study_plan(gaps, company, prep_weeks, hours_per_day)`
- `adjust_plan(progress_update, remaining_time)`
- `get_daily_tasks(date)`
- `mark_task_complete(task_id)`

### Step 2: Daily Task Generator
What it generates for each day:
- Specific LeetCode problems to solve
- Video tutorials to watch
- Mock interview topics
- Reading materials

Example Output:
```json
{
  "day": 1,
  "date": "2026-01-26",
  "focus_topic": "Arrays & Hashing",
  "tasks": [
    {"type": "leetcode", "problem": "Two Sum", "difficulty": "easy", "time": 30},
    {"type": "video", "title": "Array Patterns", "url": "...", "time": 20},
    {"type": "practice", "action": "Solve 2 more array problems", "time": 40}
  ],
  "total_hours": 1.5
}
```

### Step 3: Progress Tracking
- Track completed tasks
- Adjust future plan based on performance
- Send reminders for incomplete tasks

### Step 4: API Endpoints
- `POST /planner/create` - Create new study plan
- `GET /planner/today` - Get today's tasks
- `POST /planner/complete/{task_id}` - Mark task done
- `GET /planner/progress` - Overall progress report

---

## WEEK 10: Sandbox Code Execution

### What You're Building
Secure environment to actually run student code and verify correctness.

### How It Connects to Current System
```
answer_evaluator.py → Sandbox → Real Correctness Score
```

### Option A: Docker-based Sandbox (Self-hosted)
Uses Docker containers to run untrusted code safely.

**File:** `backend/services/code_sandbox.py`

How it works:
1. Receive student's code
2. Spin up isolated Docker container
3. Run code with test cases
4. Capture output, compare with expected
5. Return results (passed/failed, time, memory)
6. Destroy container

Resource Limits:
- CPU: 1 core max
- Memory: 256MB max
- Time: 10 seconds max
- Network: Disabled

### Option B: Piston API (Cloud-based, Easier)
Use free Piston API for code execution.

Supported Languages:
- Python, JavaScript, Java, C++, Go, Rust, etc.

API Call:
```python
response = requests.post("https://emkc.org/api/v2/piston/execute", json={
    "language": "python",
    "version": "3.10",
    "files": [{"content": student_code}],
    "stdin": test_input
})
```

### Step 1: Create Sandbox Service
Key Functions:
- `execute_code(language, code, stdin, timeout)`
- `run_test_cases(code, test_cases)`
- `calculate_score(results)`

### Step 2: Integrate with Answer Evaluator
Modify `answer_evaluator.py`:
```python
# Before (heuristic only)
score = self._rule_based_evaluate(code)

# After (sandbox + heuristic)
if sandbox_available:
    execution_score = await sandbox.run_test_cases(code, question["test_cases"])
    score = (execution_score * 0.7) + (heuristic_score * 0.3)
```

### Step 3: API Endpoints
- `POST /sandbox/run` - Execute code
- `POST /sandbox/test` - Run with test cases

---

## WEEK 11: Deep Research Tool

### What You're Building
Background service that:
1. Scrapes interview data from public sources
2. Updates company_interview_data.py automatically
3. Tracks trending DSA topics

### How It Connects to Current System
```
Deep Research Tool → company_interview_data.py (auto-update)
```

### Step 1: Web Scraper Service
**File:** `backend/services/research_agent.py`

Sources to scrape:
- LeetCode company tag pages
- GitHub interview repositories
- Public interview blogs

What to extract:
- Common DSA topics per company
- Recent interview experiences
- Trending problems

### Step 2: Background Job Scheduler
Use APScheduler for periodic updates:
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('cron', hour=2)  # Run daily at 2 AM
async def update_company_data():
    await research_agent.refresh_all_companies()
```

### Step 3: Data Validation
Before updating knowledge base:
- Validate scraped data format
- Check for duplicates
- Merge with existing data

### Step 4: API Endpoints
- `POST /research/refresh/{company}` - Manually refresh
- `GET /research/trending` - Get trending topics
- `GET /research/status` - Last update status

---

## WEEK 12: Multi-Agent Interviewer

### What You're Building
A system with multiple specialized AI agents that work together:

1. **Interviewer Agent** - Asks questions, follows up
2. **Evaluator Agent** - Scores answers in real-time
3. **Hint Agent** - Provides hints when stuck
4. **Coach Agent** - Gives encouragement, manages time

### How It Connects to Current System
```
interview_orchestrator.py → Multi-Agent Coordinator → Realistic Interview
```

### Step 1: Create Agent Framework
**File:** `backend/services/multi_agent_system.py`

Using LangChain:
```python
from langchain.agents import Agent, AgentExecutor
from langchain_google_genai import ChatGoogleGenerativeAI

class InterviewerAgent:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(model="gemini-pro")
        
    async def ask_question(self, context):
        # Generate contextual question
        
    async def follow_up(self, answer):
        # Generate follow-up based on answer
```

### Step 2: Agent Communication Protocol
Agents communicate via message passing:
```python
class AgentMessage:
    from_agent: str
    to_agent: str
    message_type: str  # "question", "evaluation", "hint", "command"
    content: dict
```

### Step 3: Conversation Flow
```
User answers → Evaluator scores → 
  If score < 50 → Hint Agent provides hint
  If score > 80 → Interviewer asks harder follow-up
  Coach monitors time and gives encouragement
```

### Step 4: Human-in-the-Loop Option
Allow human mentor to:
- Override AI evaluations
- Inject custom questions
- Provide personalized feedback

### Step 5: API Endpoints
- `POST /agents/start-interview` - Start multi-agent session
- `POST /agents/submit` - Submit answer to agents
- `GET /agents/conversation` - Get full conversation
- `POST /agents/mentor-override` - Human override

---

## Summary: What Builds on What

| Week 9-12 Feature | Uses These From Week 2-8 |
|-------------------|-------------------------|
| AI Planner | gap_analysis_service, learning_paths |
| Sandbox | answer_evaluator, question_generator |
| Deep Research | company_interview_data, company_research |
| Multi-Agent | interview_orchestrator, all evaluators |

---

## Installation & Setup

### Install New Dependencies
```bash
cd project
pip install langchain langchain-google-genai docker beautifulsoup4 apscheduler lxml
```

### Docker Setup (for Sandbox)
```bash
# Install Docker Desktop (Windows)
# Or use Piston API (no setup needed)
```

### Environment Variables
```env
# Already have
GEMINI_API_KEY=your_key

# New (optional)
PISTON_API_URL=https://emkc.org/api/v2/piston
SCRAPER_USER_AGENT=StudentHub/1.0
```

---

## Ready to Implement?

Week 9 (AI Planner) - Estimated: 15-20 tool calls
Week 10 (Sandbox) - Estimated: 10-15 tool calls  
Week 11 (Research) - Estimated: 12-18 tool calls
Week 12 (Multi-Agent) - Estimated: 20-25 tool calls

Which week would you like to start with?
