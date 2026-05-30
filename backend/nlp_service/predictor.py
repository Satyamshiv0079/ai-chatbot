import re, os, sys, math

# Fix path so training_data can always be found
sys.path.insert(0, os.path.dirname(__file__))

from training_data import training_data, INTENTS

class NLPPredictor:
    def __init__(self, model_path=None):
        print("Initializing lightweight TF-IDF NLP Predictor...")
        self.training_data = training_data
        self.intents = INTENTS
        
        # 1. Simple Tokenizer (removes special chars, extracts words of length >= 2)
        self.tokenize = lambda text: re.findall(r'\b\w{2,}\b', text.lower())
        
        # 2. Build Vocabulary and document frequencies (DF)
        self.vocab = set()
        doc_counts = {}
        
        for item in self.training_data:
            tokens = set(self.tokenize(item["text"]))
            self.vocab.update(tokens)
            for token in tokens:
                doc_counts[token] = doc_counts.get(token, 0) + 1
                
        self.vocab = list(self.vocab)
        self.vocab_indices = {word: i for i, word in enumerate(self.vocab)}
        
        num_docs = len(self.training_data)
        # IDF formula: log(1 + N / (1 + DF))
        self.idf = {word: math.log(1.0 + (num_docs / (1.0 + doc_counts[word]))) for word in self.vocab}
        
        # 3. Vectorize all training documents in-memory
        self.train_vectors = []
        for item in self.training_data:
            tokens = self.tokenize(item["text"])
            vector = self._vectorize_tokens(tokens)
            self.train_vectors.append((vector, item["intent"]))

    def _vectorize_tokens(self, tokens):
        tf = {}
        for token in tokens:
            if token in self.vocab_indices:
                tf[token] = tf.get(token, 0.0) + 1.0
                
        vector = [0.0] * len(self.vocab)
        if not tokens:
            return vector
            
        for token, count in tf.items():
            tf_score = count / len(tokens)
            idf_score = self.idf[token]
            vector[self.vocab_indices[token]] = tf_score * idf_score
            
        return vector

    def _cosine_similarity(self, vec1, vec2):
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude_vec1 = math.sqrt(sum(a * a for a in vec1))
        magnitude_vec2 = math.sqrt(sum(a * a for a in vec2))
        
        if magnitude_vec1 == 0.0 or magnitude_vec2 == 0.0:
            return 0.0
        return dot_product / (magnitude_vec1 * magnitude_vec2)

    def predict_intent(self, text):
        tokens = self.tokenize(text)
        query_vector = self._vectorize_tokens(tokens)
        
        best_similarity = 0.0
        best_intent = "greeting"  # Default fallback
        
        for train_vector, intent in self.train_vectors:
            sim = self._cosine_similarity(query_vector, train_vector)
            if sim > best_similarity:
                best_similarity = sim
                best_intent = intent
                
        confidence = round(best_similarity, 4)
        # If similarity is too low (e.g. completely out of scope), set confidence to 0.0
        # to trigger generative LLM fallback in the chat router
        if confidence < 0.25:
            confidence = 0.0
            
        return {
            "intent": best_intent,
            "confidence": confidence
        }

    def extract_entities(self, text):
        entities = {}
        # Advanced regex pattern capturing: order-12345, order id 12345, #12345, ORD12345, or a standalone 4-6 digit number
        pattern = r'(?:order|purchase|tracking)[-_\s]*(?:id|number|num|#)?\s*(\d{4,6})|ORD[-_\s]*(\d{4,6})|#\s*(\d{4,6})|\b(\d{4,6})\b'
        order_match = re.search(pattern, text, re.IGNORECASE)
        if order_match:
            # Find the non-empty captured group
            order_id = next((g for g in order_match.groups() if g is not None), None)
            if order_id:
                entities["order_id"] = order_id
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