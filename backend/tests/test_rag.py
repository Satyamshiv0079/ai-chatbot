import pytest
import os
import sys
import io
import shutil
import numpy as np

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from api.app import app
from flask_jwt_extended import create_access_token
from rag_service.document_processor import DocumentProcessor
from rag_service.embedding_service import get_embedding_service
from rag_service.vector_store import FAISSUserStore
from rag_service.rag_chain import RAGPipeline
import docx
import pypdf

TEST_VECTOR_DIR = os.path.join(os.path.dirname(__file__), 'temp_test_vector_stores')

@pytest.fixture(scope="session", autouse=True)
def cleanup_test_dirs():
    """Ensure test vector store directory is cleaned up before and after test session."""
    if os.path.exists(TEST_VECTOR_DIR):
        shutil.rmtree(TEST_VECTOR_DIR, ignore_errors=True)
    yield
    if os.path.exists(TEST_VECTOR_DIR):
        shutil.rmtree(TEST_VECTOR_DIR, ignore_errors=True)


@pytest.fixture
def auth_client():
    app.config['TESTING'] = True
    app.config['VECTOR_STORE_PATH'] = TEST_VECTOR_DIR
    with app.test_client() as client:
        with app.app_context():
            token = create_access_token(identity="rag_test_user")
        client.environ_base['HTTP_AUTHORIZATION'] = f'Bearer {token}'
        yield client


def test_document_processor_txt(tmp_path):
    processor = DocumentProcessor(chunk_size=150, chunk_overlap=30)
    txt_file = tmp_path / "sample.txt"
    sample_content = (
        "Artificial intelligence and machine learning are revolutionizing software development. "
        "Retrieval-Augmented Generation (RAG) pairs dense semantic vector search with large language models. "
        "This ensures answers are strictly grounded in custom enterprise knowledge bases."
    )
    txt_file.write_text(sample_content, encoding="utf-8")

    chunks, pages = processor.process_file(
        file_path=str(txt_file),
        filename="sample.txt",
        document_id=1,
        user_id="user_test"
    )

    assert len(chunks) >= 1
    assert pages == 1
    assert chunks[0]["document_id"] == 1
    assert chunks[0]["document_name"] == "sample.txt"
    assert "Retrieval-Augmented Generation" in chunks[0]["content"] or "Artificial intelligence" in chunks[0]["content"]


def test_document_processor_docx(tmp_path):
    processor = DocumentProcessor(chunk_size=200, chunk_overlap=40)
    docx_file = tmp_path / "test_doc.docx"

    doc = docx.Document()
    doc.add_heading("Company Policy on Generative AI", level=1)
    doc.add_paragraph("All employees must ensure customer data is strictly isolated across tenants.")
    doc.add_paragraph("FAISS vector stores must maintain separate indices per user identifier.")
    doc.save(str(docx_file))

    chunks, pages = processor.process_file(
        file_path=str(docx_file),
        filename="test_doc.docx",
        document_id=2,
        user_id="user_test"
    )

    assert len(chunks) >= 1
    assert any("strictly isolated" in c["content"] for c in chunks)


def test_embeddings_service():
    embed_svc = get_embedding_service()
    assert embed_svc.dimension == 384

    texts = [
        "Vector databases store high-dimensional embeddings.",
        "FAISS provides fast similarity search in dense vector spaces."
    ]
    embeddings = embed_svc.embed_texts(texts)
    assert isinstance(embeddings, np.ndarray)
    assert embeddings.shape == (2, 384)
    assert embeddings.dtype == np.float32

    # Verify L2 normalization: norm of each vector should equal 1.0
    for vec in embeddings:
        norm = np.linalg.norm(vec)
        assert abs(norm - 1.0) < 1e-4


