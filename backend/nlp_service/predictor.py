import torch, re, os, sys

# Fix path so training_data can always be found
sys.path.insert(0, os.path.dirname(__file__))

from transformers import BertTokenizer, BertForSequenceClassification
from training_data import INTENTS

intent2id = {intent: i for i, intent in enumerate(INTENTS)}
id2intent = {i: intent for i, intent in enumerate(INTENTS)}

class NLPPredictor:
    def __init__(self, model_path=None):
        if model_path is None:
            model_path = os.path.join(os.path.dirname(__file__), 'model')
        print("Loading trained BERT model...")
        self.tokenizer = BertTokenizer.from_pretrained(model_path)
        self.model = BertForSequenceClassification.from_pretrained(model_path)
        self.model.eval()

    def predict_intent(self, text):
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

        return {
            "intent": id2intent[predicted.item()],
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