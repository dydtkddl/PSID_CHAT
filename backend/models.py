# Pydantic models for API request/response

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# ─────────────────────────────────────────────────────────────
# Chat Models
# ─────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    category: str  # "regulations", "undergrad_rules", "grad_rules", "academic_system"
    cohort: Optional[str] = None  # "2020", "2021", etc.
    history: Optional[List[ChatMessage]] = []
    member_id: Optional[str] = None  # Make optional for frontend API calls

class SourceDocument(BaseModel):
    id: str
    title: str
    article: Optional[str] = None
    content: str
    relevance: Optional[float] = None
    uri: Optional[str] = None

class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceDocument]
    session_id: str

# ─────────────────────────────────────────────────────────────
# History Models
# ─────────────────────────────────────────────────────────────

class ChatSessionCreate(BaseModel):
    member_id: str
    title: str
    category: str
    cohort: Optional[str] = None
    messages: List[ChatMessage]

class ChatSession(BaseModel):
    id: str
    member_id: str
    title: str
    category: str
    cohort: Optional[str] = None
    messages: List[ChatMessage]
    created_at: datetime
    updated_at: datetime
    preview: str

class ChatSessionSummary(BaseModel):
    id: str
    title: str
    date: str
    preview: str
    category: str

# ─────────────────────────────────────────────────────────────
# Bookmark Models
# ─────────────────────────────────────────────────────────────

class BookmarkCreate(BaseModel):
    member_id: str
    title: str
    article: Optional[str] = None
    uri: Optional[str] = None
    category: str

class Bookmark(BaseModel):
    id: str
    member_id: str
    title: str
    article: Optional[str] = None
    uri: Optional[str] = None
    category: str
    created_at: datetime
