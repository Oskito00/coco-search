import numpy as np
from sentence_transformers import SentenceTransformer

import time

class SBERTScorer:
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(model_name)
        
    def encode_batch(self, texts: list[str], batch_size: int = 64) -> np.ndarray:
        return self.model.encode(
            texts, 
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=False
        )
    
    def score(self, query: str, items: list[str]) -> tuple[np.ndarray, np.ndarray]:
        """Returns (scores, indices) sorted by relevance"""
        query_vec = self.model.encode(query)
        item_vecs = self.encode_batch(items)
        
        # Manual cosine similarity
        query_norm = np.linalg.norm(query_vec)
        item_norms = np.linalg.norm(item_vecs, axis=1)
        sims = np.dot(item_vecs, query_vec) / (item_norms * query_norm)
        
        sorted_indices = np.argsort(sims)[::-1]
        return sims[sorted_indices], sorted_indices

# Singleton pattern
_scorer = None
def get_scorer():
    global _scorer
    if _scorer is None:
        print("Loading SBERT model...")
        start = time.time()
        _scorer = SBERTScorer()
        print(f"Model loaded in {time.time()-start:.1f}s")
    return _scorer 