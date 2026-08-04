from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import bcrypt

Base = declarative_base()

class User(Base):
    """Registered user with hashed password — real authentication."""
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    def set_password(self, password: str):
        self.password_hash = bcrypt.hashpw(
            password.encode('utf-8'), bcrypt.gensalt()
        ).decode('utf-8')

    def check_password(self, password: str) -> bool:
        return bcrypt.checkpw(
            password.encode('utf-8'),
            self.password_hash.encode('utf-8')
        )

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat()
        }


class UserSession(Base):
    __tablename__ = 'user_sessions'
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, unique=True, nullable=False)
    user_id = Column(String, nullable=False, default="anonymous")
    status = Column(String, nullable=False, default="Active")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    histories = relationship("ConversationHistory", back_populates="session", cascade="all, delete-orphan")

class ConversationHistory(Base):
    __tablename__ = 'conversation_history'
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey('user_sessions.session_id'), nullable=False)
    user_text = Column(Text, nullable=False)
    intent = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    session = relationship("UserSession", back_populates="histories")
    bot_response = relationship("ChatbotResponse", back_populates="history", uselist=False, cascade="all, delete-orphan")
    sentiment = relationship("SentimentInfo", back_populates="history", uselist=False, cascade="all, delete-orphan")

class ChatbotResponse(Base):
    __tablename__ = 'chatbot_responses'
    id = Column(Integer, primary_key=True, autoincrement=True)
    history_id = Column(Integer, ForeignKey('conversation_history.id'), nullable=False)
    response_text = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    history = relationship("ConversationHistory", back_populates="bot_response")

class SentimentInfo(Base):
    __tablename__ = 'sentiment_information'
    id = Column(Integer, primary_key=True, autoincrement=True)
    history_id = Column(Integer, ForeignKey('conversation_history.id'), nullable=False)
    sentiment_score = Column(Float, nullable=True)
    sentiment_label = Column(String, nullable=True, default="Neutral")

    # Relationships
    history = relationship("ConversationHistory", back_populates="sentiment")
