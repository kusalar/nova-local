import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from app.config import settings

logger = logging.getLogger("nova.memory.semantic")

class SemanticSearchEngine:
    """
    Offline local semantic search engine for NOVA memory.
    Uses ONNX-quantized sentence embeddings via fastembed with
    scikit-learn TF-IDF / BM25 lexical fallback.
    """

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.MEMORY_EMBEDDING_MODEL
        self.embedding_model = None
        self.is_embedding_available = False
        self._init_embedding_model()

    def _init_embedding_model(self):
        try:
            from fastembed import TextEmbedding
            # Fast, lightweight ONNX model (~30MB) running on CPU
            logger.info(f"Loading local embedding model: {self.model_name}")
            self.embedding_model = TextEmbedding(model_name=self.model_name)
            self.is_embedding_available = True
            logger.info("SemanticSearchEngine initialized with fastembed ONNX.")
        except Exception as e:
            self.is_embedding_available = False
            logger.warning(
                f"Fastembed could not be initialized ({e}). "
                "Engaging scikit-learn TF-IDF / Cosine fallback engine."
            )

    def get_embedding(self, text: str) -> Optional[np.ndarray]:
        """Generate normalized 384-d dense embedding vector for text."""
        if not text.strip():
            return None

        if self.is_embedding_available and self.embedding_model is not None:
            try:
                vectors = list(self.embedding_model.embed([text]))
                if vectors and len(vectors) > 0:
                    vec = np.array(vectors[0], dtype=np.float32)
                    norm = np.linalg.norm(vec)
                    if norm > 0:
                        vec = vec / norm
                    return vec
            except Exception as e:
                logger.warning(f"Error computing fastembed vector: {e}")

        return None

    @staticmethod
    def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))

    def search(
        self,
        query: str,
        candidate_texts: List[str],
        top_k: int = 5
    ) -> List[Tuple[int, float]]:
        """Rank a raw list of candidate strings against query, returning [(index, similarity_score)]."""
        if not candidate_texts or not query.strip():
            return []
        
        memories = [{"id": i, "content": text} for i, text in enumerate(candidate_texts)]
        ranked = self.search_memories(query=query, memories=memories, threshold=0.1, limit=top_k)
        return [(m["id"], m.get("similarity", 0.0)) for m in ranked]

    def search_memories(
        self,
        query: str,
        memories: List[Dict[str, Any]],
        threshold: float = 0.45,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Rank candidate memories by semantic similarity to query.
        Falls back gracefully to TF-IDF cosine matching if embeddings are missing.
        """
        if not memories or not query.strip():
            return []

        query_vec = self.get_embedding(query)
        scored_memories: List[Tuple[float, Dict[str, Any]]] = []

        if query_vec is not None:
            # 1. Vector Search
            for mem in memories:
                emb = mem.get("embedding")
                if emb is not None:
                    if isinstance(emb, bytes):
                        try:
                            emb = np.frombuffer(emb, dtype=np.float32)
                        except Exception:
                            emb = None
                    if isinstance(emb, np.ndarray):
                        sim = self.cosine_similarity(query_vec, emb)
                        # Boost score with importance weight
                        importance = float(mem.get("importance", 1.0))
                        boosted_score = sim * (1.0 + (importance - 1.0) * 0.15)
                        
                        if sim >= threshold or boosted_score >= threshold:
                            scored_mem = dict(mem)
                            scored_mem["similarity"] = round(float(sim), 4)
                            scored_memories.append((boosted_score, scored_mem))

        # 2. If vector search produced few results or embedding was unavailable, run lexical TF-IDF fallback
        if len(scored_memories) < limit:
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer
                from sklearn.metrics.pairwise import cosine_similarity as sk_cosine

                corpus = [m.get("content", "") for m in memories]
                vectorizer = TfidfVectorizer(stop_words="english", max_features=1000)
                tfidf_matrix = vectorizer.fit_transform(corpus + [query])
                
                doc_vecs = tfidf_matrix[:-1]
                q_vec = tfidf_matrix[-1:]
                
                sims = sk_cosine(q_vec, doc_vecs).flatten()

                # Add matches that aren't already scored higher
                existing_ids = {m[1]["id"] for m in scored_memories if "id" in m[1]}
                for idx, sim in enumerate(sims):
                    mem = memories[idx]
                    mem_id = mem.get("id")
                    if mem_id not in existing_ids and sim >= (threshold * 0.5):
                        scored_mem = dict(mem)
                        scored_mem["similarity"] = round(float(sim), 4)
                        scored_memories.append((float(sim), scored_mem))
            except Exception as e:
                logger.debug(f"Lexical TF-IDF fallback exception: {e}")
                # Simple keyword substring match as ultimate fallback
                query_words = set(query.lower().split())
                for mem in memories:
                    content_lower = mem.get("content", "").lower()
                    overlap = sum(1 for w in query_words if w in content_lower)
                    if overlap > 0:
                        sim = overlap / max(len(query_words), 1)
                        if sim >= (threshold * 0.4):
                            scored_mem = dict(mem)
                            scored_mem["similarity"] = round(float(sim), 4)
                            scored_memories.append((float(sim), scored_mem))

        # Sort descending by score
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        return [m[1] for m in scored_memories[:limit]]

# Global singleton
semantic_search = SemanticSearchEngine()
