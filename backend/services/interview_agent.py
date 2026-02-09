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
        # 1. Fetch Job Context (from RAG or DB)
        # We can use RAG to get the simplified "Job Description" vector text
        # Or just fetch from DB. For the agent prompt, DB text is fine.
        job = await self.jobs_collection.find_one({"_id": ObjectId(job_id)})
        if not job:
            job = await self.opportunities_jobs_collection.find_one({"_id": ObjectId(job_id)})
            
        if not job:
            raise ValueError("Job not found")
            
        session = {
            "user_id": ObjectId(user_id),
            "job_id": ObjectId(job_id),
            "job_title": job.get("title"),
            "job_description": job.get("description"), # Pass this to system prompt
            "history": [
                {"role": "system", "content": f"You are an AI interviewer for the role of {job.get('title')}. Conduct a professional technical interview based on the description: {job.get('description')}. Be polite but rigorous."}
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
        
        # 2. Generate Response (Mock LLM for now, can perform RAG search if needed)
        # In a real impl, retrieve history + context + query LLM
        # For this prototype: Simple contextual response
        
        try:
            # Calculate context from history
            history = session.get("history", [])
            assistant_msgs = [m for m in history if m.get("role") == "assistant"]
            last_exchange_count = len(assistant_msgs)

            # [FIX] Add timeout simulation or actual LLM call with timeout
            # If we were calling self.llm_service.generate(..., timeout=10), handle it here.
            # For now, we are mocking, but let's make it robust against any future IO blocks.
            
            import asyncio
            
            async def generate_response():
                # Simulate processing time or LLM call
                await asyncio.sleep(1.0) 
                
                if "python" in user_message.lower():
                    return "That's good. Can you explain how you handle memory management in Python?"
                elif "experience" in user_message.lower():
                     return "Impressive. Tell me about a challenging project you worked on."
                else:
                    return f"I see. Please elaborate on that. (Question {last_exchange_count + 1})"

            # Wait max 10 seconds for response (increased for safety)
            response_text = await asyncio.wait_for(generate_response(), timeout=10.0)

        except asyncio.TimeoutError:
            response_text = "I apologize, I'm taking a bit long to think. Could you please rephrase that?"
        except Exception as e:
            logger.error(f"Interview Agent Error: {e}")
            response_text = "I'm having trouble processing that. Let's move to the next topic."
            
        # 3. Append Agent Response
        await self.sessions_collection.update_one(
            {"_id": ObjectId(session_id)},
            {"$push": {"history": {"role": "assistant", "content": response_text}}, "$set": {"updated_at": datetime.utcnow()}}
        )
        
        return response_text

interview_agent = InterviewAgent()
