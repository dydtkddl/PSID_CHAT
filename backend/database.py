# Simple JSON file-based database for history and bookmarks
# Can be replaced with SQLite or other DB later

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict
import uuid

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

HISTORY_FILE = DATA_DIR / "history.json"
BOOKMARKS_FILE = DATA_DIR / "bookmarks.json"

def _load_json(filepath: Path) -> Dict:
    if not filepath.exists():
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_json(filepath: Path, data: Dict):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

# ─────────────────────────────────────────────────────────────
# History CRUD
# ─────────────────────────────────────────────────────────────

def get_user_history(member_id: str) -> List[Dict]:
    """Get all chat sessions for a user"""
    data = _load_json(HISTORY_FILE)
    user_sessions = data.get(member_id, [])
    return sorted(user_sessions, key=lambda x: x.get("updated_at", ""), reverse=True)

def get_session(member_id: str, session_id: str) -> Optional[Dict]:
    """Get a specific chat session"""
    sessions = get_user_history(member_id)
    for session in sessions:
        if session.get("id") == session_id:
            return session
    return None

def create_session(member_id: str, title: str, category: str, cohort: Optional[str] = None) -> Dict:
    """Create a new chat session"""
    data = _load_json(HISTORY_FILE)
    if member_id not in data:
        data[member_id] = []
    
    now = datetime.now().isoformat()
    session = {
        "id": str(uuid.uuid4()),
        "member_id": member_id,
        "title": title,
        "category": category,
        "cohort": cohort,
        "messages": [],
        "created_at": now,
        "updated_at": now,
        "preview": ""
    }
    data[member_id].insert(0, session)
    _save_json(HISTORY_FILE, data)
    return session

def update_session(member_id: str, session_id: str, messages: List[Dict], title: Optional[str] = None) -> Optional[Dict]:
    """Update a chat session with new messages"""
    data = _load_json(HISTORY_FILE)
    if member_id not in data:
        return None
    
    for session in data[member_id]:
        if session.get("id") == session_id:
            session["messages"] = messages
            session["updated_at"] = datetime.now().isoformat()
            if title:
                session["title"] = title
            # Update preview from last user message
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    session["preview"] = msg.get("content", "")[:50] + "..."
                    break
            _save_json(HISTORY_FILE, data)
            return session
    return None

def delete_session(member_id: str, session_id: str) -> bool:
    """Delete a chat session"""
    data = _load_json(HISTORY_FILE)
    if member_id not in data:
        return False
    
    original_len = len(data[member_id])
    data[member_id] = [s for s in data[member_id] if s.get("id") != session_id]
    if len(data[member_id]) < original_len:
        _save_json(HISTORY_FILE, data)
        return True
    return False

# ─────────────────────────────────────────────────────────────
# Bookmarks CRUD
# ─────────────────────────────────────────────────────────────

def get_user_bookmarks(member_id: str) -> List[Dict]:
    """Get all bookmarks for a user"""
    data = _load_json(BOOKMARKS_FILE)
    return data.get(member_id, [])

def add_bookmark(member_id: str, title: str, article: Optional[str], uri: Optional[str], category: str) -> Dict:
    """Add a new bookmark"""
    data = _load_json(BOOKMARKS_FILE)
    if member_id not in data:
        data[member_id] = []
    
    bookmark = {
        "id": str(uuid.uuid4()),
        "member_id": member_id,
        "title": title,
        "article": article,
        "uri": uri,
        "category": category,
        "created_at": datetime.now().isoformat()
    }
    data[member_id].append(bookmark)
    _save_json(BOOKMARKS_FILE, data)
    return bookmark

def delete_bookmark(member_id: str, bookmark_id: str) -> bool:
    """Delete a bookmark"""
    data = _load_json(BOOKMARKS_FILE)
    if member_id not in data:
        return False
    
    original_len = len(data[member_id])
    data[member_id] = [b for b in data[member_id] if b.get("id") != bookmark_id]
    if len(data[member_id]) < original_len:
        _save_json(BOOKMARKS_FILE, data)
        return True
    return False
