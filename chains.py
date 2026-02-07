# chains.py - RAG Pipeline for KHU Regulation Assistant
# Updated for langchain 1.2.x API

from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.messages import BaseMessage

# RAG 시스템 프롬프트
SYSTEM_PROMPT = (
    f"오늘 날짜: {datetime.now().strftime('%Y-%m-%d')}\n"
    "당신은 경희대학교 규정 전문 가상 어시스턴트입니다.\n\n"
    
    "## 핵심 역할\n"
    "- 제공된 문서(Context)를 **꼼꼼히 읽고** 사용자 질문에 **구체적으로** 답변하세요.\n"
    "- 문서에 있는 조항, 금액, 조건, 절차 등의 **세부 정보**를 포함하여 답변하세요.\n"
    "- 단순히 '~합니다'로 끝내지 말고, **왜/어떻게/얼마나**를 설명하세요.\n\n"
    
    "## 우선순위 규칙\n"
    "1) 여러 버전이 있으면 **가장 최신** versionDate를 우선합니다.\n"
    "2) 사용자의 의도(학부/대학원, 입학년도, 조항)에 맞는 문서를 우선합니다.\n"
    "3) effectiveFrom/effectiveUntil이 충돌하면 명시적으로 알려주세요.\n"
    "4) 질문한 학과의 정보가 문서에 없더라도, 관련 있는 **공통 규정**(졸업학점, 교양 요건 등)이 있으면 해당 내용을 답변하세요.\n"
    "   단, '해당 학과의 개별 시행세칙은 현재 데이터베이스에 포함되어 있지 않습니다'라고 명시하세요.\n"
    "5) 문서에서 아무런 관련 정보를 찾을 수 없으면 '현재 데이터베이스에 해당 정보가 없습니다. 학과 사무실이나 경희대학교 포탈(https://portal.khu.ac.kr)에서 확인해 주세요.'라고 안내하세요.\n\n"
    
    "## 출력 규칙\n"
    "- 조항, URI, 내용을 **절대 만들어내지 마세요**.\n"
    "- 모르는 값은 '-'로 표시하세요.\n"
    "- Source: <파일명> 으로 시작하는 문서 내용을 참고하세요.\n\n"
    
    "## 제공된 규정 문서:\n"
)

# 구조화 섹션 템플릿
ANSWER_FORMAT = """
📌 **요약**
[핵심 결론 2~3문장]

📋 **상세 내용**
[구체적인 조건, 금액, 절차, 기준 등을 불릿 포인트로]

📎 **근거 조항**
[실제 조문 번호와 제목 기재, 예: 제5조(전공이수학점), 제10조(졸업논문)]
- 출처: [문서명]

⚠️ **참고사항** (해당 시에만)
[예외 조건, 주의할 점]
"""


# 프로젝트 루트 디렉토리 (chains.py가 위치한 곳)
PROJECT_ROOT = Path(__file__).resolve().parent


def get_vector_store(category_slug: str, cohort: Optional[str] = None) -> FAISS:
    """
    카테고리(+코호트)별 FAISS 로드
    - 규정/학사제도: cohort=None → faiss_db/<category>/
    - 학부/대학원 시행세칙: cohort='2020' 등 → faiss_db/<category>/<cohort>/
    
    Note: Windows에서 한글 경로 문제를 우회하기 위해 임시 디렉토리에 복사 후 로드합니다.
    cohort 경로가 없으면 카테고리 기본 인덱스로 fallback합니다.
    """
    import os
    import shutil
    import tempfile
    
    base = PROJECT_ROOT / "faiss_db" / category_slug
    
    # cohort 경로 우선 시도, 없으면 기본 카테고리로 fallback
    if cohort:
        cohort_base = base / str(cohort)
        if (cohort_base / "index.faiss").exists():
            base = cohort_base
        # else: use category base (fallback)
    
    index_path = base / "index.faiss"
    pkl_path = base / "index.pkl"
    
    if not index_path.exists():
        raise FileNotFoundError(f"FAISS index not found for: {category_slug}")
    
    # 한글 경로 문제 우회: ASCII 경로 임시 디렉토리에 복사 후 로드
    temp_dir = tempfile.mkdtemp(prefix="faiss_")
    try:
        # FAISS 파일들을 임시 디렉토리로 복사
        shutil.copy2(str(index_path), os.path.join(temp_dir, "index.faiss"))
        if pkl_path.exists():
            shutil.copy2(str(pkl_path), os.path.join(temp_dir, "index.pkl"))
        
        # 임시 디렉토리에서 로드
        result = FAISS.load_local(
            temp_dir,
            embeddings=OpenAIEmbeddings(model="text-embedding-3-large"),
            allow_dangerous_deserialization=True,
        )
        return result
    finally:
        # 임시 디렉토리 정리
        shutil.rmtree(temp_dir, ignore_errors=True)


