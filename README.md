# 🤖 AI Chatbot

A full-stack AI chatbot built with Flask, React, and Groq's LLM API. Supports real user authentication, persistent chat history, multiple AI models, and a spatial 3D UI.

> Built by **Satyam** as a learning project.

---

## What It Actually Does

- Chat with a real AI (Llama 3.3 70B via Groq) — not a rule-based bot
- Create an account, log in, and your chat history is saved
- Switch between 4 different AI models mid-conversation
- Dark mode, mobile responsive, spatial glassmorphism UI
- Voice input (microphone) and optional voice output (text-to-speech)

---

## Tech Stack

**Backend**
- Python / Flask
- Groq API (LLM inference — `llama-3.3-70b-versatile`, `mixtral-8x7b`, etc.)
- HuggingFace Transformers + BERT (intent classification)
- SQLAlchemy + SQLite (database)
- Flask-JWT-Extended (authentication)
- bcrypt (password hashing)

**Frontend**
- React.js
- Axios (API calls)
- Lucide React (icons)
- react-markdown + react-syntax-highlighter (code rendering)
- CSS — spatial glassmorphism design, no Tailwind

---

## Project Structure

```
ai-chatbot/
├── backend/
│   ├── api/
│   │   └── app.py              # Flask app, all API routes
│   ├── auth/
│   │   └── auth_routes.py      # Register, login, JWT
│   ├── dialog_service/
│   │   ├── dialog_manager.py   # Groq LLM calls
│   │   ├── state_manager.py    # DB session management
│   │   └── models.py           # SQLAlchemy models
│   ├── nlp_service/
│   │   └── predictor.py        # BERT intent classifier
│   ├── .env.example            # Environment variable template
│   └── requirements.txt
└── frontend/
    └── chatbot-ui/
        └── src/
            ├── components/
            │   ├── ChatWindow.js   # Main chat UI
            │   ├── Login.js
            │   └── Signup.js
            └── services/
                └── chatService.js  # All API calls
```

---

## Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- A [Groq API key](https://console.groq.com) (free)

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your GROQ_API_KEY and JWT_SECRET_KEY

# Train the BERT intent classifier (one time)
python nlp_service/intent_classifier.py

# Start the server
python api/app.py
```

Backend runs at `http://localhost:5000`

### Frontend

```bash
cd frontend/chatbot-ui
npm install
npm start
```

Frontend runs at `http://localhost:3000`

---

## Environment Variables

Create `backend/.env` (never commit this file):

```env
GROQ_API_KEY=your_groq_api_key_here
JWT_SECRET_KEY=any_long_random_string_here
```

---

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/register` | ❌ | Create account |
| POST | `/auth/login` | ❌ | Login, returns JWT |
| POST | `/session/new` | ✅ | Start new chat session |
| POST | `/chat` | ✅ | Send message, get AI response |
| GET | `/sessions` | ✅ | List all your past sessions |
| GET | `/sessions/<id>` | ✅ | Load a specific session |
| PATCH | `/sessions/<id>/rename` | ✅ | Rename a session |
| DELETE | `/sessions/<id>` | ✅ | Delete a session |
| GET | `/models` | ✅ | List available AI models |

✅ = requires `Authorization: Bearer <token>` header

---

## Available AI Models

| Model ID | Name | Best For |
|----------|------|----------|
| `llama-3.3-70b-versatile` | Llama 3.3 70B | Best quality (default) |
| `llama-3.1-8b-instant` | Llama 3.1 8B | Fast responses |
| `mixtral-8x7b-32768` | Mixtral 8x7B | Long context |
| `gemma2-9b-it` | Gemma 2 9B | Efficient |

---

## Known Limitations

- SQLite database — fine for local dev, not ideal for production scale
- No message streaming (response appears all at once)
- BERT intent classifier is trained on a small dataset — accuracy is approximate
- No file upload / document chat yet
- JWT tokens don't expire (set `JWT_ACCESS_TOKEN_EXPIRES` for production)

---

## What's Not Done Yet

- [ ] Deploy (Vercel + Railway)
- [ ] PDF / document upload and chat
- [ ] Rename sessions from the sidebar
- [ ] Search through chat history
- [ ] Export conversations
- [ ] Message streaming

---

## License

MIT — do whatever you want with it.
