"""
Rebuild ALL FAISS indexes from JSONL data in docs/ directory.
Reads every doc.jsonl file, creates embeddings, and saves FAISS indexes.

Structure:
  docs/<category>/<year>/doc.jsonl  -> faiss_db/<category>/<year>/
  docs/<category>/doc.jsonl         -> faiss_db/<category>/
"""
import os
import sys
import json
import shutil
import tempfile
from pathlib import Path
from datetime import datetime

# Setup
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

EMBEDDING_MODEL = "text-embedding-3-large"
DOCS_DIR = PROJECT_ROOT / "docs"
FAISS_DIR = PROJECT_ROOT / "faiss_db"

def load_jsonl(filepath: Path) -> list[Document]:
    """Load documents from a JSONL file."""
    docs = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                metadata = data.get("metadata", {})
                content = data.get("page_content", "")
                if content:
                    docs.append(Document(page_content=content, metadata=metadata))
            except json.JSONDecodeError as e:
                print(f"  [WARN] Line {line_num} JSON error: {e}")
    return docs

def save_faiss(docs: list[Document], output_dir: Path, embeddings):
    """Create and save FAISS index from documents."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Build FAISS index
    vs = FAISS.from_documents(docs, embeddings)
    
    # Save to temp dir first (avoid Korean path issues), then copy
    temp_dir = tempfile.mkdtemp(prefix="faiss_build_")
    try:
        vs.save_local(temp_dir)
        # Copy to final destination
        for fname in ["index.faiss", "index.pkl"]:
            src = os.path.join(temp_dir, fname)
            dst = output_dir / fname
            if os.path.exists(src):
                shutil.copy2(src, str(dst))
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def discover_jsonl_files(docs_dir: Path) -> list[tuple]:
    """
    Discover all doc.jsonl files and return (jsonl_path, category, year_or_none).
    """
    results = []
    for category_dir in sorted(docs_dir.iterdir()):
        if not category_dir.is_dir():
            continue
        category = category_dir.name
        
        # Check for direct doc.jsonl (e.g., docs/academic_system/doc.jsonl)
        direct_jsonl = category_dir / "doc.jsonl"
        if direct_jsonl.exists():
            results.append((direct_jsonl, category, None))
        
        # Check for year subdirectories (e.g., docs/undergrad_rules/2025/doc.jsonl)
        for sub in sorted(category_dir.iterdir()):
            if sub.is_dir():
                year_jsonl = sub / "doc.jsonl"
                if year_jsonl.exists():
                    results.append((year_jsonl, category, sub.name))
    
    return results

def main():
    print("=" * 70)
    print(f"FAISS Index Rebuild - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
    
    # Discover all JSONL files
    jsonl_files = discover_jsonl_files(DOCS_DIR)
    print(f"\nFound {len(jsonl_files)} JSONL files to process:\n")
    
    for jsonl_path, category, year in jsonl_files:
        label = f"{category}/{year}" if year else category
        print(f"  - {label}: {jsonl_path.relative_to(PROJECT_ROOT)}")
    
    print()
    
    # Also build combined indexes per category (all years merged)
    category_docs: dict[str, list[Document]] = {}
    
    total_docs = 0
    total_indexes = 0
    
    for jsonl_path, category, year in jsonl_files:
        label = f"{category}/{year}" if year else category
        print(f"[{label}] Loading JSONL...", end=" ", flush=True)
        
        docs = load_jsonl(jsonl_path)
        print(f"{len(docs)} documents", end=" ", flush=True)
        
        if not docs:
            print("-> SKIP (empty)")
            continue
        
        # Determine output path
        if year:
            output_dir = FAISS_DIR / category / year
        else:
            output_dir = FAISS_DIR / category
        
        print(f"-> Building index...", end=" ", flush=True)
        try:
            save_faiss(docs, output_dir, embeddings)
            total_docs += len(docs)
            total_indexes += 1
            print(f"DONE (saved to {output_dir.relative_to(PROJECT_ROOT)})")
        except Exception as e:
            print(f"ERROR: {e}")
        
        # Accumulate for combined index
        if year:
            if category not in category_docs:
                category_docs[category] = []
            category_docs[category].extend(docs)
    
    # Build combined indexes for categories with year subdivisions
    print("\n" + "-" * 70)
    print("Building combined category-level indexes (all years merged)...")
    print("-" * 70)
    
    for category, docs in category_docs.items():
        output_dir = FAISS_DIR / category
        print(f"\n[{category}] {len(docs)} total documents from all years...", end=" ", flush=True)
        try:
            save_faiss(docs, output_dir, embeddings)
            total_docs += len(docs)
            total_indexes += 1
            print(f"DONE")
        except Exception as e:
            print(f"ERROR: {e}")
    
    print("\n" + "=" * 70)
    print(f"Rebuild complete!")
    print(f"  Total indexes built: {total_indexes}")
    print(f"  Total documents embedded: {total_docs}")
    print("=" * 70)

if __name__ == "__main__":
    main()
