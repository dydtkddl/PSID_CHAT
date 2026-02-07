# Bookmarks router - Bookmark CRUD

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from backend.models import Bookmark, BookmarkCreate
from backend import database

router = APIRouter()

@router.get("/bookmarks", response_model=List[Bookmark])
async def get_bookmarks(member_id: str = Query(...)):
    """Get all bookmarks for a user"""
    bookmarks = database.get_user_bookmarks(member_id)
    return bookmarks

@router.post("/bookmarks", response_model=Bookmark)
async def create_bookmark(bookmark: BookmarkCreate):
    """Add a new bookmark"""
    result = database.add_bookmark(
        member_id=bookmark.member_id,
        title=bookmark.title,
        article=bookmark.article,
        uri=bookmark.uri,
        category=bookmark.category
    )
    return result

@router.delete("/bookmarks/{bookmark_id}")
async def delete_bookmark(bookmark_id: str, member_id: str = Query(...)):
    """Delete a bookmark"""
    success = database.delete_bookmark(member_id, bookmark_id)
    if not success:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return {"message": "Bookmark deleted"}
