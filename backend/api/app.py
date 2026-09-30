import logging
import time
from datetime import timedelta
import sys, os
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from sqlalchemy import func
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from werkzeug.utils import secure_filename
from nlp_service.predictor import NLPPredictor
from dialog_service.dialog_manager import DialogManager
from dialog_service.models import (
    UserSession, ConversationHistory, ChatbotResponse, User,
    Document, DocumentChunk
)
from auth.auth_routes import auth_bp

load_dotenv()

# ── Structured Diagnostic Logging ─────────────────────────────────────────────
logger = logging.getLogger("novamind.rag")
if not logger.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)

try:
    from api.rate_limiter import limiter
except ImportError:
    from rate_limiter import limiter

app = Flask(__name__)

# ── CORS Configuration ────────────────────────────────────────────────────────
frontend_url = os.environ.get('FRONTEND_URL')
if frontend_url:
    origins = [o.strip() for o in frontend_url.split(',') if o.strip()]
else:
    # Explicit allowed origins for local dev and preview without wildcard
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

CORS(
    app,
    resources={r"/*": {"origins": origins}},
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
)

# ── JWT ───────────────────────────────────────────────────────────────────────
is_production = os.environ.get('FLASK_ENV') == 'production' or os.environ.get('RENDER') == 'true' or os.environ.get('ENVIRONMENT') == 'production'
jwt_secret = os.environ.get('JWT_SECRET_KEY')
if is_production and (not jwt_secret or jwt_secret == 'dev-secret-change-in-production'):
    raise RuntimeError("JWT_SECRET_KEY environment variable MUST be set to a secure string in production environments!")

app.config['JWT_SECRET_KEY'] = jwt_secret or 'dev-secret-change-in-production'
jwt_exp_hours = int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES_HOURS', 2))
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=jwt_exp_hours)
jwt = JWTManager(app)

app.register_blueprint(auth_bp)

nlp = NLPPredictor(model_path=os.path.join(os.path.dirname(__file__), '..', 'nlp_service', 'model'))
dialog = DialogManager()

# ── Uploads & RAG Configuration ───────────────────────────────────────────────
MAX_UPLOAD_SIZE_MB = int(os.environ.get('MAX_UPLOAD_SIZE_MB', 10))
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(os.path.dirname(__file__), '..', 'uploads'))
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc', 'txt', 'md', 'csv', 'json', 'py', 'js', 'html'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_SIZE_MB * 1024 * 1024

def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def _get_safe_user_dir(base_folder: str, user_id: str) -> str:
    """Sanitizes user_id and ensures the resolved directory cannot escape base_folder."""
    safe_user = "".join(c for c in str(user_id) if c.isalnum() or c in ("-", "_")).strip()
    if not safe_user:
        safe_user = "default_user"
    user_dir = os.path.abspath(os.path.join(base_folder, safe_user))
    base_canonical = os.path.abspath(base_folder)
    if not user_dir.startswith(base_canonical):
        raise ValueError("Path traversal attempt detected in user identifier")
    os.makedirs(user_dir, exist_ok=True)
    return user_dir

_rag_pipeline = None
_doc_processor = None
_vector_store = None

def _get_rag_components():
    global _rag_pipeline, _doc_processor, _vector_store
    if _rag_pipeline is None:
        from rag_service.document_processor import DocumentProcessor
        from rag_service.vector_store import FAISSUserStore
        from rag_service.rag_chain import RAGPipeline
        _vector_store = FAISSUserStore()
        _doc_processor = DocumentProcessor(chunk_size=800, chunk_overlap=120)
        _rag_pipeline = RAGPipeline(vector_store=_vector_store)
    return _rag_pipeline, _doc_processor, _vector_store


# ── Public ────────────────────────────────────────────────────────────────────
@app.route('/')
def home():
    return jsonify({"message": "AI Chatbot API is running!", "status": "ok"})

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})


# ── Session Management ────────────────────────────────────────────────────────
@app.route('/session/new', methods=['POST'])
@jwt_required()
def new_session():
    username = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    title = data.get('title', 'New Chat')
    # Create session linked to this user
    session_id = dialog.state.create_session(user_id=username)
    # Set an initial title on the session
    db = dialog.state.Session()
    try:
        s = db.query(UserSession).filter_by(session_id=session_id).first()
        if s:
            s.title = title
            db.commit()
    finally:
        db.close()
    return jsonify({"session_id": session_id, "title": title})


