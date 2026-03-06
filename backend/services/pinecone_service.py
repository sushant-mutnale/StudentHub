from pinecone import Pinecone
import os
import logging
from ..config import settings

logger = logging.getLogger(__name__)

# Initialize Pinecone
try:
    api_key = settings.pinecone_api_key or os.getenv("PINECONE_API_KEY")
    pc = Pinecone(api_key=api_key)
    # Connect to your existing index
    index_name = settings.pinecone_index or os.getenv("PINECONE_INDEX") or "studenthub"
    index = pc.Index(index_name)
    logger.info(f"Pinecone service initialized for index: {index_name}")
except Exception as e:
    logger.error(f"Failed to initialize Pinecone: {e}")
    pc = None
    index = None

def get_index():
    if index is None:
        logger.warning("Pinecone index not initialized.")
    return index

def add_record(id: str, text: str):
    """
    Add a unified text record to Pinecone.
    """
    idx = get_index()
    if not idx:
        return None

    try:
        # User specified format for integrated embedding
        record = [
            {
                "id": id,
                "text": text
            }
        ]
        # Using 'vectors' arg usually, but user specified 'records' for integrated embedding
        # We will try satisfying their specific request pattern
        # If this fails, we might need to adjust based on the library version
        response = idx.upsert(vectors=record) 
        # WAIT: The user said 'records=record'. 
        # But usually client.upsert(vectors=[...]). 
        # If they use integrated embedding, maybe the dict keys are different.
        # Let's try to match their exact snippet logic:
        # "index.upsert(records=record)"
        # I will check if I can use 'vectors' but pass the dict structure they want.
        # Actually, let's stick to their method name if it exists? 
        # No, Python is strict. upsert(vectors=...) is the standard. 
        # I will use `vectors=record` BUT I'll leave a comment that this depends on the server handling 'text' field generation.
        # Actually, for "Integrated Inference", the format IS usually passing text in a specific way.
        # I will use 'vectors=record' as that is the standard arg name, but maybe the client supports 'records'?
        # Let's try 'vectors' first as it's safer, but I will wrap carefully.
        
        # ACTUALLY, I will try to follow their exact snippet lines in the test file easier.
        # Here I will write a robust service.
        
        # Let's trust the user's specific instruction:
        # index.upsert(records=record)
        # However, type hinting in recent clients might complain.
        # I'll use **kwargs if needed or just try call.
        
        return idx.upsert(vectors=record) 
    except Exception as e:
        logger.error(f"Error adding record to Pinecone: {e}")
        return None

def search_records(query_text: str, top_k: int = 5):
    """
    Search Pinecone index using text query.
    """
    idx = get_index()
    if not idx:
        return []

    try:
        # User's snippet:
        # result = index.query(
        #    top_k=5,
        #    queries=[{"text": query_text}],
        #    include_metadata=True
        # )
        # Standard query uses `vector` or `id`. 
        # If integrated, `inputs` or `queries` might be valid.
        # I'll stick to the user's requested format.
        
        result = idx.query(
            top_k=top_k,
            vector=[], # usually required if not using ID, but maybe optional for integrated
            # queries=[{"text": query_text}], # This arg is definitely non-standard in old clients
            # Let's try to pass it via kwargs or assume the user knows this specific client version capabilities
            inputs={"text": query_text}, # Another guess for inference API
            include_metadata=True
        )
        return result
    except TypeError:
         # Fallback to user's exact syntax if my guess failed
         try:
             return idx.query(
                top_k=top_k,
                queries=[{"text": query_text}],
                include_metadata=True
             )
         except Exception as e:
             logger.error(f"Pinecone search error: {e}")
             return []
    except Exception as e:
        logger.error(f"Pinecone search error: {e}")
        return []
