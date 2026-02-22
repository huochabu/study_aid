
import os
import logging
from typing import List, Dict, Any, Optional
import numpy as np

# Change project root detection logic to be relative to this file
# This file is in backend/services/vector_service.py
# So project root is ../../
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

# Import vector retrieval dependencies
try:
    from sentence_transformers import SentenceTransformer
    import faiss
except ImportError:
    # Silent fail or log, main.py will handle the error if missing
    logger.warning("RAG dependencies not found (sentence-transformers, faiss-cpu)")
    SentenceTransformer = None
    faiss = None

# ======================
# Vector Store Class
# ======================
class VectorStore:
    # Class-level variables for singleton model
    _shared_model = None
    _model_path = None
    
    def __init__(self):
        try:
            if SentenceTransformer is None:
                raise ImportError("Missing dependencies")
                
            local_model_path = os.path.join(PROJECT_ROOT, "models/bge-small-zh")
            # Load model only if not loaded or path changed
            if VectorStore._shared_model is None or VectorStore._model_path != local_model_path:
                VectorStore._model_path = local_model_path
                # Check if model exists locally, otherwise it might download (or fail if offline)
                # But sentence_transformers usually handles this.
                # If we want to force local:
                # if not os.path.exists(local_model_path): ...
                
                VectorStore._shared_model = SentenceTransformer(local_model_path)
                logger.info(f"✅ Vector model loaded: {local_model_path}")
            self.model = VectorStore._shared_model
        except Exception as e:
            logger.error(f"❌ Vector model load failed: {str(e)}")
            # Fallback or raise? For now, we allow init but define model as None
            self.model = None
            
        self.index = None
        self.chunks = []
        self.metadata = [] # [NEW] Store metadata (filename, page, etc.)
        self.dim = 512

    def add_texts(self, texts: list, metadatas: Optional[List[Dict[str, Any]]] = None):
        """
        Add texts to index.
        Args:
            texts: List of strings
            metadatas: Optional list of dicts, same length as texts
        """
        if not texts or self.model is None:
            return
        
        try:
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            if self.index is None:
                if faiss:
                    self.index = faiss.IndexFlatL2(self.dim)
                else:
                    logger.error("FAISS not available")
                    return
            
            if self.index:
                self.index.add(embeddings)
                self.chunks.extend(texts)
                
                # Handle metadata
                if metadatas and len(metadatas) == len(texts):
                    self.metadata.extend(metadatas)
                else:
                    # Pad with empty dicts if missing or mismatch
                    self.metadata.extend([{} for _ in texts])
                    
        except Exception as e:
            logger.error(f"Failed to add vectors: {e}")

    def search(self, query: str, k=3):
        """
        Returns list of dicts: {'text': str, 'metadata': dict, 'score': float}
        """
        if self.index is None or len(self.chunks) == 0 or self.model is None:
            return []
        
        try:
            query_vec = self.model.encode([query], convert_to_numpy=True)
            distances, indices = self.index.search(query_vec, min(k, len(self.chunks)))
            
            # FAISS returns L2 distance (lower is better), but we often want similarity.
            # Here we just iterate the results.
            results = []
            for i, idx in enumerate(indices[0]):
                if idx < 0 or idx >= len(self.chunks): continue
                
                results.append({
                    "text": self.chunks[idx],
                    "metadata": self.metadata[idx] if idx < len(self.metadata) else {},
                    "score": float(distances[0][i])
                })
            return results
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

# ======================
# Global Store
# ======================
# Use memory storage (in-memory, strictly server-side)
VECTOR_STORES: Dict[str, VectorStore] = {}  # {file_id: VectorStore}
GLOBAL_HISTORY_STORE = VectorStore() # Global history vector store