@app.route('/sessions', methods=['GET'])
@jwt_required()
def list_sessions():
    """Return all sessions for the logged-in user, newest first."""
    username = get_jwt_identity()
    db = dialog.state.Session()
    try:
        sessions = (
            db.query(UserSession)
            .filter_by(user_id=username)
            .order_by(UserSession.created_at.desc())
            .all()
        )
        result = []
        for s in sessions:
            # Get message count and first user message as preview
            msg_count = len(s.histories)
            preview = s.histories[0].user_text[:60] if s.histories else "Empty chat"
            title = getattr(s, 'title', None) or (s.histories[0].user_text[:40] if s.histories else 'New Chat')
            result.append({
                "session_id": s.session_id,
                "title": title,
                "preview": preview,
                "message_count": msg_count,
                "created_at": s.created_at.isoformat(),
            })
        return jsonify({"sessions": result})
    finally:
        db.close()


@app.route('/sessions/<session_id>', methods=['GET'])
@jwt_required()
def get_session_messages(session_id):
    """Load full message history for a session."""
    username = get_jwt_identity()
    db = dialog.state.Session()
    try:
        s = db.query(UserSession).filter_by(session_id=session_id, user_id=username).first()
        if not s:
            return jsonify({"error": "Session not found"}), 404
        history = [{
            "sender": "user",
            "text": h.user_text,
            "timestamp": h.timestamp.isoformat()
        } for h in s.histories]
        # Interleave bot responses
        full_history = []
        for h in s.histories:
            full_history.append({"sender": "user", "text": h.user_text, "id": h.id * 2})
            if h.bot_response:
                full_history.append({"sender": "bot", "text": h.bot_response.response_text, "id": h.id * 2 + 1})
        title = getattr(s, 'title', None) or (s.histories[0].user_text[:40] if s.histories else 'Chat')
        return jsonify({"session_id": session_id, "title": title, "messages": full_history})
    finally:
        db.close()


@app.route('/sessions/<session_id>/rename', methods=['PATCH'])
@jwt_required()
def rename_session(session_id):
    username = get_jwt_identity()
    data = request.get_json() or {}
    new_title = data.get('title', '').strip()
    if not new_title:
        return jsonify({"error": "Title is required"}), 400
    db = dialog.state.Session()
    try:
        s = db.query(UserSession).filter_by(session_id=session_id, user_id=username).first()
        if not s:
            return jsonify({"error": "Session not found"}), 404
        s.title = new_title
        db.commit()
        return jsonify({"message": "Renamed successfully"})
    finally:
        db.close()


@app.route('/sessions/<session_id>', methods=['DELETE'])
@jwt_required()
def delete_session(session_id):
    username = get_jwt_identity()
    db = dialog.state.Session()
    try:
        s = db.query(UserSession).filter_by(session_id=session_id, user_id=username).first()
        if not s:
            return jsonify({"error": "Session not found"}), 404
        db.delete(s)
        db.commit()
        return jsonify({"message": "Deleted"})
    finally:
        db.close()


# ── Chat (with model switcher) ────────────────────────────────────────────────
# Friendly display names — ACTIVE models on Groq
MODEL_NAMES = {
    "openai/gpt-oss-20b":       "GPT OSS 20B (Fast)",
    "openai/gpt-oss-120b":      "GPT OSS 120B",
    "qwen/qwen3.8-27b":         "Qwen 3.8 27B",
    "groq/compound-mini":       "Groq Compound Mini",
}

DEFAULT_MODEL = "openai/gpt-oss-20b"

# Cache so we don't hit Groq on every request
_models_cache = None

def _fetch_groq_models():
    """Fetch available models from Groq API dynamically."""
    global _models_cache
    if _models_cache:
        return _models_cache
    try:
        import urllib.request, json as _json
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/models",
            headers={
                "Authorization": f"Bearer {os.environ.get('GROQ_API_KEY', '')}",
                "User-Agent": "ai-chatbot/1.0"
            },
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = _json.loads(resp.read())

        returned_ids = {m["id"] for m in data.get("data", [])}
        # Only show models present in both live list and active mappings
        active_list = [
            {"id": mid, "name": MODEL_NAMES[mid]}
            for mid in MODEL_NAMES
            if mid in returned_ids
        ]
        if active_list:
            _models_cache = active_list
            return _models_cache
    except Exception:
        pass

    # Fallback to active production models
    _models_cache = [
        {"id": "openai/gpt-oss-20b",   "name": "GPT OSS 20B (Fast)"},
        {"id": "openai/gpt-oss-120b",  "name": "GPT OSS 120B"},
        {"id": "qwen/qwen3.8-27b",     "name": "Qwen 3.8 27B"},
        {"id": "groq/compound-mini",   "name": "Groq Compound Mini"},
    ]
    return _models_cache

