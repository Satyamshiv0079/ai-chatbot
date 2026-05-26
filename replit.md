# AI-Powered Customer Support Chatbot

A BERT-based intelligent chatbot for customer support with a Flask backend and React frontend.

## Architecture

- **Frontend**: React + Vite (port 5000) — chat UI with intent/confidence display
- **Backend**: Flask REST API (port 8000) — coordinates NLP and dialog services
- **NLP Service**: Fine-tuned BERT (`bert-base-uncased`) for intent classification
- **Dialog Service**: Context-aware conversation manager with session state

## Running the Project

Two workflows must both be running:
1. **Start application** — React frontend on port 5000
2. **Backend API** — Flask backend on port 8000

The frontend proxies `/api/*` requests to the backend at `localhost:8000`.

## Model Training

The BERT model lives at `backend/nlp_service/model/`. To retrain:
```bash
cd backend/nlp_service && python intent_classifier.py
```
Training takes ~2 minutes on CPU. The model detects 5 intents:
- `check_order_status`, `cancel_order`, `request_refund`, `greeting`, `goodbye`

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /health | Health check |
| POST | /session/new | Create new session |
| POST | /chat | Send message |
| GET | /history/:id | Get chat history |

## Test Orders (built-in)

| Order ID | Status |
|----------|--------|
| 12345 | Shipped |
| 67890 | Processing |
| 11111 | Delivered |

## User Preferences