def test_faiss_vector_store_and_user_isolation(tmp_path):
    store = FAISSUserStore(base_dir=str(tmp_path / "vector_test"))
    embed_svc = get_embedding_service()

    # User Alice stores machine learning notes
    alice_text = ["Gradient descent optimizes the loss function of deep neural networks using backpropagation."]
    alice_chunks = [{
        "content": alice_text[0],
        "document_id": 101,
        "document_name": "ml_notes.txt",
        "page_number": 1,
        "chunk_index": 0,
        "user_id": "alice"
    }]
    alice_emb = embed_svc.embed_texts(alice_text)
    store.add_chunks(user_id="alice", new_chunks=alice_chunks, embeddings=alice_emb)

    # User Bob stores culinary recipes
    bob_text = ["Traditional sourdough bread requires sourdough starter, flour, water, and sea salt."]
    bob_chunks = [{
        "content": bob_text[0],
        "document_id": 202,
        "document_name": "sourdough.txt",
        "page_number": 1,
        "chunk_index": 0,
        "user_id": "bob"
    }]
    bob_emb = embed_svc.embed_texts(bob_text)
    store.add_chunks(user_id="bob", new_chunks=bob_chunks, embeddings=bob_emb)

    # 1. Alice searches for neural networks
    query_emb = embed_svc.embed_query("How does neural network optimization work?")
    alice_results = store.similarity_search(user_id="alice", query_embedding=query_emb, top_k=2)
    assert len(alice_results) == 1
    assert "Gradient descent" in alice_results[0]["content"]
    assert alice_results[0]["document_name"] == "ml_notes.txt"

    # 2. Bob searches for neural networks in HIS store -> Must return 0 relevant or empty
    bob_search_ml = store.similarity_search(user_id="bob", query_embedding=query_emb, top_k=2)
    # Bob has only sourdough, so no neural network content exists in Bob's index!
    assert not any("Gradient descent" in r["content"] for r in bob_search_ml)

    # 3. User isolation check: Alice CANNOT see Bob's sourdough doc
    bread_query_emb = embed_svc.embed_query("What are the ingredients in sourdough bread?")
    alice_search_bread = store.similarity_search(user_id="alice", query_embedding=bread_query_emb, top_k=2)
    assert not any("sourdough starter" in r["content"] for r in alice_search_bread)

    # 4. Bob searches sourdough
    bob_results = store.similarity_search(user_id="bob", query_embedding=bread_query_emb, top_k=2)
    assert len(bob_results) == 1
    assert "sourdough starter" in bob_results[0]["content"]


def test_document_deletion_in_vector_store(tmp_path):
    store = FAISSUserStore(base_dir=str(tmp_path / "vector_del_test"))
    embed_svc = get_embedding_service()

    chunks = [
        {"content": "Document A chunk 1", "document_id": 1, "document_name": "A.txt", "page_number": 1, "chunk_index": 0, "user_id": "carol"},
        {"content": "Document B chunk 1", "document_id": 2, "document_name": "B.txt", "page_number": 1, "chunk_index": 0, "user_id": "carol"},
    ]
    embs = embed_svc.embed_texts([c["content"] for c in chunks])
    store.add_chunks("carol", chunks, embs)
    assert store.get_user_chunks_count("carol") == 2

    # Delete Doc 1
    store.delete_document("carol", doc_id=1, embedding_service=embed_svc)
    assert store.get_user_chunks_count("carol") == 1

    # Search confirms Doc 1 is gone and Doc 2 remains
    q_emb = embed_svc.embed_query("Document B")
    res = store.similarity_search("carol", q_emb, top_k=2)
    assert len(res) == 1
    assert res[0]["document_id"] == 2


def test_rag_pipeline_out_of_context():
    """Verify that asking a question not answered in documents produces the ungrounded fallback message."""
    rag_pipe = RAGPipeline()
    # Query for a user who has no documents
    res = rag_pipe.query(user_id="empty_user_999", question="What is the internal code for project Apollo?")
    assert "You have not uploaded any documents yet" in res["answer"] or "cannot find" in res["answer"]
    assert res["sources"] == []


def test_api_document_lifecycle(auth_client):
    """Test REST API: upload -> list -> rag query -> delete document."""
    # 1. Upload a text document
    file_content = (
        b"Antigravity Corporation was founded in 2024 to advance agentic AI systems. "
        b"Its headquarters are located in San Francisco, California. "
        b"The flagship system is the AI Chatbot with FAISS-powered RAG."
    )
    data = {
        'file': (io.BytesIO(file_content), 'antigravity_info.txt')
    }
    upload_res = auth_client.post(
        '/api/documents/upload',
        data=data,
        content_type='multipart/form-data'
    )
    assert upload_res.status_code == 201
    doc_data = upload_res.json['document']
    doc_id = doc_data['id']
    assert doc_data['filename'] == 'antigravity_info.txt'
    assert doc_data['chunk_count'] >= 1

    # 2. List documents
    list_res = auth_client.get('/api/documents')
    assert list_res.status_code == 200
    docs = list_res.json['documents']
    assert any(d['id'] == doc_id for d in docs)

    # 3. RAG Query against the uploaded document
    query_res = auth_client.post(
        '/api/rag/query',
        json={"query": "Where are the headquarters of Antigravity Corporation located?"}
    )
    assert query_res.status_code == 200
    assert "answer" in query_res.json
    assert "sources" in query_res.json
    assert len(query_res.json["sources"]) >= 1
    assert query_res.json["sources"][0]["document_name"] == "antigravity_info.txt"

    # 4. Delete document
    del_res = auth_client.delete(f'/api/documents/{doc_id}')
    assert del_res.status_code == 200

    # 5. Verify document is deleted from list
    list_after_del = auth_client.get('/api/documents')
    assert not any(d['id'] == doc_id for d in list_after_del.json['documents'])
