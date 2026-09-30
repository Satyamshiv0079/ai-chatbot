import os
import gc
import threading
from typing import List, Optional
import numpy as np

_singleton_lock = threading.Lock()
_embedding_instance = None
_embedding_execution_lock = threading.RLock()

DEFAULT_BATCH_SIZE = int(os.environ.get("EMBEDDING_BATCH_SIZE", 16))

class EmbeddingService:
    """
    Thread-safe Singleton wrapper for SentenceTransformer with:
    - Lazy model loading (weights loaded only on first encode call)
    - Batched embedding workflow (default batch size 8-16)
    - Normalized float32 vectors for cosine similarity via FAISS IndexFlatIP
    - Explicit memory cleanup and concurrency protection
    """
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self._model_lock = threading.Lock()
        self._dimension = 384  # Standard dimension for all-MiniLM-L6-v2

    @property
    def model(self):
        """Lazily load SentenceTransformer weights on first use."""
        if self._model is None:
            with self._model_lock:
                if self._model is None:
                    print(f"[EmbeddingService] Lazy loading embedding model '{self.model_name}'...")
                    from sentence_transformers import SentenceTransformer
                    loaded_model = SentenceTransformer(self.model_name)
                    self._dimension = (
                        loaded_model.get_embedding_dimension()
                        if hasattr(loaded_model, "get_embedding_dimension")
                        else loaded_model.get_sentence_embedding_dimension()
                    )
                    self._model = loaded_model
                    print(f"[EmbeddingService] Model loaded successfully. Dimension: {self._dimension}")
        return self._model

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_texts(self, texts: List[str], batch_size: Optional[int] = None) -> np.ndarray:
        """
        Embed a list of text strings into normalized float32 vectors in batches.
        Batched execution prevents high temporary memory spikes on constrained services.
        """
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)

        bs = batch_size or DEFAULT_BATCH_SIZE
        all_embeddings: List[np.ndarray] = []
        total = len(texts)

        with _embedding_execution_lock:
            for start_idx in range(0, total, bs):
                end_idx = min(start_idx + bs, total)
                batch = texts[start_idx:end_idx]
                batch_num = (start_idx // bs) + 1
                total_batches = (total + bs - 1) // bs
                if total_batches > 1:
                    print(f"[EmbeddingService] Embedding batch {batch_num}/{total_batches} ({len(batch)} chunks)")

                batch_emb = self.model.encode(
                    batch,
                    batch_size=len(batch),
                    show_progress_bar=False,
                    convert_to_numpy=True,
                    normalize_embeddings=True
                )
                all_embeddings.append(batch_emb.astype(np.float32, copy=False))
                del batch

            if len(all_embeddings) == 1:
                result = all_embeddings[0]
            else:
                result = np.vstack(all_embeddings)

            del all_embeddings
            return result

    def embed_query(self, query: str) -> np.ndarray:
        """Embed a single query string into a normalized float32 vector."""
        if not query or not query.strip():
            return np.zeros((self.dimension,), dtype=np.float32)

        with _embedding_execution_lock:
            emb = self.model.encode(
                query.strip(),
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True
            )
            return emb.astype(np.float32, copy=False)


def get_embedding_service(model_name: str = "all-MiniLM-L6-v2") -> EmbeddingService:
    """Thread-safe singleton accessor for EmbeddingService."""
    global _embedding_instance
    if _embedding_instance is None:
        with _singleton_lock:
            if _embedding_instance is None:
                _embedding_instance = EmbeddingService(model_name=model_name)
    return _embedding_instance

