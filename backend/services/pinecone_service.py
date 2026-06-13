import os
import logging
from ..config import settings

logger = logging.getLogger(__name__)

# Initialize Pinecone safely
try:
    from pinecone import Pinecone
except ImportError as e:
    logger.warning(f"Pinecone SDK not installed (ModuleNotFoundError): {e}. Pinecone service will be disabled.")
    Pinecone = None

pc = None
index = None

if Pinecone is not None:
    try:
        api_key = settings.pinecone_api_key or os.getenv("PINECONE_API_KEY")
        index_name = settings.pinecone_index or os.getenv("PINECONE_INDEX") or "studenthub"
        if api_key:
            pc = Pinecone(api_key=api_key)
            index = pc.Index(index_name)
            logger.info(f"Pinecone service initialized for index: {index_name}")
        else:
            logger.warning("PINECONE_API_KEY is not set. Pinecone service will be disabled.")
    except Exception as e:
        logger.error(f"Failed to initialize Pinecone: {e}")
        pc = None
        index = None

def get_index():
    if index is None:
        logger.warning("Pinecone index not initialized.")
    return index

def add_record(id: str, text: str, namespace: str = ""):
    """
    Add a unified text record to Pinecone.
    Uses integrated embeddings if supported, otherwise falls back to OpenAI embeddings.
    """
    idx = get_index()
    if not idx:
        return None

    try:
        # Check if modern upsert_records (integrated embedding API) is supported
        if hasattr(idx, "upsert_records"):
            record = [{"id": id, "text": text}]
            return idx.upsert_records(
                namespace=namespace,
                records=record
            )
        else:
            # Fallback to OpenAI embeddings + old Index.upsert(vectors=...)
            logger.info("upsert_records not supported on index. Falling back to generating OpenAI embeddings first.")
            from langchain_openai import OpenAIEmbeddings
            openai_api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
            embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
            vector = embeddings.embed_query(text)
            
            record = [{"id": id, "values": vector, "metadata": {"text": text}}]
            return idx.upsert(vectors=record, namespace=namespace)
    except Exception as e:
        logger.error(f"Error adding record to Pinecone: {e}")
        return None

def search_records(query_text: str, top_k: int = 5, namespace: str = ""):
    """
    Search Pinecone index using text query.
    Uses integrated search if supported, otherwise falls back to OpenAI embeddings.
    """
    idx = get_index()
    if not idx:
        return []

    try:
        # Check if modern search (integrated embedding search) is supported
        if hasattr(idx, "search"):
            results = idx.search(
                namespace=namespace,
                query={"inputs": {"text": query_text}, "top_k": top_k},
                fields=["text"]
            )
            return results
        else:
            # Fallback to OpenAI embeddings + old Index.query
            logger.info("search method not supported on index. Falling back to OpenAI embeddings query.")
            from langchain_openai import OpenAIEmbeddings
            openai_api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
            embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
            vector = embeddings.embed_query(query_text)
            
            results = idx.query(
                namespace=namespace,
                vector=vector,
                top_k=top_k,
                include_metadata=True
            )
            return results
    except Exception as e:
        logger.error(f"Pinecone search error: {e}")
        return []
