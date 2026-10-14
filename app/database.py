import os
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import String, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

def uid():
    return str(uuid4())

def now():
    return datetime.now(timezone.utc).isoformat()

class Base(DeclarativeBase):
    pass

class Conversation(Base):
    __tablename__ = 'conversations'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    token_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[str] = mapped_column(default=now)
    status: Mapped[str] = mapped_column(default='open')
    interest: Mapped[str] = mapped_column(default='exploring')
    summary: Mapped[str] = mapped_column(Text, default='New visitor')

class Message(Base):
    __tablename__ = 'messages'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    conversation_id: Mapped[str] = mapped_column(ForeignKey('conversations.id'), index=True)
    role: Mapped[str]
    text: Mapped[str] = mapped_column(Text)
    sources: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[str] = mapped_column(default=now)

class Lead(Base):
    __tablename__ = 'leads'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    conversation_id: Mapped[str] = mapped_column(ForeignKey('conversations.id'), unique=True)
    name: Mapped[str]
    company: Mapped[str]
    email: Mapped[str]
    phone: Mapped[str]
    category: Mapped[str]
    buyers: Mapped[str]
    experience: Mapped[str]
    callback: Mapped[str]
    consent: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[str] = mapped_column(default=now)

class Ticket(Base):
    __tablename__ = 'tickets'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    conversation_id: Mapped[str] = mapped_column(ForeignKey('conversations.id'), unique=True)
    reason: Mapped[str]
    status: Mapped[str] = mapped_column(default='pending')
    created_at: Mapped[str] = mapped_column(default=now)

class Document(Base):
    __tablename__ = 'documents'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    title: Mapped[str]
    text: Mapped[str] = mapped_column(Text)
    source: Mapped[str]
    version: Mapped[str] = mapped_column(default='1')
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    confidential: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[str] = mapped_column(default=now)

class Unanswered(Base):
    __tablename__ = 'unanswered'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    conversation_id: Mapped[str] = mapped_column(ForeignKey('conversations.id'))
    question: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(default=now)

engine = create_async_engine(os.getenv('DATABASE_URL', 'sqlite+aiosqlite:///./sales.db'))
Session = async_sessionmaker(engine, expire_on_commit=False)
