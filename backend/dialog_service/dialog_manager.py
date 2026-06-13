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
        elif intent == "shipping_info":
            return self._handle_shipping_info(session_id)
        elif intent == "return_policy":
            return self._handle_return_policy(session_id)
        elif intent == "product_inquiry":
            return self._handle_product_inquiry(session_id)
        elif intent == "payment_issue":
            return self._handle_payment_issue(session_id)
        elif intent == "account_help":
            return self._handle_account_help(session_id)
        elif intent == "complaint":
            return self._handle_complaint(session_id)
        elif intent == "thank_you":
            return self._handle_thank_you(session_id)
        elif intent == "faq_general":
            return self._handle_faq_general(session_id)
        elif intent == "change_order":
            return self._handle_change_order(slots, session_id)
        elif intent == "promotion":
            return self._handle_promotion(session_id)
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
            with self.state._get_conn() as conn:
                conn.execute("UPDATE orders SET status = 'Refunded' WHERE order_id = ?", (order_id,))
                conn.commit()
                
            return (f"Your refund request for order #{order_id} has been submitted. "
                    f"It will be processed within 5-7 business days.")
        return f"I couldn't find order #{order_id}. Please check your order number."

    def _handle_goodbye(self):
        return "Thank you for contacting us! Have a great day. Goodbye!"

    def _handle_shipping_info(self, session_id):
        return ("We offer several shipping options:\n"
                "• Standard Shipping: 5-7 business days (free on orders over $50)\n"
                "• Express Shipping: 2-3 business days ($9.99)\n"
                "• Overnight Shipping: next business day ($19.99)\n"
                "We ship Monday through Saturday. International shipping is also available "
                "with delivery times varying by destination. Is there anything else I can help with?")

    def _handle_return_policy(self, session_id):
        return ("Our return policy allows returns within 30 days of delivery. Here are the key details:\n"
                "• Items must be in original condition with tags attached.\n"
                "• Return shipping is free for defective or incorrect items.\n"
                "• Refunds are processed within 5-7 business days after we receive the return.\n"
                "• Sale items and personalized products are final sale.\n"
                "To start a return, please visit your order history or provide your order number. "
                "Would you like to initiate a return?")

    def _handle_product_inquiry(self, session_id):
        return ("I'd be happy to help you find product information! You can browse our full catalog "
                "on our website. If you have a specific product in mind, please share the product name "
                "or item number and I can look up availability, sizes, colors, and specifications for you. "
                "Is there a particular product you're interested in?")

    def _handle_payment_issue(self, session_id):
        return ("I'm sorry you're experiencing a payment issue. Here are some troubleshooting steps:\n"
                "1. Verify your card details and billing address are correct.\n"
                "2. Ensure your card has sufficient funds and is not expired.\n"
                "3. Try a different payment method (we accept Visa, Mastercard, PayPal, and Apple Pay).\n"
                "4. Clear your browser cache and try again.\n"
                "If you were charged incorrectly or the issue persists, I can escalate this to our "
                "billing team for immediate assistance. Would you like me to do that?")

    def _handle_account_help(self, session_id):
        return ("Here's how to resolve common account issues:\n"
                "• Forgot Password: Click 'Forgot Password' on the login page and follow the email instructions.\n"
                "• Update Email/Profile: Go to Account Settings in your dashboard.\n"
                "• Account Locked: Wait 30 minutes or contact support to unlock.\n"
                "• Two-Factor Authentication: Enable it under Security Settings.\n"
                "If you're still having trouble accessing your account, please provide your registered "
                "email address and I'll help you recover it.")

    def _handle_complaint(self, session_id):
        return ("I sincerely apologize for the inconvenience you've experienced. Your feedback is very "
                "important to us and I want to make sure this is resolved properly.\n"
                "I am escalating your case to a senior support specialist who will review your concern "
                "and follow up with you within 24 hours. You can also reach our management team directly "
                "at support@novamind.com or by calling 1-800-NOVA-MIND.\n"
                "Is there anything else I can document for the escalation?")

    def _handle_thank_you(self, session_id):
        return ("You're very welcome! I'm glad I could help. If you ever need assistance in the future, "
                "don't hesitate to reach out. Have a wonderful day! 😊")

    def _handle_faq_general(self, session_id):
        return ("Here's our key information:\n"
                "• Business Hours: Monday-Friday 9:00 AM - 6:00 PM EST, Saturday 10:00 AM - 4:00 PM EST\n"
                "• Phone: 1-800-NOVA-MIND\n"
                "• Email: support@novamind.com\n"
                "• Live Chat: Available during business hours on our website\n"
                "• Headquarters: San Francisco, CA\n"
                "Is there anything specific you'd like to know?")

    def _handle_change_order(self, slots, session_id):
        order_id = slots.get("order_id")
        if not order_id:
            self.state.set_pending_state(session_id, slot_name="order_id", intent_name="change_order")
            return "I can help you modify your order. Could you please provide your order number?"

        order = self.state.get_order(order_id)
        if order:
            if order["status"] == "Delivered":
                return (f"Order #{order_id} has already been delivered and can no longer be modified. "
                        f"Please contact us about a return or exchange instead.")
            return (f"Your modification request for order #{order_id} has been logged. "
                    f"Our team will review the changes and send you a confirmation email shortly. "
                    f"Current order status: {order['status']}.")
        return f"I couldn't find order #{order_id}. Please double-check the order number."

    def _handle_promotion(self, session_id):
        return ("Here are our current promotions:\n"
                "• Use code WELCOME15 for 15% off your first order.\n"
                "• Free shipping on all orders over $50.\n"
                "• Refer a friend and you both get $10 off your next purchase.\n"
                "• Sign up for our newsletter to receive exclusive deals and early access to sales.\n"
                "You can apply promo codes at checkout. Would you like help with anything else?")