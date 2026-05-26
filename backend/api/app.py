from flask import Flask, jsonify, request
from flask_cors import CORS
import sys
import os

# Fix the path so Python can find nlp_service and dialog_service
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from nlp_service.predictor import NLPPredictor
from dialog_service.dialog_manager import DialogManager

app = Flask(__name__)
CORS(app)

# Initialize services
nlp = NLPPredictor(model_path=os.path.join(os.path.dirname(__file__), '..', 'nlp_service', 'model'))
dialog = DialogManager()

@app.route('/')
def home():
    return jsonify({"message": "AI Chatbot API is running!", "status": "ok"})

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/session/new', methods=['POST'])
def new_session():
    session_id = dialog.start_session()
    return jsonify({"session_id": session_id})

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()

    if not data or 'message' not in data:
        return jsonify({"error": "No message provided"}), 400

    user_message = data['message']
    session_id = data.get('session_id', None)

    # Step 1: NLP processes the message
    nlp_result = nlp.process(user_message)

    # Step 2: Dialog manager generates response
    dialog_result = dialog.handle(
        session_id=session_id,
        intent=nlp_result['intent'],
        entities=nlp_result['entities'],
        user_text=user_message
    )

    return jsonify({
        "session_id": dialog_result["session_id"],
        "user_message": user_message,
        "bot_response": dialog_result["response"],
        "intent": nlp_result["intent"],
        "confidence": nlp_result["confidence"],
        "entities": nlp_result["entities"]
    })

@app.route('/history/<session_id>', methods=['GET'])
def get_history(session_id):
    session = dialog.state.get_session(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    return jsonify({"history": session["history"]})

if __name__ == '__main__':
    app.run(host='localhost', debug=False, port=8000)