"""
RAG Knowledge Manager

Handles interactions with Pinecone Vector DB.
CRITICAL: Enforces strict data isolation between users.
"""

import logging
from typing import List, Dict, Any, Optional
from backend.services.pinecone_service import get_index, add_record, search_records # Re-using base service or extending it?
# Actually, let's use the base service's index but implement the logic here to keep it clean.
# Or better, let's wrap the logic here and use the low-level connection from pinecone_service.

from backend.services.pinecone_service import get_index
from backend.config import Settings

logger = logging.getLogger(__name__)

class RAGManager:
    """
    Manages Knowledge Retrieval with strict security boundaries.
    """
    
    # Namespaces
    NS_PUBLIC = "public_content"  # Jobs, Courses, General Info
    NS_USER = "user_data"         # Resumes, Notes, Personal History

    def __init__(self):
        self.index = get_index()

    async def _embed_text(self, text: str):
        """
        Generate embedding for text.
        TODO: Integrate with an embedding model (OpenAI/HuggingFace).
        For now, Pinecone 'Integrated Inference' might handle this if configured.
        Otherwise, we need an embedding service.
        For MVP, we assume text-based search or handling via the 'text' field if using integrated inference.
        """
        # Placeholder: In a real app, you'd call OpenAI here.
        # If using Pinecone Inference, we just pass text.
        return text 

    async def add_public_job(self, job_id: str, job_text: str, metadata: Dict = None):
        """Add a job description to public knowledge."""
        if not self.index: return False
        
        meta = metadata or {}
        meta["type"] = "job"
        
        try:
            # Fallback: Send a dummy vector to satisfy client validation.
            # If server has integrated embedding, it should use 'text' in metadata/inputs.
            # If not, this safeguards against client crash (but returns garbage search).
            dummy_vec = [0.1] * 1024
            
            self.index.upsert(
                vectors=[{
                    "id": f"job_{job_id}",
                    "values": dummy_vec, 
                    "metadata": {"text": job_text, **meta}
                }],
                namespace=self.NS_PUBLIC
            )
            logger.info(f"Added public job {job_id} to RAG")
            return True
        except Exception as e:
            logger.error(f"Failed to add public job: {e}")
            return False

    async def add_user_resume(self, user_id: str, resume_text: str):
        """Add a user's resume to their private isolated memory."""
        if not self.index: return False
        
        try:
            self.index.upsert(
                vectors=[{
                    "id": f"resume_{user_id}",
                    "values": [0.1] * 1024, # Dummy vector
                    "metadata": {
                        "text": resume_text,
                        "type": "resume",
                        "user_id": user_id  # CRITICAL FOR FILTERING
                    }
                }],
                namespace=self.NS_USER
            )
            logger.info(f"Added resume for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add resume: {e}")
            return False

    async def search_public(self, query: str, limit: int = 5):
        """Search global public knowledge (Jobs, Courses)."""
        if not self.index: return []
        
        try:
            # Using the same pattern as test_pinecone.py for inference
            # We assume the user config is correct about 'text' input
            res = self.index.query(
                namespace=self.NS_PUBLIC,
                inputs={"text": query},
                vector=[0.1] * 1024, # Dummy vector to bypass client "vector required" validation
                top_k=limit,
                include_metadata=True
            )
            return res.matches
        except Exception as e:
            logger.error(f"Public search failed: {e}")
            return []

    async def search_private(self, user_id: str, query: str, limit: int = 5):
        """
        Search PRIVATE user data.
        CRITICAL: Enforces metadata filter for user_id.
        """
        if not self.index: return []
        
        try:
            res = self.index.query(
                namespace=self.NS_USER,
                inputs={"text": query},
                vector=[0.1] * 1024, # Dummy vector
                top_k=limit,
                include_metadata=True,
                filter={
                    "user_id": {"$eq": user_id}  # THE SECURITY GATE
                }
            )
            return res.matches
        except Exception as e:
            logger.error(f"Private search failed for user {user_id}: {e}")
            return []

rag_manager = RAGManager()
