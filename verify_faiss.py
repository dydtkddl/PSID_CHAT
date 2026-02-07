"""Verify FAISS indexes - ASCII-safe output."""
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

# Check all index sizes
faiss_root = PROJECT_ROOT / "faiss_db"
results = []
results.append("=== FAISS Index Sizes ===")
for idx_file in sorted(faiss_root.rglob("index.faiss")):
    rel = idx_file.relative_to(faiss_root).parent
    pkl = idx_file.parent / "index.pkl"
    size_mb = idx_file.stat().st_size / (1024*1024)
    results.append(f"  {str(rel):30s} | index.faiss = {size_mb:.1f} MB")

results.append("")
results.append("=== Department Search Test (combined undergrad_rules) ===")

# Load combined undergrad_rules
faiss_dir = faiss_root / "undergrad_rules"
temp_dir = tempfile.mkdtemp(prefix="faiss_v_")
try:
    shutil.copy2(str(faiss_dir / "index.faiss"), os.path.join(temp_dir, "index.faiss"))
    shutil.copy2(str(faiss_dir / "index.pkl"), os.path.join(temp_dir, "index.pkl"))
    vs = FAISS.load_local(temp_dir, embeddings=emb, allow_dangerous_deserialization=True)
    results.append(f"Total vectors: {vs.index.ntotal}")
    results.append("")
    
    # Department names and their ASCII labels
    depts = [
        ("\uc804\uc790\uacf5\ud559\uacfc", "Electronic Eng"),
        ("\ucef4\ud4e8\ud130\uacf5\ud559\uacfc", "Computer Eng"),
        ("\ud654\ud559\uacf5\ud559\uacfc", "Chemical Eng"),
        ("\uae30\uacc4\uacf5\ud559\uacfc", "Mechanical Eng"),
        ("\uc0b0\uc5c5\uacf5\ud559\uacfc", "Industrial Eng"),
        ("\uac74\ucd95\ud559\uacfc", "Architecture"),
        ("\uc18c\ud504\ud2b8\uc6e8\uc5b4\uc735\ud569\ud559\uacfc", "Software Convergence"),
    ]
    
    for dept_kr, dept_en in depts:
        docs = vs.similarity_search(dept_kr, k=5)
        found = any(dept_kr in d.page_content for d in docs)
        tag = "FOUND" if found else "MISS"
        results.append(f"  [{tag}] {dept_en:25s}")
finally:
    shutil.rmtree(temp_dir, ignore_errors=True)

# Write results as ASCII
output = "\n".join(results)
with open(PROJECT_ROOT / "verify_result.txt", "w", encoding="ascii") as f:
    f.write(output)
print(output)
