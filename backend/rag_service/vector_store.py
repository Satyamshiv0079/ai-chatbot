import os
import json
import pickle
import threading
from typing import List, Dict, Any, Optional
import numpy as np
import faiss

# Base path for vector stores
DEFAULT_BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'vector_stores')

class FAISSUserStore:
    """
    Manages per-user FAISS vector stores with strict multi-tenant isolation.
    Each user has a dedicated directory: vector_stores/<user_id>/
    containing 'index.faiss' and 'chunks.json' (secure JSON metadata storage).
    """
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = os.environ.get("VECTOR_STORE_PATH", base_dir or DEFAULT_BASE_DIR)
        os.makedirs(self.base_dir, exist_ok=True)
        self._lock = threading.Lock()

    def _user_dir(self, user_id: str) -> str:
        # Sanitize user_id for filesystem safety - allow only alphanumeric, hyphen, underscore
        safe_user = "".join(c for c in str(user_id) if c.isalnum() or c in ("-", "_")).strip()
        if not safe_user:
            safe_user = "default_user"
        path = os.path.abspath(os.path.join(self.base_dir, safe_user))
        base_canonical = os.path.abspath(self.base_dir)
        if not path.startswith(base_canonical):
            raise ValueError("Path traversal attempt detected in user identifier")
        os.makedirs(path, exist_ok=True)
        return path

    def _index_path(self, user_id: str) -> str:
        return os.path.join(self._user_dir(user_id), "index.faiss")

    def _chunks_path(self, user_id: str) -> str:
        return os.path.join(self._user_dir(user_id), "chunks.json")

    def _legacy_chunks_path(self, user_id: str) -> str:
        return os.path.join(self._user_dir(user_id), "chunks.pkl")

    def _load_user_data(self, user_id: str) -> tuple[Optional[faiss.IndexFlatIP], List[Dict[str, Any]]]:
        idx_path = self._index_path(user_id)
        json_path = self._chunks_path(user_id)
        pkl_path = self._legacy_chunks_path(user_id)

        if not os.path.exists(idx_path):
            return None, []

        try:
            index = faiss.read_index(idx_path)
            chunks = []
            if os.path.exists(json_path):
                with open(json_path, "r", encoding="utf-8") as f:
                    chunks = json.load(f)
            elif os.path.exists(pkl_path):
                # Validate legacy path before opening
                user_dir = self._user_dir(user_id)
                if not os.path.abspath(pkl_path).startswith(user_dir):
                    raise ValueError("Untrusted legacy metadata path detected")
                with open(pkl_path, "rb") as f:
                    chunks = pickle.load(f)
                # Atomically write migrated JSON
                tmp_json = json_path + ".tmp"
                with open(tmp_json, "w", encoding="utf-8") as f:
                    json.dump(chunks, f, ensure_ascii=False)
                os.replace(tmp_json, json_path)
                try:
                    os.remove(pkl_path)
                except OSError:
                    pass
            else:
                return None, []
            return index, chunks
        except Exception as e:
            print(f"[FAISSUserStore] Error loading index for user {user_id}: {e}")
            return None, []

    def _save_user_data(self, user_id: str, index: faiss.IndexFlatIP, chunks: List[Dict[str, Any]]):
        idx_path = self._index_path(user_id)
        json_path = self._chunks_path(user_id)
        pkl_path = self._legacy_chunks_path(user_id)

        # Atomic persistence via temporary files prevents index corruption on process crash/kill
        tmp_idx = idx_path + ".tmp"
        tmp_json = json_path + ".tmp"

        try:
            faiss.write_index(index, tmp_idx)
            with open(tmp_json, "w", encoding="utf-8") as f:
                json.dump(chunks, f, ensure_ascii=False)
            os.replace(tmp_idx, idx_path)
            os.replace(tmp_json, json_path)
        finally:
            if os.path.exists(tmp_idx):
                try:
                    os.remove(tmp_idx)
                except OSError:
                    pass
            if os.path.exists(tmp_json):
                try:
                    os.remove(tmp_json)
                except OSError:
                    pass

        if os.path.exists(pkl_path):
            try:
                os.remove(pkl_path)
            except OSError:
                pass

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

            index.add(embeddings.astype(np.float32, copy=False))
            self._save_user_data(user_id, index, all_chunks)
            print(f"[FAISSUserStore] Added {len(new_chunks)} chunks for user '{user_id}'. Total: {index.ntotal}")

    def add_chunks_batched(
        self,
        user_id: str,
        chunks: List[Dict[str, Any]],
        embedding_service: Any,
        batch_size: int = 16
    ):
        """
        Memory-safe stream/batch document indexing.
        Embeds chunks in batches of 8-16 and incrementally appends to the user's FAISS index,
        releasing temporary arrays immediately to avoid RAM spikes on Render.
        """
        if not chunks:
            return

        import gc
        total = len(chunks)
        with self._lock:
            index, existing_chunks = self._load_user_data(user_id)
            dim = embedding_service.dimension

            if index is None:
                index = faiss.IndexFlatIP(dim)
                all_chunks = []
            else:
                all_chunks = existing_chunks

            for i in range(0, total, batch_size):
                batch_chunks = chunks[i : i + batch_size]
                batch_texts = [c["content"] for c in batch_chunks]
                batch_emb = embedding_service.embed_texts(batch_texts, batch_size=batch_size)

                index.add(batch_emb.astype(np.float32, copy=False))
                all_chunks.extend(batch_chunks)

                del batch_texts, batch_emb, batch_chunks

            self._save_user_data(user_id, index, all_chunks)
            print(f"[FAISSUserStore] Document indexing completed: {total} chunks added for user '{user_id}'. Total in index: {index.ntotal}")
            gc.collect()

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

    def delete_document(self, user_id: str, doc_id: int, embedding_service=None, batch_size: int = 16):
        """
        Removes all chunks for doc_id and rebuilds the FAISS index for this user
        using memory-safe batching.
        """
        import gc
        with self._lock:
            index, chunks = self._load_user_data(user_id)
            if not chunks:
                return

            remaining_chunks = [c for c in chunks if c.get("document_id") != doc_id]

            if not remaining_chunks:
                # Remove all files
                idx_path = self._index_path(user_id)
                json_path = self._chunks_path(user_id)
                pkl_path = self._legacy_chunks_path(user_id)
                for p in (idx_path, json_path, pkl_path):
                    if os.path.exists(p):
                        try:
                            os.remove(p)
                        except OSError:
                            pass
                print(f"[FAISSUserStore] Deleted doc {doc_id}. Vector store for user '{user_id}' is now empty.")
                return

            # Rebuild index for remaining chunks using memory-safe batching
            if embedding_service is None:
                from .embedding_service import get_embedding_service
                embedding_service = get_embedding_service()

            dim = embedding_service.dimension
            new_index = faiss.IndexFlatIP(dim)
            total = len(remaining_chunks)

            for i in range(0, total, batch_size):
                batch_chunks = remaining_chunks[i : i + batch_size]
                batch_texts = [c["content"] for c in batch_chunks]
                batch_emb = embedding_service.embed_texts(batch_texts, batch_size=batch_size)
                new_index.add(batch_emb.astype(np.float32, copy=False))
                del batch_texts, batch_emb, batch_chunks

            self._save_user_data(user_id, new_index, remaining_chunks)
            print(f"[FAISSUserStore] FAISS index rebuilt for user '{user_id}' after deleting doc {doc_id}. Chunks remaining: {len(remaining_chunks)}")
            gc.collect()

    def get_user_chunks_count(self, user_id: str) -> int:
        with self._lock:
            index, chunks = self._load_user_data(user_id)
            return len(chunks) if chunks else 0

    def clear_user_store(self, user_id: str):
        with self._lock:
            idx_path = self._index_path(user_id)
            json_path = self._chunks_path(user_id)
            pkl_path = self._legacy_chunks_path(user_id)
            for p in (idx_path, json_path, pkl_path):
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except OSError:
                        pass
