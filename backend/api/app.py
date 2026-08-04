from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
import sys
import os

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