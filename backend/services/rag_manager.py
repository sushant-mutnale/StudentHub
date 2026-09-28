"""
RAG Knowledge Manager

Handles interactions with Pinecone Vector DB.
CRITICAL: Enforces strict data isolation between users.

Uses real embeddings via the embedding_service when an OpenAI key is configured,
with a deterministic pseudo-embedding fallback for local/dev environments.
"""

import logging
from typing import List, Dict, Any, Optional

from .embedding_service import embed_text, embed_texts, EMBEDDING_DIMENSIONS
from .pinecone_service import get_index
from ..config import Settings

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

    # ------------------------------------------------------------------
    # Writing helpers
    # ------------------------------------------------------------------

    async def add_public_job(self, job_id: str, job_text: str, metadata: Dict = None):
        """Add a job description to public knowledge."""
        if not self.index:
            return False

        meta = metadata or {}
        meta["type"] = "job"

        try:
            vector = embed_text(job_text)
            self.index.upsert(
                vectors=[{
                    "id": f"job_{job_id}",
                    "values": vector,
                    "metadata": {"text": job_text, **meta}
                }],
                namespace=self.NS_PUBLIC
            )
            logger.info(f"Added public job {job_id} to RAG (dim={len(vector)})")
            return True
        except Exception as e:
            logger.error(f"Failed to add public job: {e}")
            return False

    async def add_user_resume(self, user_id: str, resume_text: str):
        """Add a user's resume to their private isolated memory."""
        if not self.index:
            return False

        try:
            vector = embed_text(resume_text)
            self.index.upsert(
                vectors=[{
                    "id": f"resume_{user_id}",
                    "values": vector,
                    "metadata": {
                        "text": resume_text,
                        "type": "resume",
                        "user_id": user_id  # CRITICAL FOR FILTERING
                    }
                }],
                namespace=self.NS_USER
            )
            logger.info(f"Added resume for user {user_id} (dim={len(vector)})")
            return True
        except Exception as e:
            logger.error(f"Failed to add resume: {e}")
            return False

    async def upsert_batch(self, records: List[Dict[str, Any]], namespace: str):
        """Upsert a batch of records with real embeddings.

        Each record must have ``id`` and ``text`` keys.
        Optionally include ``metadata`` (dict) to store alongside.
        """
        if not self.index or not records:
            return 0

        texts = [r["text"] for r in records]
        try:
            vectors = embed_texts(texts)
        except Exception as e:
            logger.error(f"Batch embedding failed: {e}")
            return 0

        pinecone_records = []
        for rec, vec in zip(records, vectors):
            meta = rec.get("metadata", {})
            meta["text"] = rec["text"]
            pinecone_records.append({
                "id": rec["id"],
                "values": vec,
                "metadata": meta,
            })

        try:
            # Pinecone upsert supports batches up to ~1000 vectors.
            batch_size = 100
            upserted = 0
            for i in range(0, len(pinecone_records), batch_size):
                batch = pinecone_records[i:i + batch_size]
                self.index.upsert(vectors=batch, namespace=namespace)
                upserted += len(batch)
            logger.info(f"Upserted {upserted} records to namespace={namespace}")
            return upserted
        except Exception as e:
            logger.error(f"Batch upsert failed: {e}")
            return 0

    # ------------------------------------------------------------------
    # Search helpers
    # ------------------------------------------------------------------

    async def search_public(self, query: str, limit: int = 5):
        """Search global public knowledge (Jobs, Courses)."""
        if not self.index:
            return []

        try:
            vector = embed_text(query)
            res = self.index.query(
                namespace=self.NS_PUBLIC,
                vector=vector,
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
        if not self.index:
            return []

        try:
            vector = embed_text(query)
            res = self.index.query(
                namespace=self.NS_USER,
                vector=vector,
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
