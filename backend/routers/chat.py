# Chat router - RAG API endpoint
# Connects to existing chains.py and query_parser.py

from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage, AIMessage
import sys
import os
import uuid

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.models import ChatRequest, ChatResponse, SourceDocument
from backend import database

router = APIRouter()

def _convert_history(history: list) -> list:
    """Convert chat history to LangChain message format"""
    messages = []
    for msg in history:
        if msg.role == "user":
            messages.append(HumanMessage(content=msg.content))
        else:
            messages.append(AIMessage(content=msg.content))
    return messages

def _decode_title(title: str) -> str:
    """디코드 hex 인코딩된 한글 파일명 및 경로 정리"""
    import os
    
    # 경로에서 파일명만 추출
    if "\\" in title or "/" in title:
        title = os.path.basename(title)
    
    # Hex 인코딩된 파일명 디코딩 (예: <312E20B1B3...>)
    if title.startswith('<') and title.endswith('>'):
        try:
            hex_str = title[1:-1]
            title = bytes.fromhex(hex_str).decode('cp949')
        except:
            pass
    
    # .pdf 확장자 제거
    if title.endswith(".pdf"):
        title = title.rsplit(".", 1)[0]
    
    return title

def _extract_sources(context_docs: list) -> list[SourceDocument]:
    """Extract source documents from RAG response"""
    sources = []
    seen = set()
    for i, doc in enumerate(context_docs[:5]):  # Limit to top 5
        meta = getattr(doc, "metadata", {}) if hasattr(doc, "metadata") else {}
        
        # Try multiple keys for title (different JSON formats use different keys)
        raw_title = (
            meta.get("document_title") or 
            meta.get("title") or 
            meta.get("sourceFile") or 
            meta.get("filename") or 
            meta.get("source") or 
            "문서"
        )
        
        # Clean up title
        title = _decode_title(raw_title)
        
        article = meta.get("articleNumber") or meta.get("article_number")
        if article:
            article_str = f"제{article}조"
        else:
            article_str = None
        
        # Deduplicate by title + content preview (same doc, different chunks are OK)
        content_key = doc.page_content[:100] if hasattr(doc, 'page_content') else ""
        dedup_key = f"{title}::{content_key[:50]}"
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        
        # Get a cleaner content preview (remove Source: prefix if present)
        content = doc.page_content
        if content.startswith("Source :"):
            content = content.split("\n", 1)[-1] if "\n" in content else content
        preview = content[:200] + "..." if len(content) > 200 else content
        
        sources.append(SourceDocument(
            id=str(i + 1),
            title=title,
            article=article_str,
            content=preview,
            relevance=round((1 - i * 0.1) * 100),  # Approximate relevance
            uri=meta.get("uri") or meta.get("articleUri")
        ))
    return sources


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Process a chat message through the RAG pipeline.
    Returns the assistant response and source documents.
    """
    try:
        # Import chains dynamically to avoid circular imports
        from chains import get_multi_year_vector_store, get_retriever_chain, get_conversational_rag
        from query_parser import parse_query
        from reranker import rerank
        
        # Parse query for metadata hints
        meta_filter, hints = parse_query(request.message)
        
        # Load vector store with cross-year fallback
        try:
            vector_store = get_multi_year_vector_store(request.category, request.cohort)
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        
        # Build retriever chain with metadata filter and year priority
        # top_k=8: reranker가 넓은 풀에서 재정렬하도록
        retriever_chain = get_retriever_chain(
            vector_store,
            meta_filter=meta_filter,
            top_k=8,
            primary_cohort=request.cohort,
        )
        
        # Build conversational RAG chain
        rag_chain = get_conversational_rag(retriever_chain)
        
        # Convert history to LangChain format
        chat_history = _convert_history(request.history or [])
        
        # Invoke the chain
        result = rag_chain.invoke({
            "input": request.message,
            "chat_history": chat_history
        })
        
        # Extract answer and sources
        answer = result.get("answer", "죄송합니다. 응답을 생성하는 데 문제가 발생했습니다.")
        context_docs = result.get("context", [])
        
        # Apply BM25+MMR reranking to context docs
        if context_docs:
            try:
                rerank_input = []
                for doc in context_docs:
                    if hasattr(doc, "page_content"):
                        rerank_input.append({
                            "page_content": doc.page_content,
                            "metadata": doc.metadata if hasattr(doc, "metadata") else {},
                            "score": 0.0,
                        })
                    elif isinstance(doc, dict):
                        rerank_input.append(doc)
                
                if rerank_input:
                    reranked = rerank(rerank_input, hints, request.message)
                    # reranked 결과에서 sources 추출
                    sources = _extract_sources(reranked)
                else:
                    sources = _extract_sources(context_docs)
            except Exception as e:
                print(f"[Reranker] Failed, falling back: {e}")
                sources = _extract_sources(context_docs)
        else:
            sources = _extract_sources(context_docs)
        
        # Generate or retrieve session ID
        session_id = str(uuid.uuid4())
        
        # Auto-save to history if member_id is provided
        if request.member_id:
            try:
                # Build messages list (including current exchange)
                all_messages = []
                for msg in (request.history or []):
                    all_messages.append({"role": msg.role, "content": msg.content})
                all_messages.append({"role": "user", "content": request.message})
                all_messages.append({"role": "assistant", "content": answer})
                
                # Check if session exists for this user, otherwise create new
                existing_sessions = database.get_user_history(request.member_id)
                
                # Try to find an active session (less than 1 hour old with same category)
                from datetime import datetime
                active_session = None
                for s in existing_sessions[:5]:  # Check only recent 5
                    if s.get("category") == request.category:
                        try:
                            updated = datetime.fromisoformat(s.get("updated_at", ""))
                            if (datetime.now() - updated).total_seconds() < 3600:  # 1 hour
                                active_session = s
                                break
                        except:
                            pass
                
                if active_session:
                    # Update existing session
                    database.update_session(
                        request.member_id, 
                        active_session["id"], 
                        all_messages
                    )
                    session_id = active_session["id"]
                else:
                    # Create new session with title from first message
                    title = request.message[:30] + "..." if len(request.message) > 30 else request.message
                    new_session = database.create_session(
                        request.member_id,
                        title,
                        request.category,
                        request.cohort
                    )
                    database.update_session(
                        request.member_id,
                        new_session["id"],
                        all_messages
                    )
                    session_id = new_session["id"]
            except Exception as e:
                # Log error but don't fail the request
                print(f"[History] Failed to save: {e}")
        
        return ChatResponse(
            answer=answer,
            sources=sources,
            session_id=session_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"RAG pipeline error: {str(e)}")
