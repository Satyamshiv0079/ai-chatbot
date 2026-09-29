from typing import List, Optional, Any
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document as LCDocument
from langchain_core.callbacks import CallbackManagerForRetrieverRun

from pydantic import ConfigDict

class UserScopedRetriever(BaseRetriever):
    """
    LangChain BaseRetriever adapter over the existing per-user FAISS vector store.
    Guarantees user isolation at the retriever level by binding retrieval strictly
    to the authenticated user's index partition.
    """
    user_id: str
    vector_store: Any
    embedding_service: Any
    doc_ids: Optional[List[int]] = None
    top_k: int = 4
    min_similarity: float = 0.15

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _get_relevant_documents(
        self, query: str, *, run_manager: Optional[CallbackManagerForRetrieverRun] = None
    ) -> List[LCDocument]:
        """
        Embeds query using SentenceTransformer, queries user's FAISS index,
        and packages results into LangChain Document objects with complete metadata.
        """
        if not query or not query.strip():
            return []

        # 1. Embed query
        query_embedding = self.embedding_service.embed_query(query.strip())

        # 2. Similarity search in user's isolated FAISS index
        raw_chunks = self.vector_store.similarity_search(
            user_id=self.user_id,
            query_embedding=query_embedding,
            top_k=self.top_k,
            doc_ids=self.doc_ids
        )

        if not raw_chunks:
            return []

        # 3. Filter by similarity threshold & wrap into LangChain Document objects
        documents: List[LCDocument] = []
        for chunk in raw_chunks:
            score = float(chunk.get("score", 0.0))
            if score < self.min_similarity:
                continue

            content = chunk.get("content", "").strip()
            snippet = content[:220] + "..." if len(content) > 220 else content

            metadata = {
                "user_id": self.user_id,
                "document_id": chunk.get("document_id"),
                "document_name": chunk.get("document_name", "Unknown Document"),
                "page_number": chunk.get("page_number", 1),
                "chunk_index": chunk.get("chunk_index", 0),
                "similarity_score": round(score, 3),
                "snippet": snippet
            }

            doc = LCDocument(page_content=content, metadata=metadata)
            documents.append(doc)

        return documents
