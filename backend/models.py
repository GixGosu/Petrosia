from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from database import Base
from datetime import datetime
from typing import Optional, Dict, List
from pydantic import BaseModel
import uuid


class Article(Base):
    __tablename__ = "articles"
    __table_args__ = (UniqueConstraint('slug', 'namespace', name='uq_article_slug_namespace'),)

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    created_by = Column(String(255))
    status = Column(String(50), default='published', index=True)
    namespace = Column(String(100), default='default', nullable=False, index=True)

    # Relationship to article content
    content_entries = relationship("ArticleContent", back_populates="article", cascade="all, delete-orphan")


class ArticleContent(Base):
    __tablename__ = "article_content"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    article_id = Column(PG_UUID(as_uuid=True), ForeignKey('articles.id', ondelete='CASCADE'), nullable=False)
    language = Column(String(10), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)
    embedding = Column(Vector(384))  # MiniLM dimension
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(255))

    # Relationship to article
    article = relationship("Article", back_populates="content_entries")


class ArticleVersion(Base):
    __tablename__ = "article_versions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    article_content_id = Column(PG_UUID(as_uuid=True), ForeignKey('article_content.id'))
    title = Column(String(500))
    body = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(255))


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    provider = Column(String(50))
    sources = Column(JSON)
    session_id = Column(String(255), index=True, nullable=True)
    model = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key_hash = Column(String(128), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used = Column(DateTime(timezone=True), nullable=True)
    permissions = Column(JSON, default=list)  # ["read", "write", "admin"]
    namespace = Column(String(100), default='default', index=True)
    is_active = Column(Boolean, default=True)


# Pydantic models for API
class ArticleContentSchema(BaseModel):
    language: str
    title: str
    body: str

    class Config:
        from_attributes = True


class ArticleCreate(BaseModel):
    slug: str
    content: Dict[str, Dict[str, str]]  # {"en": {"title": "...", "body": "..."}, ...}
    status: str = "published"
    created_by: Optional[str] = "system"


class ArticleUpdate(BaseModel):
    title: str
    body: str
    updated_by: Optional[str] = "system"


class ArticleResponse(BaseModel):
    id: uuid.UUID
    slug: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    content: Dict[str, Dict[str, str]]  # {"en": {"title": "...", "body": "..."}}

    class Config:
        from_attributes = True


class SearchResult(BaseModel):
    article_id: uuid.UUID
    slug: str
    language: str
    title: str
    body: str
    score: float


class ChatRequest(BaseModel):
    query: str
    language: str = "en"
    provider: Optional[str] = None
    model: Optional[str] = None
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    sources: List[SearchResult]
    provider: str


class AskRequest(BaseModel):
    query: str
    language: str = "auto"
    provider: Optional[str] = None
    model: Optional[str] = None
    session_id: Optional[str] = None

    model_config = {"json_schema_extra": {"examples": [
        {"query": "How do I reset my password?"},
        {"query": "What is your refund policy?", "provider": "claude", "model": "claude-sonnet-4-20250514"},
    ]}}


class AskResponse(BaseModel):
    answer: str
    sources: List[SearchResult]
    provider: str
    model: str
    grounded: bool
    confidence: float

    model_config = {"json_schema_extra": {"examples": [
        {
            "answer": "To reset your password, go to the login page and click 'Forgot Password'...",
            "sources": [{"article_id": "550e8400-e29b-41d4-a716-446655440000", "slug": "password-reset", "language": "en", "title": "How to Reset Your Password", "body": "...", "score": 0.82}],
            "provider": "ollama",
            "model": "qwen2.5:3b",
            "grounded": True,
            "confidence": 0.82,
        }
    ]}}


class ApiKeyCreate(BaseModel):
    name: str
    permissions: List[str] = ["read"]
    namespace: str = "default"


class ApiKeyResponse(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime
    permissions: List[str]
    namespace: str
    is_active: bool
    key: Optional[str] = None  # Only populated on creation


class BulkCreateRequest(BaseModel):
    articles: List[ArticleCreate]


class BulkCreateResponse(BaseModel):
    created: int
    failed: int
    errors: List[dict]


class SearchRequest(BaseModel):
    query: str
    language: str = "en"
    limit: int = 5


class ProviderInfo(BaseModel):
    name: str
    available: bool
    model: Optional[str] = None
