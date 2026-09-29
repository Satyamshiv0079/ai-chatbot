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
    email = Column(String(120), nullable=True)  # Not unique — allows multiple users with no email
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
    title = Column(String(100), nullable=True, default="New Chat")
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


class Document(Base):
    """Uploaded document for RAG indexing with per-user isolation."""
    __tablename__ = 'documents'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(80), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)  # pdf, docx, txt, etc.
    file_size = Column(Integer, default=0)          # in bytes
    chunk_count = Column(Integer, default=0)
    page_count = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default="ready")    # processing, ready, error

    # Relationships
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'filename': self.filename,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'chunk_count': self.chunk_count,
            'page_count': self.page_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'status': self.status
        }


class DocumentChunk(Base):
    """Text chunks extracted from documents, embedded and stored in FAISS."""
    __tablename__ = 'document_chunks'
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey('documents.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(String(80), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    page_number = Column(Integer, default=1)
    content = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=True)

    # Relationships
    document = relationship("Document", back_populates="chunks")

    def to_dict(self):
        return {
            'id': self.id,
            'document_id': self.document_id,
            'user_id': self.user_id,
            'chunk_index': self.chunk_index,
            'page_number': self.page_number,
            'content': self.content,
            'metadata_json': self.metadata_json
        }
