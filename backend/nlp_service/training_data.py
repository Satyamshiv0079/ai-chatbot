training_data = [
    # Check order status
    {"text": "Where is my order?", "intent": "check_order_status", "entities": {}},
    {"text": "What is the status of my order #12345?", "intent": "check_order_status", "entities": {"order_id": "12345"}},
    {"text": "Track my order", "intent": "check_order_status", "entities": {}},
    {"text": "When will my package arrive?", "intent": "check_order_status", "entities": {}},
    {"text": "track order", "intent": "check_order_status", "entities": {}},
    {"text": "Where is my package?", "intent": "check_order_status", "entities": {}},
    {"text": "Can you check my order status?", "intent": "check_order_status", "entities": {}},
    {"text": "I want to track my order", "intent": "check_order_status", "entities": {}},
    {"text": "What happened to my order?", "intent": "check_order_status", "entities": {}},
    {"text": "Has my order shipped yet?", "intent": "check_order_status", "entities": {}},
    {"text": "Order status please", "intent": "check_order_status", "entities": {}},
    {"text": "Check my order", "intent": "check_order_status", "entities": {}},

    # Cancel order
    {"text": "I want to cancel my order", "intent": "cancel_order", "entities": {}},
    {"text": "Please cancel order #67890", "intent": "cancel_order", "entities": {"order_id": "67890"}},
    {"text": "Cancel my recent purchase", "intent": "cancel_order", "entities": {}},
    {"text": "Cancel order", "intent": "cancel_order", "entities": {}},
    {"text": "I want to cancel", "intent": "cancel_order", "entities": {}},
    {"text": "Stop my order", "intent": "cancel_order", "entities": {}},
    {"text": "Please stop my order", "intent": "cancel_order", "entities": {}},
    {"text": "I changed my mind, cancel my order", "intent": "cancel_order", "entities": {}},
    {"text": "Can you cancel my purchase?", "intent": "cancel_order", "entities": {}},
    {"text": "Cancel my order please", "intent": "cancel_order", "entities": {}},
    {"text": "I don't want this order anymore", "intent": "cancel_order", "entities": {}},

    # Request refund
    {"text": "I want a refund", "intent": "request_refund", "entities": {}},
    {"text": "How do I get my money back?", "intent": "request_refund", "entities": {}},
    {"text": "I need to return this item", "intent": "request_refund", "entities": {}},
    {"text": "Request refund", "intent": "request_refund", "entities": {}},
    {"text": "refund please", "intent": "request_refund", "entities": {}},
    {"text": "I need my money back", "intent": "request_refund", "entities": {}},
    {"text": "give me a refund", "intent": "request_refund", "entities": {}},
    {"text": "Can I get my money back?", "intent": "request_refund", "entities": {}},
    {"text": "I would like a refund", "intent": "request_refund", "entities": {}},
    {"text": "Process my refund", "intent": "request_refund", "entities": {}},
    {"text": "I want to return and get refund", "intent": "request_refund", "entities": {}},
    {"text": "Please refund my order", "intent": "request_refund", "entities": {}},

    # Greeting
    {"text": "Hello", "intent": "greeting", "entities": {}},
    {"text": "Hi there", "intent": "greeting", "entities": {}},
    {"text": "Hey, I need help", "intent": "greeting", "entities": {}},
    {"text": "Hi", "intent": "greeting", "entities": {}},
    {"text": "Hey", "intent": "greeting", "entities": {}},
    {"text": "Good morning", "intent": "greeting", "entities": {}},
    {"text": "Good evening", "intent": "greeting", "entities": {}},
    {"text": "Hello, I need some help", "intent": "greeting", "entities": {}},
    {"text": "Hi, can you help me?", "intent": "greeting", "entities": {}},
    {"text": "Greetings", "intent": "greeting", "entities": {}},

    # Goodbye
    {"text": "Bye", "intent": "goodbye", "entities": {}},
    {"text": "Thank you, goodbye", "intent": "goodbye", "entities": {}},
    {"text": "That's all I needed", "intent": "goodbye", "entities": {}},
    {"text": "Goodbye", "intent": "goodbye", "entities": {}},
    {"text": "See you later", "intent": "goodbye", "entities": {}},
    {"text": "Thanks, bye", "intent": "goodbye", "entities": {}},
    {"text": "That will be all", "intent": "goodbye", "entities": {}},
    {"text": "Thank you for your help", "intent": "goodbye", "entities": {}},
    {"text": "I'm done, thanks", "intent": "goodbye", "entities": {}},
    {"text": "Have a good day", "intent": "goodbye", "entities": {}},
]

# All possible intents
INTENTS = [
    "check_order_status",
    "cancel_order",
    "request_refund",
    "greeting",
    "goodbye"
]