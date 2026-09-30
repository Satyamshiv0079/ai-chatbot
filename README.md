# NovaMind AI — Production RAG & Multi-Model GenAI Platform

A production-grade GenAI SaaS platform combining multi-turn conversational AI with Retrieval-Augmented Generation (RAG) over user documents (PDF, DOCX, TXT). Powered by isolated FAISS vector stores, HuggingFace SentenceTransformers (`all-MiniLM-L6-v2`), LangChain orchestration, and active Groq LLM inference with automated fallback routing.

🌐 **Live Production App**: [https://ai-chatbot-km3hk7gvd-satyamshiv0079s-projects.vercel.app](https://ai-chatbot-km3hk7gvd-satyamshiv0079s-projects.vercel.app/)

⚡ **Backend API**: [https://ai-chatbot-w1x8.onrender.com](https://ai-chatbot-w1x8.onrender.com)

> Built by **Satyam**.

---

## 📸 Screenshots

| Modern GenAI Landing Page | Conversational Interface & RAG Mode | Accessible Auth & Password Controls |
|:---:|:---:|:---:|
| ![NovaMind Landing Page](docs/screenshots/landing-page.png) | ![Conversational Workspace](docs/screenshots/chat-interface.png) | ![Accessible Login](docs/screenshots/login-page.png) |

---

## 🏗️ Architecture & Dual-Mode Engine

The platform operates in two distinct, production-engineered operational modes:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 React 3D Spatial UI                                    │
│                    [ Mode A: General AI ]  |  [ Mode B: Ask My Documents (RAG) ]       │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ JWT Bearer Auth (Token verified per request)
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                Flask REST API Gateway                                  │
│                 Routes: /chat, /session/*, /api/documents/*, /api/rag/query            │
└───────────────────────┬────────────────────────────────────────┬───────────────────────┘
                        │                                        │
           [ Mode A: General AI Chat ]              [ Mode B: RAG Document Q&A ]
                        │                                        │
                        ▼                                        ▼
             BERT Intent Predictor                     Document Ingestion & Parser
           (HuggingFace Transformers)                  (PDF: pypdf, DOCX: docx, TXT)
                        │                                        │
                        ▼                                        ▼
             Conversation State Manager               RecursiveCharacterTextSplitter
             (Supabase PostgreSQL / SQLite)           (Chunk size: 800, Overlap: 120)
                        │                                        │
                        ▼                                        ▼
                 Groq LLM Engine                       SentenceTransformer Embedder
             - openai/gpt-oss-20b (Fast)               ('all-MiniLM-L6-v2' 384-d dense)
             - openai/gpt-oss-120b                               │
             - qwen/qwen3.8-27b                                  ▼
             - groq/compound-mini                     FAISS User-Isolated Vector Index
             (Automatic failover routing)             (backend/vector_stores/<user_id>/)
                        │                                        │
                        │                              Similarity Search (Cosine)
                        │                                        │
                        │                                        ▼
                        │                             Strict Grounded Context Prompt
                        │                             (Grounded Refusal Guardrails)
                        │                                        │
                        └───────────────────────┬────────────────┘
                                                │
                                                ▼
                                    Groq LLM Generation
                                                │
                                                ▼
                         Grounded Response + Collapsible Source Citations
                         (Document Name, Page Number, Match %, Snippet)
```

### 1. Mode A: General AI Chat
- Multi-turn contextual conversation memory.
- Fine-tuned BERT intent prediction (`nlp_service`) for customer-service slot filling and intent tagging.
- Dynamic model switcher supporting active Groq models with seamless fallback resilience.

### 2. Mode B: Ask My Documents (RAG)
- **Document Ingestion**: Supports `.pdf`, `.docx`, and `.txt` with per-page text extraction.
- **Semantic Chunking**: LangChain recursive text splitter with 800 character chunk size and 120 character overlap to maintain context across chunk boundaries.
- **Dense Vector Embeddings**: SentenceTransformer (`all-MiniLM-L6-v2`) generating 384-dimensional normalized vectors running locally on CPU.
- **Isolated Vector Storage**: Per-user FAISS `IndexFlatIP` indices partitioned at `backend/vector_stores/<user_id>/`. Strict multi-tenant isolation guarantees strong cross-user data isolation.
- **Strict Grounded Answering**: Prompt constraints enforce that answers are derived strictly from retrieved context. If information is not in the documents, the model responds: *"I couldn't find this information in the provided documents."*
- **Verifiable Source Citations**: Responses return structured source metadata rendered as interactive badges in the UI displaying document name, page number, similarity percentage, and preview snippet.

### 🔄 Runtime RAG Pipeline Flow

```mermaid
flowchart TD
    A["User Question"] --> B["JWT Authentication"]
    B --> C["User ID Extracted"]
    C --> D["SentenceTransformer (all-MiniLM-L6-v2)<br/>(query embedding: 384 dimensions)"]
    D --> E["FAISS Vector Store (backend/vector_stores/&lt;user_id&gt;/)<br/>(cosine similarity search, top-k chunks)"]
    E --> F["LangChain Document Objects (LCDocument)<br/>(page_content + metadata: doc_name, page, chunk_idx)"]
    F --> G["LangChain BaseRetriever (UserScopedRetriever)<br/>(retrieves relevant documents for user)"]
    G --> H["LangChain ChatPromptTemplate<br/>(strict context injection + grounded retrieval rules)"]
    H --> I["LangChain ChatGroq LLM<br/>(with RunnableWithFallbacks: gpt-oss-20b → gpt-oss-120b → qwen3.8-27b)"]
    I --> J["LangChain StrOutputParser<br/>(clean string output)"]
    J --> K["Response + Structured Sources<br/>(doc name, page number, similarity %, snippet)"]
    K --> L["React UI (Ask My Documents Mode)"]
```

---

## 💡 Architectural Decisions & Technical Q&A

### Why embeddings?
Large Language Models process tokens, but cannot perform real-time, low-latency similarity searches across thousands of unstructured document passages. Embeddings convert text into dense mathematical vectors where semantically similar phrases are located close to each other in high-dimensional vector space. This allows the system to retrieve passages based on conceptual meaning (e.g., matching "leave policy" with "vacation entitlement") rather than brittle keyword matching.

### Why chunking?
Full documents (PDFs, DOCXs, TXTs) easily exceed context window budgets and introduce extraneous noise that degrades LLM attention. Chunking divides documents into focused, retrievable semantic passages (800 characters with 120 character overlap). The overlap ensures that context, numbers, and sentences spanning boundary breaks are never severed, preserving semantic completeness during retrieval.

### Why FAISS?
Facebook AI Similarity Search (FAISS) is an industry-standard, high-performance C++ vector search library. Using `faiss.IndexFlatIP` (Inner Product on normalized embeddings) gives exact cosine similarity matching with microsecond search latency. It runs completely in-process on CPU without needing external managed vector databases (reducing infrastructure cost and network latency to zero), while easily persisting per-user index directories (`backend/vector_stores/<user_id>/`) for strict multi-tenant isolation.

### Why LangChain?
LangChain provides standard composable primitives for production GenAI architectures. In this application, LangChain is deeply integrated across the runtime pipeline:
1. Custom `UserScopedRetriever` subclasses `BaseRetriever` to decouple retrieval from model generation.
2. Retrieved chunks are normalized into standard LangChain `Document` objects containing rich metadata.
3. `ChatPromptTemplate` enforces rigorous system prompts and grounded refusal guardrails.
4. `ChatGroq` is composed with `.with_fallbacks()` into a resilient LangChain Expression Language (LCEL) sequence (`prompt | llm | StrOutputParser()`).

### Why Sentence Transformers?
`all-MiniLM-L6-v2` is a specialized bi-encoder fine-tuned for semantic search. It projects text into a compact 384-dimensional dense vector space with exceptional balance between speed and retrieval accuracy. It runs entirely on local CPU via PyTorch in single-digit milliseconds, eliminating recurring embedding API billing and third-party network failure points.

### Why BERT? (for intent classification, NOT RAG embeddings!)
BERT (`bert-base-uncased`) is a bidirectional transformer encoder fine-tuned in `nlp_service` specifically for sequence classification and entity slot extraction (e.g., greeting, tracking orders, cancellations, refunds) in conversational Mode A. **BERT is NOT used for RAG vector embeddings.** BERT produces token-level contextual representations that require pooling layers and is not contrastively trained for sentence similarity, whereas `SentenceTransformers` (`all-MiniLM-L6-v2`) is explicitly trained using contrastive loss (Cosine Similarity Loss) to generate dense document embeddings for semantic search.

### Why Groq?
Groq's custom Language Processing Units (LPUs) provide near-instantaneous inference speeds (hundreds of tokens per second) for state-of-the-art open models like `openai/gpt-oss-20b`, `openai/gpt-oss-120b`, and `qwen/qwen3.8-27b`. Because RAG already requires document retrieval before generation, Groq's high token throughput keeps total user wait time well under 1-2 seconds, creating a truly responsive conversational experience.

---

## ⚡ Render Memory Optimization

The application is engineered to operate stably within constrained memory environments (such as Render's 512 MB free tier) by employing targeted resource management strategies:

* **Lazy Loading for Transformers**: Both BERT (`NLPPredictor`) and SentenceTransformer (`all-MiniLM-L6-v2`) models utilize lazy on-demand loading rather than loading at application boot time. This keeps initial boot memory at ~60MB (well below Render's 512MB limit) and prevents startup out-of-memory restarts.
* **Batched Embedding Generation**: Chunks are processed in small, bounded batches (16 chunks) using single-threaded PyTorch execution (`torch.set_num_threads(1)`) to avoid CPU thread contention and memory allocation spikes.
* **Memory-Safe FAISS Indexing**: Vector additions and deletions rebuild incrementally in batches of 16 rather than holding full document datasets in memory simultaneously.
* **Bounded Document Processing**: Document uploads enforce configurable guardrails (`MAX_UPLOAD_SIZE_MB`, `MAX_DOCUMENT_PAGES`, and `MAX_DOCUMENT_CHUNKS`) to reject oversized files before parsing.
* **Single Gunicorn Worker & Port Dynamic Binding**: Configured with `--workers 1 --threads 2 --timeout 120` and dynamic host binding `0.0.0.0:$PORT` in `gunicorn.conf.py` to avoid 503 hibernate-wake-errors and eliminate memory duplication across multiple worker processes.
* **Controlled Garbage Collection & Deserialization Safety**: Vector metadata is stored in human-readable `chunks.json` rather than binary pickles, eliminating arbitrary code execution risks. Temporary batch arrays and text buffers are explicitly unreferenced (`del`) and collected via `gc.collect()`.

---

## 🔒 Security & Data Isolation Architecture

* **Tenant Vector Store Isolation**: Every user's embeddings are stored strictly in their own dedicated directory (`backend/vector_stores/<user_id>/index.faiss` and `chunks.json`). Similarity searches query solely against the authenticated user's index.
* **Dashboard Data Isolation**: SQL queries for session counts, message statistics, intent distributions, and recent activity are strictly scoped to `UserSession.user_id == username`. Cross-tenant data leakage is completely prevented.
* **IDOR Protection on Chat Sessions**: When submitting a message to `/chat` with a `session_id`, the backend validates session ownership against the JWT identity before processing, rejecting unauthorized session tampering with HTTP 403 Forbidden.
* **Rate Limiting**: Sliding-window in-memory rate limiter protects `/auth/register` (10 req/min), `/auth/login` (10 req/min), `/chat` (30 req/min), and `/api/documents/upload` (10 req/min). Configurable via `RATE_LIMIT_ENABLED`.
* **JWT Token Security & Expiration**: Eliminates permanent tokens by enforcing `JWT_ACCESS_TOKEN_EXPIRES` (default: 2 hours). In production environments, missing or default `JWT_SECRET_KEY` triggers an immediate runtime exception at boot.
* **Prompt Injection Defense**: Grounded RAG prompts treat document contents as untrusted context, enforcing explicit instructions to ignore injected system commands and answer strictly from verified facts.

---

## 🚀 Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | React 19, Lucide Icons, ReactMarkdown, Prism Syntax Highlighter, Web Speech API (STT/TTS), Recharts |
| **Backend API** | Python 3.12, Flask 3.1, Flask-JWT-Extended, Flask-CORS, Gunicorn |
| **RAG & NLP** | LangChain, FAISS (`faiss-cpu`), SentenceTransformers, PyTorch, pypdf, python-docx, BERT |
| **Database & ORM** | SQLAlchemy 2.0, Supabase Cloud PostgreSQL with automatic SQLite fallback |
| **LLM Inference** | Groq API (`openai/gpt-oss-20b`, `openai/gpt-oss-120b`, `qwen/qwen3.8-27b`, `groq/compound-mini`) |
| **PWA & Mobile** | Service Worker (`sw.js`), Web App Manifest, responsive desktop & mobile drawer |

---

## 🔌 API Endpoints

### Authentication & Sessions
| Method | Endpoint | Auth | Description |
|---|---|:---:|---|
| `POST` | `/auth/register` | ❌ (Rate limited: 10/min) | Create new user account (bcrypt password hashing) |
| `POST` | `/auth/login` | ❌ (Rate limited: 10/min) | Authenticate user and return JWT access token (2h expiry) |
| `GET`  | `/auth/me` | ✅ | Get profile of authenticated user |
| `POST` | `/session/new` | ✅ | Initialize new chat session |
| `GET` | `/sessions` | ✅ | Fetch all past sessions for logged-in user (isolated) |
| `GET` | `/sessions/<id>` | ✅ | Load complete message history for user session |
| `PATCH` | `/sessions/<id>/rename` | ✅ | Rename chat session title |
| `DELETE` | `/sessions/<id>` | ✅ | Delete session and associated messages |
| `GET` | `/models` | ✅ | List active, validated Groq AI models |

### Mode A: Conversational Chat
| Method | Endpoint | Auth | Description |
|---|---|:---:|---|
| `POST` | `/chat` | ✅ (Rate limited: 30/min) | Multi-turn conversational prompt with BERT intent classification & IDOR validation |

### Mode B: RAG & Document Management
| Method | Endpoint | Auth | Description |
|---|---|:---:|---|
| `POST` | `/api/documents/upload` | ✅ (Rate limited: 10/min) | Upload PDF/DOCX/TXT; extracts, chunks, embeds (batch size 16), and indexes into user FAISS index |
| `GET` | `/api/documents` | ✅ | List all user documents with page counts and chunk counts |
| `DELETE` | `/api/documents/<id>` | ✅ | Delete document, remove file, and safely rebuild user's FAISS index |
| `POST` | `/api/rag/query` | ✅ (Rate limited: 30/min) | Grounded RAG query against user's vector store; returns answer + source citations |

### Analytics Dashboard
| Method | Endpoint | Auth | Description |
|---|---|:---:|---|
| `GET` | `/api/dashboard/stats` | ✅ | User-isolated metrics: sessions, messages, documents, intent distribution, and recent activity |

### 🌐 Frontend Routes
| Route | Access | Description |
|---|:---:|---|
| `/` | Public | Modern GenAI SaaS landing page featuring product preview, pipeline, and tech stack |
| `/login` | Public | Accessible sign-in with password toggle, keyboard navigation, and automatic wake-up retry |
| `/signup` | Public | Registration with accessible password strength meter |
| `/chat` | Authenticated | Dual-mode AI workspace (Mode A: General AI Chat, Mode B: Ask My Documents RAG) |
| `/dashboard` | Authenticated | System analytics overview and user-isolated intent distribution |

---

## 💻 Local Setup & Development

### Prerequisites
- Python 3.10+ (tested on Python 3.12)
- Node.js 18+
- Free [Groq API Key](https://console.groq.com)

### 1. Backend Setup

```bash
cd backend

# Create & activate virtual environment
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment variables (.env)
cp .env.example .env
# Edit .env with your GROQ_API_KEY and JWT_SECRET_KEY

# Run automated tests
pytest tests/ -v

# Start Flask API server
python api/app.py
```

### 2. Frontend Setup

```bash
cd frontend/chatbot-ui

# Install dependencies
npm install

# Start development server
npm start
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🧪 Automated Testing Suite

The project includes 33 passing automated tests covering RAG, security, and API integrity:

```bash
# Run all tests
pytest backend/tests/ -v

# Run RAG test suite (document processing, FAISS isolation, grounded generation)
pytest backend/tests/test_rag.py -v

# Run API test suite (JWT protection, chat, sessions, conversational flows)
pytest backend/tests/test_api.py -v

# Run Security & Optimization suite (Dashboard isolation, IDOR, Rate limiting, Token expiry)
pytest backend/tests/test_security_and_optimizations.py -v
```

---

## 💬 Interview Discussion Points & Architectural Trade-offs

1. **Why FAISS `IndexFlatIP` vs. Managed Vector Databases (e.g., Pinecone/pgvector)?**
   - *Design rationale*: `IndexFlatIP` performs exact inner product search over normalized embeddings (equivalent to exact cosine similarity) without requiring quantization loss or an external hosted vector DB. Per-user directory isolation (`backend/vector_stores/<user_id>/`) guarantees zero cross-tenant leakage with near-zero cold-start latency.
2. **How was the 512MB RAM limitation on Render resolved?**
   - *Design rationale*: Eager loading both BERT (~440MB) and SentenceTransformers (~150MB) during application boot exceeded Render's 512MB threshold immediately. By implementing lazy property loading, setting single-threaded PyTorch execution (`torch.set_num_threads(1)`), streaming document embedding in batches of 16, and configuring Gunicorn with 1 worker and 2 threads (`gunicorn.conf.py`), initial boot memory was reduced to ~60MB.
3. **In-Memory Rate Limiting vs. Redis**:
   - *Design rationale*: A sliding-window thread-safe in-memory rate limiter provides immediate denial-of-service protection with zero external infrastructure overhead on single-instance web services, while remaining toggleable via `RATE_LIMIT_ENABLED` for automated CI/CD pipelines.

---

## 📜 License

MIT License. Built by Satyam.
