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
            session = self.state.get_session(session_id)

        # 1. Dialog Finite State Machine (FSM) Slot Filling check
        pending_slot = session.get("pending_slot") if session else None
        pending_intent = session.get("pending_intent") if session else None

        if pending_slot == "order_id":
            # Check if order_id is in current entities, or try extracting it from user text
            order_id = entities.get("order_id")
            if not order_id:
                # Direct check if the user just replied with a 4-6 digit number
                import re
                num_match = re.search(r'\b(\d{4,6})\b', user_text)
                if num_match:
                    order_id = num_match.group(1)
            
            if order_id:
                # Slot is filled! Bind it to entities
                entities["order_id"] = order_id
                # Override active intent with the pending one
                intent = pending_intent
                # Clear pending state in SQLite database
                self.state.clear_pending_state(session_id)
                # Re-fetch session state so all_slots includes the new slot value
                session = self.state.get_session(session_id)

        existing_slots = session["slots"] if session else {}
        all_slots = {**existing_slots, **entities}

        response = self._route_intent(intent, all_slots, session_id)

        self.state.update_session(session_id, intent, entities, user_text, response)

        return {
            "session_id": session_id,
            "response": response,
            "intent": intent,
            "entities": entities
        }

    def _route_intent(self, intent, slots, session_id):
        if intent == "greeting":
            return self._handle_greeting(session_id)
        elif intent == "check_order_status":
            return self._handle_order_status(slots, session_id)
        elif intent == "cancel_order":
            return self._handle_cancel_order(slots, session_id)
        elif intent == "request_refund":
            return self._handle_refund(slots, session_id)
        elif intent == "goodbye":
            return self._handle_goodbye()
        else:
            return "I'm sorry, I didn't understand that. Could you rephrase?"

    def _handle_greeting(self, session_id):
        session = self.state.get_session(session_id)
        if session and len(session["history"]) > 0:
            return "Welcome back! How can I help you today?"
        return "Hello! Welcome to customer support. How can I help you today?"

    def _handle_order_status(self, slots, session_id):
        order_id = slots.get("order_id")
        if not order_id:
            # Set FSM state to wait for order_id
            self.state.set_pending_state(session_id, slot_name="order_id", intent_name="check_order_status")
            return "I'd be happy to check that for you! Could you please provide your order number?"
            
        order = ORDERS.get(order_id)
        if order:
            return (f"Your order #{order_id} is currently: {order['status']}. "
                    f"Estimated delivery: {order['eta']}.")
        return f"I couldn't find order #{order_id}. Please double-check the order number."

    def _handle_cancel_order(self, slots, session_id):
        order_id = slots.get("order_id")
        if not order_id:
            # Set FSM state to wait for order_id
            self.state.set_pending_state(session_id, slot_name="order_id", intent_name="cancel_order")
            return "I can help cancel that order. Could you please share your order number?"
            
        order = ORDERS.get(order_id)
        if order:
            if order["status"] == "Delivered":
                return (f"Order #{order_id} has already been delivered. "
                        f"Please request a refund instead.")
            return (f"Order #{order_id} has been successfully cancelled. "
                    f"You will receive a confirmation email shortly.")
        return f"I couldn't find order #{order_id}. Please check your order number."

    def _handle_refund(self, slots, session_id):
        order_id = slots.get("order_id")
        if not order_id:
            # Set FSM state to wait for order_id
            self.state.set_pending_state(session_id, slot_name="order_id", intent_name="request_refund")
            return "I can process a refund for you. Could you please provide your order number?"
            
        order = ORDERS.get(order_id)
        if order:
            return (f"Your refund request for order #{order_id} has been submitted. "
                    f"It will be processed within 5-7 business days.")
        return f"I couldn't find order #{order_id}. Please check your order number."

    def _handle_goodbye(self):
        return "Thank you for contacting us! Have a great day. Goodbye!"