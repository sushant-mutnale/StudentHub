
import os
import time
from pinecone import Pinecone

api_key = os.getenv("PINECONE_API_KEY") or "pcsk_..." # It's in .env usually
pc = Pinecone(api_key=api_key)

try:
    print("Testing pc.inference.embed...")
    # Try to embed text using the model the user mentioned: multilingual-e5-large
    embeddings = pc.inference.embed(
        model="multilingual-e5-large",
        inputs=["Hello world"],
        parameters={"input_type": "passage", "truncate": "END"}
    )
    print("Success!")
    print(f"Embedding dimensions: {len(embeddings[0]['values'])}")
    
except Exception as e:
    print(f"Inference failed: {e}")
    # Inspect valid attributes
    print("pc attributes:", dir(pc))