def get_multi_year_vector_store(
    category_slug: str,
    primary_cohort: Optional[str] = None,
    max_fallback: int = 3,
) -> FAISS:
    """
    Cross-year fallback retrieval.
    primary_cohort (예: "2025") 인덱스를 로드하고,
    인접 연도의 인덱스를 merge하여 검색 범위를 확장합니다.

    전략:
      1) primary_cohort 인덱스 로드
      2) 인접 연도(최신 → 과거)를 최대 max_fallback개까지 병합
      3) 각 문서 metadata에 '_cohort_year' 태그 추가

    cohort가 None이면 카테고리 통합 인덱스를 반환합니다.
    """
    if not primary_cohort:
        return get_vector_store(category_slug, None)

    import re
    base_dir = PROJECT_ROOT / "faiss_db" / category_slug

    # 사용 가능한 연도 목록 스캔
    available_years = sorted(
        [
            d.name
            for d in base_dir.iterdir()
            if d.is_dir()
            and re.match(r"^\d{4}$", d.name)
            and (d / "index.faiss").exists()
        ],
        reverse=True,  # 최신순
    )

    if not available_years:
        # 연도 디렉토리가 없으면 카테고리 통합 인덱스 사용
        return get_vector_store(category_slug, None)

    # primary 연도 인덱스 로드
    primary_year = str(primary_cohort)
    try:
        merged_vs = get_vector_store(category_slug, primary_year)
        # primary 문서에 연도 태그 추가
        _tag_cohort_year(merged_vs, primary_year)
    except FileNotFoundError:
        merged_vs = None

    # 인접 연도 선택: primary보다 가까운 연도 순서 (최신 우선)
    fallback_years = [
        y for y in available_years
        if y != primary_year
    ]
    # 가까운 연도 순 정렬 (primary와의 차이 절대값 기준)
    try:
        primary_int = int(primary_year)
        fallback_years.sort(key=lambda y: abs(int(y) - primary_int))
    except ValueError:
        pass

    # 최대 max_fallback개 병합
    merged_count = 0
    for year in fallback_years:
        if merged_count >= max_fallback:
            break
        try:
            fallback_vs = get_vector_store(category_slug, year)
            _tag_cohort_year(fallback_vs, year)
            if merged_vs is None:
                merged_vs = fallback_vs
            else:
                merged_vs.merge_from(fallback_vs)
            merged_count += 1
        except FileNotFoundError:
            continue

    if merged_vs is None:
        return get_vector_store(category_slug, None)

    return merged_vs


def _tag_cohort_year(vs: FAISS, year: str) -> None:
    """FAISS vector store의 모든 문서 metadata에 _cohort_year 태그 추가."""
    try:
        for doc_id in vs.docstore._dict:
            doc = vs.docstore._dict[doc_id]
            if hasattr(doc, "metadata"):
                doc.metadata["_cohort_year"] = year
    except Exception:
        pass  # 태그 실패해도 검색에는 영향 없음


def format_docs(docs: List) -> str:
    """Format retrieved documents into context string"""
    parts = []
    for doc in docs:
        src = doc.metadata.get("source", doc.metadata.get("filename", "알 수 없음"))
        year_tag = doc.metadata.get("_cohort_year", "")
        year_prefix = f"[{year_tag}년도] " if year_tag else ""
        parts.append(f"Source: {year_prefix}{src}\n{doc.page_content}")
    return "\n\n---\n\n".join(parts)


