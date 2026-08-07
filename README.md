# 🤖 AI Chatbot

A full-stack AI chatbot built with Flask, React, Supabase PostgreSQL, and Groq's LLM API. Supports real user authentication, persistent chat history, multiple AI models, and a spatial 3D UI.

🌐 **Live Demo**: [https://ai-chatbot-6njs1ys87-satyamshiv0079s-projects.vercel.app](https://ai-chatbot-6njs1ys87-satyamshiv0079s-projects.vercel.app)

> Built by **Satyam**.

---

## 🚀 Live Production Stack

| Component | Platform | Tech |
|---|---|---|
| **Frontend** | Vercel | React.js, Glassmorphism 3D CSS |
| **Backend** | Render | Python / Flask, Gunicorn |
| **Database** | Supabase | PostgreSQL |
| **AI Model** | Groq API | Llama 3.3 70B, Mixtral 8x7B, Gemma 2 9B |

---

## What It Does

- 💬 **AI Intelligence**: Fast, accurate responses powered by Groq LLMs (`llama-3.3-70b-versatile`, `mixtral-8x7b`, etc.)
- 🔐 **Real Authentication**: Register, log in, JWT token authorization, bcrypt password hashing
- 💾 **Persistent Chat History**: Session history stored permanently in cloud PostgreSQL
- 🎛️ **Model Switcher**: Seamlessly switch between 4 AI models mid-conversation
- 🎨 **Spatial 3D UI**: Perspective hover tilt, frosted glass cards, dynamic floating orbs, dark mode
- 📱 **Fully Responsive**: Adaptive sidebar drawer layout for mobile, tablet, and desktop

---

## Tech Stack

**Backend**
- Python 3.11 / Flask
- Groq API (LLM inference)
- SQLAlchemy + PostgreSQL (Supabase) / SQLite (Local)
- Flask-JWT-Extended (Authentication)
- bcrypt (Password hashing)
- Gunicorn (Production WSGI)

**Frontend**
- React.js
- Axios (API calls)
- Lucide React (Icons)
- CSS — Spatial glassmorphism design system, dark mode, responsive drawer

---

## Project Structure

```
ai-chatbot/
├── backend/
│   ├── api/
│   │   └── app.py              # Flask REST API & routes
│   ├── auth/
│   │   └── auth_routes.py      # Auth logic (Register, Login, JWT)
│   ├── dialog_service/
│   │   ├── dialog_manager.py   # Groq LLM integration
│   │   ├── state_manager.py    # DB session & history management
│   │   └── models.py           # SQLAlchemy models
│   ├── Procfile                # Production startup command for Render
│   └── requirements.txt        # Production dependencies
└── frontend/
    └── chatbot-ui/
        └── src/
            ├── components/
            │   ├── ChatWindow.js   # Main spatial chat interface
            │   ├── Login.js        # Login page
            │   └── Signup.js       # Registration page
            └── services/
                └── chatService.js  # API service layer
```

---

## Local Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- A free [Groq API key](https://console.groq.com)

### 1. Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Environment configuration
# Create .env with GROQ_API_KEY and JWT_SECRET_KEY

# Run server
python api/app.py
```

### 2. Frontend

```bash
cd frontend/chatbot-ui
npm install
npm start
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

---

## Roadmap & Features

- [x] JWT Authentication & bcrypt security
- [x] Spatial 3D UI & glassmorphism design
- [x] Persistent database session history
- [x] Multi-model selector (Llama 3.3, Mixtral, Gemma)
- [x] Responsive overlay drawer for mobile & tablet
- [x] Free Cloud Deployment (Vercel + Render + Supabase)
- [ ] PDF / Document upload and chat
- [ ] Voice input & hands-free speech output
- [ ] Export conversations (PDF/Text)

---

## License

MIT — feel free to use and modify!