@app.route('/models', methods=['GET'])
@jwt_required()
def list_models():
    return jsonify({"models": _fetch_groq_models()})


@app.route('/chat', methods=['POST'])
@jwt_required()
@limiter.limit(max_requests=30, window_seconds=60)
def chat():
    username = get_jwt_identity()
    data = request.get_json(silent=True) or {}

    if 'message' not in data:
        return jsonify({"error": "No message provided"}), 400

    user_message = data['message']
    session_id = data.get('session_id')
    model = data.get('model', DEFAULT_MODEL)

    if session_id:
        db = dialog.state.Session()
        try:
            s = db.query(UserSession).filter_by(session_id=session_id).first()
            if s and s.user_id and s.user_id != username:
                return jsonify({"error": "Forbidden: Session belongs to another user"}), 403
        finally:
            db.close()

    # Validate model — use first available from live list if requested one isn't accessible
    available = _fetch_groq_models()
    available_ids = {m["id"] for m in available}
    if model not in available_ids:
        model = available[0]["id"] if available else DEFAULT_MODEL

    nlp_result = nlp.process(user_message)
    intent = nlp_result['intent']
    entities = nlp_result['entities']

    dialog_result = dialog.handle(
        session_id=session_id,
        intent=intent,
        entities=entities,
        user_text=user_message,
        model=model
    )

    # Auto-title the session from the first user message
    if dialog_result.get("session_id"):
        db = dialog.state.Session()
        try:
            s = db.query(UserSession).filter_by(session_id=dialog_result["session_id"]).first()
            if s and (not getattr(s, 'title', None) or s.title == 'New Chat'):
                s.title = user_message[:45] + ('…' if len(user_message) > 45 else '')
                s.user_id = username
                db.commit()
        finally:
            db.close()

    return jsonify({
        "session_id": dialog_result["session_id"],
        "user_message": user_message,
        "bot_response": dialog_result["response"],
        "intent": intent,
        "entities": entities,
        "confidence": nlp_result["confidence"],
        "model": model,
    })