def get_retriever_chain(
    vector_store: FAISS,
    meta_filter: Optional[Dict[str, Any]] = None,
    top_k: int = 5,
    primary_cohort: Optional[str] = None,
):
    """
    Hybrid retriever: semantic search + keyword boosting.
    학과명 등 핵심 키워드가 포함된 문서를 반드시 결과에 포함시킴.
    """
    import re as _re
    
    # 더 많이 검색 후 필터링
    fetch_k = top_k * 5
    skw = {"k": fetch_k}
    if meta_filter:
        skw["filter"] = {k: v for k, v in meta_filter.items() if v not in (None, "", [])}
    
    base_retriever = vector_store.as_retriever(search_kwargs=skw)
    
    # 알려진 학과명 패턴 (키워드 추출용)
    DEPT_PATTERNS = [
        "전자공학과", "컴퓨터공학과", "컴퓨터공학부", "화학공학과", "기계공학과",
        "산업경영공학과", "원자력공학과", "건축공학과", "건축학과",
        "사회기반시스템공학과", "환경학및환경공학과", "신소재공학과",
        "정보전자신소재공학과", "소프트웨어융합학과", "인공지능학과",
        "생체의공학과", "반도체공학과", "전자정보공학부",
        "응용수학과", "응용물리학과", "응용화학과", "우주과학과",
        "식품생명공학과", "유전생명공학과", "원예생명공학과",
        "한방생명공학과", "스마트팜과학과",
        "융합바이오", "국제학과", "아시아학과",
    ]
    
    # 약어 매핑
    DEPT_ALIASES = {
        "전자과": "전자공학과", "전공과": "전자공학과", "전자": "전자공학과",
        "컴공과": "컴퓨터공학과", "컴공": "컴퓨터공학과", "컴퓨터": "컴퓨터공학과",
        "화공과": "화학공학과", "화공": "화학공학과",
        "기공과": "기계공학과", "기계": "기계공학과",
        "산공과": "산업경영공학과", "산공": "산업경영공학과",
        "원자력": "원자력공학과",
        "건축": "건축공학과",
        "환경": "환경학및환경공학과",
        "소융": "소프트웨어융합학과", "소프트웨어": "소프트웨어융합학과",
        "반도체": "반도체공학과",
        "인공지능": "인공지능학과", "AI": "인공지능학과",
        "생의공": "생체의공학과",
        "신소재": "신소재공학과",
    }
    
    def _extract_dept_keywords(query: str) -> List[str]:
        """쿼리에서 학과명 키워드 추출"""
        keywords = []
        # 정식 학과명 매칭
        for dept in DEPT_PATTERNS:
            if dept in query:
                keywords.append(dept)
        # 약어 매칭
        for alias, full_name in DEPT_ALIASES.items():
            if alias in query and full_name not in keywords:
                keywords.append(full_name)
        return keywords
    
    def _keyword_search(keywords: List[str], max_results: int = 10) -> List:
        """FAISS docstore에서 키워드 포함 문서 직접 검색"""
        results = []
        seen_ids = set()
        try:
            for doc_id, doc in vector_store.docstore._dict.items():
                if doc_id in seen_ids:
                    continue
                content = getattr(doc, "page_content", "")
                for kw in keywords:
                    if kw in content:
                        results.append(doc)
                        seen_ids.add(doc_id)
                        break
                if len(results) >= max_results:
                    break
        except Exception:
            pass
        return results
    
    class HybridRetriever:
        def __init__(self, retriever, final_k, target_year=None):
            self.retriever = retriever
            self.final_k = final_k
            self.target_year = target_year
        
        def _score_korean(self, content: str) -> float:
            if not content:
                return 0
            korean_chars = sum(1 for c in content if '\uac00' <= c <= '\ud7a3')
            total_chars = len(content.replace(" ", "").replace("\n", ""))
            return korean_chars / max(total_chars, 1)
        
        def _score_year(self, doc) -> float:
            if not self.target_year:
                return 0.5
            doc_year = doc.metadata.get("_cohort_year", "")
            if not doc_year:
                return 0.3
            try:
                diff = abs(int(doc_year) - int(self.target_year))
                return max(0, 1.0 - diff * 0.2)
            except (ValueError, TypeError):
                return 0.3
        
        def invoke(self, query: str) -> List:
            # 1) Semantic search
            semantic_docs = self.retriever.invoke(query)
            
            # 2) Keyword search for department names
            dept_keywords = _extract_dept_keywords(query)
            keyword_docs = _keyword_search(dept_keywords, max_results=10) if dept_keywords else []
            
            # 3) Merge: keyword docs first, then semantic (deduplicate)
            seen_content = set()
            all_docs = []
            
            # Add keyword-matched docs with boost flag
            for doc in keyword_docs:
                content_key = doc.page_content[:200]
                if content_key not in seen_content:
                    seen_content.add(content_key)
                    all_docs.append((doc, True))  # True = keyword match
            
            # Add semantic docs
            for doc in semantic_docs:
                content_key = doc.page_content[:200]
                if content_key not in seen_content:
                    seen_content.add(content_key)
                    all_docs.append((doc, False))
            
            # 4) Score and rank
            scored = []
            for i, (doc, is_keyword_match) in enumerate(all_docs):
                korean_score = self._score_korean(doc.page_content[:500])
                year_score = self._score_year(doc)
                rank_bonus = 1 - (i / max(len(all_docs), 1)) * 0.15
                
                # 키워드 매칭 문서에 큰 boost
                keyword_boost = 0.5 if is_keyword_match else 0.0
                
                # 학과명이 content에 직접 포함되는지 추가 확인
                content_match = 0.0
                if dept_keywords:
                    for kw in dept_keywords:
                        if kw in doc.page_content:
                            content_match = 0.3
                            break
                
                final_score = (
                    korean_score * 0.25
                    + year_score * 0.20
                    + rank_bonus * 0.10
                    + keyword_boost
                    + content_match
                )
                scored.append((final_score, doc))
            
            scored.sort(key=lambda x: x[0], reverse=True)
            return [doc for _, doc in scored[:self.final_k]]
        
        def get_relevant_documents(self, query: str) -> List:
            return self.invoke(query)
    
    return HybridRetriever(base_retriever, top_k, primary_cohort)


