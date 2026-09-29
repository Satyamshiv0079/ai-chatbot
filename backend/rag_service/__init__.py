"""
RAG Service Package for AI Chatbot.
Provides document parsing, semantic chunking, embedding generation,
per-user FAISS vector storage, LangChain UserScopedRetriever, and
LangChain ChatPromptTemplate + ChatGroq RAG pipeline.
"""
from .embedding_service import get_embedding_service, EmbeddingService
from .document_processor import DocumentProcessor
from .vector_store import FAISSUserStore
from .retriever import UserScopedRetriever
from .rag_chain import RAGPipeline

__all__ = [
    "get_embedding_service",
    "EmbeddingService",
    "DocumentProcessor",
    "FAISSUserStore",
    "UserScopedRetriever",
    "RAGPipeline",
]
