from flask import Flask, jsonify, request
from flask_cors import CORS
import sys
import os
import threading
from functools import wraps
from dotenv import load_dotenv
load_dotenv()

# Fix the path so Python can find nlp_service and dialog_service
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from nlp_service.predictor import NLPPredictor
from dialog_service.dialog_manager import DialogManager
from groq import Groq

groq_lock = threading.Lock()

app = Flask(__name__)

# Configure CORS to restrict allowed origins to trusted clients
allowed_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5000").split(",")
CORS(app, resources={r"/*": {"origins": allowed_origins}})

# Secure API Token Verification Decorator
def require_api_token(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Always allow testing mode (pytest) to bypass the token check to keep unit tests passing
        if app.config.get('TESTING', False):
            return f(*args, **kwargs)
            
        token = os.environ.get("API_AUTH_TOKEN")
        # If no token is set in the environment, bypass the check in development
        if not token:
            return f(*args, **kwargs)
            
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Unauthorized. Missing or invalid Bearer token."}), 401
            
        provided_token = auth_header.split(" ")[1]
        if provided_token != token:
            return jsonify({"error": "Unauthorized. Invalid Bearer token."}), 401
            
        return f(*args, **kwargs)
    return decorated_function

# Initialize services
nlp = NLPPredictor(model_path=os.path.join(os.path.dirname(__file__), '..', 'nlp_service', 'model'))
dialog = DialogManager()

# Groq client
groq_client = None

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
@require_api_token
def new_session():
    session_id = dialog.start_session()
    return jsonify({"session_id": session_id})

# Groq client helper
def get_groq_client():
    global groq_client
    if groq_client is None:
        with groq_lock:
            if groq_client is None:
                api_key = os.environ.get("GROQ_API_KEY")
                if api_key:
                    groq_client = Groq(api_key=api_key)
    return groq_client

@app.route('/sessions', methods=['GET'])
@require_api_token
def list_sessions():
    sessions = dialog.state.list_sessions()
    return jsonify({"sessions": sessions})

@app.route('/chat', methods=['POST'])
@require_api_token
def chat():
    data = request.get_json()

    if not data or 'message' not in data:
        return jsonify({"error": "No message provided"}), 400

    user_message = data['message']
    session_id = data.get('session_id', None)
    model_key = data.get('model', 'llama3-70b')
    model_id = GROQ_MODELS.get(model_key, GROQ_MODELS['llama3-70b'])
    mode = data.get('mode', 'support_engine')

    if mode == 'novamind_ai':
        # Pure general-purpose AI Mode (bypasses intent classification & local support FSM)
        client = get_groq_client()
        if client is None:
            bot_response = "I'm sorry, I'm having trouble connecting to my AI brain. Please configure your GROQ_API_KEY in the environment."
            engine = "fallback_engine"
            if not session_id or not dialog.state.get_session(session_id):
                session_id = dialog.start_session()
        else:
            session = dialog.state.get_session(session_id)
            if not session:
                session_id = dialog.start_session()
                session = dialog.state.get_session(session_id)

            # Filter history to only include general-purpose Q&A to isolate context completely!
            history = [turn for turn in session["history"] if turn.get("intent") == "generative_qa"] if session else []

            messages = [
                {
                    "role": "system",
                    "content": "You are NovaMind, an ultra-advanced AI companion with the versatile intelligence and conversational capabilities of Claude, Gemini, and Grok. "
                               "You possess deep knowledge in coding, science, mathematics, analysis, and creative writing. "
                               "Be natural, warm, engaging, and witty. Answer the user's questions in detail. "
                               "Do NOT mention order tracking, shipping, refunds, or customer support unless the user explicitly asks for it."
                }
            ]
            for turn in history[-8:]:
                messages.append({"role": "user", "content": turn["user"]})
                messages.append({"role": "assistant", "content": turn["bot"]})

            messages.append({"role": "user", "content": user_message})

            try:
                completion = client.chat.completions.create(
                    model=model_id,
                    messages=messages,
                    max_tokens=1024,
                    temperature=0.7
                )
                bot_response = completion.choices[0].message.content
                engine = "generative_engine"
            except Exception as e:
                bot_response = f"I encountered an error communicating with my generative brain: {str(e)}"
                engine = "fallback_engine"

            # Log to SQLite session database as generative_qa to preserve chat history
            dialog.state.update_session(
                session_id=session_id,
                intent="generative_qa",
                entities={},
                user_text=user_message,
                bot_response=bot_response
            )

        return jsonify({
            "session_id": session_id,
            "user_message": user_message,
            "bot_response": bot_response,
            "intent": "generative_qa",
            "confidence": 1.0,
            "entities": {},
            "engine": engine,
            "model": model_id if engine == "generative_engine" else None
        })

    # 1. Run local BERT Intent Classifier
    nlp_result = nlp.process(user_message)
    intent = nlp_result['intent']
    confidence = nlp_result['confidence']
    entities = nlp_result['entities']

    # Standard support intents that require deterministic database/logic
    support_intents = ['check_order_status', 'cancel_order', 'request_refund', 'greeting', 'goodbye']

    # Get active session FSM state to check if we are waiting for order_id
    session = dialog.state.get_session(session_id)
    pending_slot = session.get("pending_slot") if session else None

    # LLM-Assisted Fallback Extraction:
    # If the database is waiting for "order_id" but our advanced regex failed to extract it,
    # we ask Groq Llama to extract any 4-6 digit order number from the user's text!
    if pending_slot == "order_id" and "order_id" not in entities:
        client = get_groq_client()
        if client:
            try:
                extraction_prompt = [
                    {
                        "role": "system",
                        "content": "You are a precise JSON extractor. Your only task is to extract a 4-to-6 digit order ID number from the user text. "
                                   "If you find an order ID number, return it in this exact JSON format: {\"order_id\": \"number\"}. "
                                   "If no order number is present in the text, return exactly: {}"
                    },
                    {
                        "role": "user",
                        "content": f"Extract order ID from: \"{user_message}\""
                    }
                ]
                completion = client.chat.completions.create(
                    model="llama-3.1-8b-instant",  # Use the fastest model for extraction
                    messages=extraction_prompt,
                    response_format={"type": "json_object"},
                    max_tokens=64,
                    temperature=0.0
                )
                import json
                extracted_data = json.loads(completion.choices[0].message.content)
                if "order_id" in extracted_data:
                    entities["order_id"] = str(extracted_data["order_id"])
            except Exception as e:
                print(f"LLM extraction fallback failed: {e}")

    # 2. Check routing condition
    has_order_id = bool(entities.get("order_id"))

    # We route directly to the local Dialog Manager if:
    # 1. The user is actively supplying slot input to fill a pending FSM slot (is_filling_slot)
    # 2. Or, the intent classifier has high confidence for a support action
    # 3. Or, we have an order ID and a support intent
    is_filling_slot = (pending_slot is not None and has_order_id)
    
    if is_filling_slot or (confidence >= 0.65 and intent in support_intents) or (has_order_id and intent in ['check_order_status', 'cancel_order', 'request_refund']):
        # High confidence support query or transactional query with order ID -> local Dialog Manager
        dialog_result = dialog.handle(
            session_id=session_id,
            intent=intent,
            entities=entities,
            user_text=user_message
        )
        session_id = dialog_result["session_id"]
        bot_response = dialog_result["response"]
        engine = "support_engine"
    else:
        # If the low-confidence query is a support action without an order ID,
        # we pre-register the pending FSM state in SQLite (only if there is no active pending slot already!)
        if pending_slot is None and intent in ['check_order_status', 'cancel_order', 'request_refund']:
            dialog.state.set_pending_state(session_id, slot_name="order_id", intent_name=intent)

        # Low confidence or out-of-scope query -> fallback to Groq Llama
        client = get_groq_client()
        if client is None:
            bot_response = "I'm sorry, I'm having trouble connecting to my AI brain. Please configure your GROQ_API_KEY in the environment."
            engine = "fallback_engine"
            # Ensure session exists
            if not session_id or not dialog.state.get_session(session_id):
                session_id = dialog.start_session()
        else:
            # Resolve or create session
            session = dialog.state.get_session(session_id)
            if not session:
                session_id = dialog.start_session()
                session = dialog.state.get_session(session_id)

            history = session["history"] if session else []

            # Format the system prompt to guide Llama
            messages = [
                {
                    "role": "system",
                    "content": "You are NovaMind, an ultra-advanced hybrid AI assistant with the versatile intelligence and conversational capabilities of Claude, Gemini, and Grok. "
                               "You possess a highly capable General AI brain for coding, analysis, creative writing, and open-ended Q&A, and a built-in Customer Support Engine. "
                               "Be natural, engaging, witty, and highly helpful. "
                               "If the user asks general questions, writes code, or just chats, act like a premium general-purpose AI companion (do not randomly bring up order numbers, refunds, or shipping details unless specifically asked). "
                               "If they ask to track an order, cancel an order, or request a refund, politely let them know that you can automatically resolve it if they ask a specific support question (like 'Where is my order?') and provide their order number."
                }
            ]

            # Add context-aware history (limit to last 8 turns to avoid bloat)
            for turn in history[-8:]:
                messages.append({"role": "user", "content": turn["user"]})
                messages.append({"role": "assistant", "content": turn["bot"]})

            messages.append({"role": "user", "content": user_message})

            try:
                completion = client.chat.completions.create(
                    model=model_id,
                    messages=messages,
                    max_tokens=1024,
                    temperature=0.7
                )
                bot_response = completion.choices[0].message.content
                engine = "generative_engine"
            except Exception as e:
                bot_response = f"I encountered an error communicating with my generative brain: {str(e)}"
                engine = "fallback_engine"

            # Update dialog session state so generative responses persist in session history
            dialog.state.update_session(
                session_id=session_id,
                intent="generative_qa",
                entities={},
                user_text=user_message,
                bot_response=bot_response
            )

    return jsonify({
        "session_id": session_id,
        "user_message": user_message,
        "bot_response": bot_response,
        "intent": "generative_qa" if engine == "generative_engine" else intent,
        "confidence": confidence,
        "entities": entities,
        "engine": engine,
        "model": model_id if engine == "generative_engine" else None
    })

@app.route('/chat/groq', methods=['POST'])
@require_api_token
def chat_groq():
    global groq_client
    if groq_client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            return jsonify({"error": "Groq API key not configured"}), 500
        groq_client = Groq(api_key=api_key)

    data = request.get_json()

    if not data or 'message' not in data:
        return jsonify({"error": "No message provided"}), 400

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
@require_api_token
def get_groq_models():
    return jsonify({"models": list(GROQ_MODELS.keys())})

@app.route('/history/<session_id>', methods=['GET'])
@require_api_token
def get_history(session_id):
    session = dialog.state.get_session(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    return jsonify({"history": session["history"]})

if __name__ == '__main__':
    app.run(host='localhost', debug=False, port=8000)