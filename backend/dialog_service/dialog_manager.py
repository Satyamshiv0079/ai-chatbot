import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from state_manager import ConversationState
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

state_manager = ConversationState()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY and GROQ_API_KEY != "your_groq_api_key_here" else None

SYSTEM_PROMPT = (
    "You are a highly intelligent, helpful AI assistant similar to ChatGPT or Gemini. "
    "You can answer questions on any topic: science, math, coding, history, creative writing, philosophy, and more. "
    "Respond in a natural, conversational tone. Use markdown formatting where appropriate. "
    "For code blocks, use triple backticks with the language name. "
    "Be concise when the question is simple, detailed when it demands depth. "
    "Never refuse to answer reasonable questions."
)

class DialogManager:
    def __init__(self):
        self.state = state_manager

    def start_session(self):
        return self.state.create_session()

    def handle(self, session_id, intent, entities, user_text, model="llama-3.3-70b-versatile"):
        session = self.state.get_session(session_id)
        if not session:
            session_id = self.state.create_session()
            session = self.state.get_session(session_id)

        if client:
            response = self._generate_groq_response(session, user_text, model)
        else:
            response = (
                "I cannot connect to the AI right now. "
                "Please make sure the GROQ_API_KEY is set in your backend/.env file."
            )

        self.state.update_session(session_id, intent, entities, user_text, response)

        return {
            "session_id": session_id,
            "response": response,
            "intent": intent,
            "entities": entities
        }

    def _generate_groq_response(self, session, user_text, model="llama-3.3-70b-versatile"):
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Include last 6 turns for conversation memory
        for turn in session["history"][-6:]:
            messages.append({"role": "user", "content": turn["user"]})
            messages.append({"role": "assistant", "content": turn["bot"]})

        messages.append({"role": "user", "content": user_text})

        try:
            chat_completion = client.chat.completions.create(
                messages=messages,
                model=model,
                temperature=0.7,
                max_tokens=2048,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            return f"Error connecting to AI: {str(e)}"