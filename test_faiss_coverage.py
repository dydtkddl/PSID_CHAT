"""Test FAISS index coverage after rebuild."""
import os, sys, shutil, tempfile
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

# Load via temp dir (Korean path workaround)
temp_dir = tempfile.mkdtemp(prefix="faiss_test_")
try:
    shutil.copy2(str(faiss_dir / "index.faiss"), os.path.join(temp_dir, "index.faiss"))
    shutil.copy2(str(faiss_dir / "index.pkl"), os.path.join(temp_dir, "index.pkl"))
    vs = FAISS.load_local(temp_dir, embeddings=emb, allow_dangerous_deserialization=True)
    
    results = []
    results.append(f"Total vectors in combined undergrad_rules: {vs.index.ntotal}")
    results.append("")
    
    departments = [
        "전자공학과",
        "컴퓨터공학과",
        "화학공학과",
        "기계공학과",
        "산업공학과",
        "건축학과",
        "소프트웨어융합학과",
        "정보전자신소재공학과",
    ]
    
    for dept in departments:
        docs = vs.similarity_search(dept, k=5)
        found = any(dept in d.page_content for d in docs)
        src = docs[0].metadata.get("source", "?") if docs else "none"
        tag = "FOUND" if found else "MISS"
        results.append(f"[{tag}] {dept} (top source: {src})")
    
    # Write results
    output_path = PROJECT_ROOT / "faiss_test_result.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(results))
    
    print("Test complete. Results saved to faiss_test_result.txt")
    
finally:
    shutil.rmtree(temp_dir, ignore_errors=True)
