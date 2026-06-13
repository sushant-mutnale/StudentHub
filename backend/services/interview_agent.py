"""
Interview Agent Service

Manages conversational interviews with candidates.
Maintains session state and uses RAG for context.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from bson import ObjectId

from backend.database import get_database
from backend.services.rag_manager import rag_manager
from backend.config import settings

logger = logging.getLogger(__name__)

class InterviewAgent:
    """
    AI Interviewer that conducts structured or semi-structured interviews.
    """
    
    
    def __init__(self):
        pass
        
    @property
    def sessions_collection(self):
        return get_database()["interview_sessions"]

    @property
    def jobs_collection(self):
        return get_database()["jobs"]

    @property
    def opportunities_jobs_collection(self):
        return get_database()["opportunities_jobs"]

        
    async def start_session(self, user_id: str, job_id: str) -> str:
        """
        Initialize a new interview session.
        """
        # Fetch Job Context
        job = await self.jobs_collection.find_one({"_id": ObjectId(job_id)})
        if not job:
            job = await self.opportunities_jobs_collection.find_one({"_id": ObjectId(job_id)})
            
        if not job:
            raise ValueError("Job not found")
            
        # Fetch Candidate Resume Context
        resume_doc = await get_database()["resume_uploads"].find_one(
            {"student_id": ObjectId(user_id)},
            sort=[("uploaded_at", -1)]
        )
        resume_text = ""
        if resume_doc:
            resume_text = resume_doc.get("raw_text", "")
            if not resume_text and resume_doc.get("parsed_data"):
                pd = resume_doc["parsed_data"]
                skills = ", ".join(pd.get("skills", []))
                resume_text = f"Skills: {skills}"

        system_instruction = (
            f"You are an AI interviewer for the role of {job.get('title')}.\n"
            f"Company / Job Description Details:\n{job.get('description')}\n\n"
            f"Candidate Resume Details:\n{resume_text or 'No resume details provided.'}\n\n"
            "Interviewer Guidelines:\n"
            "- Conduct a professional, realistic interview.\n"
            "- Keep replies very concise (under 50 words) to support natural voice flow.\n"
            "- Ask one question at a time.\n"
            "- Reference candidate's resume projects or skills organically where appropriate.\n"
            "- In your first greeting, introduce yourself and ask an opening question referencing their background."
        )

        session = {
            "user_id": ObjectId(user_id),
            "job_id": ObjectId(job_id),
            "job_title": job.get("title"),
            "job_description": job.get("description"),
            "resume_text": resume_text,
            "history": [
                {"role": "system", "content": system_instruction}
            ],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = await self.sessions_collection.insert_one(session)
        return str(result.inserted_id)

    async def get_session(self, session_id: str):
        return await self.sessions_collection.find_one({"_id": ObjectId(session_id)})

    async def chat(self, session_id: str, user_message: str) -> str:
        """
        Process user message and return agent response.
        """
        session = await self.get_session(session_id)
        if not session:
            raise ValueError("Session not found")
            
        # 1. Append User Message
        await self.sessions_collection.update_one(
            {"_id": ObjectId(session_id)},
            {"$push": {"history": {"role": "user", "content": user_message}}}
        )
        
        # 2. Query LLM Service with conversation history
        try:
            # Reload session to get latest history
            updated_session = await self.get_session(session_id)
            history = updated_session.get("history", [])
            
            from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
            from backend.services.llm_service import llm_service
            
            lc_messages = []
            for msg in history:
                role = msg.get("role")
                content = msg.get("content", "")
                if role == "system":
                    lc_messages.append(SystemMessage(content=content))
                elif role == "user":
                    lc_messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    lc_messages.append(AIMessage(content=content))
            
            # Generate LLM response
            response_text = await llm_service.generate_from_messages(lc_messages)
            response_text = response_text.strip()
            
            # Handle empty or error messages gracefully
            if response_text.startswith("Error:") or not response_text:
                logger.error(f"LLM generation failed: {response_text}")
                response_text = "Got it. Let's move to the next technical topic. Tell me about your experience with building REST APIs."
                
        except Exception as e:
            logger.error(f"Interview Agent Chat Error: {e}")
            response_text = "Understood. Let's proceed. Can you explain how you handle database connections efficiently in an API?"
            
        # 3. Append Agent Response
        await self.sessions_collection.update_one(
            {"_id": ObjectId(session_id)},
            {"$push": {"history": {"role": "assistant", "content": response_text}}, "$set": {"updated_at": datetime.utcnow()}}
        )
        
        return response_text

interview_agent = InterviewAgent()
