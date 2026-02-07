"""Detailed verification: what does the search actually return?"""
import os, shutil, tempfile
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib

PROJECT_ROOT = Path(__file__).parent.resolve()
secrets_path = PROJECT_ROOT / ".streamlit" / "secrets.toml"
with open(secrets_path, "rb") as f:
    secrets = tomllib.load(f)
    os.environ["OPENAI_API_KEY"] = secrets["OPENAI_API_KEY"]

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

emb = OpenAIEmbeddings(model="text-embedding-3-large")
faiss_dir = PROJECT_ROOT / "faiss_db" / "undergrad_rules"

temp_dir = tempfile.mkdtemp(prefix="faiss_v2_")
try:
    shutil.copy2(str(faiss_dir / "index.faiss"), os.path.join(temp_dir, "index.faiss"))
    shutil.copy2(str(faiss_dir / "index.pkl"), os.path.join(temp_dir, "index.pkl"))
    vs = FAISS.load_local(temp_dir, embeddings=emb, allow_dangerous_deserialization=True)

    results = []    
    results.append(f"Total vectors: {vs.index.ntotal}")
    results.append("")
    
    # Detailed search for each department
    depts = [
        ("\uc804\uc790\uacf5\ud559\uacfc", "Electronic Eng"),
        ("\ucef4\ud4e8\ud130\uacf5\ud559\uacfc", "Computer Eng"),
        ("\ud654\ud559\uacf5\ud559\uacfc", "Chemical Eng"),
    ]
    
    for dept_kr, dept_en in depts:
        docs = vs.similarity_search(dept_kr, k=5)
        results.append(f"=== {dept_en} ===")
        for i, d in enumerate(docs):
            src = d.metadata.get("source", "?")
            found = dept_kr in d.page_content
            tag = "Y" if found else "N"
            # Get first 200 chars, ASCII-safe
            preview = d.page_content[:200].replace("\n", " ")
            preview_ascii = preview.encode("ascii", "replace").decode("ascii")
            results.append(f"  [{i+1}][{tag}] src={src}")
            results.append(f"       {preview_ascii}")
        results.append("")
    
    # Also count how many docs contain each dept name 
    results.append("=== Raw text search (grep in all docs) ===")
    for dept_kr, dept_en in depts:
        count = 0
        # Search through all stored docs
        all_docs = vs.similarity_search("", k=vs.index.ntotal) if vs.index.ntotal < 5000 else []
        # Instead just grep the JSONL files
        import json
        doc_count = 0
        for jsonl_path in (PROJECT_ROOT / "docs" / "undergrad_rules").rglob("doc.jsonl"):
            with open(jsonl_path, "r", encoding="utf-8") as f:
                for line in f:
                    if dept_kr in line:
                        doc_count += 1
        results.append(f"  {dept_en}: {doc_count} lines in JSONL files contain department name")
    
    output = "\n".join(results)
    with open(PROJECT_ROOT / "verify_detail.txt", "w", encoding="ascii", errors="replace") as f:
        f.write(output)
    print("Done. Results in verify_detail.txt")

finally:
    shutil.rmtree(temp_dir, ignore_errors=True)
