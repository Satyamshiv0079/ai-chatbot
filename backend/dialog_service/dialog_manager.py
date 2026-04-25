import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from state_manager import ConversationState

state_manager = ConversationState()

# Simulated order database
ORDERS = {
    "12345": {"status": "Shipped", "eta": "Tomorrow by 8 PM"},
    "67890": {"status": "Processing", "eta": "3-5 business days"},
    "11111": {"status": "Delivered", "eta": "Already delivered"},
}

class DialogManager:
    def __init__(self):
        self.state = state_manager

    def start_session(self):
        return self.state.create_session()

    def handle(self, session_id, intent, entities, user_text):
        session = self.state.get_session(session_id)
        if not session:
            session_id = self.state.create_session()

        existing_slots = session["slots"] if session else {}
        all_slots = {**existing_slots, **entities}

        response = self._route_intent(intent, all_slots, session)

        self.state.update_session(session_id, intent, entities, user_text, response)

        return {
            "session_id": session_id,
            "response": response,
            "intent": intent,
            "entities": entities
        }

    def _route_intent(self, intent, slots, session):
        if intent == "greeting":
            return self._handle_greeting(session)
        elif intent == "check_order_status":
            return self._handle_order_status(slots)
        elif intent == "cancel_order":
            return self._handle_cancel_order(slots)
        elif intent == "request_refund":
            return self._handle_refund(slots)
        elif intent == "goodbye":
            return self._handle_goodbye()
        else:
            return "I'm sorry, I didn't understand that. Could you rephrase?"

    def _handle_greeting(self, session):
        if session and len(session["history"]) > 0:
            return "Welcome back! How can I help you today?"
        return "Hello! Welcome to customer support. How can I help you today?"

    def _handle_order_status(self, slots):
        order_id = slots.get("order_id")
        if not order_id:
            return "I'd be happy to check that for you! Could you please provide your order number?"
        order = ORDERS.get(order_id)
        if order:
            return (f"Your order #{order_id} is currently: {order['status']}. "
                    f"Estimated delivery: {order['eta']}.")
        return f"I couldn't find order #{order_id}. Please double-check the order number."

    def _handle_cancel_order(self, slots):
        order_id = slots.get("order_id")
        if not order_id:
            return "I can help with that. Could you please share your order number so I can cancel it?"
        order = ORDERS.get(order_id)
        if order:
            if order["status"] == "Delivered":
                return (f"Order #{order_id} has already been delivered. "
                        f"Please request a refund instead.")
            return (f"Order #{order_id} has been successfully cancelled. "
                    f"You will receive a confirmation email shortly.")
        return f"I couldn't find order #{order_id}. Please check your order number."

    def _handle_refund(self, slots):
        order_id = slots.get("order_id")
        if not order_id:
            return "I can process a refund for you. Could you please provide your order number?"
        return (f"Your refund request for order #{order_id} has been submitted. "
                f"It will be processed within 5-7 business days.")

    def _handle_goodbye(self):
        return "Thank you for contacting us! Have a great day. Goodbye!"