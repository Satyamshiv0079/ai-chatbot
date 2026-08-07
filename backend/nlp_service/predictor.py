import torch, re, os, sys

# Fix path so training_data can always be found
sys.path.insert(0, os.path.dirname(__file__))

from transformers import AutoTokenizer, BertForSequenceClassification
from training_data import INTENTS

intent2id = {intent: i for i, intent in enumerate(INTENTS)}
id2intent = {i: intent for i, intent in enumerate(INTENTS)}

class NLPPredictor:
    def __init__(self, model_path=None):
        if model_path is None:
            model_path = os.path.join(os.path.dirname(__file__), 'model')
        
        # Check if local directory exists and has model files
        if os.path.isdir(model_path) and os.path.exists(os.path.join(model_path, 'config.json')):
            target = model_path
            print(f"Loading local BERT model from {target}...")
        else:
            target = "bert-base-uncased"
            print(f"Local model not found at {model_path}, using default '{target}'...")

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(target)
            self.model = BertForSequenceClassification.from_pretrained(target, num_labels=len(INTENTS))
            self.model.eval()
        except Exception as e:
            print(f"Warning: Could not load BERT model ({e}). Using dummy predictor.")
            self.tokenizer = None
            self.model = None

    def predict_intent(self, text):
        if not self.model or not self.tokenizer:
            return {"intent": "general_query", "confidence": 0.99}

        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            max_length=64,
            padding="max_length",
            truncation=True
        )
        with torch.no_grad():
            outputs = self.model(**inputs)

        probs = torch.softmax(outputs.logits, dim=1)
        confidence, predicted = torch.max(probs, dim=1)

        pred_id = predicted.item()
        intent = id2intent.get(pred_id, "general_query")

        return {
            "intent": intent,
            "confidence": round(confidence.item(), 4)
        }

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