# 오타 호환
get_retreiver_chain = get_retriever_chain


def get_conversational_rag(retriever):
    """
    End-to-end Conversational RAG chain using modern LCEL
    """
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    # Query Rewriting Prompt for context-aware search
    query_rewrite_prompt = ChatPromptTemplate.from_messages([
        ("system", 
         "당신은 대화 맥락을 이해하여 검색 쿼리를 재작성하는 어시스턴트입니다.\n\n"
         "## 역할\n"
         "사용자의 최신 질문이 이전 대화를 참조하는 경우, 대화 맥락을 파악하여 "
         "**독립적이고 완전한 검색 쿼리**로 재작성하세요.\n\n"
         "## 예시\n"
         "대화: '화학공학과 졸업요건 알려줘' -> '나는 4학년인데 뭘 들어야해?' -> '아니 과목말야'\n"
         "재작성: '경희대학교 화학공학과 4학년 전공 과목 목록'\n\n"
         "대화: '장학금 신청 방법' -> '언제까지야?'\n"
         "재작성: '장학금 신청 마감일 기한'\n\n"
         "## 규칙\n"
         "1. 질문이 이미 완전하면 그대로 반환\n"
         "2. 대화에서 언급된 학과, 학년, 주제 등을 포함\n"
         "3. 검색에 최적화된 키워드 형태로 작성\n"
         "4. 한국어로 작성"
        ),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("user", "현재 질문: {input}\n\n검색에 사용할 재작성된 쿼리:")
    ])
    
    query_rewriter = query_rewrite_prompt | llm | StrOutputParser()
    
    # Build the chain using LCEL
    def retrieve_and_format(inputs: dict):
        """Retrieve documents and format them with context-aware query rewriting"""
        original_query = inputs.get("input", "")
        chat_history = inputs.get("chat_history", [])
        
        # Rewrite query if there's conversation history
        if chat_history and len(chat_history) > 0:
            try:
                rewritten_query = query_rewriter.invoke({
                    "input": original_query,
                    "chat_history": chat_history
                })
                search_query = rewritten_query.strip()
            except Exception:
                search_query = original_query
        else:
            search_query = original_query
        
        docs = retriever.invoke(search_query)
        return {
            **inputs,
            "context": format_docs(docs),
            "_retrieved_docs": docs  # Keep for later extraction
        }
    
    # RAG prompt for answer generation
    rag_prompt = ChatPromptTemplate.from_messages([
        ("system", 
         SYSTEM_PROMPT
         + "\n\n{context}\n\n"
         "위 문서를 바탕으로 사용자 질문에 **상세하게** 답변하세요.\n\n"
         "답변 작성 시 주의사항:\n"
         "1. 문서에 있는 **구체적인 수치, 조건, 절차**를 포함하세요.\n"
         "2. 단순히 '~합니다'로 끝내지 말고 **세부 내용**을 설명하세요.\n"
         "3. 여러 조항이 관련되면 모두 언급하세요.\n"
         "4. 반드시 **한국어**로 답변하세요.\n\n"
         "다음 형식으로 답변하세요:\n"
         + ANSWER_FORMAT
        ),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("user", "{input}")
    ])
    
    # Chain that retrieves, formats, and generates
    chain = (
        RunnableLambda(retrieve_and_format)
        | RunnablePassthrough.assign(
            answer=rag_prompt | llm | StrOutputParser()
        )
    )
    
    # Wrap to return context docs as well
    def invoke_with_context(inputs: dict):
        result = chain.invoke(inputs)
        return {
            "answer": result.get("answer", ""),
            "context": result.get("_retrieved_docs", []),
            "input": inputs.get("input", "")
        }
    
    return RunnableLambda(invoke_with_context)
