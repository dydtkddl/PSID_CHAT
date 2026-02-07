"""
Rebuild FAISS indexes using smart-chunked documents.
====================================================
1) smart_chunker.py로 모든 JSONL 재청킹 → docs_v2/
2) 재청킹된 JSONL로 FAISS 인덱스 리빌드 → faiss_db/
"""
import os
import sys
import json
import shutil
import tempfile
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

# Load API key
secrets_path = PROJECT_ROOT / ".streamlit" / "secrets.toml"
if secrets_path.exists():
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib
    with open(secrets_path, "rb") as f:
        secrets = tomllib.load(f)
        if "OPENAI_API_KEY" in secrets:
            os.environ["OPENAI_API_KEY"] = secrets["OPENAI_API_KEY"]

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from smart_chunker import rechunk_jsonl

EMBEDDING_MODEL = "text-embedding-3-large"
DOCS_DIR = PROJECT_ROOT / "docs"
DOCS_V2_DIR = PROJECT_ROOT / "docs_v2"
FAISS_DIR = PROJECT_ROOT / "faiss_db"


def save_faiss(docs: list, output_dir: Path, embeddings):
    """FAISS 인덱스 빌드 + 저장 (한글 경로 우회)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    vs = FAISS.from_documents(docs, embeddings)

    temp_dir = tempfile.mkdtemp(prefix="faiss_build_")
    try:
        vs.save_local(temp_dir)
        for fname in ["index.faiss", "index.pkl"]:
            src = os.path.join(temp_dir, fname)
            dst = output_dir / fname
            if os.path.exists(src):
                shutil.copy2(src, str(dst))
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    return len(docs)


def load_rechunked_jsonl(filepath: Path) -> list:
    """docs_v2 JSONL → LangChain Document 리스트"""
    docs = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                content = data.get("page_content", "")
                meta = data.get("metadata", {})
                if content and len(content) > 30:
                    docs.append(Document(page_content=content, metadata=meta))
            except json.JSONDecodeError:
                continue
    return docs


def discover_jsonl_files(docs_dir: Path):
    """모든 doc.jsonl 파일 발견 → (path, category, year_or_None)"""
    results = []
    for cat_dir in sorted(docs_dir.iterdir()):
        if not cat_dir.is_dir():
            continue
        category = cat_dir.name
        direct = cat_dir / "doc.jsonl"
        if direct.exists():
            results.append((direct, category, None))
        for sub in sorted(cat_dir.iterdir()):
            if sub.is_dir():
                year_jsonl = sub / "doc.jsonl"
                if year_jsonl.exists():
                    results.append((year_jsonl, category, sub.name))
    return results


def main():
    print("=" * 70)
    print(f"Smart Rechunk + FAISS Rebuild — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Phase 1: 재청킹
    print("\n[Phase 1] Smart re-chunking all JSONL files...\n")

    jsonl_files = discover_jsonl_files(DOCS_DIR)
    print(f"Found {len(jsonl_files)} JSONL files\n")

    all_stats = {}
    for jsonl_path, category, year in jsonl_files:
        label = f"{category}/{year}" if year else category

        if year:
            out_path = DOCS_V2_DIR / category / year / "doc.jsonl"
        else:
            out_path = DOCS_V2_DIR / category / "doc.jsonl"

        print(f"  [{label}] ", end="", flush=True)
        stats = rechunk_jsonl(jsonl_path, out_path)
        print(f"{stats['original_count']} → {stats['new_count']} docs "
              f"(avg {stats['original_avg_len']:.0f} → {stats['new_avg_len']:.0f} chars)")
        all_stats[label] = stats

    # Phase 2: FAISS 리빌드
    print("\n" + "=" * 70)
    print("[Phase 2] Building FAISS indexes from re-chunked data...\n")

    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
    v2_files = discover_jsonl_files(DOCS_V2_DIR)

    total_docs = 0
    total_indexes = 0
    category_docs = {}  # 카테고리별 통합 인덱스용

    for jsonl_path, category, year in v2_files:
        label = f"{category}/{year}" if year else category
        docs = load_rechunked_jsonl(jsonl_path)

        if not docs:
            print(f"  [{label}] SKIP (empty)")
            continue

        out_dir = FAISS_DIR / category / year if year else FAISS_DIR / category
        print(f"  [{label}] {len(docs)} docs → ", end="", flush=True)

        try:
            n = save_faiss(docs, out_dir, embeddings)
            total_docs += n
            total_indexes += 1
            print(f"DONE")
        except Exception as e:
            print(f"ERROR: {e}")

        if year:
            category_docs.setdefault(category, []).extend(docs)

    # 카테고리별 통합 인덱스
    print("\n  Building combined category indexes...")
    for category, docs in category_docs.items():
        out_dir = FAISS_DIR / category
        print(f"  [{category}] {len(docs)} total → ", end="", flush=True)
        try:
            n = save_faiss(docs, out_dir, embeddings)
            total_docs += n
            total_indexes += 1
            print(f"DONE")
        except Exception as e:
            print(f"ERROR: {e}")

    # Summary
    print("\n" + "=" * 70)
    print(f"Complete!")
    print(f"  Indexes built: {total_indexes}")
    print(f"  Total vectors: {total_docs}")

    # Before/After comparison
    print("\n  Before/After comparison:")
    for label, stats in all_stats.items():
        print(f"    {label}: {stats['original_count']} → {stats['new_count']} chunks")
    print("=" * 70)


if __name__ == "__main__":
    main()