# ── RAG & Document Management ─────────────────────────────────────────────────
@app.route('/api/documents/upload', methods=['POST'])
@jwt_required()
@limiter.limit(max_requests=10, window_seconds=60)
def upload_document():
    """
    Accepts multipart file upload (PDF, DOCX, TXT, MD, etc.),
    validates file, extracts text, chunks and embeds, updates user's isolated FAISS index,
    and commits database records with detailed diagnostic logging.
    """
    start_time = time.time()
    username = get_jwt_identity()

    if 'file' not in request.files:
        return jsonify({"error": "No file part in request"}), 400

    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if not _allowed_file(file.filename):
        allowed_list = ", ".join(ALLOWED_EXTENSIONS)
        return jsonify({"error": f"Unsupported file type. Allowed: {allowed_list}"}), 400

    filename = secure_filename(file.filename)
    if not filename:
        filename = f"upload_{int(time.time())}.txt"

    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'txt'

    # Secure user upload path with path traversal defense
    try:
        user_upload_dir = _get_safe_user_dir(app.config['UPLOAD_FOLDER'], username)
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400

    file_path = os.path.abspath(os.path.join(user_upload_dir, filename))
    if not file_path.startswith(user_upload_dir):
        return jsonify({"error": "Invalid upload path: path traversal detected"}), 400

    # Save to disk
    file.save(file_path)
    file_size = os.path.getsize(file_path)

    logger.info(
        "Document upload started: user_id='%s', filename='%s', extension='%s', size=%d bytes",
        username, filename, ext, file_size
    )

    if file_size > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        try:
            os.remove(file_path)
        except OSError:
            pass
        logger.warning(
            "Upload rejected (file too large): user_id='%s', filename='%s', size=%d bytes",
            username, filename, file_size
        )
        return jsonify({"error": f"File size exceeds maximum limit of {MAX_UPLOAD_SIZE_MB}MB"}), 413

    if file_size == 0:
        try:
            os.remove(file_path)
        except OSError:
            pass
        return jsonify({"error": "The uploaded file is empty (0 bytes)."}), 400

    db = dialog.state.Session()
    doc = None
    try:
        doc = Document(
            user_id=username,
            filename=filename,
            file_type=ext,
            file_size=file_size,
            status="processing"
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        rag_pipe, doc_proc, vec_store = _get_rag_components()
        from rag_service.embedding_service import get_embedding_service
        embed_svc = get_embedding_service()

        try:
            chunks, total_pages = doc_proc.process_file(
                file_path=file_path,
                filename=filename,
                document_id=doc.id,
                user_id=username
            )
        except ValueError as ve:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass
            db.delete(doc)
            db.commit()
            logger.warning(
                "Document extraction rejected: user_id='%s', filename='%s', reason='%s'",
                username, filename, str(ve)
            )
            return jsonify({"error": str(ve)}), 400

        # Memory-safe batch embedding and FAISS indexing
        batch_size = 16
        vec_store.add_chunks_batched(
            user_id=username,
            chunks=chunks,
            embedding_service=embed_svc,
            batch_size=batch_size
        )

        # Persist chunk records to DB
        for c in chunks:
            db_chunk = DocumentChunk(
                document_id=doc.id,
                user_id=username,
                chunk_index=c["chunk_index"],
                page_number=c["page_number"],
                content=c["content"],
                metadata_json=str(c.get("metadata", {}))
            )
            db.add(db_chunk)

        doc.chunk_count = len(chunks)
        doc.page_count = total_pages
        doc.status = "ready"
        db.commit()

        duration = round(time.time() - start_time, 2)
        logger.info(
            "Document indexed successfully: user_id='%s', doc_id=%d, filename='%s', chunks=%d, pages=%d, batch_size=%d, dimension=%d, duration=%.2fs",
            username, doc.id, filename, len(chunks), total_pages, batch_size, embed_svc.dimension, duration
        )

        import gc
        gc.collect()

        return jsonify({
            "message": f"Successfully indexed '{filename}' ({len(chunks)} chunks, {total_pages} page(s))",
            "document": doc.to_dict()
        }), 201
    except Exception as e:
        db.rollback()
        if doc and getattr(doc, 'id', None):
            try:
                db.delete(doc)
                db.commit()
            except Exception:
                pass
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
        logger.error(
            "Document processing failed: user_id='%s', filename='%s', error=%s",
            username, filename, str(e), exc_info=True
        )
        return jsonify({
            "error": "Couldn't index this document. The file was uploaded, but document processing failed. Please verify the file is not corrupted and try again."
        }), 500
    finally:
        db.close()


@app.route('/api/documents', methods=['GET'])
@jwt_required()
def list_documents():
    """Returns all documents uploaded and indexed by the authenticated user."""
    username = get_jwt_identity()
    db = dialog.state.Session()
    try:
        docs = (
            db.query(Document)
            .filter_by(user_id=username)
            .order_by(Document.created_at.desc())
            .all()
        )
        return jsonify({"documents": [d.to_dict() for d in docs]})
    finally:
        db.close()


@app.route('/api/documents/<int:doc_id>', methods=['DELETE'])
@jwt_required()
def delete_document(doc_id):
    """
    Deletes a document by ID: removes from FAISS vector store,
    deletes file from disk, and removes DB records.
    Verifies document ownership strictly against authenticated JWT identity.
    """
    username = get_jwt_identity()
    db = dialog.state.Session()
    try:
        doc = db.query(Document).filter_by(id=doc_id, user_id=username).first()
        if not doc:
            return jsonify({"error": "Document not found"}), 404

        filename = doc.filename
        _, _, vec_store = _get_rag_components()
        from rag_service.embedding_service import get_embedding_service
        vec_store.delete_document(user_id=username, doc_id=doc_id, embedding_service=get_embedding_service())

        user_upload_dir = _get_safe_user_dir(app.config['UPLOAD_FOLDER'], username)
        file_path = os.path.abspath(os.path.join(user_upload_dir, secure_filename(filename)))
        if os.path.exists(file_path) and file_path.startswith(user_upload_dir):
            try:
                os.remove(file_path)
            except OSError:
                pass

        db.delete(doc)
        db.commit()
        logger.info("Document deleted: user_id='%s', doc_id=%d, filename='%s'", username, doc_id, filename)
        return jsonify({"message": f"Document '{filename}' deleted successfully"})
    except Exception as e:
        db.rollback()
        logger.error("Document delete failed: user_id='%s', doc_id=%d, error=%s", username, doc_id, str(e), exc_info=True)
        return jsonify({"error": "Failed to delete document."}), 500
    finally:
        db.close()


@app.route('/api/rag/query', methods=['POST'])
@jwt_required()
@limiter.limit(max_requests=30, window_seconds=60)
def rag_query():
    """
    Mode B (RAG / Ask My Documents):
    Performs similarity search over user's documents in FAISS, constructs a grounded prompt,
    invokes Groq LLM with fallback resilience, and returns answer + source citations.
    """
    username = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    query_text = (data.get('query') or '').strip()
    if not query_text:
        return jsonify({"error": "Query is required"}), 400

    model = data.get('model', DEFAULT_MODEL)
    doc_ids = data.get('doc_ids', None)
    top_k = int(data.get('top_k', 4))

    # IDOR protection: Verify any requested doc_ids belong to the authenticated user
    if doc_ids and isinstance(doc_ids, list):
        db = dialog.state.Session()
        try:
            valid_ids = {
                r[0] for r in db.query(Document.id).filter(
                    Document.id.in_(doc_ids), Document.user_id == username
                ).all()
            }
            # If user specified doc_ids but owns none, pass [-1] so no chunks are retrieved
            doc_ids = list(valid_ids) if valid_ids else [-1]
        finally:
            db.close()

    rag_pipe, _, _ = _get_rag_components()
    result = rag_pipe.query(
        user_id=username,
        question=query_text,
        model=model,
        doc_ids=doc_ids,
        top_k=top_k
    )

    return jsonify({
        "query": query_text,
        "answer": result["answer"],
        "sources": result["sources"],
        "model": result["model"]
    })


# ── Dashboard ─────────────────────────────────────────────────────────────────
@app.route('/api/dashboard/stats', methods=['GET'])
@jwt_required()
def dashboard_stats():
    username = get_jwt_identity()
    db = dialog.state.Session()
    try:
        # Strictly user-isolated statistics
        total_sessions = db.query(UserSession).filter_by(user_id=username).count()
        total_messages = (
            db.query(ConversationHistory)
            .join(UserSession, ConversationHistory.session_id == UserSession.session_id)
            .filter(UserSession.user_id == username)
            .count()
        )
        intent_counts = (
            db.query(ConversationHistory.intent, func.count(ConversationHistory.id))
            .join(UserSession, ConversationHistory.session_id == UserSession.session_id)
            .filter(UserSession.user_id == username)
            .group_by(ConversationHistory.intent)
            .all()
        )
        total_documents = db.query(Document).filter_by(user_id=username).count()

        recent_records = (
            db.query(ConversationHistory)
            .join(UserSession, ConversationHistory.session_id == UserSession.session_id)
            .filter(UserSession.user_id == username)
            .order_by(ConversationHistory.timestamp.desc())
            .limit(5)
            .all()
        )
        recent_activity = [{
            "intent": r.intent or "general",
            "user": r.user_text[:30] if r.user_text else "",
            "time": r.timestamp.isoformat() if r.timestamp else ""
        } for r in recent_records]

        return jsonify({
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "total_documents": total_documents,
            "intents_distribution": [{"name": i[0] or "unknown", "value": i[1]} for i in intent_counts],
            "recent_activity": recent_activity
        })
    finally:
        db.close()


# ── Global Error Handlers ─────────────────────────────────────────────────────
@app.errorhandler(400)
def bad_request(e):
    return jsonify({"error": getattr(e, 'description', "Bad request"), "status_code": 400}), 400

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Resource not found", "status_code": 404}), 404

@app.errorhandler(413)
def entity_too_large(e):
    return jsonify({"error": f"File size exceeds maximum upload limit of {MAX_UPLOAD_SIZE_MB}MB", "status_code": 413}), 413

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "An internal server error occurred", "status_code": 500}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', debug=False, port=port)