import uuid
from datetime import datetime

class ConversationState:
    def __init__(self):
        self.sessions = {}

    def create_session(self):
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "history": [],
            "context": {},
            "current_intent": None,
            "slots": {}
        }
        return session_id

    def get_session(self, session_id):
        return self.sessions.get(session_id)

    def update_session(self, session_id, intent, entities, user_text, bot_response):
        if session_id not in self.sessions:
            return
        session = self.sessions[session_id]
        session["current_intent"] = intent
        session["slots"].update(entities)
        session["history"].append({
            "user": user_text,
            "bot": bot_response,
            "intent": intent,
            "timestamp": datetime.now().isoformat()
        })

    def get_slot(self, session_id, slot_name):
        session = self.get_session(session_id)
        if session:
            return session["slots"].get(slot_name)
        return None

    def clear_session(self, session_id):
        if session_id in self.sessions:
            del self.sessions[session_id]