import os
import pickle
import threading
from typing import List, Dict, Any, Optional
import numpy as np
import faiss

# Base path for vector stores
DEFAULT_BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'vector_stores')

class FAISSUserStore:
    """
    Manages per-user FAISS vector stores with strict isolation.
    Each user has a dedicated directory: vector_stores/<user_id>/
    containing 'index.faiss' and 'chunks.pkl'.
    """
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = os.environ.get("VECTOR_STORE_PATH", base_dir or DEFAULT_BASE_DIR)
        os.makedirs(self.base_dir, exist_ok=True)
        self._lock = threading.Lock()

    def _user_dir(self, user_id: str) -> str:
        # Sanitize user_id for filesystem safety
        safe_user = "".join(c for c in user_id if c.isalnum() or c in ("-", "_")).strip()
        if not safe_user:
            safe_user = "default_user"
        path = os.path.join(self.base_dir, safe_user)
        os.makedirs(path, exist_ok=True)
        return path

    def _index_path(self, user_id: str) -> str:
        return os.path.join(self._user_dir(user_id), "index.faiss")

    def _chunks_path(self, user_id: str) -> str:
        return os.path.join(self._user_dir(user_id), "chunks.pkl")

    def _load_user_data(self, user_id: str) -> tuple[Optional[faiss.IndexFlatIP], List[Dict[str, Any]]]:
        idx_path = self._index_path(user_id)
        chunks_path = self._chunks_path(user_id)

        if not os.path.exists(idx_path) or not os.path.exists(chunks_path):
            return None, []

        try:
            index = faiss.read_index(idx_path)
            with open(chunks_path, "rb") as f:
                chunks = pickle.load(f)
            return index, chunks
        except Exception as e:
            print(f"[FAISSUserStore] Error loading index for user {user_id}: {e}")
            return None, []

    def _save_user_data(self, user_id: str, index: faiss.IndexFlatIP, chunks: List[Dict[str, Any]]):
        idx_path = self._index_path(user_id)
        chunks_path = self._chunks_path(user_id)

        faiss.write_index(index, idx_path)
        with open(chunks_path, "wb") as f:
            pickle.dump(chunks, f)

    def add_chunks(self, user_id: str, new_chunks: List[Dict[str, Any]], embeddings: np.ndarray):
        """
        Appends new document chunks and their vectors to the user's FAISS index.
        """
        if not new_chunks or embeddings.shape[0] == 0:
            return

        with self._lock:
            index, existing_chunks = self._load_user_data(user_id)
            dim = embeddings.shape[1]

            if index is None:
                # Use Inner Product (IP) index. Since embeddings are L2 normalized,
                # Inner Product is mathematically identical to Cosine Similarity.
                index = faiss.IndexFlatIP(dim)
                all_chunks = list(new_chunks)
            else:
                all_chunks = existing_chunks + list(new_chunks)

            index.add(embeddings)
            self._save_user_data(user_id, index, all_chunks)
            print(f"[FAISSUserStore] Added {len(new_chunks)} chunks for user '{user_id}'. Total: {index.ntotal}")

    def similarity_search(
        self,
        user_id: str,
        query_embedding: np.ndarray,
        top_k: int = 4,
        doc_ids: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """
        Searches the user's FAISS index for the top_k most similar chunks.
        Optionally filters results to a specific list of document IDs.
        """
        with self._lock:
            index, chunks = self._load_user_data(user_id)

        if index is None or index.ntotal == 0 or not chunks:
            return []

        # Ensure query is 2D float32
        if query_embedding.ndim == 1:
            query_embedding = np.expand_dims(query_embedding, axis=0)
        query_embedding = query_embedding.astype(np.float32)

        # Retrieve more candidates if we need to filter by doc_ids
        fetch_k = min(top_k * 4 if doc_ids else top_k, index.ntotal)
        scores, indices = index.search(query_embedding, fetch_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(chunks):
                continue
            chunk = chunks[idx]
            if doc_ids and chunk.get("document_id") not in doc_ids:
                continue

            results.append({
                "content": chunk.get("content", ""),
                "document_id": chunk.get("document_id"),
                "document_name": chunk.get("document_name", "Unknown Document"),
                "page_number": chunk.get("page_number", 1),
                "chunk_index": chunk.get("chunk_index", 0),
                "score": float(score),
                "metadata": chunk.get("metadata", {})
            })

            if len(results) >= top_k:
                break

        return results

    def delete_document(self, user_id: str, doc_id: int, embedding_service=None):
        """
        Removes all chunks for doc_id and rebuilds the FAISS index for this user.
        """
        with self._lock:
            index, chunks = self._load_user_data(user_id)
            if not chunks:
                return

            remaining_chunks = [c for c in chunks if c.get("document_id") != doc_id]

            if not remaining_chunks:
                # Remove all files
                idx_path = self._index_path(user_id)
                chunks_path = self._chunks_path(user_id)
                if os.path.exists(idx_path):
                    os.remove(idx_path)
                if os.path.exists(chunks_path):
                    os.remove(chunks_path)
                print(f"[FAISSUserStore] Deleted doc {doc_id}. Vector store for user '{user_id}' is now empty.")
                return

            # Rebuild index for remaining chunks
            if embedding_service is None:
                from .embedding_service import get_embedding_service
                embedding_service = get_embedding_service()

            texts = [c["content"] for c in remaining_chunks]
            embeddings = embedding_service.embed_texts(texts)

            new_index = faiss.IndexFlatIP(embeddings.shape[1])
            new_index.add(embeddings)
            self._save_user_data(user_id, new_index, remaining_chunks)
            print(f"[FAISSUserStore] Rebuilt index for user '{user_id}' after deleting doc {doc_id}. Chunks remaining: {len(remaining_chunks)}")

    def get_user_chunks_count(self, user_id: str) -> int:
        with self._lock:
            index, chunks = self._load_user_data(user_id)
            return len(chunks) if chunks else 0

    def clear_user_store(self, user_id: str):
        with self._lock:
            idx_path = self._index_path(user_id)
            chunks_path = self._chunks_path(user_id)
            if os.path.exists(idx_path):
                os.remove(idx_path)
            if os.path.exists(chunks_path):
                os.remove(chunks_path)
