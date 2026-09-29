import os
from typing import List, Dict, Any, Optional
from groq import Groq
from dotenv import load_dotenv

from .embedding_service import get_embedding_service
from .vector_store import FAISSUserStore

load_dotenv()

RAG_SYSTEM_PROMPT = (
    "You are an expert AI document assistant designed to provide accurate answers strictly based on the user's provided document context.\n\n"
    "CRITICAL RULES:\n"
    "1. Answer the question using ONLY the information provided in the context below.\n"
    "2. If the answer cannot be determined directly from the context, state clearly:\n"
    "   \"I cannot find the answer to that in the provided documents.\"\n"
    "3. Never make up facts, hallucinate, or extrapolate beyond what is explicitly written in the context.\n"
    "4. When stating facts, cite the source document name and page number if available (e.g. \"According to [doc.pdf, Page 1]...\").\n"
    "5. Format your response cleanly using Markdown."
)

FALLBACK_MODELS = [
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b",
    "groq/compound-mini",
]


class RAGPipeline:
    """
    Production-ready RAG pipeline:
    1. Embeds user query using SentenceTransformer.
    2. Performs similarity search in user's isolated FAISS index.
    3. Formulates a grounded context prompt.
    4. Invokes Groq LLM with fallback resilience.
    5. Returns grounded answer alongside structured source citations.
    """
    def __init__(self, vector_store: Optional[FAISSUserStore] = None):
        self.embedding_service = get_embedding_service()
        self.vector_store = vector_store or FAISSUserStore()
        api_key = os.environ.get("GROQ_API_KEY", "").strip()
        self.client = Groq(api_key=api_key) if api_key and api_key != "your_groq_api_key_here" else None

    def query(
        self,
        user_id: str,
        question: str,
        model: str = "openai/gpt-oss-20b",
        doc_ids: Optional[List[int]] = None,
        top_k: int = 4
    ) -> Dict[str, Any]:
        """
        Executes grounded RAG search & generation for the given user and question.
        """
        if not question or not question.strip():
            return {
                "answer": "Please ask a question about your documents.",
                "sources": [],
                "model": model
            }

        # Check if user has any documents/chunks indexed
        user_chunk_count = self.vector_store.get_user_chunks_count(user_id)
        if user_chunk_count == 0:
            return {
                "answer": (
                    "You have not uploaded any documents yet. "
                    "Please upload a PDF, DOCX, or TXT document using the attachment button "
                    "or the Document Management panel to ask questions about it."
                ),
                "sources": [],
                "model": model
            }

        # 1. Embed query
        query_embedding = self.embedding_service.embed_query(question.strip())

        # 2. Similarity search in user's FAISS index
        retrieved_chunks = self.vector_store.similarity_search(
            user_id=user_id,
            query_embedding=query_embedding,
            top_k=top_k,
            doc_ids=doc_ids
        )

        if not retrieved_chunks:
            return {
                "answer": "I cannot find the answer to that in the provided documents.",
                "sources": [],
                "model": model
            }

        # Filter out very low similarity matches (e.g. negative or near-zero cosine similarity)
        relevant_chunks = [c for c in retrieved_chunks if c.get("score", 0) > 0.15]
        if not relevant_chunks:
            return {
                "answer": "I cannot find the answer to that in the provided documents.",
                "sources": [],
                "model": model
            }

        # 3. Build grounded context
        context_parts = []
        for i, chunk in enumerate(relevant_chunks):
            doc_name = chunk.get("document_name", "Document")
            page_num = chunk.get("page_number", 1)
            content = chunk.get("content", "").strip()
            context_parts.append(f"--- Document: {doc_name} (Page {page_num}) ---\n{content}")

        context_str = "\n\n".join(context_parts)

        # 4. Deduplicate source citations for UI display
        sources = []
        seen = set()
        for chunk in relevant_chunks:
            key = (chunk.get("document_name"), chunk.get("page_number"), chunk.get("chunk_index"))
            if key not in seen:
                seen.add(key)
                content_snippet = chunk.get("content", "").strip()
                if len(content_snippet) > 220:
                    content_snippet = content_snippet[:220] + "..."
                sources.append({
                    "document_id": chunk.get("document_id"),
                    "document_name": chunk.get("document_name", "Unknown Document"),
                    "page_number": chunk.get("page_number", 1),
                    "chunk_index": chunk.get("chunk_index", 0),
                    "score": round(chunk.get("score", 0.0), 3),
                    "snippet": content_snippet
                })

        # 5. LLM Generation
        if not self.client:
            return {
                "answer": (
                    "RAG context retrieved successfully, but GROQ_API_KEY is not configured on the server. "
                    "Please configure GROQ_API_KEY in backend/.env."
                ),
                "sources": sources,
                "model": model
            }

        prompt_messages = [
            {"role": "system", "content": RAG_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"DOCUMENT CONTEXT:\n{context_str}\n\nUSER QUESTION:\n{question.strip()}\n\nGROUNDED ANSWER:"
            }
        ]

        candidate_models = [model]
        for fb in FALLBACK_MODELS:
            if fb not in candidate_models:
                candidate_models.append(fb)

        model_used = model
        answer_text = None
        last_error = None

        for candidate in candidate_models:
            try:
                response = self.client.chat.completions.create(
                    messages=prompt_messages,
                    model=candidate,
                    temperature=0.2,  # Low temperature for strict adherence to facts
                    max_tokens=1500
                )
                answer_text = response.choices[0].message.content
                model_used = candidate
                break
            except Exception as e:
                err_str = str(e)
                last_error = err_str
                if "model_decommissioned" in err_str or "model_not_found" in err_str or "does not exist" in err_str:
                    continue
                return {
                    "answer": f"Error generating answer with AI: {err_str}",
                    "sources": sources,
                    "model": candidate
                }

        if answer_text is None:
            answer_text = f"Error generating answer with AI: {last_error}"

        return {
            "answer": answer_text,
            "sources": sources,
            "model": model_used
        }
