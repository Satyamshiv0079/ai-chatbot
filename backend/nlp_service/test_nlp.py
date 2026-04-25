from predictor import NLPPredictor

nlp = NLPPredictor(model_path="model")

test_sentences = [
    "Where is my order #12345?",
    "I want to cancel my order",
    "Hello, I need some help",
    "Can I get a refund please?",
    "Thank you, goodbye!"
]

for sentence in test_sentences:
    result = nlp.process(sentence)
    print(f"\nInput:      {result['text']}")
    print(f"Intent:     {result['intent']} ({result['confidence']*100:.1f}% confidence)")
    print(f"Entities:   {result['entities']}")