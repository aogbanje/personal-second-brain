import os
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from config import CHROMA_DB_PATH

def initialize_vector_db():
    try:
        os.makedirs(CHROMA_DB_PATH, exist_ok=True)
        chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        
        # Instantiate a completely free, local text math vector calculator
        local_ef = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        
        # Attach the local math space schema right into your collection structure
        collection = chroma_client.get_or_create_collection(
            name="second_brain_knowledge",
            embedding_function=local_ef
        )
        print(f"📦 Chroma DB Initialized successfully using local SentenceTransformer vectors.")
        return collection
    except Exception as e:
        print(f"❌ Error initializing vector database: {e}")
        return None
