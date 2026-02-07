#!/usr/bin/env python3
"""
컴퓨터공학과 검색 품질 진단 스크립트
실제 FAISS에서 어떤 문서가 검색되는지 확인
"""

import os
import sys
from pathlib import Path

# API 키 로드
try:
    import tomllib
except ImportError:
    import tomli as tomllib

secrets_path = Path(__file__).parent / ".streamlit" / "secrets.toml"
if secrets_path.exists():
    with open(secrets_path, "rb") as f:
        secrets = tomllib.load(f)
    os.environ.setdefault("OPENAI_API_KEY", secrets.get("OPENAI_API_KEY", ""))

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from chains import get_multi_year_vector_store, get_retriever_chain
from query_parser import parse_query


def diagnose_search(query: str, category: str = "undergrad_rules", cohort: str = "2025"):
    """특정 쿼리에 대한 검색 결과 진단"""
    print("=" * 80)
    print(f"🔍 진단: '{query}'")
    print(f"   카테고리: {category}, 코호트: {cohort}")
    print("=" * 80)
    
    # 1. 쿼리 파싱 결과
    print("\n[1] Query Parser 결과:")
    meta_filter, hints = parse_query(query)
    print(f"  Meta Filter: {meta_filter}")
    print(f"  Routing Hints: {hints}")
    
    # 2. Vector Store 로드
    print(f"\n[2] Vector Store 로드 중...")
    try:
        vs = get_multi_year_vector_store(category, cohort)
        print(f"  ✅ 로드 성공! 총 벡터 수: {vs.index.ntotal}")
    except Exception as e:
        print(f"  ❌ 로드 실패: {e}")
        return
    
    # 3. 직접 벡터 검색 (시맨틱 서치)
    print(f"\n[3] 벡터 검색 (Semantic Search) - Top 10:")
    semantic_docs = vs.similarity_search(query, k=10)
    for i, doc in enumerate(semantic_docs, 1):
        meta = doc.metadata
        dept = extract_dept_from_content(doc.page_content)
        year = meta.get("_cohort_year", "?")
        source = meta.get("sourceFile", meta.get("source", "?"))
        preview = doc.page_content[:150].replace("\n", " ")
        
        print(f"\n  [{i}] 연도:{year} | 학과:{dept} | 출처:{source}")
        print(f"      내용: {preview}...")
    
    # 4. Retriever Chain 검색 (Hybrid)
    print(f"\n[4] Retriever Chain (Hybrid) - Top 5:")
    retriever = get_retriever_chain(vs, meta_filter=meta_filter, top_k=5, primary_cohort=cohort)
    hybrid_docs = retriever.invoke(query)
    for i, doc in enumerate(hybrid_docs, 1):
        meta = doc.metadata
        dept = extract_dept_from_content(doc.page_content)
        year = meta.get("_cohort_year", "?")
        source = meta.get("sourceFile", meta.get("source", "?"))
        preview = doc.page_content[:150].replace("\n", " ")
        
        print(f"\n  [{i}] 연도:{year} | 학과:{dept} | 출처:{source}")
        print(f"      내용: {preview}...")
    
    # 5. 키워드 직접 검색
    print(f"\n[5] 키워드 직접 검색 ('컴퓨터공학' 포함 문서):")
    keyword_matches = []
    try:
        for doc_id, doc in vs.docstore._dict.items():
            if "컴퓨터공학" in doc.page_content:
                keyword_matches.append(doc)
                if len(keyword_matches) >= 10:
                    break
    except Exception as e:
        print(f"  ❌ 키워드 검색 실패: {e}")
        keyword_matches = []
    
    print(f"  총 {len(keyword_matches)}개 발견")
    for i, doc in enumerate(keyword_matches[:5], 1):
        meta = doc.metadata
        year = meta.get("_cohort_year", "?")
        source = meta.get("sourceFile", meta.get("source", "?"))
        preview = doc.page_content[:150].replace("\n", " ")
        
        print(f"\n  [{i}] 연도:{year} | 출처:{source}")
        print(f"      내용: {preview}...")
    
    # 6. 인덱스 통계
    print(f"\n[6] 인덱스 통계:")
    dept_stats = analyze_department_coverage(vs)
    print(f"  총 문서 수: {vs.index.ntotal}")
    print(f"  학과별 문서 수:")
    for dept, count in sorted(dept_stats.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"    {dept}: {count}개")


def extract_dept_from_content(content: str) -> str:
    """문서 내용에서 학과명 추출"""
    depts = [
        "컴퓨터공학과", "전자공학과", "화학공학과", "기계공학과",
        "산업경영공학과", "건축학과", "소프트웨어융합학과",
        "전자정보공학부", "공과대학", "전자정보대학"
    ]
    for dept in depts:
        if dept in content:
            return dept
    return "-"


def analyze_department_coverage(vs: FAISS) -> dict:
    """인덱스 내 학과별 문서 커버리지 분석"""
    dept_counts = {}
    try:
        for doc_id, doc in vs.docstore._dict.items():
            dept = extract_dept_from_content(doc.page_content)
            if dept != "-":
                dept_counts[dept] = dept_counts.get(dept, 0) + 1
    except Exception:
        pass
    return dept_counts


if __name__ == "__main__":
    # 테스트 쿼리들
    queries = [
        "컴퓨터공학과 졸업요건 알려줘",
        "전자공학과 졸업요건",
        "전자정보대학 졸업학점",
    ]
    
    for query in queries:
        diagnose_search(query)
        print("\n\n")
