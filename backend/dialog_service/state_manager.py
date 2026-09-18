import uuid
from datetime import datetime
import os
from sqlalchemy import create_engine, text as sqlalchemy_text
from sqlalchemy.orm import sessionmaker, scoped_session

# We must import models so Base knows about them
from models import Base, UserSession, ConversationHistory, ChatbotResponse, SentimentInfo

# ── Database URL ──────────────────────────────────────────────────────────────
SQLITE_FALLBACK = f"sqlite:///{os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'chatbot_orm.db')}"
DB_URL = os.environ.get("DATABASE_URL", SQLITE_FALLBACK)

# Supabase requires postgresql:// scheme (not postgres://)
if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)


class ConversationState:
    def __init__(self):
        engine_kwargs = {"echo": False}
        if DB_URL.startswith("postgresql"):
            engine_kwargs.update({
                "pool_pre_ping": True,
                "pool_recycle": 280,
                "pool_size": 3,
                "max_overflow": 5,
                "connect_args": {
                    "sslmode": "require",
                    "connect_timeout": 8,
                },
            })

        # create_engine is lazy — no connection is made here
        self.engine = create_engine(DB_URL, **engine_kwargs)
        self._initialized = False
        self.Session = scoped_session(sessionmaker(bind=self.engine))
        print("[DB] Engine created (no connection yet — lazy init)")

    def _ensure_initialized(self):
        """Lazy init — runs schema + migrations on first actual DB use."""
        if self._initialized:
            return
        try:
            Base.metadata.create_all(self.engine)
            self._run_migrations()
            self._initialized = True
            print("[DB] Schema ready (PostgreSQL)")
        except Exception as e:
            print(f"[DB] PostgreSQL init failed: {e} — switching to SQLite")
            self.engine = create_engine(SQLITE_FALLBACK, echo=False)
            self.Session = scoped_session(sessionmaker(bind=self.engine))
            Base.metadata.create_all(self.engine)
            self._run_migrations()
            self._initialized = True
            print("[DB] Schema ready (SQLite fallback)")

    def _run_migrations(self):
        """Safely add new columns to existing DB without data loss."""
        with self.engine.connect() as conn:
            migrations = [
                "ALTER TABLE user_sessions ADD COLUMN title VARCHAR(100) DEFAULT 'New Chat'",
                "ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1",
            ]
            for sql in migrations:
                try:
                    conn.execute(sqlalchemy_text(sql))
                    conn.commit()
                except Exception:
                    pass  # Column already exists — safe to ignore

    def create_session(self, user_id="anonymous", status="Active"):
        self._ensure_initialized()
        session_id = str(uuid.uuid4())
        db_session = self.Session()
        try:
            new_session = UserSession(
                session_id=session_id,
                user_id=user_id,
                status=status
            )
            db_session.add(new_session)
            db_session.commit()
            return session_id
        except Exception as e:
            db_session.rollback()
            raise e
        finally:
            db_session.close()

    def get_session(self, session_id):
        self._ensure_initialized()
        db_session = self.Session()
        try:
            user_session = db_session.query(UserSession).filter_by(session_id=session_id).first()
            if not user_session:
                return None
            history_list = []
            for h in user_session.histories:
                history_list.append({
                    "user": h.user_text,
                    "bot": h.bot_response.response_text if h.bot_response else "",
                    "intent": h.intent,
                    "timestamp": h.timestamp.isoformat()
                })
            return {
                "session_id": user_session.session_id,
                "created_at": user_session.created_at.isoformat(),
                "history": history_list,
                "context": {},
                "current_intent": None,
                "slots": {}
            }
        finally:
            db_session.close()

    def update_session(self, session_id, intent, entities, user_text, bot_response):
        self._ensure_initialized()
        db_session = self.Session()
        try:
            user_session = db_session.query(UserSession).filter_by(session_id=session_id).first()
            if not user_session:
                return
            new_history = ConversationHistory(
                session_id=session_id,
                user_text=user_text,
                intent=intent
            )
            db_session.add(new_history)
            db_session.flush()

            new_response = ChatbotResponse(
                history_id=new_history.id,
                response_text=bot_response
            )
            db_session.add(new_response)

            new_sentiment = SentimentInfo(
                history_id=new_history.id,
                sentiment_score=0.5,
                sentiment_label="Neutral"
            )
            db_session.add(new_sentiment)
            db_session.commit()
        except Exception as e:
            db_session.rollback()
            raise e
        finally:
            db_session.close()

    def update_status(self, session_id, status):
        self._ensure_initialized()
        db_session = self.Session()
        try:
            user_session = db_session.query(UserSession).filter_by(session_id=session_id).first()
            if user_session:
                user_session.status = status
                db_session.commit()
        finally:
            db_session.close()

    def get_slot(self, session_id, slot_name):
        return None

    def clear_session(self, session_id):
        self._ensure_initialized()
        db_session = self.Session()
        try:
            user_session = db_session.query(UserSession).filter_by(session_id=session_id).first()
            if user_session:
                db_session.delete(user_session)
                db_session.commit()
        finally:
            db_session.close()