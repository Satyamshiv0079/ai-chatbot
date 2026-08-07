from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from sqlalchemy import func
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from nlp_service.predictor import NLPPredictor
from dialog_service.dialog_manager import DialogManager
from dialog_service.models import UserSession, ConversationHistory, ChatbotResponse, User
from auth.auth_routes import auth_bp
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# ── JWT ───────────────────────────────────────────────────────────────────────
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'dev-secret-change-in-production')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = False
jwt = JWTManager(app)

app.register_blueprint(auth_bp)

nlp = NLPPredictor(model_path=os.path.join(os.path.dirname(__file__), '..', 'nlp_service', 'model'))
dialog = DialogManager()


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
    data = request.get_json() or {}
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
ALLOWED_MODELS = {
    "llama-3.3-70b-versatile": "Llama 3.3 70B",
    "llama-3.1-8b-instant": "Llama 3.1 8B (Fast)",
    "mixtral-8x7b-32768": "Mixtral 8x7B",
    "gemma2-9b-it": "Gemma 2 9B",
}

@app.route('/models', methods=['GET'])
@jwt_required()
def list_models():
    return jsonify({"models": [{"id": k, "name": v} for k, v in ALLOWED_MODELS.items()]})


@app.route('/chat', methods=['POST'])
@jwt_required()
def chat():
    username = get_jwt_identity()
    data = request.get_json()

    if not data or 'message' not in data:
        return jsonify({"error": "No message provided"}), 400

    user_message = data['message']
    session_id = data.get('session_id')
    model = data.get('model', 'llama-3.3-70b-versatile')

    # Validate model
    if model not in ALLOWED_MODELS:
        model = 'llama-3.3-70b-versatile'

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
        "confidence": nlp_result["confidence"],
        "model": model,
    })


# ── Dashboard ─────────────────────────────────────────────────────────────────
@app.route('/api/dashboard/stats', methods=['GET'])
@jwt_required()
def dashboard_stats():
    db = dialog.state.Session()
    try:
        total_sessions = db.query(UserSession).count()
        total_messages = db.query(ConversationHistory).count()
        intent_counts = db.query(
            ConversationHistory.intent, func.count(ConversationHistory.id)
        ).group_by(ConversationHistory.intent).all()
        return jsonify({
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "intents_distribution": [{"name": i[0] or "unknown", "value": i[1]} for i in intent_counts],
        })
    finally:
        db.close()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', debug=False, port=port)


sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from nlp_service.predictor import NLPPredictor
from dialog_service.dialog_manager import DialogManager
from dialog_service.models import UserSession, ConversationHistory, ChatbotResponse, User
from auth.auth_routes import auth_bp
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# ── JWT Configuration ────────────────────────────────────────────────────────
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'dev-secret-change-in-production')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = False   # Tokens don't expire in dev; set timedelta in production
jwt = JWTManager(app)

# ── Register auth blueprint ──────────────────────────────────────────────────
app.register_blueprint(auth_bp)

# ── Initialize ML services ───────────────────────────────────────────────────
nlp = NLPPredictor(model_path=os.path.join(os.path.dirname(__file__), '..', 'nlp_service', 'model'))
dialog = DialogManager()


# ── Public routes ─────────────────────────────────────────────────────────────
@app.route('/')
def home():
    return jsonify({"message": "AI Chatbot API is running!", "status": "ok"})


@app.route('/health')
def health():
    return jsonify({"status": "healthy"})


# ── Protected routes (require valid JWT) ──────────────────────────────────────
@app.route('/session/new', methods=['POST'])
@jwt_required()
def new_session():
    session_id = dialog.start_session()
    return jsonify({"session_id": session_id})


@app.route('/chat', methods=['POST'])
@jwt_required()
def chat():
    current_user = get_jwt_identity()
    data = request.get_json()

    if not data or 'message' not in data:
        return jsonify({"error": "No message provided"}), 400

    user_message = data['message']
    session_id = data.get('session_id', None)

    nlp_result = nlp.process(user_message)
    intent = nlp_result['intent']
    entities = nlp_result['entities']

    dialog_result = dialog.handle(
        session_id=session_id,
        intent=intent,
        entities=entities,
        user_text=user_message
    )

    return jsonify({
        "session_id": dialog_result["session_id"],
        "user_message": user_message,
        "bot_response": dialog_result["response"],
        "intent": intent,
        "confidence": nlp_result["confidence"],
        "entities": entities
    })


@app.route('/history/<session_id>', methods=['GET'])
@jwt_required()
def get_history(session_id):
    session = dialog.state.get_session(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    return jsonify({"history": session["history"]})


# ── Dashboard (protected) ────────────────────────────────────────────────────
from sqlalchemy import func

@app.route('/api/dashboard/stats', methods=['GET'])
@jwt_required()
def dashboard_stats():
    db_session = dialog.state.Session()
    try:
        total_sessions = db_session.query(UserSession).count()
        total_messages = db_session.query(ConversationHistory).count()

        intent_counts = db_session.query(
            ConversationHistory.intent,
            func.count(ConversationHistory.id)
        ).group_by(ConversationHistory.intent).all()

        intents_data = [{"name": i[0] or "unknown", "value": i[1]} for i in intent_counts]

        recent = db_session.query(ConversationHistory).order_by(
            ConversationHistory.timestamp.desc()
        ).limit(5).all()

        recent_history = [{
            "user": r.user_text,
            "bot": r.bot_response.response_text if r.bot_response else "",
            "intent": r.intent,
            "time": r.timestamp.isoformat()
        } for r in recent]

        return jsonify({
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "intents_distribution": intents_data,
            "recent_activity": recent_history
        })
    finally:
        db_session.close()


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=False, port=5000)