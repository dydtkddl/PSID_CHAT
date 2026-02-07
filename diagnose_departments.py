"""학과별 문서 존재 여부 진단"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load API key
secrets_path = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")
if os.path.exists(secrets_path):
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib
    with open(secrets_path, "rb") as f:
        secrets = tomllib.load(f)
        if "OPENAI_API_KEY" in secrets:
            os.environ["OPENAI_API_KEY"] = secrets["OPENAI_API_KEY"]

from chains import get_vector_store, get_retriever_chain

vs = get_vector_store("undergrad_rules", "2025")

# 1) 전체 문서 소스 파일 목록
print("=" * 60)
print("FAISS DB 내 문서 소스 파일 목록")
print("=" * 60)
docstore = vs.docstore
all_docs = list(docstore._dict.values())
sources = set()
for doc in all_docs:
    src = doc.metadata.get("source", "unknown")
    sources.add(src)
for s in sorted(sources):
    count = sum(1 for d in all_docs if d.metadata.get("source") == s)
    print(f"  [{count:3d} chunks] {s}")

# 2) 학과별 검색 테스트
print("\n" + "=" * 60)
print("학과별 검색 테스트 (raw FAISS, top 3)")
print("=" * 60)
queries = [
    "전자공학과 졸업요건",
    "컴퓨터공학과 졸업요건", 
    "화학공학과 졸업요건",
    "기계공학과 졸업요건",
    "신소재공학과 졸업요건",
]

for q in queries:
    print(f"\n>> Query: {q}")
    docs = vs.similarity_search(q, k=3)
    for i, doc in enumerate(docs):
        content_preview = doc.page_content[:150].replace('\n', ' ')
        has_dept = q.split(" ")[0] in doc.page_content
        marker = "FOUND" if has_dept else "MISS"
        print(f"  [{i+1}] [{marker}] {content_preview}...")
