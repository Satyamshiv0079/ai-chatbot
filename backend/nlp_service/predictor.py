import re, os, sys

# Fix path so training_data can always be found
sys.path.insert(0, os.path.dirname(__file__))
from training_data import INTENTS

id2intent = {i: intent for i, intent in enumerate(INTENTS)}

class NLPPredictor:
    def __init__(self, model_path=None):
        self.use_torch = False
        self.tokenizer = None
        self.model = None

        # Try loading PyTorch/Transformers if installed, otherwise use lightweight fallback
        try:
            import torch
            from transformers import AutoTokenizer, BertForSequenceClassification
            
            if model_path is None:
                model_path = os.path.join(os.path.dirname(__file__), 'model')
            
            if os.path.isdir(model_path) and os.path.exists(os.path.join(model_path, 'config.json')):
                print(f"Loading local BERT model from {model_path}...")
                self.tokenizer = AutoTokenizer.from_pretrained(model_path)
                self.model = BertForSequenceClassification.from_pretrained(model_path)
                self.model.eval()
                self.use_torch = True
        except Exception as e:
            print(f"Running in lightweight cloud mode (no PyTorch required): {e}")

    def predict_intent(self, text):
        if self.use_torch and self.model and self.tokenizer:
            import torch
            inputs = self.tokenizer(
                text, return_tensors="pt", max_length=64, padding="max_length", truncation=True
            )
            with torch.no_grad():
                outputs = self.model(**inputs)
            probs = torch.softmax(outputs.logits, dim=1)
            confidence, predicted = torch.max(probs, dim=1)
            return {
                "intent": id2intent.get(predicted.item(), "general_query"),
                "confidence": round(confidence.item(), 4)
            }
        
        # Lightweight fast keyword classifier (uses 0MB extra RAM)
        text_lower = text.lower()
        if any(w in text_lower for w in ["hi", "hello", "hey", "greetings"]):
            return {"intent": "greeting", "confidence": 0.95}
        elif any(w in text_lower for w in ["bye", "goodbye", "see you"]):
            return {"intent": "goodbye", "confidence": 0.95}
        elif any(w in text_lower for w in ["help", "support", "assist"]):
            return {"intent": "help", "confidence": 0.90}
        return {"intent": "general_query", "confidence": 0.85}

    def extract_entities(self, text):
        entities = {}
        order_match = re.search(r'#?(\d{4,6})', text)
        if order_match:
            entities["order_id"] = order_match.group(1)
        return entities

    def process(self, text):
        intent_result = self.predict_intent(text)
        entities = self.extract_entities(text)
        return {
            "text": text,
            "intent": intent_result["intent"],
            "confidence": intent_result["confidence"],
            "entities": entities
        }