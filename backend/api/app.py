from flask import Flask, jsonify, request
from flask_cors import CORS
import sys
import os

# Fix the path so Python can find nlp_service and dialog_service
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from nlp_service.predictor import NLPPredictor
from dialog_service.dialog_manager import DialogManager
from groq import Groq

app = Flask(__name__)
CORS(app)

# Initialize services
nlp = NLPPredictor(model_path=os.path.join(os.path.dirname(__file__), '..', 'nlp_service', 'model'))
dialog = DialogManager()

# Groq client
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

GROQ_MODELS = {
    "llama3-70b": "llama-3.3-70b-versatile",
    "llama3-8b": "llama-3.1-8b-instant",
}

@app.route('/')
def home():
    return jsonify({"message": "AI Chatbot API is running!", "status": "ok"})

@app.route('/health')
def health():
    groq_ok = bool(os.environ.get("GROQ_API_KEY"))
    return jsonify({"status": "healthy", "groq_enabled": groq_ok})

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

@app.route('/chat/groq', methods=['POST'])
def chat_groq():
    data = request.get_json()

    if not data or 'message' not in data:
        return jsonify({"error": "No message provided"}), 400

    if not os.environ.get("GROQ_API_KEY"):
        return jsonify({"error": "Groq API key not configured"}), 500

    user_message = data['message']
    history = data.get('history', [])
    model_key = data.get('model', 'llama3-70b')
    model_id = GROQ_MODELS.get(model_key, GROQ_MODELS['llama3-70b'])

    messages = [
        {
            "role": "system",
            "content": "You are a helpful AI assistant. Be concise, friendly, and accurate."
        }
    ]
    for turn in history[-10:]:
        if turn.get('role') and turn.get('content'):
            messages.append({"role": turn['role'], "content": turn['content']})

    messages.append({"role": "user", "content": user_message})

    try:
        completion = groq_client.chat.completions.create(
            model=model_id,
            messages=messages,
            max_tokens=1024,
            temperature=0.7
        )
        reply = completion.choices[0].message.content
        return jsonify({
            "bot_response": reply,
            "model": model_id,
            "usage": {
                "prompt_tokens": completion.usage.prompt_tokens,
                "completion_tokens": completion.usage.completion_tokens
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/groq/models', methods=['GET'])
def get_groq_models():
    return jsonify({"models": list(GROQ_MODELS.keys())})

@app.route('/history/<session_id>', methods=['GET'])
def get_history(session_id):
    session = dialog.state.get_session(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    return jsonify({"history": session["history"]})

if __name__ == '__main__':
    app.run(host='localhost', debug=False, port=8000)
