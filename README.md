# 🔮 NovaMind AI — Next-Gen Spatial AI Platform

NovaMind is an immersive, feature-packed AI assistant platform built with Flask, React, Supabase PostgreSQL, and Groq's LLM API. It features real user authentication, persistent chat history, multi-model selection, document analysis (RAG), voice mode, chat export, and PWA offline support wrapped in a stunning spatial 3D UI.

🌐 **Live Production App**: [https://ai-chatbot-6njs1ys87-satyamshiv0079s-projects.vercel.app](https://ai-chatbot-6njs1ys87-satyamshiv0079s-projects.vercel.app)  
⚡ **Backend API**: [https://ai-chatbot-w1x8.onrender.com](https://ai-chatbot-w1x8.onrender.com)

> Built by **Satyam**.

---

## 🚀 Live Production Stack

| Component | Platform | Tech |
|---|---|---|
| **Frontend** | Vercel | React.js, Glassmorphism 3D CSS, Web Speech API |
| **Backend** | Render | Python 3.11 / Flask, Gunicorn |
| **Database** | Supabase | Cloud PostgreSQL |
| **AI Models** | Groq API | Llama 3.3 70B, Llama 3.1 8B, Mixtral 8x7B, Gemma 2 9B |
| **PWA** | Web Standard | Service Worker (`sw.js`), Web App Manifest |

---

## ✨ Features & Capability Overview

- 🔮 **NovaMind Spatial 3D UI**: Perspective 3D cursor tilt, frosted glass cards, dynamic background floating orbs, and light/dark theme toggle.
- 📄 **Document & File Analysis (RAG Context)**: Attach `.pdf`, `.txt`, `.md`, `.json`, `.csv`, `.py`, `.js` files to analyze or summarize document content.
- 🎙️ **Full Voice Mode (STT & TTS)**:
  - **Speech-to-Text**: Hands-free voice input via Web Speech Recognition.
  - **Text-to-Speech**: Speech synthesis playback of AI responses.
- 🎛️ **Multi-Model Intelligence**: Instant mid-chat switching between 4 cutting-edge LLMs (`llama-3.3-70b-versatile`, `llama-3.1-8b-instant`, `mixtral-8x7b-32768`, `gemma2-9b-it`).
- 🔐 **JWT Authentication**: Full user signup & login with bcrypt password hashing and token persistence.
- 💾 **Persistent Chat History & Session Search**: Saved on Supabase cloud PostgreSQL. Includes instant title search filter and inline double-click session renaming.
- 📥 **Export Chat History**: Export full chat conversations instantly as Markdown (`.md`).
- 📱 **Progressive Web App (PWA)**: Standalone installation support on Android, iOS, Windows, and macOS with service worker shell caching.

---

## 🛠️ Project Structure

```
ai-chatbot/
├── backend/
│   ├── api/
│   │   └── app.py              # Flask REST API & session endpoints
│   ├── auth/
│   │   └── auth_routes.py      # Auth logic (Register, Login, JWT)
│   ├── dialog_service/
│   │   ├── dialog_manager.py   # Groq LLM integration
│   │   ├── state_manager.py    # Supabase PostgreSQL session history
│   │   └── models.py           # SQLAlchemy database schema
│   ├── Procfile                # Production command for Render
│   └── requirements.txt        # Production Python dependencies
└── frontend/
    └── chatbot-ui/
        ├── public/
        │   ├── manifest.json   # PWA manifest
        │   └── sw.js           # PWA service worker
        └── src/
            ├── components/
            │   ├── ChatWindow.js   # Main NovaMind workspace
            │   ├── MessageBubble.js# 3D spatial cards & Markdown rendering
            │   ├── Login.js        # Login UI
            │   └── Signup.js       # Registration UI
            └── services/
                └── chatService.js  # API service layer
```

---

## 💻 Local Setup Instructions

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

# Create .env file with your credentials:
# GROQ_API_KEY=your_groq_key
# JWT_SECRET_KEY=your_secret
# DATABASE_URL=postgresql://...

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

## 🔌 API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/register` | ❌ | Create new account |
| POST | `/auth/login` | ❌ | User login & return JWT token |
| POST | `/session/new` | ✅ | Start new chat session |
| POST | `/chat` | ✅ | Send prompt/document, return AI response |
| GET | `/sessions` | ✅ | Fetch all past sessions |
| GET | `/sessions/<id>` | ✅ | Load session messages |
| PATCH | `/sessions/<id>/rename` | ✅ | Rename chat title |
| DELETE | `/sessions/<id>` | ✅ | Delete session |
| GET | `/models` | ✅ | List available AI models |

---

## ✅ Feature Completion Checklist

- [x] JWT Authentication & bcrypt security
- [x] Spatial 3D UI & glassmorphism design system
- [x] Persistent cloud database history (Supabase PostgreSQL)
- [x] Multi-model selector (Llama 3.3 70B, Llama 3.1 8B, Mixtral, Gemma 2)
- [x] Responsive overlay drawer for mobile & tablet
- [x] Document & PDF file attachment analysis
- [x] Hands-free Speech-to-Text & Text-to-Speech Voice Mode
- [x] Sidebar chat search filter & inline title rename
- [x] Conversation Markdown export (`.md`)
- [x] PWA standalone mobile/desktop installation & Service Worker
- [x] Free Cloud Deployment (Vercel + Render + Supabase)

---

## 📜 License

MIT — feel free to fork, adapt, and build upon NovaMind!

