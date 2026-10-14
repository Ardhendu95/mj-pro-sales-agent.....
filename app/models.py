from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, JSON, Integer, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from pgvector.sqlalchemy import Vector
from .settings import DATABASE_URL

def uid(): return str(uuid4())
def utcnow(): return datetime.now(timezone.utc)

class Base(DeclarativeBase): pass
class Record:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class Conversation(Record, Base):
    __tablename__ = 'demo_conversations'
    token_hash: Mapped[str] = mapped_column(String(64))
    interest: Mapped[str] = mapped_column(default='exploring')
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    qualification: Mapped[dict] = mapped_column(JSON, default=dict)
    summary: Mapped[str] = mapped_column(Text, default='No callback requested yet.')
    summary_kind: Mapped[str] = mapped_column(default='pending')
    summary_sources: Mapped[list] = mapped_column(JSON, default=list)

class Message(Record, Base):
    __tablename__ = 'demo_messages'
    conversation_id: Mapped[str] = mapped_column(ForeignKey('demo_conversations.id'), index=True)
    role: Mapped[str]
    text: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    request_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    __table_args__ = (UniqueConstraint('conversation_id', 'role', 'request_id'),)

class Lead(Record, Base):
    __tablename__ = 'demo_leads'
    conversation_id: Mapped[str] = mapped_column(ForeignKey('demo_conversations.id'), unique=True)
    details: Mapped[dict] = mapped_column(JSON)
    consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    consent_text: Mapped[str] = mapped_column(Text)
    submission_id: Mapped[str] = mapped_column(String(36), unique=True)

class Ticket(Record, Base):
    __tablename__ = 'demo_tickets'
    conversation_id: Mapped[str] = mapped_column(ForeignKey('demo_conversations.id'), unique=True)
    status: Mapped[str] = mapped_column(default='pending')
    reason: Mapped[str] = mapped_column(default='Visitor requested a callback')

class Document(Record, Base):
    __tablename__ = 'demo_documents'
    family: Mapped[str] = mapped_column(String(36), index=True, default=uid)
    version: Mapped[int] = mapped_column(Integer, default=1)
    title: Mapped[str]
    text: Mapped[str] = mapped_column(Text)
    source: Mapped[str]
    effective_date: Mapped[str]
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    confidential: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    indexing_status: Mapped[str] = mapped_column(default='not_indexed')
    index_generation: Mapped[str] = mapped_column(default='')
    __table_args__ = (UniqueConstraint('family', 'version'),)

class Chunk(Record, Base):
    __tablename__ = 'demo_chunks'
    document_id: Mapped[str] = mapped_column(ForeignKey('demo_documents.id'), index=True)
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list] = mapped_column(Vector(768).with_variant(JSON(), 'sqlite'))
    generation: Mapped[str] = mapped_column(index=True)
    model: Mapped[str]

class Plan(Record, Base):
    __tablename__ = 'demo_plans'
    name: Mapped[str]
    amount_minor: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(default='INR')
    months: Mapped[int] = mapped_column(Integer)
    source: Mapped[str]
    effective_date: Mapped[str]
    tax_note: Mapped[str] = mapped_column(default='Tax treatment is not specified in the public FAQ.')
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class Audit(Record, Base):
    __tablename__ = 'demo_audit'
    document_id: Mapped[str] = mapped_column(ForeignKey('demo_documents.id'), index=True)
    action: Mapped[str]
    details: Mapped[dict] = mapped_column(JSON, default=dict)

class Usage(Record, Base):
    __tablename__ = 'demo_usage'
    kind: Mapped[str]
    model: Mapped[str]
    tokens: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str]

class Unanswered(Record, Base):
    __tablename__ = 'demo_unanswered'
    conversation_id: Mapped[str] = mapped_column(ForeignKey('demo_conversations.id'), index=True)
    question: Mapped[str] = mapped_column(Text)

class AdminSession(Record, Base):
    __tablename__ = 'demo_admin_sessions'
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

engine = create_async_engine(DATABASE_URL)
Session = async_sessionmaker(engine, expire_on_commit=False)
