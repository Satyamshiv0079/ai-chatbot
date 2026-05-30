import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from state_manager import ConversationState

state_manager = ConversationState()

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
            order_id = entities.get("order_id")
            if not order_id:
                import re
                num_match = re.search(r'\b(\d{4,6})\b', user_text)
                if num_match:
                    order_id = num_match.group(1)
            
            if order_id:
                entities["order_id"] = order_id
                intent = pending_intent
                self.state.clear_pending_state(session_id)
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
            self.state.set_pending_state(session_id, slot_name="order_id", intent_name="check_order_status")
            return "I'd be happy to check that for you! Could you please provide your order number?"
            
        # Dynamic SQLite Query
        order = self.state.get_order(order_id)
        if order:
            return (f"Your order #{order_id} is currently: {order['status']}. "
                    f"Estimated delivery: {order['eta']}.")
        return f"I couldn't find order #{order_id}. Please double-check the order number."

    def _handle_cancel_order(self, slots, session_id):
        order_id = slots.get("order_id")
        if not order_id:
            self.state.set_pending_state(session_id, slot_name="order_id", intent_name="cancel_order")
            return "I can help cancel that order. Could you please share your order number?"
            
        # Dynamic SQLite Query
        order = self.state.get_order(order_id)
        if order:
            if order["status"] == "Delivered":
                return (f"Order #{order_id} has already been delivered. "
                        f"Please request a refund instead.")
            
            # Update order status to Cancelled in SQLite database for high-fidelity persistence!
            with self.state._get_conn() as conn:
                conn.execute("UPDATE orders SET status = 'Cancelled' WHERE order_id = ?", (order_id,))
                conn.commit()
                
            return (f"Order #{order_id} has been successfully cancelled. "
                    f"You will receive a confirmation email shortly.")
        return f"I couldn't find order #{order_id}. Please check your order number."

    def _handle_refund(self, slots, session_id):
        order_id = slots.get("order_id")
        if not order_id:
            self.state.set_pending_state(session_id, slot_name="order_id", intent_name="request_refund")
            return "I can process a refund for you. Could you please provide your order number?"
            
        # Dynamic SQLite Query
        order = self.state.get_order(order_id)
        if order:
            # Update status to Refunded in SQLite database for high-fidelity persistence!
            with self.state._get_conn() as conn:
                conn.execute("UPDATE orders SET status = 'Refunded' WHERE order_id = ?", (order_id,))
                conn.commit()
                
            return (f"Your refund request for order #{order_id} has been submitted. "
                    f"It will be processed within 5-7 business days.")
        return f"I couldn't find order #{order_id}. Please check your order number."

    def _handle_goodbye(self):
        return "Thank you for contacting us! Have a great day. Goodbye!"