# AI-Powered Customer Support Chatbot

A BERT-based intelligent chatbot for customer support, built using
Agile microservices architecture.

## Authors
- Aman
- Satyam

## Architecture
- NLP Service: Fine-tuned BERT (bert-base-uncased)
- Dialog Service: Context-aware conversation manager
- Frontend: React.js chat interface
- Backend: Flask REST API

## Tech Stack
- Python 3.11, Flask, HuggingFace Transformers
- PyTorch, React.js, SQLite

## Setup Instructions

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python nlp_service/intent_classifier.py  # Train model
python api/app.py                         # Start server
```

### Frontend
```bash
cd frontend/chatbot-ui
npm install
npm start
```

## API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | / | Health check |
| POST | /session/new | Create new session |
| POST | /chat | Send message |
| GET | /history/:id | Get chat history |

## Performance Targets
| Metric | Target | Status |
|--------|--------|--------|
| Intent Accuracy | >94% | ✓ |
| Response Time | <2 seconds | ✓ |
| Availability | 24/7 | ✓ |