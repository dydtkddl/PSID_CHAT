# History router - Chat history CRUD

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from backend.models import ChatSession, ChatSessionSummary, ChatMessage
from backend import database
from datetime import datetime

router = APIRouter()

def _format_date(iso_date: str) -> str:
    """Format ISO date to relative date string"""
    try:
        dt = datetime.fromisoformat(iso_date)
        now = datetime.now()
        diff = now - dt
        
        if diff.days == 0:
            return "오늘"
        elif diff.days == 1:
            return "어제"
        elif diff.days < 7:
            return f"{diff.days}일 전"
        elif diff.days < 30:
            weeks = diff.days // 7
            return f"{weeks}주일 전"
        else:
            return dt.strftime("%Y-%m-%d")
    except:
        return iso_date

@router.get("/history", response_model=List[ChatSessionSummary])
async def get_history(member_id: str = Query(...)):
    """Get all chat sessions for a user"""
    sessions = database.get_user_history(member_id)
    return [
        ChatSessionSummary(
            id=s["id"],
            title=s.get("title", "Untitled"),
            date=_format_date(s.get("updated_at", s.get("created_at", ""))),
            preview=s.get("preview", "")[:50] + "..." if len(s.get("preview", "")) > 50 else s.get("preview", ""),
            category=s.get("category", "regulations")
        )
        for s in sessions
    ]

@router.get("/history/{session_id}")
async def get_session(session_id: str, member_id: str = Query(...)):
    """Get a specific chat session with full messages"""
    session = database.get_session(member_id, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.post("/history")
async def create_session(
    member_id: str,
    title: str,
    category: str,
    cohort: Optional[str] = None
):
    """Create a new chat session"""
    session = database.create_session(member_id, title, category, cohort)
    return session

@router.put("/history/{session_id}")
async def update_session(
    session_id: str,
    member_id: str,
    messages: List[ChatMessage],
    title: Optional[str] = None
):
    """Update a chat session with new messages"""
    messages_dict = [{"role": m.role, "content": m.content} for m in messages]
    session = database.update_session(member_id, session_id, messages_dict, title)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.delete("/history/{session_id}")
async def delete_session(session_id: str, member_id: str = Query(...)):
    """Delete a chat session"""
    success = database.delete_session(member_id, session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session deleted"}
