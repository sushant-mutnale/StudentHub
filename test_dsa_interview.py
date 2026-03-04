import asyncio
from backend.services.multi_agent_system import multi_agent_interview
import uuid

async def test_dsa_interview():
    session_id = str(uuid.uuid4())
    print(f"Starting DSA interview session: {session_id}")
    
    result = await multi_agent_interview.start(
        session_id=session_id,
        student_id="test_student",
        company="Google",
        role="Software Engineer",
        difficulty="medium",
        interview_type="dsa", 
        resume_text=""
    )
    
    print("\n--- FIRST QUESTION (from Coordinator / Interviewer) ---")
    print(result.get("question", "NO QUESTION RETURNED"))
    print("------------------------------------------------------\n")
    
    print("Submitting a poor answer...")
    answer_result = await multi_agent_interview.answer(
        session_id=session_id,
        answer="I don't know how to solve this."
    )
    
    print("\n--- EVALUATION RESPONSE ---")
    score = answer_result.get("evaluation", {}).get("score", "NO SCORE")
    print(f"Score: {score}")
    print(f"Feedback: {answer_result.get('evaluation', {}).get('feedback', '')}")
    print("---------------------------\n")

if __name__ == "__main__":
    asyncio.run(test_dsa_interview())
