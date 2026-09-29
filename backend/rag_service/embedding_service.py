import threading
import numpy as np
from sentence_transformers import SentenceTransformer

_lock = threading.Lock()
_embedding_instance = None

class EmbeddingService:
    """
    Thread-safe Singleton wrapper for SentenceTransformer.
    Ensures model weights ('all-MiniLM-L6-v2') are only loaded into memory once.
    """
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        print(f"[EmbeddingService] Loading embedding model '{model_name}'...")
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.dimension = (
            self.model.get_embedding_dimension()
            if hasattr(self.model, "get_embedding_dimension")
            else self.model.get_sentence_embedding_dimension()
        )
        print(f"[EmbeddingService] Model loaded successfully. Dimension: {self.dimension}")

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        """
        Embed a list of text strings into normalized numpy float32 vectors.
        Normalized vectors allow Inner Product in FAISS to equate to Cosine Similarity.
        """
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)
        embeddings = self.model.encode(
            texts,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        return embeddings.astype(np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        """Embed a single query string into a 1D or 2D normalized float32 vector."""
        emb = self.model.encode(
            query,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        return emb.astype(np.float32)


def get_embedding_service(model_name: str = "all-MiniLM-L6-v2") -> EmbeddingService:
    """Thread-safe singleton accessor for EmbeddingService."""
    global _embedding_instance
    if _embedding_instance is None:
        with _lock:
            if _embedding_instance is None:
                _embedding_instance = EmbeddingService(model_name=model_name)
    return _embedding_instance
