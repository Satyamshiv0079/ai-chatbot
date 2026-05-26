import torch
from transformers import BertTokenizer, BertForSequenceClassification
from torch.optim import AdamW
from torch.utils.data import Dataset, DataLoader
from training_data import training_data, INTENTS
import json, os

# Map intents to numbers
intent2id = {intent: i for i, intent in enumerate(INTENTS)}
id2intent = {i: intent for intent, i in intent2id.items()}

class IntentDataset(Dataset):
    def __init__(self, data, tokenizer, max_len=64):
        self.data = data
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        item = self.data[idx]
        encoding = self.tokenizer(
            item["text"],
            max_length=self.max_len,
            padding="max_length",
            truncation=True,
            return_tensors="pt"
        )
        return {
            "input_ids": encoding["input_ids"].squeeze(),
            "attention_mask": encoding["attention_mask"].squeeze(),
            "label": torch.tensor(intent2id[item["intent"]])
        }

def train_model():
    print("Loading BERT tokenizer and model...")
    tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
    model = BertForSequenceClassification.from_pretrained(
        "bert-base-uncased",
        num_labels=len(INTENTS)
    )

    dataset = IntentDataset(training_data, tokenizer)
    loader = DataLoader(dataset, batch_size=16, shuffle=True)
    optimizer = AdamW(model.parameters(), lr=3e-5)

    EPOCHS = 5
    print("Training started...")
    model.train()
    for epoch in range(EPOCHS):
        total_loss = 0
        for batch in loader:
            optimizer.zero_grad()
            outputs = model(
                input_ids=batch["input_ids"],
                attention_mask=batch["attention_mask"],
                labels=batch["label"]
            )
            loss = outputs.loss
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        print(f"Epoch {epoch+1}/{EPOCHS} — Loss: {total_loss:.4f}")

    # Save the model
    os.makedirs("model", exist_ok=True)
    model.save_pretrained("model")
    tokenizer.save_pretrained("model")
    print("Model saved to backend/nlp_service/model/")

if __name__ == "__main__":
    train_model()