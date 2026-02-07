#!/usr/bin/env python
"""
rebuild_faiss.py - docs/ 폴더의 JSONL 파일을 기반으로 FAISS 인덱스 재구축 (원본 보존)
"""

import os
import sys
import json
import math
from pathlib import Path
from typing import List, Optional

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
try:
    from langchain.schema import Document as LCDocument
except Exception:
    from langchain_core.documents import Document as LCDocument

# 경로 설정
BASE = Path(__file__).parent
DOCS_BASE = BASE / "docs"
FAISS_BASE = BASE / "faiss_db"

CATEGORIES = ["regulations", "academic_system", "grad_rules", "undergrad_rules"]


def load_jsonl(path: Path) -> List[LCDocument]:
    """JSONL 파일을 LangChain Document 리스트로 로드"""
    docs = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    # LangChain serialized format 처리
                    if "page_content" in obj:
                        content = obj["page_content"]
                        metadata = obj.get("metadata", {})
                    elif "text" in obj:
                        content = obj["text"]
                        metadata = obj.get("metadata", {})
                    else:
                        continue
                    
                    docs.append(LCDocument(page_content=content, metadata=metadata))
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"  Warning: {path} 로드 실패: {e}")
    return docs


def build_index(docs: List[LCDocument], emb, batch_size: int = 32) -> Optional[FAISS]:
    """문서 리스트로 FAISS 인덱스 구축"""
    if not docs:
        return None
    
    total = len(docs)
    num_batches = math.ceil(total / batch_size)
    vs = None
    
    for bi in range(num_batches):
        start = bi * batch_size
        end = min((bi + 1) * batch_size, total)
        batch = docs[start:end]
        print(f"  배치 {bi+1}/{num_batches} ({len(batch)}개 문서)")
        
        if vs is None:
            vs = FAISS.from_documents(batch, embedding=emb)
        else:
            vs.add_documents(batch)
    
    return vs


def rebuild_category(category: str, emb) -> int:
    """단일 카테고리 인덱스 재구축"""
    import tempfile
    import shutil
    
    docs_dir = DOCS_BASE / category
    faiss_dir = FAISS_BASE / category
    
    if not docs_dir.exists():
        print(f"[{category}] 폴더 없음: {docs_dir}")
        return 0
    
    # 모든 jsonl 파일 수집
    jsonl_files = list(docs_dir.rglob("*.jsonl"))
    json_files = list(docs_dir.rglob("*.json"))
    all_files = jsonl_files + json_files
    
    if not all_files:
        print(f"[{category}] JSONL/JSON 파일 없음")
        return 0
    
    print(f"\n[{category}] {len(all_files)}개 파일 발견")
    
    # 모든 문서 로드
    all_docs = []
    for fpath in sorted(all_files):
        rel = fpath.relative_to(docs_dir)
        docs = load_jsonl(fpath)
        if docs:
            print(f"  {rel}: {len(docs)}개 청크")
            all_docs.extend(docs)
    
    if not all_docs:
        print(f"[{category}] 로드된 문서 없음")
        return 0
    
    print(f"[{category}] 총 {len(all_docs)}개 문서 인덱싱 시작...")
    
    # 인덱스 구축
    vs = build_index(all_docs, emb, batch_size=32)
    
    if vs is None:
        print(f"[{category}] 인덱스 생성 실패")
        return 0
    
    # 한글 경로 우회: 임시 디렉토리에 저장 후 복사
    faiss_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = tempfile.mkdtemp(prefix=f"faiss_{category}_")
    try:
        # 임시 디렉토리에 저장
        vs.save_local(temp_dir)
        
        # 타겟으로 복사
        for fname in ["index.faiss", "index.pkl"]:
            src = os.path.join(temp_dir, fname)
            dst = str(faiss_dir / fname)
            if os.path.exists(src):
                shutil.copy2(src, dst)
        
        print(f"[{category}] 저장 완료: {faiss_dir}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    return len(all_docs)


def main():
    print("=" * 60)
    print("FAISS 인덱스 재구축 시작")
    print("=" * 60)
    
    emb = OpenAIEmbeddings(model="text-embedding-3-large")
    
    total_docs = 0
    for cat in CATEGORIES:
        count = rebuild_category(cat, emb)
        total_docs += count
    
    print("\n" + "=" * 60)
    print(f"완료! 총 {total_docs}개 문서 인덱싱")
    print("=" * 60)


if __name__ == "__main__":
    main()
